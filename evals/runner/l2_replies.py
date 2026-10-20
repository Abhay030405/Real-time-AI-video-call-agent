"""L2 single replies: one reply to one message, in a given skill, checked by plain code.

Each case is a short conversation so far, what the person says next, and what a good reply
must and must not do. The reply is produced the way a real call produces it: the rules check
runs first, the Conductor assembles the layers (fixed text, skill note, overrides, session
note) and M1 answers. The helpline guarantee and the under-18 ending are applied as in a call.
The AI judge (tone, relevance, "sounds like Vaani") is added with the judge in step 5.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any

from livekit.agents import llm

from conductor.layers import TurnContext, assemble, fixed_instructions, session_note
from conductor.skills import SKILLS, load_skill, skill_note
from rules_check import (
    AGE_ENDING_LINE,
    AGE_ENDING_WITH_HELPLINES,
    HELPLINE_LINE,
    RulesConfig,
    RulesState,
    check,
)
from rules_check.patterns import HINDI, HINDI_AMBIGUOUS, mentions_helplines
from settings import REPO_ROOT, Settings
from telemetry import CostMeter, Prices
from vendors.brain import build_m1

from .checks import run_checks
from .record import CaseResult
from .runner import TestSet

DATASET = REPO_ROOT / "evals" / "datasets" / "l2_single_replies"


def read_cases(split: str, skills: tuple[str, ...] = SKILLS) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for skill in skills:
        path = DATASET / split / f"{skill}.jsonl"
        cases += [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
    return cases


def dataset_checksum(split: str, skills: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for skill in skills:
        digest.update((DATASET / split / f"{skill}.jsonl").read_bytes())
    return "sha256:" + digest.hexdigest()[:16]


def person_used_hindi(history: list[list[str]], user: str) -> bool:
    texts = [t for role, t in history if role == "user"] + [user]
    return any(
        {w.lower() for w in HINDI.findall(t)} - HINDI_AMBIGUOUS for t in texts
    )


class _Replier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.loop = asyncio.new_event_loop()
        self.m1 = build_m1(settings)
        self.config = RulesConfig(
            opening_minutes=settings.get_float("RULES_OPENING_MINUTES"),
            wrap_up_minute=settings.get_float("RULES_WRAP_UP_MINUTE"),
            crisis_turns=settings.get_int("RULES_CRISIS_TURNS"),
            jev_under_18_threshold=settings.get_float("RULES_JEV_UNDER_18_THRESHOLD"),
        )
        self.meter = CostMeter(Prices.from_settings(settings), {"m1": settings.get("M1_MODEL")})
        self.session_minutes = settings.get_int("SESSION_MINUTES")
        # Evaluation runs send many requests in a row: pace them and ride out rate limits.
        # (Tests may retry; the live call path never does, hard rule 9.)
        self.gap_s = settings.get_float("EVAL_MIN_SECONDS_BETWEEN_CALLS")
        self.retries = settings.get_int("EVAL_RETRIES_ON_RATE_LIMIT")
        self._last_call = 0.0
        self.loop.run_until_complete(self._ask(llm.ChatContext(), "Hi"))  # warm connection

    async def _ask(self, ctx: llm.ChatContext, text: str) -> tuple[str, float, int, int]:
        ctx.add_message(role="user", content=text)
        started = time.perf_counter()
        reply, first, tin, tout = "", None, 0, 0
        async with self.m1.chat(chat_ctx=ctx) as stream:
            async for chunk in stream:
                if chunk.delta and chunk.delta.content:
                    first = first or (time.perf_counter() - started)
                    reply += chunk.delta.content
                if chunk.usage:
                    tin, tout = chunk.usage.prompt_tokens, chunk.usage.completion_tokens
        return reply.strip(), (first or 0.0) * 1000, tin, tout

    def _ask_paced(self, ctx: llm.ChatContext, text: str) -> tuple[str, float, int, int]:
        for attempt in range(self.retries + 1):
            wait = self.gap_s - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
            try:
                return self.loop.run_until_complete(self._ask(ctx.copy(), text))
            except Exception as error:
                if "429" not in str(error) and "rate" not in str(error).lower():
                    raise
                if attempt == self.retries:
                    raise
                time.sleep(5 * (attempt + 1))  # back off, then try the same case again
        raise RuntimeError("unreachable")

    def run_case(self, case_id: str, repeat: int, cases: dict[str, dict[str, Any]]) -> CaseResult:
        case = cases[case_id]
        history: list[list[str]] = case["history"]
        state = RulesState(hindi_used=person_used_hindi(history, ""))
        rules = check(case["user"], state, self.config, case["minutes"])
        expectations = dict(case["checks"])
        label = f"{case['skill']}/{case['group']}"

        if rules.end_call_reason:  # the under-18 ending is fixed text, not a brain reply
            line = AGE_ENDING_WITH_HELPLINES if rules.crisis else AGE_ENDING_LINE
            ok = case.get("expects_end") == rules.end_call_reason
            return CaseResult(case_id, repeat, case["user"], label, output=line,
                              hard_checks={"ends_call_kindly": ok})
        if case.get("expects_end"):
            return CaseResult(case_id, repeat, case["user"], label, output="",
                              hard_checks={"ends_call_kindly": False})

        context = llm.ChatContext()
        context.add_message(role="system", content=fixed_instructions())
        for role, text in history:
            context.add_message(role="user" if role == "user" else "assistant", content=text)
        turn = TurnContext(
            skill_note=skill_note(load_skill(case["skill"]), case.get("intensity", "medium")),
            overrides=rules.overrides,
            session_note=session_note(
                int(case["minutes"]), self.session_minutes, len(history) // 2
            ),
        )
        prompt = assemble(context, turn)
        try:
            reply, first_ms, tin, tout = self._ask_paced(prompt, case["user"])
        except Exception as error:
            return CaseResult(case_id, repeat, case["user"], label,
                              hard_checks={"has_reply": False}, error=str(error)[:200])
        if rules.crisis and not mentions_helplines(reply):
            reply = f"{reply} {HELPLINE_LINE}"  # the helpline guarantee, as in a call
        self.meter.add_llm(self.settings.get("M1_MODEL"), tin, tout)
        _, cost = self.meter.take()
        checks = run_checks(reply, expectations, state.hindi_used, crisis_expected=rules.crisis)
        return CaseResult(
            case_id=case_id, repeat=repeat, input=case["user"], expected=label, output=reply,
            hard_checks=checks, timings_ms={"m1_first_word_ms": first_ms},
            cost_inr=cost["total"], cost_by={"m1": cost["m1"]},
        )

    def close(self) -> None:
        self.loop.close()


def l2_replies_test_set(
    settings: Settings, split: str = "working", skills: tuple[str, ...] = SKILLS, repeats: int = 1
) -> TestSet:
    cases = {c["id"]: c for c in read_cases(split, skills)}
    replier = _Replier(settings)
    return TestSet(
        name="l2_single_replies",
        level="L2",
        version="v1",
        split=split,
        case_ids=list(cases),
        run_case=lambda case_id, repeat: replier.run_case(case_id, repeat, cases),
        file_list_checksum=dataset_checksum(split, skills),
        repeats=repeats,
        close=replier.close,
    )
