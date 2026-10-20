"""Runs a test set and writes a result record.

    uv run --project agent python -m evals.runner --dummy
    uv run --project agent python -m evals.runner l1_models --split working
    uv run --project agent python -m evals.runner l1_voice --split hidden

Run it from the repository root. Records go to `evals/results/<YYYY-MM>/` (or `--out`).
Until the LiveKit Cloud deploy, every record says it was a local run, not a Mumbai run.
"""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))

from conductor.layers import fingerprints  # noqa: E402
from conductor.skills import SKILLS  # noqa: E402
from settings import REPO_ROOT, Settings, load_settings  # noqa: E402
from vendors.brain import describe_brain  # noqa: E402
from vendors.decision_model import describe_decision_model  # noqa: E402
from vendors.speech_to_text import describe_speech_to_text  # noqa: E402
from vendors.voice import describe_voice  # noqa: E402

from .dummy import dummy_test_set  # noqa: E402
from .l1_decision_model import l1_decision_model_test_set  # noqa: E402
from .l1_models import l1_models_test_set  # noqa: E402
from .l1_voice import l1_voice_test_set  # noqa: E402
from .l2_replies import l2_replies_test_set  # noqa: E402
from .runner import RunInfo, TestSet, run_test_set  # noqa: E402

SETS = ("l1_models", "l1_voice", "l2_replies", "l1_decision_model")


def build_info(settings: Settings, purpose: str) -> RunInfo:
    return RunInfo(
        machine=f"founder laptop ({platform.system()}), local run, not Mumbai",
        triggered_by="founder, by hand",
        purpose=purpose,
        settings={"values": settings.public(), "fingerprint": settings.fingerprint()},
        prompts=fingerprints(),
        vendors={
            "speech_to_text": describe_speech_to_text(settings),
            **describe_voice(settings),
            **describe_brain(settings),
            "decision_model": describe_decision_model(settings),
        },
        cost={"exchange_rate": f"{settings.get('USD_INR')} on {settings.get('USD_INR_DATE')}"},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evals.runner")
    parser.add_argument("test_set", nargs="?", choices=SETS, help="which test set to run")
    parser.add_argument("--dummy", action="store_true", help="run the built-in dummy test set")
    parser.add_argument("--split", choices=("working", "hidden"), default="working")
    parser.add_argument("--purpose", default="")
    parser.add_argument("--skill", choices=SKILLS, help="only this skill (l2_replies)")
    parser.add_argument("--repeats", type=int, default=1, help="runs of every case (l2_replies)")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "evals" / "results")
    args = parser.parse_args(argv)
    if not args.dummy and not args.test_set:
        parser.error("name a test set (" + ", ".join(SETS) + ") or use --dummy")

    settings = load_settings()
    test_set: TestSet
    if args.dummy:
        test_set = dummy_test_set()
    elif args.test_set == "l1_models":
        test_set = l1_models_test_set(settings, args.split)
    elif args.test_set == "l1_decision_model":
        test_set = l1_decision_model_test_set(settings, args.split)
    elif args.test_set == "l2_replies":
        chosen = (args.skill,) if args.skill else SKILLS
        test_set = l2_replies_test_set(settings, args.split, chosen, args.repeats)
    else:
        test_set = l1_voice_test_set(settings, args.split)
    purpose = args.purpose or f"{test_set.name} {args.split} run"
    summary, summary_path, cases_path = run_test_set(
        test_set, build_info(settings, purpose), args.out, REPO_ROOT
    )
    print(f"{summary['run_id']}: {summary['verdict']}")
    for result in summary["results"]:
        shown = result.get("percentiles") or result.get("value")
        print(f"  {result['name']}: {shown}  passed={result.get('passed')}")
    print("cost:", summary["cost"])
    print(summary_path)
    print(cases_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
