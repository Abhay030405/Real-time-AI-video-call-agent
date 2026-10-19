"""Watches the speech-to-text and decides when to ask again or end the call (RE-D9).

Pure logic: it is told what happened and says what to do. The session wiring does the doing.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from reliability.stt_failure_rule import SttAction, SttFailureRule


class SttGuard:
    def __init__(
        self,
        rule: SttFailureRule,
        min_speech_s: float,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._rule = rule
        self._min_speech_s = min_speech_s
        self._now = now
        self._speech_started: float | None = None

    def on_user_state(self, old: str, new: str) -> None:
        """The person started or stopped speaking (from the voice detector)."""
        if new == "speaking":
            self._speech_started = self._now()
        elif old == "speaking" and self._speech_started is not None:
            spoke_for = self._now() - self._speech_started
            self._speech_started = None
            if spoke_for >= self._min_speech_s:  # a cough or a click does not count as a turn
                self._rule.expect_transcript()

    def on_transcript(self) -> SttAction:
        return self._rule.on_transcript()

    def on_error(self) -> SttAction:
        return self._rule.on_error()

    def poll(self) -> SttAction:
        return self._rule.poll()
