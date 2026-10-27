"""Judge calibration: does the AI judge agree with the founder's own scores? (V0_07 section 6)

The founder scores 50 replies in `evals/judge/calibration/founder_scores.csv` without seeing the
judge. The judge scores the same replies. Passing marks: on pass/fail questions the judge must
agree at least 80% of the time; on 1-to-5 scores it must be within one point at least 85% of
the time. When calibration passes, the run is recorded in `calibration/latest.json`, and judge
scores in later runs are marked as trusted only while the judge model and its instructions
are unchanged.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from evals.judge import Judge, JudgeError, format_case, instructions_version

from settings import REPO_ROOT, Settings

from .l1_models import file_checksum
from .record import CaseResult
from .runner import TestSet

CALIBRATION = REPO_ROOT / "evals" / "judge" / "calibration"
LATEST = CALIBRATION / "latest.json"


def read_items() -> list[dict[str, Any]]:
    path = CALIBRATION / "replies.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def read_founder_scores(
    path: Path = CALIBRATION / "founder_scores.csv",
) -> dict[str, dict[str, str]]:
    scores: dict[str, dict[str, str]] = {}
    if not path.is_file():
        return scores
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            values = {k: (row.get(k) or "").strip().lower() for k in
                      ("tone", "responds", "sounds_like_vaani", "meets_standard")}
            if any(values.values()):
                scores[row["id"]] = values
    return scores


def within_one(a: float, b: float) -> float:
    return 1.0 if abs(a - b) <= 1 else 0.0


def calibration_status(settings: Settings) -> dict[str, Any]:
    """Is the current judge (model and instructions) the one that passed calibration?"""
    current = {"model": settings.get("JUDGE_MODEL"), "instructions_version": instructions_version()}
    if not LATEST.is_file():
        return {**current, "calibration_run": None, "trusted": False}
    saved = json.loads(LATEST.read_text(encoding="utf-8"))
    same = (saved["model"], saved["instructions_version"]) == (
        current["model"], current["instructions_version"]
    )
    return {**current, "calibration_run": saved["run_id"] if same else None, "trusted": same}


class _Calibrator:
    def __init__(self, settings: Settings) -> None:
        self.judge = Judge(settings)
        self.items = {i["id"]: i for i in read_items()}
        self.founder = read_founder_scores()

    def run_case(self, case_id: str, repeat: int) -> CaseResult:
        item = self.items[case_id]
        mine = self.founder.get(case_id)
        text = format_case(item["skill"], item["history"], item["user"], item["reply"],
                           item.get("standard"))
        soft: dict[str, float] = {}
        notes: list[str] = []
        try:
            if item["source"] == "l5":
                answer = self.judge.score("meets_standard", text)
                notes.append(f"standard: {answer.reasoning}")
                if mine and mine["meets_standard"]:
                    soft["passfail_agreement"] = float(
                        answer.passed == (mine["meets_standard"] == "pass")
                    )
            else:
                tone = self.judge.score("tone", text)
                like = self.judge.score("sounds_like_vaani", text)
                responds = self.judge.score("responds", text)
                notes += [f"tone: {tone.reasoning}", f"vaani: {like.reasoning}",
                          f"responds: {responds.reasoning}"]
                if mine:
                    if mine["tone"].isdigit():
                        soft["tone_within_one"] = within_one(tone.score or 0, float(mine["tone"]))
                    if mine["sounds_like_vaani"].isdigit():
                        soft["sounds_like_within_one"] = within_one(
                            like.score or 0, float(mine["sounds_like_vaani"])
                        )
                    if mine["responds"]:
                        soft["passfail_agreement"] = float(
                            responds.passed == (mine["responds"] == "pass")
                        )
        except JudgeError as error:
            return CaseResult(case_id, repeat, item["reply"], "judge answers",
                              hard_checks={"judge_answered": False}, error=str(error)[:200])
        return CaseResult(
            case_id=case_id, repeat=repeat, input=item["reply"],
            expected=json.dumps(mine) if mine else "not scored yet",
            output="", hard_checks={"judge_answered": True}, soft_scores=soft,
            reasoning=" | ".join(notes),
        )

    def close(self) -> None:
        self.judge.close()


def judge_calibration_test_set(settings: Settings) -> TestSet:
    calibrator = _Calibrator(settings)
    return TestSet(
        name="judge_calibration",
        level="L1",
        version="v1",
        split="working",
        case_ids=list(calibrator.items),
        run_case=calibrator.run_case,
        file_list_checksum=file_checksum(CALIBRATION / "replies.jsonl"),
        targets={
            "passfail_agreement": {"min": 0.80},
            "tone_within_one": {"min": 0.85},
            "sounds_like_within_one": {"min": 0.85},
        },
        close=calibrator.close,
    )


def save_latest(run_id: str, settings: Settings) -> None:
    """Remember a passing calibration so later runs know the judge is trusted."""
    LATEST.write_text(json.dumps({
        "run_id": run_id,
        "model": settings.get("JUDGE_MODEL"),
        "instructions_version": instructions_version(),
    }, indent=2) + "\n", encoding="utf-8")
