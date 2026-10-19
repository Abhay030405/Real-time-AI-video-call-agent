import json
from pathlib import Path

import pytest
from evals.runner.dummy import dummy_test_set
from evals.runner.record import (
    CaseResult,
    make_run_id,
    percentile,
    summarise,
    validate_summary,
    verdict_for,
    write_record,
)
from evals.runner.runner import RunInfo, TestSet, run_test_set

from settings import REPO_ROOT

INFO = RunInfo(machine="test machine", triggered_by="founder, by hand", purpose="unit test")


def test_dummy_run_writes_a_valid_record(tmp_path: Path) -> None:
    summary, summary_path, cases_path = run_test_set(
        dummy_test_set(repeats=2), INFO, tmp_path, REPO_ROOT
    )
    assert validate_summary(summary) == []
    assert summary["verdict"] == "pass"  # every hard check passed
    assert summary["test_set"]["case_count"] == 3
    on_disk = json.loads(summary_path.read_text(encoding="utf-8"))
    assert on_disk["run_id"] == summary["run_id"]
    assert len(cases_path.read_text(encoding="utf-8").splitlines()) == 6  # 3 cases x 2 repeats


def test_records_are_never_overwritten(tmp_path: Path) -> None:
    summary, _, _ = run_test_set(dummy_test_set(), INFO, tmp_path, REPO_ROOT)
    with pytest.raises(FileExistsError):
        write_record(tmp_path, summary, [], hidden=False)


def test_hidden_sets_keep_scores_not_replies(tmp_path: Path) -> None:
    _, _, cases_path = run_test_set(dummy_test_set(split="hidden"), INFO, tmp_path, REPO_ROOT)
    line = json.loads(cases_path.read_text(encoding="utf-8").splitlines()[0])
    assert line["output"] is None
    assert "reasoning" not in line["scores"]
    assert line["scores"]["hard"] == {"matches_expected": True}


def test_one_hard_failure_fails_the_run() -> None:
    cases = [
        CaseResult("A", 1, "i", "e", hard_checks={"safe": True}, soft_scores={"quality": 5.0}),
        CaseResult("B", 1, "i", "e", hard_checks={"safe": False}, soft_scores={"quality": 5.0}),
    ]
    results, failures = summarise(cases, {})
    assert failures == ["B"]
    assert verdict_for(results, failures) == "fail"


def test_target_decides_pass_or_fail() -> None:
    cases = [CaseResult("A", 1, "i", "e", timings_ms={"first_word_ms": t}) for t in (400, 500, 900)]
    results, _ = summarise(cases, {"first_word_ms": {"max": 700, "at": "p95"}})
    assert results[0]["percentiles"]["p95"] == 900
    assert results[0]["passed"] is False
    assert verdict_for(results, []) == "fail"


def test_percentiles_use_nearest_rank() -> None:
    values = list(range(1, 101))
    assert (percentile(values, 50), percentile(values, 95), percentile(values, 99)) == (50, 95, 99)


def test_validation_reports_missing_fields() -> None:
    problems = validate_summary({"record_format_version": 1})
    assert any("run_id" in p for p in problems)


def test_run_id_shape() -> None:
    run_id = make_run_id("L1", "stt_hinglish")
    assert run_id.split("_")[2:4] == ["L1", "stt-hinglish"]
    assert len(run_id.rsplit("_", 1)[1]) == 4


def test_custom_test_set_runs(tmp_path: Path) -> None:
    ts = TestSet(
        name="mini", level="L1", version="v1", split="working", case_ids=["X"],
        run_case=lambda cid, rep: CaseResult(cid, rep, "i", "e", hard_checks={"ok": True}),
    )
    summary, _, _ = run_test_set(ts, INFO, tmp_path, REPO_ROOT)
    assert summary["verdict"] == "pass"


def test_no_targets_means_recorded() -> None:
    cases = [CaseResult("A", 1, "i", "e", timings_ms={"silence_ms": 300.0})]
    results, failures = summarise(cases, {})
    assert verdict_for(results, failures) == "recorded"
