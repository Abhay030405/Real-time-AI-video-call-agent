"""A tiny test set that proves the runner works. It calls no outside service."""

from __future__ import annotations

from .record import CaseResult
from .runner import TestSet

_EXPECTED = {"D1": "hello", "D2": "namaste", "D3": "thank you"}


def _run_case(case_id: str, repeat: int) -> CaseResult:
    expected = _EXPECTED[case_id]
    return CaseResult(
        case_id=case_id,
        repeat=repeat,
        input=f"dummy input {case_id}",
        expected=expected,
        output=expected,
        hard_checks={"matches_expected": True},
        soft_scores={"dummy_quality": 4.0},
        timings_ms={"dummy_stage_ms": 10.0 + len(case_id)},
    )


def dummy_test_set(split: str = "working", repeats: int = 1) -> TestSet:
    return TestSet(
        name="dummy",
        level="L0",
        version="v1",
        split=split,
        case_ids=list(_EXPECTED),
        run_case=_run_case,
        repeats=repeats,
    )
