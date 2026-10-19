"""Speed and cost report from the telemetry files.

    uv run --project agent python scripts/timing_report.py [folder]

Reads every session file in `storage/telemetry` (or the folder you give) and prints each
stage at the 50th, 95th and 99th percentile, plus the cost per call by vendor.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "agent"))
sys.path.insert(0, str(REPO_ROOT))

from evals.runner.record import percentile  # noqa: E402

STAGES = ("turn_detection_ms", "first_word_ms", "first_audio_ms", "reply_total_ms")


def read(folder: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    turns: list[dict[str, Any]] = []
    sessions: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record.get("type") == "turn":
                turns.append(record)
            elif record.get("type") == "session_summary":
                sessions.append(record)
    return turns, sessions


def report(turns: list[dict[str, Any]], sessions: list[dict[str, Any]]) -> str:
    out: list[str] = []
    user_turns = [t for t in turns if t["kind"] == "user"]
    out.append(f"{len(sessions)} call(s), {len(user_turns)} spoken turns, {len(turns)} replies")
    out.append("")
    out.append(f"{'stage (ms)':<22}{'p50':>8}{'p95':>8}{'p99':>8}{'n':>5}")
    for stage in STAGES:
        values = [t["stages_ms"][stage] for t in user_turns if stage in t["stages_ms"]]
        if values:
            row = (percentile(values, 50), percentile(values, 95), percentile(values, 99))
            out.append(f"{stage:<22}{row[0]:>8.0f}{row[1]:>8.0f}{row[2]:>8.0f}{len(values):>5}")
    m2 = sum(1 for t in turns if t.get("brain") == "m2")
    fillers = sum(1 for t in turns if any(n.startswith("clip:hmm") for n in t.get("notes", [])))
    out.append("")
    out.append(f"replies from M2: {m2}   fillers played: {fillers}")
    if sessions:
        totals: dict[str, float] = {}
        for s in sessions:
            for vendor, value in s["cost_inr"].items():
                totals[vendor] = totals.get(vendor, 0.0) + value
        out.append("")
        out.append("cost per call (rupees):")
        for vendor, value in totals.items():
            out.append(f"  {vendor:<16}{value / len(sessions):>9.3f}")
    return "\n".join(out)


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "storage" / "telemetry"
    if not folder.is_dir():
        print(f"No telemetry folder at {folder}. Make a call first.")
        return 1
    turns, sessions = read(folder)
    if not turns:
        print("No turns logged yet.")
        return 1
    print(report(turns, sessions))
    return 0


if __name__ == "__main__":
    sys.exit(main())
