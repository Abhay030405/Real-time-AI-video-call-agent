"""Runs a named test set and saves a result record."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .record import (
    INDIAN_TIME,
    RECORD_FORMAT_VERSION,
    CaseResult,
    code_version,
    make_run_id,
    summarise,
    verdict_for,
    write_record,
)


@dataclass
class TestSet:
    """One named set of cases. `run_case(case_id, repeat)` does the work for one case."""

    __test__ = False  # not a pytest class

    name: str  # for example "l1_speech_to_text"
    level: str  # L1 to L7
    version: str  # for example "v1"
    split: str  # "working" or "hidden"
    case_ids: Sequence[str]
    run_case: Callable[[str, int], CaseResult]
    file_list_checksum: str = ""
    repeats: int = 1
    targets: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


@dataclass
class RunInfo:
    """Everything about the run that is not the cases themselves."""

    machine: str
    triggered_by: str  # "founder, by hand", "phase gate" or "release"
    purpose: str
    settings: Mapping[str, Any] = field(default_factory=dict)  # public settings and fingerprint
    prompts: Mapping[str, Any] = field(default_factory=dict)
    vendors: Mapping[str, Any] = field(default_factory=dict)
    judge: Mapping[str, Any] = field(default_factory=dict)
    cost: Mapping[str, Any] = field(default_factory=dict)
    notes: str = ""


def run_test_set(
    test_set: TestSet, info: RunInfo, out_dir: Path, repo_root: Path
) -> tuple[dict[str, Any], Path, Path]:
    """Run every case `repeats` times, build the summary, write both files.

    Returns the summary and the two file paths.
    """
    started = datetime.now(INDIAN_TIME)
    timer = time.perf_counter()  # this machine's own steady timer
    cases = [
        test_set.run_case(case_id, repeat)
        for repeat in range(1, test_set.repeats + 1)
        for case_id in test_set.case_ids
    ]
    duration_s = time.perf_counter() - timer
    finished = datetime.now(INDIAN_TIME)

    results, hard_failures = summarise(cases, test_set.targets)
    summary: dict[str, Any] = {
        "record_format_version": RECORD_FORMAT_VERSION,
        "run_id": make_run_id(test_set.level, test_set.name, started),
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "duration_s": round(duration_s, 3),
        "machine": info.machine,
        "triggered_by": info.triggered_by,
        "purpose": info.purpose,
        "level": test_set.level,
        "test_set": {
            "name": test_set.name, "version": test_set.version, "split": test_set.split,
            "file_list_checksum": test_set.file_list_checksum, "case_count": len(test_set.case_ids),
        },
        "repeats": test_set.repeats,
        "code": code_version(repo_root),
        "prompts": dict(info.prompts),
        "settings": dict(info.settings),
        "vendors": dict(info.vendors),
        "judge": dict(info.judge),
        "results": results,
        "hard_failures": hard_failures,
        "verdict": verdict_for(results, hard_failures),
        "cost": dict(info.cost),
        "baseline_run_id": None,
        "notes": info.notes,
    }
    summary_path, cases_path = write_record(
        out_dir, summary, cases, hidden=test_set.split == "hidden"
    )
    return summary, summary_path, cases_path
