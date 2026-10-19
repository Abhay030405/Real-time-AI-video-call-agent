"""Saves telemetry as one JSON line per event, in a file for each session.

Every record carries a format version, and the file is named by the session, so a second
write of the same session lands in the same file (rule 11). Only timings and numbers are
saved: never what was said.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FORMAT_VERSION = 1


class TelemetryWriter:
    def __init__(self, folder: Path, session_id: str) -> None:
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)
        stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / f"{stamp}_{safe_id}.jsonl"
        self._session_id = session_id

    def write(self, record_type: str, /, **fields: Any) -> None:
        record = {
            "format_version": FORMAT_VERSION,
            "session_id": self._session_id,
            "type": record_type,
            "at": datetime.now(UTC).isoformat(timespec="milliseconds"),
            **fields,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
