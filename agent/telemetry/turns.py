"""Timing of one turn, on this machine's own steady clock (rule 10).

A turn runs: the person stops speaking, the turn is detected, the brain is asked, its first
word arrives, and the first sound plays. Browser times are never mixed in: they would come
from another machine's clock.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Turn:
    number: int
    kind: str  # "user" or "greeting" (the greeting has no person speaking before it)
    speech_ended: float | None = None
    llm_requested: float | None = None
    first_word: float | None = None
    first_audio: float | None = None
    livekit_ms: dict[str, float] = field(default_factory=dict)
    brain: str = "unknown"
    notes: list[str] = field(default_factory=list)


class TurnRecorder:
    def __init__(self, now: Callable[[], float] = time.perf_counter) -> None:
        self._now = now
        self._count = 0
        self._turn: _Turn | None = None

    def _start(self, kind: str) -> _Turn:
        self._count += 1
        self._turn = _Turn(number=self._count, kind=kind)
        return self._turn

    def speech_ended(self) -> None:
        """The person stopped speaking. This starts a new turn."""
        self._start("user").speech_ended = self._now()

    def llm_requested(self) -> None:
        turn = self._turn
        if turn is None or turn.llm_requested is not None:
            turn = self._start("greeting")  # a reply with no person before it
        turn.llm_requested = self._now()

    def first_word(self) -> None:
        if self._turn is not None and self._turn.first_word is None:
            self._turn.first_word = self._now()

    def first_audio(self) -> None:
        if self._turn is not None and self._turn.first_audio is None:
            self._turn.first_audio = self._now()

    def note(self, text: str) -> None:
        if self._turn is not None and text not in self._turn.notes:
            self._turn.notes.append(text)

    def set_brain(self, which: str) -> None:
        if self._turn is not None:
            self._turn.brain = which

    def add_livekit_ms(self, name: str, value_ms: float) -> None:
        if self._turn is not None:
            self._turn.livekit_ms[name] = round(value_ms, 1)

    def finish(self) -> dict[str, Any] | None:
        """Close the current turn and return its timings. None if there is nothing to report."""
        turn, self._turn = self._turn, None
        if turn is None or turn.first_audio is None:
            return None
        stages: dict[str, float] = {}
        if turn.speech_ended is not None and turn.llm_requested is not None:
            stages["turn_detection_ms"] = _ms(turn.llm_requested - turn.speech_ended)
        if turn.llm_requested is not None and turn.first_word is not None:
            stages["first_word_ms"] = _ms(turn.first_word - turn.llm_requested)
        if turn.first_word is not None:
            stages["first_audio_ms"] = _ms(turn.first_audio - turn.first_word)
        start = turn.speech_ended if turn.speech_ended is not None else turn.llm_requested
        if start is not None:
            stages["reply_total_ms"] = _ms(turn.first_audio - start)
        return {
            "turn": turn.number,
            "kind": turn.kind,
            "brain": turn.brain,
            "stages_ms": stages,
            "livekit_ms": turn.livekit_ms,
            "notes": turn.notes,
        }


def _ms(seconds: float) -> float:
    return round(seconds * 1000, 1)
