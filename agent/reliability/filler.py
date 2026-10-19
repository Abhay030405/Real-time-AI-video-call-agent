"""The "hmm" filler timer (V0_04 section 9).

If the brain has no first word after `after_s` seconds, one short pre-recorded filler plays
so the person does not sit in silence. It plays at most once per reply.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
from collections.abc import Awaitable, Callable


class FillerTimer:
    def __init__(self, after_s: float, play: Callable[[], Awaitable[None] | None]) -> None:
        self._after_s = after_s
        self._play = play
        self._task: asyncio.Task[None] | None = None
        self.fired = False

    def start(self) -> None:
        """Call when the request to the brain goes out."""
        self.cancel()
        self.fired = False
        self._task = asyncio.create_task(self._wait())

    def first_word(self) -> None:
        """Call when the brain's first word arrives. Stops the timer."""
        self.cancel()

    def cancel(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = None

    async def _wait(self) -> None:
        await asyncio.sleep(self._after_s)
        self.fired = True
        with contextlib.suppress(Exception):  # a failed filler must never break the reply
            result = self._play()
            if inspect.isawaitable(result):
                await result
