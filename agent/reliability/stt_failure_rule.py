"""The speech-to-text failure rule (RE-D9).

Sarvam has no backup service, so the rule is: one lost turn means ask the person to
repeat; two errors in a row, or no answer at all for `no_response_limit_s`, means a
pre-recorded apology, a clean end and a rejoin link.
"""

from __future__ import annotations

import enum
import time
from collections.abc import Callable


class SttAction(enum.Enum):
    NONE = "none"
    ASK_REPEAT = "ask_repeat"
    APOLOGISE_AND_END = "apologise_and_end"


class SttFailureRule:
    def __init__(
        self,
        fails_in_a_row: int,
        no_response_limit_s: float,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        if fails_in_a_row < 1:
            raise ValueError("fails_in_a_row must be at least 1")
        self._limit = fails_in_a_row
        self._no_response_limit_s = no_response_limit_s
        self._now = now
        self._fails = 0
        self._waiting_since: float | None = None

    def expect_transcript(self) -> None:
        """The person has stopped speaking, so a transcript should arrive."""
        if self._waiting_since is None:
            self._waiting_since = self._now()

    def on_transcript(self) -> SttAction:
        self._fails = 0
        self._waiting_since = None
        return SttAction.NONE

    def on_error(self) -> SttAction:
        self._waiting_since = None
        self._fails += 1
        if self._fails >= self._limit:
            return SttAction.APOLOGISE_AND_END
        return SttAction.ASK_REPEAT

    def poll(self) -> SttAction:
        """Call from time to time. Ends the call when Sarvam has said nothing for too long."""
        if self._waiting_since is not None and (
            self._now() - self._waiting_since >= self._no_response_limit_s
        ):
            self._waiting_since = None
            return SttAction.APOLOGISE_AND_END
        return SttAction.NONE
