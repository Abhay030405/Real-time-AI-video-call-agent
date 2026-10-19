"""Fault tests for the Phase 1 gate: what happens when a part is killed (V0_03, L6).

Fast versions with fake parts. `scripts/fault_checks.py` repeats the same faults against the
real services.
"""

import asyncio
import time

from livekit.agents import AgentSession, tts

from conductor.agent import VaaniAgent, load_instructions
from reliability.filler import FillerTimer
from reliability.m1_breaker import M1Breaker
from reliability.stt_failure_rule import SttAction, SttFailureRule
from tests.fakes import FakeLLM, FakeTTS, fails, says, silent_then_says
from vendors.brain.fallback import BrainFallback


async def test_killing_m1_switches_to_m2_with_one_filler_in_time() -> None:
    """Scaled down: switch limit 0.3 s (really 1.5 s), filler at 0.15 s (really 1.0 s)."""
    played: list[str] = []
    filler = FillerTimer(0.15, lambda: played.append("hmm"))
    brain = BrainFallback(
        FakeLLM("m1", silent_then_says),  # M1 hangs
        FakeLLM("m2", lambda s: says(s, "from m2")),
        switch_after_s=0.3,
        m2_first_word_limit_s=2.0,
        breaker=M1Breaker(fails_before_open=2, stay_seconds=300),
    )
    async with AgentSession(llm=brain) as session:
        await session.start(VaaniAgent(load_instructions(), filler=filler))
        started = time.monotonic()
        result = await session.run(user_input="Hello")
        took = time.monotonic() - started
        result.expect.next_event().is_message(role="assistant")
    assert played == ["hmm"]  # one filler, not more
    assert took < 0.3 + 1.0  # switched at about the limit, then M2 answered


async def test_killing_m1_hard_gives_the_same_answer_path() -> None:
    brain = BrainFallback(
        FakeLLM("m1", fails),
        FakeLLM("m2", lambda s: says(s, "from m2")),
        switch_after_s=0.3,
        m2_first_word_limit_s=2.0,
        breaker=M1Breaker(fails_before_open=2, stay_seconds=300),
    )
    async with AgentSession(llm=brain) as session:
        await session.start(VaaniAgent(load_instructions()))
        result = await session.run(user_input="Hello")
        result.expect.next_event().is_message(role="assistant")


async def test_killing_cartesia_switches_to_the_backup_voice() -> None:
    cartesia, bulbul = FakeTTS("cartesia", broken=True), FakeTTS("bulbul")
    voice = tts.FallbackAdapter([cartesia, bulbul])
    frames = [event.frame async for event in voice.synthesize("Hello there")]
    assert sum(f.samples_per_channel for f in frames) > 0
    assert bulbul.calls >= 1  # the backup spoke


async def test_a_working_cartesia_keeps_the_backup_silent() -> None:
    cartesia, bulbul = FakeTTS("cartesia"), FakeTTS("bulbul")
    voice = tts.FallbackAdapter([cartesia, bulbul])
    _ = [event async for event in voice.synthesize("Hello there")]
    assert (cartesia.calls, bulbul.calls) == (1, 0)


async def test_killing_sarvam_gives_apology_and_a_clean_end() -> None:
    """Errors in a row: ask to repeat once, then apologise and end. Silence ends it too."""
    rule = SttFailureRule(fails_in_a_row=2, no_response_limit_s=0.2)
    assert rule.on_error() is SttAction.ASK_REPEAT
    assert rule.on_error() is SttAction.APOLOGISE_AND_END

    silent = SttFailureRule(fails_in_a_row=2, no_response_limit_s=0.2)
    silent.expect_transcript()
    assert silent.poll() is SttAction.NONE
    await asyncio.sleep(0.25)
    assert silent.poll() is SttAction.APOLOGISE_AND_END
