import asyncio
from typing import Any

import pytest
from livekit.agents import AgentSession, StopResponse, llm

from conductor.agent import VaaniAgent, has_words, load_instructions
from reliability.filler import FillerTimer
from rules_check import AGE_ENDING_LINE, CRISIS_OVERRIDE, HELPLINE_LINE
from tests.fakes import FakeLLM, FakeStream, says, silent_then_says


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


class Clock:
    now = 0.0

    def __call__(self) -> float:
        return self.now


async def test_the_rules_check_runs_after_each_spoken_turn() -> None:
    """The hook runs for a real spoken turn (not for the text shortcut used by session.run)."""
    flags: list[str] = []
    clock = Clock()
    agent = VaaniAgent(load_instructions(), clock=clock, flag_sink=flags.append)
    clock.now += 5 * 60  # past the opening minutes
    message = llm.ChatMessage(role="user", content=["I want to end my life"])
    await agent.on_user_turn_completed(llm.ChatContext(), message)
    assert CRISIS_OVERRIDE in agent.turn.overrides  # carried into layer 3 of the reply
    assert "crisis" in flags


async def test_no_override_means_nothing_extra_is_added() -> None:
    clock = Clock()
    agent = VaaniAgent(load_instructions(), clock=clock)
    clock.now += 5 * 60
    message = llm.ChatMessage(role="user", content=["hi"])
    await agent.on_user_turn_completed(llm.ChatContext(), message)
    assert agent.turn.overrides == ()


async def test_a_clearly_under_18_person_gets_the_kind_ending_and_no_brain_reply() -> None:
    ended: list[tuple[str, str]] = []

    async def end_call(reason: str, line: str) -> None:
        ended.append((reason, line))

    agent = VaaniAgent(load_instructions(), end_call=end_call)
    message = llm.ChatMessage(role="user", content=["I am 15 years old"])
    with pytest.raises(StopResponse):
        await agent.on_user_turn_completed(llm.ChatContext(), message)
    await asyncio.sleep(0)
    assert ended == [("under_18", AGE_ENDING_LINE)]


async def test_a_crisis_reply_without_the_numbers_gets_the_helpline_line() -> None:
    quiet_reply = FakeLLM("m", lambda s: says(s, "I am here with you. Please talk to someone."))
    agent = VaaniAgent(load_instructions())
    agent._crisis_reply = True
    async with AgentSession(llm=quiet_reply) as session:
        await session.start(agent)
        await session.run(user_input="I want to die")
        await asyncio.sleep(0.2)
        said = [m.text_content for m in session.history.messages()]
    assert HELPLINE_LINE in said


async def test_a_crisis_reply_that_has_the_numbers_needs_no_extra_line() -> None:
    full = FakeLLM("m", lambda s: says(s, "Please call Tele-MANAS on 14416 or 112 right now."))
    agent = VaaniAgent(load_instructions())
    agent._crisis_reply = True
    async with AgentSession(llm=full) as session:
        await session.start(agent)
        await session.run(user_input="I want to die")
        await asyncio.sleep(0.2)
        said = [m.text_content for m in session.history.messages()]
    assert HELPLINE_LINE not in said


async def test_a_late_first_word_plays_one_filler() -> None:
    played: list[str] = []
    timer = FillerTimer(0.05, lambda: played.append("hmm"))
    slow: Any = FakeLLM("slow", lambda s: silent_then_says(s, delay_s=0.3))
    async with AgentSession(llm=slow) as session:
        await session.start(VaaniAgent(load_instructions(), filler=timer))
        await session.run(user_input="Hello")
    await asyncio.sleep(0.01)
    assert played == ["hmm"]
