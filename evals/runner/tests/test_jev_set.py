from pathlib import Path

from evals.runner.l1_decision_model import read_conversations, read_tags


def test_thirty_conversations_with_a_hidden_third() -> None:
    working, hidden = read_conversations("working"), read_conversations("hidden")
    assert len(working) + len(hidden) == 30
    assert not {c["id"] for c in working} & {c["id"] for c in hidden}
    for conv in working + hidden:
        assert conv["turns"][-1][0] == "user"  # every conversation ends on the person's message


def test_only_fully_tagged_rows_are_used(tmp_path: Path) -> None:
    sheet = tmp_path / "tags.csv"
    sheet.write_text(
        "id,skill,intensity,heavy,hinglish\n"
        "J01,support,high,yes,none\n"
        "J02,support,,no,none\n"
        "J03, Casual_Chat ,low,NO,light\n",
        encoding="utf-8",
    )
    tags = read_tags(sheet)
    assert set(tags) == {"J01", "J03"}
    expected = {"skill": "casual_chat", "intensity": "low", "heavy": "no", "hinglish": "light"}
    assert tags["J03"] == expected


def test_a_missing_sheet_means_no_tags() -> None:
    assert read_tags(Path("does-not-exist.csv")) == {}
