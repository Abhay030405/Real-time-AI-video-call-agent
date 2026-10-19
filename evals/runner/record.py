"""Result records, as designed in `docs/phase0/05_result_record_design.md`.

Each run writes two files into `evals/results/<YYYY-MM>/`:
`<run_id>.json` (the summary) and `<run_id>.cases.jsonl` (one line per case per repeat).
A record is never edited after it is written: files are created, never overwritten.
"""

from __future__ import annotations

import json
import math
import secrets
import statistics
import string
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

RECORD_FORMAT_VERSION = 1
INDIAN_TIME = timezone(timedelta(hours=5, minutes=30))

REQUIRED_SUMMARY_FIELDS = (
    "record_format_version", "run_id", "started_at", "finished_at", "duration_s", "machine",
    "triggered_by", "purpose", "level", "test_set", "repeats", "code", "prompts", "settings",
    "vendors", "judge", "results", "hard_failures", "verdict", "cost", "baseline_run_id", "notes",
)


@dataclass
class CaseResult:
    """What one case produced in one repeat."""

    case_id: str
    repeat: int
    input: str
    expected: str
    output: str | None = None
    hard_checks: dict[str, bool] = field(default_factory=dict)  # name -> passed
    soft_scores: dict[str, float] = field(default_factory=dict)  # name -> 1 to 5
    reasoning: str | None = None  # the judge's reasoning, left out for hidden sets
    timings_ms: dict[str, float] = field(default_factory=dict)  # stage -> milliseconds
    cost_inr: float = 0.0
    error: str | None = None


def percentile(values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile."""
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def make_run_id(level: str, test_set: str, now: datetime | None = None) -> str:
    """`<date>_<time>_<level>_<test set>_<4 random letters>`, in Indian time."""
    stamp = (now or datetime.now(INDIAN_TIME)).strftime("%Y-%m-%d_%H%M")
    letters = "".join(secrets.choice(string.ascii_lowercase) for _ in range(4))
    return f"{stamp}_{level}_{test_set.replace('_', '-')}_{letters}"


def code_version(repo_root: Path) -> dict[str, Any]:
    """The exact commit and whether there were unsaved changes ("dirty")."""
    def git(*args: str) -> str:
        done = subprocess.run(
            ["git", *args], cwd=repo_root, capture_output=True, text=True, check=False
        )
        return done.stdout.strip() if done.returncode == 0 else ""

    commit = git("rev-parse", "--short", "HEAD")
    dirty = bool(git("status", "--porcelain")) or not commit
    return {"commit": commit or "unknown", "dirty": dirty}


def summarise(cases: Sequence[CaseResult], targets: Mapping[str, Mapping[str, Any]]) -> tuple[
    list[dict[str, Any]], list[str]
]:
    """Turn case results into the summary's results list and the hard failures."""
    results: list[dict[str, Any]] = []
    hard_failures = sorted({c.case_id for c in cases if not all(c.hard_checks.values())})

    hard_names = sorted({n for c in cases for n in c.hard_checks})
    for name in hard_names:
        checks = [c.hard_checks[name] for c in cases if name in c.hard_checks]
        results.append({
            "name": name, "kind": "hard", "value": sum(checks), "n": len(checks),
            "target": "all pass", "passed": all(checks),
        })

    soft_names = sorted({n for c in cases for n in c.soft_scores})
    for name in soft_names:
        scores = [c.soft_scores[name] for c in cases if name in c.soft_scores]
        spread = {
            "std": statistics.pstdev(scores) if len(scores) > 1 else 0.0,
            "min": min(scores), "max": max(scores),
        }
        results.append(_with_target({
            "name": name, "kind": "soft", "value": statistics.fmean(scores), "spread": spread,
            "n": len(scores),
        }, targets))

    stages = sorted({s for c in cases for s in c.timings_ms})
    for stage in stages:
        times = [c.timings_ms[stage] for c in cases if stage in c.timings_ms]
        results.append(_with_target({
            "name": stage, "kind": "time_ms", "n": len(times),
            "percentiles": {
                "p50": percentile(times, 50), "p95": percentile(times, 95),
                "p99": percentile(times, 99), "samples": len(times),
            },
        }, targets))
    return results, hard_failures


def _with_target(entry: dict[str, Any], targets: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Attach a target and `passed` when the measure has one (`max` or `min` on its headline)."""
    target = targets.get(entry["name"])
    if not target:
        return {**entry, "target": None, "passed": None}
    headline = entry["value"] if "value" in entry else entry["percentiles"][target.get("at", "p95")]
    ok = headline <= target["max"] if "max" in target else headline >= target["min"]
    return {**entry, "target": dict(target), "passed": ok}


def verdict_for(results: Sequence[Mapping[str, Any]], hard_failures: Sequence[str]) -> str:
    """One hard failure fails the run. With no targets at all the verdict is "recorded"."""
    if hard_failures or any(r.get("passed") is False for r in results):
        return "fail"
    if not any(r.get("target") for r in results):
        return "recorded"
    return "pass"


def validate_summary(summary: Mapping[str, Any]) -> list[str]:
    """Return a list of problems; empty means the summary is valid."""
    problems = [f"missing field: {f}" for f in REQUIRED_SUMMARY_FIELDS if f not in summary]
    if summary.get("record_format_version") != RECORD_FORMAT_VERSION:
        problems.append("record_format_version is not the current version")
    if summary.get("verdict") not in ("pass", "fail", "recorded"):
        problems.append("verdict must be pass, fail or recorded")
    if summary.get("hard_failures") and summary.get("verdict") != "fail":
        problems.append("a run with hard failures must have verdict fail")
    return problems


def write_record(
    out_dir: Path, summary: Mapping[str, Any], cases: Sequence[CaseResult], hidden: bool
) -> tuple[Path, Path]:
    """Write both files. Refuses to overwrite: a wrong run is replaced by a new run."""
    problems = validate_summary(summary)
    if problems:
        raise ValueError("Invalid result record: " + "; ".join(problems))
    month_dir = out_dir / str(summary["started_at"])[:7]
    month_dir.mkdir(parents=True, exist_ok=True)
    summary_path = month_dir / f"{summary['run_id']}.json"
    cases_path = month_dir / f"{summary['run_id']}.cases.jsonl"

    with summary_path.open("x", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with cases_path.open("x", encoding="utf-8") as f:
        for c in cases:
            line = {
                "case_id": c.case_id, "repeat": c.repeat, "input": c.input,
                "expected": c.expected,
                # Hidden sets keep scores, not Vaani's replies or the judge's reasoning
                "output": None if hidden else c.output,
                "scores": {
                    "hard": c.hard_checks, "soft": c.soft_scores,
                    **({} if hidden else {"reasoning": c.reasoning}),
                },
                "timings_ms": c.timings_ms, "cost_inr": c.cost_inr, "error": c.error,
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return summary_path, cases_path
