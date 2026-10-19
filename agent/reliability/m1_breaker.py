"""The M1 circuit breaker (V0_04 section 9).

After `fails_before_open` M1 failures in a row, use M2 for `stay_seconds` instead of paying
M1's timeout on every turn. When the time is up M1 gets one more try: a single failure
opens the breaker again, a success closes it for good.
"""

from __future__ import annotations

import time
from collections.abc import Callable


class M1Breaker:
    def __init__(
        self,
        fails_before_open: int,
        stay_seconds: float,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        if fails_before_open < 1:
            raise ValueError("fails_before_open must be at least 1")
        self._fails_before_open = fails_before_open
        self._stay_seconds = stay_seconds
        self._now = now
        self._fails = 0
        self._open_until: float | None = None
        self.opened_count = 0  # how many times the breaker has opened (for the logs)

    @property
    def is_open(self) -> bool:
        """True while M1 should be skipped. Reading it after the time is up lets M1 try again."""
        if self._open_until is None:
            return False
        if self._now() >= self._open_until:
            self._open_until = None
            self._fails = self._fails_before_open - 1  # one more failure opens it again
            return False
        return True

    def record_failure(self) -> None:
        if self.is_open:
            return
        self._fails += 1
        if self._fails >= self._fails_before_open:
            self._open_until = self._now() + self._stay_seconds
            self.opened_count += 1

    def record_success(self) -> None:
        self._fails = 0
        self._open_until = None
