from pathlib import Path

from evals.runner.l1_models import read_snippets
from evals.runner.l1_voice import read_ratings, read_sentences, write_rating_sheet
from evals.runner.record import CaseResult, aggregate_cost


def test_models_set_has_sixty_snippets_in_both_languages_and_a_hidden_third() -> None:
    working, hidden = read_snippets("working"), read_snippets("hidden")
    everything = working + hidden
    assert len(everything) == 60
    assert {s["language"] for s in everything} == {"en", "hinglish"}
    assert 0.25 <= len(hidden) / len(everything) <= 0.40  # about 30% stays hidden
    assert not {s["id"] for s in working} & {s["id"] for s in hidden}


def test_voice_set_has_fifty_sentences_with_names_places_and_numbers() -> None:
    working, hidden = read_sentences("working"), read_sentences("hidden")
    assert len(working) + len(hidden) == 50
    assert not {s["id"] for s in working} & {s["id"] for s in hidden}
    text = " ".join(s["text"] for s in working + hidden)
    for expected in ("Priya", "Bengaluru", "nine eight one one", "yaar"):
        assert expected in text


def test_a_rating_sheet_is_made_once_and_never_overwritten(tmp_path: Path) -> None:
    sheet = tmp_path / "ratings.csv"
    write_rating_sheet(sheet, [{"id": "V01", "text": "Hello"}])
    sheet.write_text(
        "id,text,cartesia_rating,bulbul_rating,notes\nV01,Hello,5,3,\n", encoding="utf-8"
    )
    write_rating_sheet(sheet, [{"id": "V01", "text": "Hello"}])  # must not wipe the ratings
    assert read_ratings(sheet) == {("V01", "cartesia"): 5, ("V01", "bulbul"): 3}


def test_empty_or_wrong_ratings_are_ignored(tmp_path: Path) -> None:
    sheet = tmp_path / "ratings.csv"
    sheet.write_text(
        "id,text,cartesia_rating,bulbul_rating,notes\nV01,a,,9,\nV02,b,4,x,\n", encoding="utf-8"
    )
    assert read_ratings(sheet) == {("V02", "cartesia"): 4}


def test_cost_is_added_up_per_vendor_and_per_thousand_cases() -> None:
    cases = [
        CaseResult("a", 1, "i", "e", cost_inr=0.2, cost_by={"m1": 0.2}),
        CaseResult("b", 1, "i", "e", cost_inr=0.3, cost_by={"m1": 0.1, "m2": 0.2}),
    ]
    cost = aggregate_cost(cases)
    assert cost["m1"] == 0.3 and cost["m2"] == 0.2
    assert cost["total_inr"] == 0.5
    assert cost["per_1000_cases_inr"] == 250.0
