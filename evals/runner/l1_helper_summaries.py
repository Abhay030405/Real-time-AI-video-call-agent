"""L1 helper (S1): do its summaries keep the facts? (V0_07: at least 90% of key facts kept)

Each conversation has facts planted in it. S1 writes the summary; the AI judge checks, one fact
at a time, whether the summary keeps each one.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from evals.judge import Judge, JudgeError

from memory import summarise
from settings import REPO_ROOT, Settings
from telemetry import CostMeter, Prices
from vendors.brain import build_s1

from .l1_models import file_checksum
from .record import CaseResult
from .runner import TestSet

DATASET = REPO_ROOT / "evals" / "datasets" / "l1_helper_summaries"
MAX_WORDS = 150


def read_conversations(split: str) -> list[dict[str, Any]]:
    path = DATASET / split / "conversations.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


class _Summariser:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.loop = asyncio.new_event_loop()
        self.s1 = build_s1(settings)
        self.judge = Judge(settings)
        self.meter = CostMeter(Prices.from_settings(settings), {"s1": settings.get("S1_MODEL")})
        self.gap_s = settings.get_float("EVAL_MIN_SECONDS_BETWEEN_CALLS")

    def run_case(self, case_id: str, repeat: int, convs: dict[str, dict[str, Any]]) -> CaseResult:
        conv = convs[case_id]
        turns = [(role, text) for role, text in conv["turns"]]
        time.sleep(self.gap_s)
        try:
            summary = self.loop.run_until_complete(summarise(self.s1, turns))
        except Exception as error:
            return CaseResult(case_id, repeat, "", "a summary", hard_checks={"summary_made": False},
                              error=f"{type(error).__name__}: {error}"[:200])
        kept, notes = 0, []
        try:
            for fact in conv["facts"]:
                answer = self.judge.score("fact_kept", f"SUMMARY:\n{summary}\n\nFACT: {fact}")
                kept += bool(answer.passed)
                if not answer.passed:
                    notes.append(f"missing: {fact}")
        except JudgeError as error:
            return CaseResult(case_id, repeat, summary, "facts kept",
                              hard_checks={"judge_answered": False}, error=str(error)[:200])
        words = len(summary.split())
        return CaseResult(
            case_id=case_id, repeat=repeat, input=f"{len(turns)} turns, {len(conv['facts'])} facts",
            expected="every fact kept", output=summary,
            hard_checks={"summary_made": bool(summary), "short_summary": words <= MAX_WORDS},
            soft_scores={"facts_kept": kept / len(conv["facts"])},
            reasoning="; ".join(notes) or None,
        )

    def close(self) -> None:
        self.judge.close()
        self.loop.close()


def l1_helper_summaries_test_set(settings: Settings, split: str = "working") -> TestSet:
    convs = {c["id"]: c for c in read_conversations(split)}
    summariser = _Summariser(settings)
    return TestSet(
        name="l1_helper_summaries",
        level="L1",
        version="v1",
        split=split,
        case_ids=list(convs),
        run_case=lambda case_id, repeat: summariser.run_case(case_id, repeat, convs),
        file_list_checksum=file_checksum(DATASET / split / "conversations.jsonl"),
        targets={"facts_kept": {"min": 0.90}},
        close=summariser.close,
    )
