"""Lists the calls that were flagged for the founder's review (crisis, heavy moment, under 18).

    uv run --project agent python scripts/flagged_sessions.py [folder]

Reads the telemetry files in `storage/telemetry`. Only the kind of flag and when it
happened are saved: never what was said.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW = ("crisis", "under_18")  # these are reviewed by the founder; "heavy" is only counted


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "storage" / "telemetry"
    if not folder.is_dir():
        print(f"No telemetry folder at {folder}.")
        return 1
    found = 0
    for path in sorted(folder.glob("*.jsonl")):
        flags = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if '"type": "flag"' in line
        ]
        review = [f for f in flags if f["flag"] in REVIEW]
        if review:
            found += 1
            kinds = ", ".join(sorted({f["flag"] for f in review}))
            print(f"{path.name}: {kinds} (first at {review[0]['at']}, turn {review[0]['turn']})")
    print(f"\n{found} call(s) to review" if found else "No calls flagged for review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
