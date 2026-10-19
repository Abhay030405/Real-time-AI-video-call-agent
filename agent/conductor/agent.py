"""Vaani as a LiveKit agent: her instructions, the rules check, and the filler timer."""

from __future__ import annotations

from collections.abc import AsyncIterable
from pathlib import Path

from livekit.agents import Agent, ModelSettings, llm

import rules_check
from reliability.filler import FillerTimer
from telemetry import TurnRecorder

INSTRUCTIONS_FILE = (
    Path(__file__).resolve().parents[1] / "prompts" / "layer0_identity" / "phase1_placeholder.md"
)


def load_instructions() -> str:
    """The fixed instructions. Layers 0 and 1 never change during a session (rule 3)."""
    return INSTRUCTIONS_FILE.read_text(encoding="utf-8").strip()


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
    ) -> None:
        super().__init__(instructions=instructions)
        self._filler = filler
        self._recorder = recorder

    async def on_user_turn_completed(
        self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage
    ) -> None:
        """Step 4 of a turn: the rules check (plain code) adds any override for this reply."""
        result = rules_check.check(new_message.text_content or "")
        for override in result.overrides:
            turn_ctx.add_message(role="system", content=override)

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.Tool],
        model_settings: ModelSettings,
    ) -> AsyncIterable[llm.ChatChunk | str]:
        """Ask the brain. If the first word is late, one filler plays (V0_04 section 9)."""
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
