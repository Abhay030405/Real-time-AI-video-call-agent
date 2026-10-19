import asyncio
from typing import Any

import pytest
from livekit.agents import AgentSession, llm

import rules_check
from conductor.agent import VaaniAgent, has_words, load_instructions
from reliability.filler import FillerTimer
from tests.fakes import FakeLLM, FakeStream, silent_then_says


def test_the_instructions_load_and_are_plain_text() -> None:
    text = load_instructions()
    assert "Vaani" in text and "AI" in text
    assert "{" not in text  # nothing that changes during a session goes in a fixed layer


def test_has_words_ignores_role_only_chunks() -> None:
    assert has_words("hi")
    assert not has_words("")
    assert has_words(llm.ChatChunk(id="1", delta=llm.ChoiceDelta(role="assistant", content="hi")))
    assert not has_words(llm.ChatChunk(id="1", delta=llm.ChoiceDelta(role="assistant")))


def recording_fake(seen: list[llm.ChatContext]) -> FakeLLM:
    async def behaviour(stream: FakeStream) -> None:
        seen.append(stream.chat_ctx)
        stream.send(
            llm.ChatChunk(id="x", delta=llm.ChoiceDelta(role="assistant", content="Hello there."))
        )

    return FakeLLM("recorder", behaviour)


async def test_a_turn_reaches_the_brain_with_the_instructions() -> None:
    seen: list[llm.ChatContext] = []
    async with AgentSession(llm=recording_fake(seen)) as session:
        await session.start(VaaniAgent(load_instructions()))
        result = await session.run(user_input="Hi Vaani")
        result.expect.next_event().is_message(role="assistant")
    messages = [m for m in seen[0].messages() if m.role == "system"]
    assert any("Vaani" in (m.text_content or "") for m in messages)


async def test_the_rules_check_runs_after_each_spoken_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hook runs for a real spoken turn (not for the text shortcut used by session.run)."""
    seen_text: list[str] = []

    def fake_check(text: str) -> rules_check.RulesResult:
        seen_text.append(text)
        return rules_check.RulesResult(overrides=("Be extra gentle.",))

    monkeypatch.setattr(rules_check, "check", fake_check)
    agent = VaaniAgent(load_instructions())
    turn_ctx = llm.ChatContext()
    message = llm.ChatMessage(role="user", content=["I had a bad day"])
    await agent.on_user_turn_completed(turn_ctx, message)
    assert seen_text == ["I had a bad day"]
    assert [m.text_content for m in turn_ctx.messages()] == ["Be extra gentle."]


async def test_no_override_means_nothing_is_added() -> None:
    agent = VaaniAgent(load_instructions())
    turn_ctx = llm.ChatContext()
    await agent.on_user_turn_completed(turn_ctx, llm.ChatMessage(role="user", content=["hi"]))
    assert turn_ctx.messages() == []


async def test_a_late_first_word_plays_one_filler() -> None:
    played: list[str] = []
    timer = FillerTimer(0.05, lambda: played.append("hmm"))
    slow: Any = FakeLLM("slow", lambda s: silent_then_says(s, delay_s=0.3))
    async with AgentSession(llm=slow) as session:
        await session.start(VaaniAgent(load_instructions(), filler=timer))
        await session.run(user_input="Hello")
    await asyncio.sleep(0.01)
    assert played == ["hmm"]
