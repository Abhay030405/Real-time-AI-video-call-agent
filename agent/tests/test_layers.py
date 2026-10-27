import re

from livekit.agents import llm

from conductor.agent import VaaniAgent
from conductor.layers import (
    TurnContext,
    assemble,
    fingerprints,
    fixed_instructions,
    session_note,
)


def base_context() -> llm.ChatContext:
    ctx = llm.ChatContext()
    ctx.add_message(role="system", content=fixed_instructions())
    ctx.add_message(role="user", content="Hi")
    ctx.add_message(role="assistant", content="Hello!")
    ctx.add_message(role="user", content="How are you?")
    return ctx


def roles_and_text(ctx: llm.ChatContext) -> list[tuple[str, str]]:
    return [(m.role, m.text_content or "") for m in ctx.messages()]


def test_the_fixed_layers_carry_the_safety_and_honesty_rules() -> None:
    text = fixed_instructions()
    for must in ("14416", "112", "under 18", "human or an AI", "forget that", "Hinglish", "Vaani"):
        assert must in text, must
    # the priority order is stated
    assert text.index("safety") < text.index("honesty") < text.index("trust")


def test_the_fixed_layers_hold_nothing_that_changes() -> None:
    text = fixed_instructions()
    assert not re.search(r"\{|\}|<[a-z_]+>", text)  # no placeholders to fill in
    assert not re.search(r"\b(20\d\d|\d{1,2}:\d{2})\b", text)  # no dates or clock times
    assert fixed_instructions() == fixed_instructions()  # identical on every call


def test_the_fixed_layers_stay_small_so_replies_stay_fast() -> None:
    assert len(fixed_instructions().split()) <= 1500


def test_the_fixed_layers_have_a_fingerprint_per_layer() -> None:
    prints = fingerprints()
    assert set(prints) == {"layer0", "layer1"}
    assert all(v.startswith("sha256:") for v in prints.values())


def test_order_is_fixed_then_layers_2_and_3_then_turns_then_session_note() -> None:
    turn = TurnContext(
        session_context="Earlier: they talked about exams.",
        skill_note="Skill: support.",
        overrides=("Be extra gentle.",),
        session_note="Session note: minute 3.",
    )
    out = roles_and_text(assemble(base_context(), turn))
    texts = [t for _, t in out]
    assert texts[0] == fixed_instructions()
    assert texts[1] == "Earlier: they talked about exams."
    assert texts[2] == "Skill: support.\nBe extra gentle."
    assert texts[3:7] == ["Hi", "Hello!", "How are you?"] + [texts[6]]
    assert texts[-1] == "Session note: minute 3."


def test_empty_layers_add_nothing() -> None:
    out = roles_and_text(assemble(base_context(), TurnContext()))
    assert [r for r, _ in out] == ["system", "user", "assistant", "user"]


def test_assembling_never_changes_the_original_or_the_fixed_block() -> None:
    base = base_context()
    before = roles_and_text(base)
    assemble(base, TurnContext(skill_note="Skill: casual chat."))
    assert roles_and_text(base) == before


def test_session_note_says_where_we_are_in_plain_words() -> None:
    note = session_note(minutes_elapsed=0, minutes_total=20, turns_so_far=0)
    assert "minute 1 of 20" in note and "still warming up" in note
    later = session_note(minutes_elapsed=17, minutes_total=20, turns_so_far=40)
    assert "minute 18 of 20" in later and "3 minutes left" in later
    assert "Opening minutes: no" in later


class Clock:
    now = 1000.0

    def __call__(self) -> float:
        return self.now


async def test_the_agent_updates_the_session_note_each_spoken_turn() -> None:
    clock = Clock()
    agent = VaaniAgent(fixed_instructions(), session_minutes=20, clock=clock)
    assert "minute 1 of 20" in agent.turn.session_note
    clock.now += 18 * 60
    await agent.on_user_turn_completed(
        llm.ChatContext(), llm.ChatMessage(role="user", content=["Hello"])
    )
    assert "minute 19 of 20" in agent.turn.session_note
    assert "Turns so far: 1" in agent.turn.session_note
