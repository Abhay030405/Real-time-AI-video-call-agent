"""The quick checks, run by hand before accepting any change (there are no automatic checks).

    python scripts/quick_checks.py

Runs code style, type checks and unit tests for the agent and the web page,
and the secret scan. Stops with a non-zero
exit code if anything fails, and prints what failed.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT = REPO_ROOT / "agent"
WEB = REPO_ROOT / "web"
PNPM_VERSION = "pnpm@9.15.9"  # the version the web starter pins


def uv_command() -> list[str]:
    found = shutil.which("uv")
    return [found] if found else [sys.executable, "-m", "uv"]


def pnpm_command() -> list[str]:
    corepack = shutil.which("corepack")
    if corepack:
        return [corepack, PNPM_VERSION]
    return [shutil.which("pnpm") or "pnpm"]


def run(label: str, command: list[str], cwd: Path) -> bool:
    print(f"\n== {label}")
    ok = subprocess.run(command, cwd=cwd, check=False).returncode == 0
    print(f"-> {'OK' if ok else 'FAILED'}: {label}")
    return ok


def main() -> int:
    uv = [*uv_command(), "run", "--project", str(AGENT)]
    code_folders = [".", "../evals", "../scripts"]
    steps = [
        ("Code style (ruff)", [*uv, "ruff", "check", *code_folders], AGENT),
        ("Type checks (mypy)", [*uv, "mypy", "main.py", "settings", "../evals/runner",
                                "../scripts"], AGENT),
        ("Unit tests (pytest)", [*uv, "pytest", "-q"], AGENT),
        ("Web code style (eslint)", [*pnpm_command(), "lint"], WEB),
        ("Web formatting (prettier)", [*pnpm_command(), "format:check"], WEB),
        ("Web type checks (tsc)", [*pnpm_command(), "typecheck"], WEB),
        ("Web unit tests (vitest)", [*pnpm_command(), "test"], WEB),
        ("Secret scan", [sys.executable, str(REPO_ROOT / "scripts" / "secret_scan.py")], REPO_ROOT),
    ]
    results = [(label, run(label, cmd, cwd)) for label, cmd, cwd in steps]

    print("\n== Summary")
    for label, ok in results:
        print(f"  {'OK    ' if ok else 'FAILED'}  {label}")
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    sys.exit(main())
