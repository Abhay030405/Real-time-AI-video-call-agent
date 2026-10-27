"""The AI judge (V0_07 section 6).

Rules it follows: a model from another family than M1; one question per call; reason first,
score second; written score descriptions (`instructions/*.md`); pinned model and instruction
versions, so a change to either means calibration is redone; calibrated against the founder's own
scores before its scores are used.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from livekit.agents import llm

from settings import Settings
from vendors.judge import build_judge

INSTRUCTIONS = Path(__file__).resolve().parent / "instructions"
QUESTIONS = ("tone", "responds", "sounds_like_vaani", "meets_standard", "fact_kept")
SCORED = {"tone", "sounds_like_vaani"}  # 1 to 5; the others are pass or fail


@dataclass(frozen=True)
class JudgeAnswer:
    question: str
    reasoning: str
    score: float | None  # 1 to 5 for scored questions
    passed: bool | None  # for pass or fail questions
    cost_usd_tokens: tuple[int, int]  # prompt and completion tokens
    seconds: float


class JudgeError(Exception):
    """The judge did not return a usable answer."""


def instructions_version() -> str:
    """A fingerprint of every instruction file. If it changes, calibration is redone."""
    digest = hashlib.sha256()
    for name in sorted(QUESTIONS):
        digest.update((INSTRUCTIONS / f"{name}.md").read_bytes())
    return "sha256:" + digest.hexdigest()[:16]


def parse_answer(question: str, text: str) -> tuple[str, float | None, bool | None]:
    """Read the judge's JSON. Raises JudgeError if it is not a valid answer."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match is None:
        raise JudgeError(f"no JSON in the judge's answer: {text[:120]!r}")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as error:
        raise JudgeError(f"the judge's JSON is invalid: {text[:120]!r}") from error
    reasoning = str(data.get("reasoning", "")).strip()
    if question in SCORED:
        score = data.get("score")
        if not isinstance(score, int | float) or not 1 <= score <= 5:
            raise JudgeError(f"the score must be 1 to 5, got {score!r}")
        return reasoning, float(score), None
    verdict = str(data.get("verdict", "")).strip().lower()
    if verdict not in ("pass", "fail"):
        raise JudgeError(f"the verdict must be pass or fail, got {verdict!r}")
    return reasoning, None, verdict == "pass"


def format_case(
    skill: str,
    history: list[list[str]],
    user: str,
    reply: str,
    standard: str | None = None,
) -> str:
    lines = [f"Skill in use: {skill}", "", "Conversation so far:"]
    for role, text in history:
        lines.append(f"{'Person' if role == 'user' else 'Vaani'}: {text}")
    if not history:
        lines.append("(this is the start of the conversation)")
    lines += ["", f"Person's last message: {user}", "", f"Vaani's reply to judge: {reply}"]
    if standard:
        lines += ["", f"STANDARD the reply must meet: {standard}"]
    return "\n".join(lines)


class Judge:
    """Synchronous judge for the test runner. It owns one event loop for all its calls."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.loop = asyncio.new_event_loop()
        self.model = build_judge(settings)
        self._instructions = {
            q: (INSTRUCTIONS / f"{q}.md").read_text(encoding="utf-8") for q in QUESTIONS
        }
        self.gap_s = settings.get_float("EVAL_MIN_SECONDS_BETWEEN_CALLS")
        self.retries = settings.get_int("EVAL_RETRIES_ON_RATE_LIMIT")
        self.tokens_in = 0
        self.tokens_out = 0
        self._last = 0.0

    async def _call(self, question: str, case_text: str) -> tuple[str, int, int]:
        context = llm.ChatContext()
        context.add_message(role="system", content=self._instructions[question])
        context.add_message(role="user", content=case_text)
        text, tin, tout = "", 0, 0
        async with self.model.chat(chat_ctx=context) as stream:
            async for chunk in stream:
                if chunk.delta and chunk.delta.content:
                    text += chunk.delta.content
                if chunk.usage:
                    tin, tout = chunk.usage.prompt_tokens, chunk.usage.completion_tokens
        return text, tin, tout

    def score(self, question: str, case_text: str) -> JudgeAnswer:
        """One question about one reply. Rate limits and unreadable answers are retried (tests)."""
        started = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            wait = self.gap_s - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                text, tin, tout = self.loop.run_until_complete(self._call(question, case_text))
                reasoning, score, passed = parse_answer(question, text)
                self.tokens_in += tin
                self.tokens_out += tout
                return JudgeAnswer(
                    question, reasoning, score, passed, (tin, tout), time.monotonic() - started
                )
            except Exception as error:  # rate limit, bad JSON: try again, tests only
                last_error = error
                time.sleep(2 * (attempt + 1))
        raise JudgeError(f"the judge failed after {self.retries + 1} tries: {last_error}")

    def describe(self) -> dict[str, Any]:
        return {
            "model": self.settings.get("JUDGE_MODEL"),
            "instructions_version": instructions_version(),
        }

    def close(self) -> None:
        self.loop.close()
