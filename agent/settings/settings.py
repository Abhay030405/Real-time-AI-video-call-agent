"""The one place that reads `.env`.

Everything else in the agent, the evals and the scripts gets its values from here.
A missing required setting stops the program with a message that names it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

# Names that hold a secret. Their values are never shown, logged or saved in result records.
_SECRET_NAME = re.compile(r"(_KEY|_SECRET|_PASSWORD|_TOKEN)$|^(DATABASE_URL|REDIS_URL)$")

# agent/settings/settings.py -> repository root
REPO_ROOT = Path(__file__).resolve().parents[2]


class SettingsError(Exception):
    """A required setting is missing or empty."""


def is_secret(name: str) -> bool:
    return bool(_SECRET_NAME.search(name))


def parse_env_file(path: Path) -> dict[str, str]:
    """Read KEY=value lines. Blank lines and `#` comments are skipped."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass(frozen=True)
class Settings:
    """All settings, read once. Real environment variables win over the `.env` file."""

    values: Mapping[str, str]

    def get(self, name: str, default: str = "") -> str:
        return self.values.get(name, default)

    def require(self, *names: str) -> None:
        """Stop with a clear message naming every required setting that is missing or empty."""
        missing = [n for n in names if not self.values.get(n)]
        if missing:
            raise SettingsError(
                "Missing required setting(s) in .env: "
                + ", ".join(missing)
                + ". Add them (see .env.example)."
            )

    def get_required(self, name: str) -> str:
        self.require(name)
        return self.values[name]

    def get_float(self, name: str) -> float:
        raw = self.get_required(name)
        try:
            return float(raw)
        except ValueError as err:
            raise SettingsError(f"Setting {name} must be a number, got {raw!r}.") from err

    def get_int(self, name: str) -> int:
        raw = self.get_required(name)
        try:
            return int(raw)
        except ValueError as err:
            raise SettingsError(f"Setting {name} must be a whole number, got {raw!r}.") from err

    def secret_values(self) -> list[str]:
        """Secret values long enough to search for. Used only by the secret scan."""
        return [v for n, v in self.values.items() if is_secret(n) and len(v) >= 8]

    def public(self) -> dict[str, str]:
        """Settings that are safe to save in a result record: no keys, secrets or database URLs."""
        return {n: v for n, v in sorted(self.values.items()) if v and not is_secret(n)}

    def fingerprint(self, names: Iterable[str] | None = None) -> str:
        """A short fingerprint of the public settings (or of the named ones)."""
        pub = self.public()
        if names is not None:
            pub = {n: pub[n] for n in sorted(names) if n in pub}
        digest = hashlib.sha256(json.dumps(pub, sort_keys=True).encode()).hexdigest()
        return "sha256:" + digest[:16]


def load_settings(env_file: Path | None = None) -> Settings:
    """Read `.env` (default: the one in the repository root) plus real environment variables."""
    values = parse_env_file(env_file if env_file is not None else REPO_ROOT / ".env")
    known = set(values) | set(parse_env_file(REPO_ROOT / ".env.example"))
    for name in known:
        if name in os.environ:
            values[name] = os.environ[name]
    return Settings(values=values)
