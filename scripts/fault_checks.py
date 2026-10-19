"""Live fault checks for the Phase 1 gate: break one part, make a scripted call, see what happens.

    uv run --project agent python scripts/fault_checks.py

For each fault it stops the normal agent, starts a throwaway agent container with one part
broken (a dead address or a wrong key), runs `scripts/smoke_call.py` against it, reads the
telemetry the agent wrote, then puts the normal agent back. Needs
`docker compose up -d livekit web`.
The faults exist from the start of the call; they are not switched on in the middle of one.
Costs a few rupees.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TELEMETRY = REPO_ROOT / "storage" / "telemetry"
NAME = "vaani-fault-agent"


def uv_command() -> list[str]:
    found = shutil.which("uv")
    return [found] if found else ["python", "-m", "uv"]


def sh(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args), cwd=REPO_ROOT, capture_output=True, text=True, check=check, errors="replace"
    )


def newest_session() -> list[dict[str, Any]]:
    files = sorted(TELEMETRY.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not files:
        return []
    return [json.loads(x) for x in files[-1].read_text(encoding="utf-8").splitlines()]


def run_with_fault(env: dict[str, str]) -> tuple[str, list[dict[str, Any]]]:
    """Start a broken agent, make one scripted call, return the call's output and telemetry."""
    sh("docker", "compose", "stop", "agent")
    sh("docker", "rm", "-f", NAME)
    before = {p.name for p in TELEMETRY.glob("*.jsonl")}
    flags = [x for k, v in env.items() for x in ("-e", f"{k}={v}")]
    sh("docker", "compose", "run", "-d", "--no-deps", "--name", NAME, *flags, "agent")
    time.sleep(14)  # let the worker register
    call = subprocess.run(
        [*uv_command(), "run", "--project", "agent", "python", "scripts/smoke_call.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        errors="replace",
    )
    time.sleep(6)
    sh("docker", "rm", "-f", NAME)
    out = "\n".join(
        line
        for line in (call.stdout + call.stderr).splitlines()
        if line.startswith(("OK", "FAILED", "NOTE"))
    )
    fresh = [p for p in TELEMETRY.glob("*.jsonl") if p.name not in before]
    records: list[dict[str, Any]] = []
    for path in sorted(fresh):
        records += [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    return out, records


def user_turns(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in records if r["type"] == "turn" and r["kind"] == "user"]


def check_m1_dead(out: str, records: list[dict[str, Any]]) -> list[str]:
    turns = user_turns(records)
    problems = []
    if not turns:
        return ["no spoken turn was answered"]
    turn = turns[0]
    if turn["brain"] != "m2":
        problems.append(f"expected M2 to answer, got {turn['brain']}")
    fillers = sum(1 for n in turn["notes"] if n.startswith("clip:hmm"))
    if fillers > 1:
        problems.append(f"{fillers} fillers played, expected at most one")
    first_word = turn["stages_ms"].get("first_word_ms", 99999)
    detail = f"first word {first_word:.0f} ms, fillers {fillers}"
    return problems or [f"OK M2 answered ({detail})"]


def check_cartesia_dead(out: str, records: list[dict[str, Any]]) -> list[str]:
    summary = next((r for r in records if r["type"] == "session_summary"), None)
    if not user_turns(records):
        return ["no spoken turn was answered"]
    if summary is None:
        return ["no session summary written"]
    if summary["units"]["bulbul_chars"] <= 0:
        return ["the backup voice (Bulbul) did not speak"]
    return [f"OK Bulbul spoke {summary['units']['bulbul_chars']} characters"]


def check_sarvam_dead(out: str, records: list[dict[str, Any]]) -> list[str]:
    if "stt_failure" not in out:
        return ["the agent did not end the call with the speech-to-text apology"]
    return ["OK the agent apologised and ended the call (reason stt_failure)"]


FAULTS: list[tuple[str, dict[str, str], Callable[[str, list[dict[str, Any]]], list[str]]]] = [
    (
        "M1 killed (dead address)",
        {"M1_BASE_URL": "http://host.docker.internal:9/v1"},
        check_m1_dead,
    ),
    ("Cartesia killed (wrong key)", {"CARTESIA_API_KEY": "sk_car_wrong"}, check_cartesia_dead),
    (
        "Sarvam hearing killed (dead address)",
        {"SARVAM_STT_URL": "ws://host.docker.internal:9"},
        check_sarvam_dead,
    ),
]


def main() -> int:
    failures = 0
    try:
        for label, env, check in FAULTS:
            print(f"\n== {label}")
            out, records = run_with_fault(env)
            print(out or "(the call printed nothing)")
            results = check(out, records)
            bad = [r for r in results if not r.startswith("OK")]
            failures += bool(bad)
            for line in results:
                print(("  " if line.startswith("OK") else "  FAILED ") + line)
    finally:
        sh("docker", "rm", "-f", NAME)
        sh("docker", "compose", "up", "-d", "agent")  # put the normal agent back
    print("\nall faults behaved as designed" if not failures else f"\n{failures} fault(s) did not")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
