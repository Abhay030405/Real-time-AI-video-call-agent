from pathlib import Path

import pytest

from conductor.agent import VaaniAgent, load_instructions
from conductor.layers import assemble
from conductor.skills import (
    DATASETS,
    DEFAULT_SKILL,
    INTENSITIES,
    SKILLS,
    dials_for,
    load_skill,
    missing_parts,
    ready_skills,
    skill_note,
)


def test_there_are_exactly_five_skills_and_each_loads() -> None:
    assert len(SKILLS) == 5
    for name in SKILLS:
        skill = load_skill(name)
        assert skill.title and skill.spec and skill.instructions


def test_every_skill_has_a_what_bad_looks_like_line() -> None:
    for name in SKILLS:
        assert "What bad looks like" in load_skill(name).instructions, name


def test_skill_instructions_are_short_so_replies_stay_fast() -> None:
    for name in SKILLS:
        assert len(load_skill(name).instructions.split()) <= 140, name


def test_every_spec_covers_the_checklist() -> None:
    for name in SKILLS:
        spec = load_skill(name).spec
        for part in ("When it starts", "What the person should feel", "India-specific",
                     "Rules most likely to break"):
            assert part in spec, (name, part)


def test_default_dials_follow_the_skill_table() -> None:
    expected = {
        "casual_chat": ("medium", "medium"),
        "curious_deep_dive": ("high", "low"),
        "serious_discussion": ("low", "high"),
        "support": ("low", "high"),
        "playful_banter": ("high", "low"),
    }
    for name, dials in expected.items():
        assert dials_for(load_skill(name), "medium") == dials


def test_intensity_moves_only_the_skills_main_dial_and_never_to_zero() -> None:
    support = load_skill("support")
    assert dials_for(support, "high") == ("low", "high")  # already at the top
    assert dials_for(support, "low") == ("low", "medium")
    playful = load_skill("playful_banter")
    assert dials_for(playful, "low") == ("medium", "low")
    casual = load_skill("casual_chat")
    assert {dials_for(casual, i) for i in INTENSITIES} == {("medium", "medium")}
    for name in SKILLS:
        for intensity in INTENSITIES:
            dials = dials_for(load_skill(name), intensity)
            assert all(d in ("low", "medium", "high") for d in dials)  # never zero


def test_the_skill_note_has_the_instructions_and_the_dials_in_words() -> None:
    note = skill_note(load_skill("support"), "high")
    assert "Skill: support" in note
    assert "Spark is low" in note and "Steadiness is high" in note
    assert not any(ch.isdigit() for ch in note)  # the AI never sees numbers


def test_a_bad_intensity_is_refused() -> None:
    with pytest.raises(ValueError):
        dials_for(load_skill("support"), "extreme")


def test_all_five_skills_are_complete_once_their_tests_exist() -> None:
    assert ready_skills(min_test_cases=30) == list(SKILLS)
    for name in SKILLS:
        assert missing_parts(name, 30) == []


def test_a_skill_without_tests_is_kept_out_of_the_chooser(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    (skills / "support").mkdir(parents=True)
    (skills / "support" / "spec.md").write_text("spec", encoding="utf-8")
    (skills / "support" / "skill.json").write_text("{}", encoding="utf-8")
    (skills / "support" / "instructions.md").write_text("text", encoding="utf-8")
    assert "tests" in missing_parts("support", 30, skills, tmp_path / "none")[0]
    assert ready_skills(30, skills, tmp_path / "none") == []


def test_a_skill_missing_its_spec_or_instructions_is_kept_out(tmp_path: Path) -> None:
    (tmp_path / "support").mkdir()
    missing = missing_parts("support", 0, tmp_path, tmp_path)
    assert "spec" in missing and "instructions" in missing


def test_the_test_files_exist_for_every_skill_in_both_splits() -> None:
    for name in SKILLS:
        for split in ("working", "hidden"):
            assert (DATASETS / split / f"{name}.jsonl").is_file(), (name, split)


def test_a_call_starts_in_casual_chat_and_the_skill_can_change() -> None:
    from livekit.agents import llm

    agent = VaaniAgent(load_instructions())
    assert agent.skill == DEFAULT_SKILL
    assert "Skill: casual chat" in agent.turn.skill_note
    agent.set_skill("support", "high")
    assert "Skill: support" in agent.turn.skill_note
    ctx = llm.ChatContext()
    ctx.add_message(role="system", content=load_instructions())
    ctx.add_message(role="user", content="hi")
    texts = [m.text_content or "" for m in assemble(ctx, agent.turn).messages()]
    assert texts[0] == load_instructions()  # the fixed block did not change
    assert "Skill: support" in texts[1]


def test_the_skill_tests_are_found_through_the_root_setting() -> None:
    """In the Docker image the code lives in /app, so the test files are looked up from there."""
    from settings import REPO_ROOT

    assert DATASETS == REPO_ROOT / "evals" / "datasets" / "l2_single_replies"
