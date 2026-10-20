"""Vaani as a LiveKit agent: her instructions, the rules check, the filler timer and the
helpline guarantee."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterable, Callable, Coroutine
from typing import Any

from livekit.agents import Agent, ModelSettings, StopResponse, llm

import rules_check
from conductor.layers import TurnContext, assemble, fixed_instructions, session_note
from conductor.skills import DEFAULT_SKILL, load_skill, skill_note
from reliability.filler import FillerTimer
from rules_check import (
    AGE_ENDING_LINE,
    AGE_ENDING_WITH_HELPLINES,
    HELPLINE_LINE,
    RulesConfig,
    RulesState,
)
from rules_check.patterns import mentions_helplines
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


def chunk_text(chunk: llm.ChatChunk | str | object) -> str:
    if isinstance(chunk, str):
        return chunk
    if isinstance(chunk, llm.ChatChunk) and chunk.delta and chunk.delta.content:
        return chunk.delta.content
    return ""


EndCall = Callable[[str, str], Coroutine[Any, Any, None]]  # (reason, spoken text)


class VaaniAgent(Agent):
    def __init__(
        self,
        instructions: str,
        filler: FillerTimer | None = None,
        recorder: TurnRecorder | None = None,
        session_minutes: int = 20,
        clock: Callable[[], float] = time.monotonic,
        rules_config: RulesConfig | None = None,
        flag_sink: Callable[[str], None] | None = None,
        end_call: EndCall | None = None,
    ) -> None:
        super().__init__(instructions=instructions)
        self._filler = filler
        self._recorder = recorder
        self._session_minutes = session_minutes
        self._clock = clock
        self._started = clock()
        self._user_turns = 0
        self._rules_config = rules_config or RulesConfig(
            opening_minutes=2, wrap_up_minute=17, crisis_turns=5, jev_under_18_threshold=0.9
        )
        self.rules_state = RulesState()
        self._flag_sink = flag_sink
        self._end_call = end_call
        self._crisis_reply = False
        self.turn = TurnContext()  # the changing layers, set before each reply
        self.skill = DEFAULT_SKILL  # every call starts in light conversation
        self.intensity = "medium"
        self.set_skill(DEFAULT_SKILL, "medium")
        self._refresh_session_note()

    def set_skill(self, skill: str, intensity: str = "medium") -> None:
        """Change the skill note (layer 3) for the next reply. Layers 0 and 1 do not change."""
        self.skill, self.intensity = skill, intensity
        self.turn.skill_note = skill_note(load_skill(skill), intensity)

    def minutes_elapsed(self) -> float:
        return (self._clock() - self._started) / 60

    def _refresh_session_note(self) -> None:
        minutes = int(self.minutes_elapsed())
        self.turn.session_note = session_note(minutes, self._session_minutes, self._user_turns)

    async def on_user_turn_completed(
        self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage
    ) -> None:
        """Step 4 of a turn: the rules check (plain code) decides what to add for this reply."""
        result = rules_check.check(
            new_message.text_content or "",
            self.rules_state,
            self._rules_config,
            self.minutes_elapsed(),
        )
        self._user_turns += 1
        self.turn.overrides = result.overrides
        self._crisis_reply = result.crisis
        self._refresh_session_note()
        if self._flag_sink is not None:
            for flag in result.flags:
                self._flag_sink(flag)
        if result.end_call_reason is not None and self._end_call is not None:
            line = AGE_ENDING_WITH_HELPLINES if result.crisis else AGE_ENDING_LINE
            asyncio.create_task(self._end_call(result.end_call_reason, line))
            raise StopResponse()  # no brain reply: the kind ending is spoken instead

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.Tool],
        model_settings: ModelSettings,
    ) -> AsyncIterable[llm.ChatChunk | str]:
        """Ask the brain. A late first word plays one filler; a crisis reply gets its numbers."""
        chat_ctx = assemble(chat_ctx, self.turn)  # layers 2 and 3 and the session note
        if self._recorder is not None:
            self._recorder.llm_requested()
        if self._filler is not None:
            self._filler.start()
        reply = ""
        try:
            stream = Agent.default.llm_node(self, chat_ctx, tools, model_settings)
            async for chunk in await _resolve(stream):
                if has_words(chunk):
                    if self._filler is not None:
                        self._filler.first_word()
                    if self._recorder is not None:
                        self._recorder.first_word()
                reply += chunk_text(chunk)
                yield chunk
        finally:
            if self._filler is not None:
                self._filler.cancel()
        # Guarantee: a crisis reply always carries the helpline numbers, even if the AI left
        # them out, by speaking the fixed line straight after it.
        if self._crisis_reply and reply and not mentions_helplines(reply):
            self.session.say(HELPLINE_LINE, add_to_chat_ctx=True)
            if self._recorder is not None:
                self._recorder.note("helpline_line_added")


async def _resolve(result: object) -> AsyncIterable[llm.ChatChunk | str]:
    """The default llm_node may return the stream directly or as an awaitable."""
    if hasattr(result, "__await__"):
        result = await result
    return result  # type: ignore[return-value]
