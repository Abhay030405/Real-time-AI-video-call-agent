"""Secret scan: fails if a key or secret could be committed.

Looks in every file git would track (tracked files plus new files that are not ignored).
Checks for common key shapes and for the exact secret values found in the local `.env`.
Prints file names and line numbers only, never the secret.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "agent"))

from settings import load_settings  # noqa: E402

KEY_SHAPES = {
    "OpenRouter key": re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}"),
    "Cartesia key": re.compile(r"sk_car_[A-Za-z0-9]{10,}"),
    "Sarvam key": re.compile(r"sk_[a-z0-9]{8}_[A-Za-z0-9]{20,}"),
    "TypeSafe key": re.compile(r"apikey_[0-9a-f]{20,}"),
    "Private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
}
MAX_BYTES = 2_000_000


def files_to_scan() -> list[Path]:
    done = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return [REPO_ROOT / name for name in done.stdout.split("\0") if name]


def scan() -> list[str]:
    problems: list[str] = []
    secret_values = load_settings().secret_values()
    for path in files_to_scan():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            problems.append(f"{rel}: a real .env file would be committed")
            continue
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary file
        for number, line in enumerate(text.splitlines(), start=1):
            for label, shape in KEY_SHAPES.items():
                if shape.search(line):
                    problems.append(f"{rel}:{number}: looks like a {label}")
            if any(value in line for value in secret_values):
                problems.append(f"{rel}:{number}: contains a value from your .env")
    return problems


def main() -> int:
    problems = scan()
    for problem in problems:
        print("SECRET SCAN:", problem)
    if problems:
        return 1
    print("Secret scan: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
