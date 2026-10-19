"""L1 models: how fast and how cheap the chosen brains are on English and Hinglish snippets.

For M1, M2 and S1 it measures time to the first word, total time, tokens and cost on each
snippet. The reply-quality scoring and the comparison of other models are postponed
(`docs/not_implemented_features.md`).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path

from livekit.agents import llm

from conductor.agent import load_instructions
from settings import REPO_ROOT, Settings
from telemetry import CostMeter, Prices
from vendors.brain import build_m1, build_m2, build_s1

from .record import CaseResult
from .runner import TestSet

DATASET = REPO_ROOT / "evals" / "datasets" / "l1_models"
ROLES = ("m1", "m2", "s1")
MARKDOWN_MARKS = ("*", "#", "`", "\n- ")


def read_snippets(split: str) -> list[dict[str, str]]:
    path = DATASET / split / "snippets.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def file_checksum(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]


class _Asker:
    """Sends snippets to the three models on one long-lived event loop (warm connections)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.loop = asyncio.new_event_loop()
        self.models = {"m1": build_m1(settings), "m2": build_m2(settings), "s1": build_s1(settings)}
        self.meter = CostMeter(
            Prices.from_settings(settings),
            {r: settings.get(f"{r.upper()}_MODEL") for r in ROLES},
        )
        self.system = load_instructions()
        for role in ROLES:  # one untimed request each, so no case pays for a new connection
            self.loop.run_until_complete(self._ask(role, "Hi"))

    async def _ask(self, role: str, text: str) -> tuple[str, float, float, int, int]:
        context = llm.ChatContext()
        context.add_message(role="system", content=self.system)
        context.add_message(role="user", content=text)
        started = time.perf_counter()
        first: float | None = None
        reply, tokens_in, tokens_out = "", 0, 0
        async with self.models[role].chat(chat_ctx=context) as stream:
            async for chunk in stream:
                if chunk.delta and chunk.delta.content:
                    if first is None:
                        first = time.perf_counter() - started
                    reply += chunk.delta.content
                if chunk.usage:
                    tokens_in, tokens_out = chunk.usage.prompt_tokens, chunk.usage.completion_tokens
        total = time.perf_counter() - started
        return reply.strip(), (first or total) * 1000, total * 1000, tokens_in, tokens_out

    def run_case(
        self, case_id: str, repeat: int, snippets: dict[str, dict[str, str]]
    ) -> CaseResult:
        role, snippet_id = case_id.split(":")
        snippet = snippets[snippet_id]
        try:
            reply, first_ms, total_ms, tokens_in, tokens_out = self.loop.run_until_complete(
                self._ask(role, snippet["text"])
            )
        except Exception as error:  # a failed request is a failed case, not a crashed run
            return CaseResult(
                case_id, repeat, snippet["text"], "a short spoken reply",
                hard_checks={"has_reply": False}, error=f"{type(error).__name__}: {error}"[:200],
            )
        self.meter.add_llm(self.settings.get(f"{role.upper()}_MODEL"), tokens_in, tokens_out)
        _, cost = self.meter.take()
        return CaseResult(
            case_id=case_id,
            repeat=repeat,
            input=snippet["text"],
            expected="a short spoken reply, no lists or markdown",
            output=reply,
            hard_checks={
                "has_reply": bool(reply),
                "spoken_style": not any(mark in reply for mark in MARKDOWN_MARKS),
            },
            timings_ms={f"{role}_first_word_ms": first_ms, f"{role}_total_ms": total_ms},
            cost_inr=cost["total"],
            cost_by={role: cost[role]},
        )

    def close(self) -> None:
        self.loop.close()


def l1_models_test_set(settings: Settings, split: str = "working") -> TestSet:
    snippets = {s["id"]: s for s in read_snippets(split)}
    asker = _Asker(settings)
    return TestSet(
        name="l1_models",
        level="L1",
        version="v1",
        split=split,
        case_ids=[f"{role}:{sid}" for role in ROLES for sid in snippets],
        run_case=lambda case_id, repeat: asker.run_case(case_id, repeat, snippets),
        file_list_checksum=file_checksum(DATASET / split / "snippets.jsonl"),
        # The Phase 1 gate: M1 first word at the 95th percentile within 0.7 s
        targets={"m1_first_word_ms": {"max": 700, "at": "p95"}},
        close=asker.close,
    )
