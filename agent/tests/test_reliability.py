import asyncio

import pytest

from reliability.filler import FillerTimer
from reliability.m1_breaker import M1Breaker
from reliability.stt_failure_rule import SttAction, SttFailureRule


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# ---- M1 circuit breaker ----


def test_breaker_opens_after_two_failures_in_a_row() -> None:
    clock = FakeClock()
    breaker = M1Breaker(fails_before_open=2, stay_seconds=300, now=clock)
    breaker.record_failure()
    assert not breaker.is_open
    breaker.record_failure()
    assert breaker.is_open
    assert breaker.opened_count == 1


def test_a_success_between_failures_keeps_it_closed() -> None:
    breaker = M1Breaker(fails_before_open=2, stay_seconds=300, now=FakeClock())
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    assert not breaker.is_open


def test_breaker_stays_open_then_gives_m1_one_more_try() -> None:
    clock = FakeClock()
    breaker = M1Breaker(fails_before_open=2, stay_seconds=300, now=clock)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(299)
    assert breaker.is_open
    clock.advance(2)
    assert not breaker.is_open  # time is up: M1 is tried again
    breaker.record_failure()  # a single failure now opens it again
    assert breaker.is_open
    assert breaker.opened_count == 2


def test_a_success_after_the_wait_closes_it_for_good() -> None:
    clock = FakeClock()
    breaker = M1Breaker(fails_before_open=2, stay_seconds=300, now=clock)
    breaker.record_failure()
    breaker.record_failure()
    clock.advance(301)
    assert not breaker.is_open
    breaker.record_success()
    breaker.record_failure()
    assert not breaker.is_open


# ---- Speech-to-text failure rule (RE-D9) ----


def test_one_lost_turn_asks_to_repeat() -> None:
    rule = SttFailureRule(fails_in_a_row=2, no_response_limit_s=5, now=FakeClock())
    assert rule.on_error() is SttAction.ASK_REPEAT


def test_two_errors_in_a_row_end_the_call() -> None:
    rule = SttFailureRule(fails_in_a_row=2, no_response_limit_s=5, now=FakeClock())
    rule.on_error()
    assert rule.on_error() is SttAction.APOLOGISE_AND_END


def test_a_good_transcript_resets_the_count() -> None:
    rule = SttFailureRule(fails_in_a_row=2, no_response_limit_s=5, now=FakeClock())
    rule.on_error()
    rule.on_transcript()
    assert rule.on_error() is SttAction.ASK_REPEAT


def test_no_answer_for_five_seconds_ends_the_call() -> None:
    clock = FakeClock()
    rule = SttFailureRule(fails_in_a_row=2, no_response_limit_s=5, now=clock)
    rule.expect_transcript()
    clock.advance(4.9)
    assert rule.poll() is SttAction.NONE
    clock.advance(0.2)
    assert rule.poll() is SttAction.APOLOGISE_AND_END


def test_an_answer_in_time_stops_the_wait() -> None:
    clock = FakeClock()
    rule = SttFailureRule(fails_in_a_row=2, no_response_limit_s=5, now=clock)
    rule.expect_transcript()
    clock.advance(3)
    rule.on_transcript()
    clock.advance(10)
    assert rule.poll() is SttAction.NONE


def test_rules_need_sensible_numbers() -> None:
    with pytest.raises(ValueError):
        M1Breaker(fails_before_open=0, stay_seconds=1)
    with pytest.raises(ValueError):
        SttFailureRule(fails_in_a_row=0, no_response_limit_s=1)


# ---- Filler timer ----


async def test_filler_plays_once_when_the_first_word_is_late() -> None:
    played: list[str] = []
    timer = FillerTimer(0.05, lambda: played.append("hmm"))
    timer.start()
    await asyncio.sleep(0.15)
    assert played == ["hmm"]
    assert timer.fired


async def test_no_filler_when_the_first_word_comes_in_time() -> None:
    played: list[str] = []
    timer = FillerTimer(0.1, lambda: played.append("hmm"))
    timer.start()
    await asyncio.sleep(0.02)
    timer.first_word()
    await asyncio.sleep(0.2)
    assert played == []
    assert not timer.fired


async def test_a_broken_filler_never_breaks_the_reply() -> None:
    def broken() -> None:
        raise RuntimeError("speaker gone")

    timer = FillerTimer(0.01, broken)
    timer.start()
    await asyncio.sleep(0.05)
    assert timer.fired  # it tried; the error was swallowed
