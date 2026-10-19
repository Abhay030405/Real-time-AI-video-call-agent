import json
import sys
from pathlib import Path

from settings import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import timing_report  # noqa: E402


def turn(reply_ms: float, brain: str = "m1") -> dict[str, object]:
    return {
        "type": "turn",
        "kind": "user",
        "brain": brain,
        "notes": [],
        "stages_ms": {"reply_total_ms": reply_ms, "first_word_ms": reply_ms / 2},
    }


def test_the_report_gives_percentiles_and_cost(tmp_path: Path) -> None:
    lines = [turn(float(ms)) for ms in range(100, 1100, 10)] + [turn(900, "m2")]
    lines.append({"type": "session_summary", "cost_inr": {"m1": 2.0, "total": 2.0}})
    (tmp_path / "a.jsonl").write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    turns, sessions = timing_report.read(tmp_path)
    text = timing_report.report(turns, sessions)
    assert "reply_total_ms" in text and "p95" in text
    assert "replies from M2: 1" in text
    assert "m1" in text and "2.000" in text
