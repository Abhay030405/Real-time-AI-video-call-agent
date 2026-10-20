"""Vaani as a LiveKit agent: her instructions, the rules check, and the filler timer."""

from __future__ import annotations

import time
from collections.abc import AsyncIterable, Callable

from livekit.agents import Agent, ModelSettings, llm

import rules_check
from conductor.layers import TurnContext, assemble, fixed_instructions, session_note
from reliability.filler import FillerTimer
from telemetry import TurnRecorder


def load_instructions() -> str:
    """The fixed instructions. Layers 0 and 1 never change during a session (rule 3)."""
    return fixed_instructions()


def has_words(chunk: llm.ChatChunk | str | object) -> bool:
    """True when this piece of the reply carries actual words (not just a role marker)."""
    if isinstance(chunk, str):
        return bool(chunk)
    if isinstance(chunk, llm.ChatChunk):
        return chunk.has_response()
    return False


class VaaniAgent(Agent):
    def __init__(
        self,
        instructions: str,
        filler: FillerTimer | None = None,
        recorder: TurnRecorder | None = None,
        session_minutes: int = 20,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(instructions=instructions)
        self._filler = filler
        self._recorder = recorder
        self._session_minutes = session_minutes
        self._clock = clock
        self._started = clock()
        self._user_turns = 0
        self.turn = TurnContext()  # the changing layers, set before each reply
        self._refresh_session_note()

    def _refresh_session_note(self) -> None:
        minutes = int((self._clock() - self._started) // 60)
        self.turn.session_note = session_note(minutes, self._session_minutes, self._user_turns)

    async def on_user_turn_completed(
        self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage
    ) -> None:
        """Step 4 of a turn: the rules check (plain code) adds any override for this reply."""
        result = rules_check.check(new_message.text_content or "")
        self._user_turns += 1
        self.turn.overrides = result.overrides
        self._refresh_session_note()

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.Tool],
        model_settings: ModelSettings,
    ) -> AsyncIterable[llm.ChatChunk | str]:
        """Ask the brain. If the first word is late, one filler plays (V0_04 section 9)."""
        chat_ctx = assemble(chat_ctx, self.turn)  # layers 2 and 3 and the session note
        if self._recorder is not None:
            self._recorder.llm_requested()
        if self._filler is not None:
            self._filler.start()
        try:
            stream = Agent.default.llm_node(self, chat_ctx, tools, model_settings)
            async for chunk in await _resolve(stream):
                if has_words(chunk):
                    if self._filler is not None:
                        self._filler.first_word()
                    if self._recorder is not None:
                        self._recorder.first_word()
                yield chunk
        finally:
            if self._filler is not None:
                self._filler.cancel()


async def _resolve(result: object) -> AsyncIterable[llm.ChatChunk | str]:
    """The default llm_node may return the stream directly or as an awaitable."""
    if hasattr(result, "__await__"):
        result = await result
    return result  # type: ignore[return-value]
