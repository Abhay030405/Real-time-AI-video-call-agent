"""Builds the call session and connects the reliability rules to its events."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from livekit import rtc
from livekit.agents import AgentSession, vad
from livekit.agents.voice.turn import TurnHandlingOptions
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from conductor.agent import VaaniAgent, load_instructions
from conductor.clips import ClipLibrary, frames_from_wav
from conductor.guard import SttGuard
from reliability.filler import FillerTimer
from reliability.stt_failure_rule import SttAction, SttFailureRule
from settings import Settings
from vendors.brain import build_brain
from vendors.speech_to_text import build_speech_to_text
from vendors.voice import build_voice

logger = logging.getLogger("vaani.conductor")

END_TOPIC = "vaani.session_end"
TURN_MODES = ("multilingual", "vad", "stt", "manual")


def turn_handling(settings: Settings) -> TurnHandlingOptions:
    """Who decides the person has finished. `manual` is the version 0.5 plug-in point."""
    mode = settings.get("TURN_DETECTION") or "multilingual"
    if mode not in TURN_MODES:
        raise ValueError(f"TURN_DETECTION must be one of {TURN_MODES}, got {mode!r}")
    return {
        "turn_detection": MultilingualModel() if mode == "multilingual" else mode,  # type: ignore[typeddict-item]
        # One main AI call per turn (rule 1): no speculative early calls
        "preemptive_generation": {"enabled": False},
        # The adaptive mode needs LiveKit Cloud's servers; the plain voice detector works anywhere
        "interruption": {"mode": "vad"},
    }


def build_session(settings: Settings, voice_detector: vad.VAD) -> AgentSession[Any]:
    return AgentSession(
        stt=build_speech_to_text(settings),
        vad=voice_detector,
        llm=build_brain(settings),
        tts=build_voice(settings),
        turn_handling=turn_handling(settings),
    )


class CallRunner:
    """One call: builds the agent and applies the filler and speech-to-text failure rules."""

    def __init__(self, settings: Settings, session: AgentSession[Any], room: rtc.Room) -> None:
        self._settings = settings
        self._session = session
        self._room = room
        self._clips = ClipLibrary()
        self._guard = SttGuard(
            SttFailureRule(
                fails_in_a_row=settings.get_int("STT_FAILS_IN_A_ROW"),
                no_response_limit_s=settings.get_float("STT_NO_RESPONSE_LIMIT_S"),
            ),
            min_speech_s=settings.get_float("STT_MIN_SPEECH_S"),
        )
        self._filler = FillerTimer(settings.get_float("FILLER_AFTER_S"), self._play_filler)
        self._ending = False
        self.agent = VaaniAgent(load_instructions(), filler=self._filler)

    # ---- wiring ----

    def connect_events(self) -> asyncio.Task[None]:
        self._session.on("user_state_changed", self._on_user_state)
        self._session.on("user_input_transcribed", self._on_transcript)
        self._session.on("error", self._on_error)
        return asyncio.create_task(self._poll_loop(), name="stt-no-response-poll")

    def _on_user_state(self, event: Any) -> None:
        self._guard.on_user_state(str(event.old_state), str(event.new_state))

    def _on_transcript(self, event: Any) -> None:
        if event.is_final:
            self._guard.on_transcript()

    def _on_error(self, event: Any) -> None:
        source = str(getattr(event.error, "type", "")) + str(event.source)
        logger.warning("session error from %s: %s", source, event.error)
        if "stt" in source.lower():
            asyncio.create_task(self._act(self._guard.on_error()))

    async def _poll_loop(self) -> None:
        while not self._ending:
            await asyncio.sleep(0.5)
            await self._act(self._guard.poll())

    # ---- actions ----

    async def _act(self, action: SttAction) -> None:
        if action is SttAction.ASK_REPEAT:
            await self._play_clip(self._clips.ask_repeat(), fallback_text="Sorry, say that again?")
        elif action is SttAction.APOLOGISE_AND_END:
            await self.end_call("stt_failure")

    async def _play_filler(self) -> None:
        await self._play_clip(self._clips.pick_filler(), fallback_text=None)

    async def _play_clip(self, clip: Path | None, fallback_text: str | None) -> None:
        if clip is not None:
            self._session.say(clip.stem, audio=frames_from_wav(clip), add_to_chat_ctx=False)
        elif fallback_text:
            self._session.say(fallback_text, add_to_chat_ctx=False)

    async def end_call(self, reason: str) -> None:
        """Apology, clean end, and a note to the web page so it can offer to start again."""
        if self._ending:
            return
        self._ending = True
        clip = self._clips.apology()
        if clip is not None:
            handle = self._session.say(
                clip.stem, audio=frames_from_wav(clip), add_to_chat_ctx=False
            )
            await handle.wait_for_playout()
        rejoin_minutes = self._settings.get_int("REJOIN_VALID_MINUTES")
        await self._notify_end(reason, rejoin_minutes)
        await self._session.aclose()

    async def _notify_end(self, reason: str, rejoin_minutes: int) -> None:
        note = {"reason": reason, "rejoin_until": int(time.time()) + rejoin_minutes * 60}
        try:
            await self._room.local_participant.publish_data(
                json.dumps(note), topic=END_TOPIC, reliable=True
            )
        except Exception:
            logger.exception("could not tell the web page the call ended")

