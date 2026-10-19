import time

import pytest
from livekit.agents import llm

from reliability.m1_breaker import M1Breaker
from tests.fakes import FakeLLM, fails, says, silent_then_says
from vendors.brain.fallback import BrainFallback


def make(m1: FakeLLM, m2: FakeLLM, *, switch_after_s: float = 0.3, fails_before_open: int = 2):
    breaker = M1Breaker(fails_before_open=fails_before_open, stay_seconds=300)
    brain = BrainFallback(
        m1, m2, switch_after_s=switch_after_s, m2_first_word_limit_s=2.0, breaker=breaker
    )
    return brain, breaker


async def ask(brain: BrainFallback) -> tuple[str, float]:
    """Send one turn. Returns the text and how long the first word took."""
    started = time.monotonic()
    first_word_at = 0.0
    text = ""
    async with brain.chat(chat_ctx=llm.ChatContext()) as stream:
        async for chunk in stream:
            if chunk.delta and chunk.delta.content:
                if not text:
                    first_word_at = time.monotonic() - started
                text += chunk.delta.content
    return text, first_word_at


async def test_healthy_m1_answers_and_m2_is_not_used() -> None:
    m1, m2 = FakeLLM("m1", says), FakeLLM("m2", says)
    brain, _ = make(m1, m2)
    text, _ = await ask(brain)
    assert text == "hello"
    assert (m1.calls, m2.calls) == (1, 0)


async def test_m1_error_switches_to_m2_on_the_same_turn() -> None:
    m1, m2 = FakeLLM("m1", fails), FakeLLM("m2", lambda s: says(s, "from m2"))
    brain, _ = make(m1, m2)
    text, _ = await ask(brain)
    assert text == "from m2"
    # M1 is not retried for this turn: M2 answers once. (A second M1 call, if any, is
    # LiveKit's background health probe, which never sits on the reply path.)
    assert m2.calls == 1


async def test_m1_with_no_first_word_in_time_switches_to_m2() -> None:
    m1 = FakeLLM("m1", silent_then_says)  # connects, then thinks for 5 s
    m2 = FakeLLM("m2", lambda s: says(s, "from m2"))
    brain, _ = make(m1, m2, switch_after_s=0.3)
    text, first_word_at = await ask(brain)
    assert text == "from m2"
    assert 0.25 < first_word_at < 1.5  # waited about the limit, then M2 answered


async def test_two_m1_failures_make_m2_go_first_for_a_while() -> None:
    m1, m2 = FakeLLM("m1", fails), FakeLLM("m2", lambda s: says(s, "from m2"))
    brain, breaker = make(m1, m2, fails_before_open=2)
    await ask(brain)  # M1 fails (1st)
    assert not breaker.is_open
    brain._status[0].available = True  # pretend M1 was probed and looked healthy again
    await ask(brain)  # M1 fails (2nd)
    assert breaker.is_open
    m1_calls = m1.calls
    text, _ = await ask(brain)  # breaker open: M2 goes first, M1 is not paid for again
    assert text == "from m2"
    assert m1.calls == m1_calls


async def test_a_good_m1_answer_resets_the_failure_count() -> None:
    m1, m2 = FakeLLM("m1", says), FakeLLM("m2", says)
    brain, breaker = make(m1, m2, fails_before_open=2)
    breaker.record_failure()
    await ask(brain)  # M1 answers fine
    breaker.record_failure()
    assert not breaker.is_open  # the earlier failure was forgotten


async def test_if_both_fail_the_error_reaches_the_caller() -> None:
    brain, _ = make(FakeLLM("m1", fails), FakeLLM("m2", fails))
    with pytest.raises(Exception, match="all LLMs failed"):
        await ask(brain)


async def test_warm_up_sends_one_small_request_to_m1_and_survives_failure() -> None:
    m1, m2 = FakeLLM("m1", says), FakeLLM("m2", says)
    brain, _ = make(m1, m2)
    await brain.warm_up()
    assert (m1.calls, m2.calls) == (1, 0)

    broken_m1 = FakeLLM("m1", fails)
    brain2, _ = make(broken_m1, FakeLLM("m2", says))
    await brain2.warm_up()  # must not raise
