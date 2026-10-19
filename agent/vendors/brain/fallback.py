"""M1 with M2 behind it.

LiveKit's fallback adapter does the switching: no retries, a timeout per attempt, and nothing
resent after the first words. We add our circuit breaker on top: after repeated M1 failures,
M2 goes first for a while, so every turn does not pay M1's timeout again.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from livekit.agents import llm

from reliability.m1_breaker import M1Breaker

from .first_word_guard import FirstWordGuard

logger = logging.getLogger("vaani.brain")


class BrainFallback(llm.FallbackAdapter):
    def __init__(
        self,
        m1: llm.LLM[Any],
        m2: llm.LLM[Any],
        *,
        switch_after_s: float,
        m2_first_word_limit_s: float,
        breaker: M1Breaker,
        on_switch: Callable[[str], None] | None = None,
    ) -> None:
        guarded_m1 = FirstWordGuard(m1)  # enforces the first-word deadline
        super().__init__(
            [guarded_m1, FirstWordGuard(m2, limit_s=m2_first_word_limit_s)],
            attempt_timeout=switch_after_s,  # no first word by then: give up on M1
            max_retry_per_llm=0,  # no blind retries on the live path
            retry_on_chunk_sent=False,  # never resend once words reached the person
        )
        self.breaker = breaker
        self._m1 = guarded_m1
        self._on_switch = on_switch
        self.on("llm_availability_changed", self._availability_changed)
        guarded_m1.on("metrics_collected", self._m1_answered)

    def _llm_order(self) -> list[int]:
        """M2 first while the breaker is open; otherwise M1 first."""
        return [1, 0] if self.breaker.is_open else [0, 1]

    def _availability_changed(self, event: Any) -> None:
        if event.llm is self._m1 and not event.available:
            self.breaker.record_failure()
            logger.warning("M1 failed; breaker open=%s", self.breaker.is_open)
            if self._on_switch is not None:
                self._on_switch("m1_failed")

    def _m1_answered(self, *_: Any) -> None:
        self.breaker.record_success()
