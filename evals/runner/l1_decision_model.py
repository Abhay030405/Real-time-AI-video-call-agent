"""L1 decision model: does Jev agree with the founder's tags on 30 conversations?

The founder tags each conversation (skill, intensity, heavy, Hinglish level) in
`evals/datasets/l1_decision_model/tags.csv` without seeing Jev's answers. Jev reads each
conversation the way it does in a call and the answers are compared. Targets (V0_07):
skill choice agrees at least 85%, heavy-disclosure agrees at least 90%. Answer time is
recorded at the 50th, 95th and 99th percentile.
"""

from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path
from typing import Any

from background_decisions import build_questions, format_window, parse_decision
from conductor.skills import ready_skills
from settings import REPO_ROOT, Settings
from vendors.decision_model import DecisionModelError, build_decision_model

from .l1_models import file_checksum
from .record import CaseResult
from .runner import TestSet

DATASET = REPO_ROOT / "evals" / "datasets" / "l1_decision_model"


def read_conversations(split: str) -> list[dict[str, Any]]:
    path = DATASET / split / "conversations.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def read_tags(path: Path = DATASET / "tags.csv") -> dict[str, dict[str, str]]:
    """id -> the founder's tags. Rows with any empty tag are skipped (not tagged yet)."""
    tags: dict[str, dict[str, str]] = {}
    if not path.is_file():
        return tags
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            values = {k: (row.get(k) or "").strip().lower() for k in
                      ("skill", "intensity", "heavy", "hinglish")}
            if all(values.values()):
                tags[row["id"]] = values
    return tags


class _Asker:
    def __init__(self, settings: Settings) -> None:
        self.loop = asyncio.new_event_loop()
        self.model = build_decision_model(settings)
        self.window = settings.get_int("JEV_WINDOW_TURNS")
        self.questions = build_questions(ready_skills(settings.get_int("SKILL_MIN_TEST_CASES")))
        self.loop.run_until_complete(self._ask("Person: Hi"))  # warm connection

    async def _ask(self, state: str) -> tuple[dict[str, Any], float]:
        return await self.model.ask(state, self.questions)

    def run_case(
        self, case_id: str, repeat: int, convs: dict[str, dict[str, Any]],
        tags: dict[str, dict[str, str]],
    ) -> CaseResult:
        conv = convs[case_id]
        turns = [(role, text) for role, text in conv["turns"]]
        text = format_window(turns, self.window)
        try:
            answers, ms = self.loop.run_until_complete(self._ask(text))
            decision = parse_decision(answers, ms)
        except (DecisionModelError, KeyError, ValueError) as error:
            return CaseResult(
                case_id, repeat, text, "Jev answers", hard_checks={"jev_answered": False},
                error=f"{type(error).__name__}: {error}"[:200],
            )
        soft: dict[str, float] = {}
        mine = tags.get(case_id)
        if mine is not None:
            soft = {
                "skill_agreement": float(decision.skill == mine["skill"]),
                "heavy_agreement": float((decision.heavy >= 0.5) == (mine["heavy"] == "yes")),
                "intensity_agreement": float(decision.intensity == mine["intensity"]),
                "hinglish_agreement": float(decision.hinglish == mine["hinglish"]),
            }
        return CaseResult(
            case_id=case_id, repeat=repeat, input=text,
            expected=json.dumps(mine) if mine else "not tagged yet",
            output=json.dumps({
                "skill": decision.skill, "skill_probability": round(decision.skill_probability, 3),
                "intensity": decision.intensity, "heavy": round(decision.heavy, 3),
                "under_18": round(decision.under_18, 3),
                "hinted_crisis": round(decision.hinted_crisis, 3), "hinglish": decision.hinglish,
            }),
            hard_checks={"jev_answered": True}, soft_scores=soft,
            timings_ms={"jev_answer_ms": ms},
        )

    def close(self) -> None:
        self.loop.run_until_complete(self.model.aclose())
        self.loop.close()


def l1_decision_model_test_set(settings: Settings, split: str = "working") -> TestSet:
    convs = {c["id"]: c for c in read_conversations(split)}
    asker = _Asker(settings)
    tags = read_tags()
    return TestSet(
        name="l1_decision_model",
        level="L1",
        version="v1",
        split=split,
        case_ids=list(convs),
        run_case=lambda case_id, repeat: asker.run_case(case_id, repeat, convs, tags),
        file_list_checksum=file_checksum(DATASET / split / "conversations.jsonl"),
        targets={"skill_agreement": {"min": 0.85}, "heavy_agreement": {"min": 0.90}},
        close=asker.close,
    )
