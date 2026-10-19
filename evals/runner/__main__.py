"""`python -m evals.runner --dummy` runs the dummy test set and writes a result record.

Run it from the repository root: `uv run --project agent python -m evals.runner --dummy`.
Real test sets are added with the features that need them.
"""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))

from settings import REPO_ROOT, load_settings  # noqa: E402

from .dummy import dummy_test_set  # noqa: E402
from .runner import RunInfo, run_test_set  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evals.runner")
    parser.add_argument("--dummy", action="store_true", help="run the built-in dummy test set")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "evals" / "results")
    args = parser.parse_args(argv)
    if not args.dummy:
        parser.error("only --dummy exists so far; real test sets arrive with their features")

    settings = load_settings()
    info = RunInfo(
        machine=f"{platform.node()}, {platform.system()}",
        triggered_by="founder, by hand",
        purpose="Runner check with the dummy test set",
        settings={"values": settings.public(), "fingerprint": settings.fingerprint()},
    )
    summary, summary_path, cases_path = run_test_set(
        dummy_test_set(), info, args.out, REPO_ROOT
    )
    print(f"{summary['run_id']}: {summary['verdict']}")
    print(summary_path)
    print(cases_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
