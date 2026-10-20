"""Builds the call session and connects the reliability rules to its events."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from livekit import rtc
from livekit.agents import AgentSession, metrics, vad
from livekit.agents.voice.turn import TurnHandlingOptions
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from background_decisions import BackgroundDecider, DecisionConfig
from conductor.agent import VaaniAgent, load_instructions
from conductor.clips import ClipLibrary, frames_from_wav
from conductor.guard import SttGuard
from conductor.skills import ready_skills
from reliability.filler import FillerTimer
from reliability.stt_failure_rule import SttAction, SttFailureRule
from rules_check import RulesConfig
from settings import REPO_ROOT, Settings
from telemetry import CostMeter, Prices, TelemetryWriter, TurnRecorder
from vendors.brain import build_brain
from vendors.decision_model import build_decision_model
from vendors.speech_to_text import build_speech_to_text
from vendors.voice import build_voice

logger = logging.getLogger("vaani.conductor")

END_TOPIC = "vaani.session_end"
TURN_MODES = ("multilingual", "vad", "stt", "manual")


def accepted_consent(attributes: Mapping[str, str], settings: Settings) -> str | None:
    """The consent wording the person agreed to, if the agent accepts it. None means no call."""
    accepted = {v.strip() for v in settings.get_required("ACCEPTED_CONSENT_VERSIONS").split(",")}
    version = attributes.get("consent_version", "")
    return version if version in accepted else None


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


def build_session(
    settings: Settings,
    voice_detector: vad.VAD,
    on_brain_event: Callable[[str], None] | None = None,
) -> AgentSession[Any]:
    return AgentSession(
        stt=build_speech_to_text(settings),
        vad=voice_detector,
        llm=build_brain(settings, on_switch=on_brain_event),
        tts=build_voice(settings),
        turn_handling=turn_handling(settings),
    )


class CallRunner:
    """One call: builds the agent and applies the filler and speech-to-text failure rules."""

    def __init__(self, settings: Settings, session: AgentSession[Any], room: rtc.Room) -> None:
        self._settings = settings
        self._session = session
        self._room = room
        self._recorder = TurnRecorder()
        self._meter = CostMeter(
            Prices.from_settings(settings),
            {
                "m1": settings.get("M1_MODEL"),
                "m2": settings.get("M2_MODEL"),
                "s1": settings.get("S1_MODEL"),
            },
        )
        folder = Path(settings.get_required("TELEMETRY_DIR"))
        self._writer = TelemetryWriter(
            folder if folder.is_absolute() else REPO_ROOT / folder, room.name or "session"
        )
        self._turns_logged = 0
        self._decider: BackgroundDecider | None = None
        self._jev_model = None
        skills_ready = ready_skills(settings.get_int("SKILL_MIN_TEST_CASES"))
        if settings.get("JEV_ENABLED") == "true" and not skills_ready:
            logger.error("No skill is complete (spec, instructions and tests), so Jev is not used")
        if settings.get("JEV_ENABLED") == "true" and skills_ready:
            self._jev_model = build_decision_model(settings)
            self._decider = BackgroundDecider(
                self._jev_model,
                DecisionConfig(
                    enabled=True,
                    window_turns=settings.get_int("JEV_WINDOW_TURNS"),
                    skill_switch_threshold=settings.get_float("SKILL_SWITCH_THRESHOLD"),
                    heavy_threshold=settings.get_float("JEV_HEAVY_THRESHOLD"),
                    crisis_threshold=settings.get_float("JEV_CRISIS_THRESHOLD"),
                ),
                skills_ready,
                on_event=self._jev_event,
            )
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
        self.agent = VaaniAgent(
            load_instructions(),
            filler=self._filler,
            recorder=self._recorder,
            session_minutes=settings.get_int("SESSION_MINUTES"),
            rules_config=RulesConfig(
                opening_minutes=settings.get_float("RULES_OPENING_MINUTES"),
                wrap_up_minute=settings.get_float("RULES_WRAP_UP_MINUTE"),
                crisis_turns=settings.get_int("RULES_CRISIS_TURNS"),
                jev_under_18_threshold=settings.get_float("RULES_JEV_UNDER_18_THRESHOLD"),
            ),
            flag_sink=self._flag,
            end_call=self.end_call,
        )

    async def warm_up_jev(self) -> None:
        if self._jev_model is not None:
            await self._jev_model.warm_up()

    def record_consent(self, version: str) -> None:
        """Save which consent wording this call was made under (a label, never words)."""
        self._writer.write("session_start", consent_version=version)

    async def refuse_without_consent(self) -> None:
        """No agreement to an accepted wording, no call: tell the page and leave the room."""
        self._writer.write("session_refused", reason="no_consent")
        await self._notify_end("no_consent", 0)
        await self._room.disconnect()

    def brain_event(self, what: str) -> None:
        """Called by the brain when M1 fails and M2 takes over."""
        self._recorder.note(what)

    # ---- wiring ----

    def connect_events(self) -> asyncio.Task[None]:
        self._session.on("user_state_changed", self._on_user_state)
        self._session.on("user_input_transcribed", self._on_transcript)
        self._session.on("error", self._on_error)
        self._session.on("conversation_item_added", self._on_item)
        self._session.on("agent_state_changed", self._on_agent_state)
        self._session.on("metrics_collected", self._on_metrics)
        self._session.on("close", self._on_close)
        return asyncio.create_task(self._poll_loop(), name="stt-no-response-poll")

    def _on_user_state(self, event: Any) -> None:
        self._guard.on_user_state(str(event.old_state), str(event.new_state))
        if str(event.old_state) == "speaking" and str(event.new_state) != "speaking":
            self._recorder.speech_ended()

    # ---- telemetry ----

    def _jev_event(self, kind: str, fields: dict[str, Any]) -> None:
        """Jev's answers and delays are saved as numbers and labels (never words)."""
        try:
            self._writer.write(kind, **fields)
        except Exception:
            logger.exception("could not save a Jev record")

    def _history(self) -> list[tuple[str, str]]:
        return [
            ("user" if m.role == "user" else "assistant", m.text_content or "")
            for m in self._session.history.messages()
            if m.role in ("user", "assistant") and (m.text_content or "").strip()
        ]

    def _on_agent_state(self, event: Any) -> None:
        old, new = str(event.old_state), str(event.new_state)
        if new == "speaking":
            self._recorder.first_audio()
            if self._decider is not None and old != "speaking":
                # The reply has started: now, in the background, Jev reads the last few turns
                self._decider.schedule(self.agent.user_turns, self._history(), self.agent)
        elif old == "speaking":
            self._log_turn()

    def _log_turn(self) -> None:
        """Telemetry must never break a call, so any problem here is only logged."""
        try:
            record = self._recorder.finish()
            if record is None:
                return
            units, cost = self._meter.take()
            self._turns_logged += 1
            self._writer.write("turn", **record, units=units.to_dict(), cost_inr=cost)
        except Exception:
            logger.exception("could not log the turn")

    def _on_metrics(self, event: Any) -> None:
        try:
            self._count_metrics(event.metrics)
        except Exception:
            logger.exception("could not count a metric")

    def _count_metrics(self, m: Any) -> None:
        meta = getattr(m, "metadata", None)
        if isinstance(m, metrics.LLMMetrics):
            role = self._meter.add_llm(
                getattr(meta, "model_name", "") or "", m.prompt_tokens, m.completion_tokens
            )
            if role in ("m1", "m2"):
                self._recorder.set_brain(role)
            self._recorder.add_livekit_ms("llm_ttft", m.ttft * 1000)
        elif isinstance(m, metrics.TTSMetrics):
            provider = getattr(meta, "model_provider", "") or m.label
            self._meter.add_tts(provider, m.characters_count, m.audio_duration)
            self._recorder.add_livekit_ms("tts_ttfb", m.ttfb * 1000)
        elif isinstance(m, metrics.STTMetrics):
            self._meter.add_stt(m.audio_duration)
        elif isinstance(m, metrics.EOUMetrics):
            self._recorder.add_livekit_ms("end_of_utterance_delay", m.end_of_utterance_delay * 1000)
            self._recorder.add_livekit_ms("transcription_delay", m.transcription_delay * 1000)

    def _on_close(self, event: Any) -> None:
        if self._jev_model is not None:
            asyncio.create_task(self._jev_model.aclose())
        try:
            _, cost = self._meter.take()
            self._writer.write(
                "session_summary",
                turns=self._turns_logged,
                units=self._meter.total.to_dict(),
                cost_inr=self._meter.cost_inr(self._meter.total),
                unlogged_cost_inr=cost,
            )
        except Exception:
            logger.exception("could not write the session summary")

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
            self._recorder.note("clip:" + clip.stem)
            self._session.say(clip.stem, audio=frames_from_wav(clip), add_to_chat_ctx=False)
        elif fallback_text:
            self._session.say(fallback_text, add_to_chat_ctx=False)

    def _flag(self, flag: str) -> None:
        """A crisis, heavy-moment or under-18 flag, saved for the founder's review (no words)."""
        self._recorder.note(f"flag:{flag}")
        try:
            self._writer.write("flag", flag=flag, turn=self._turns_logged + 1)
        except Exception:
            logger.exception("could not save a flag")

    def _on_item(self, event: Any) -> None:
        item = event.item
        if getattr(item, "role", None) == "assistant":
            self.agent.rules_state.note_reply(getattr(item, "text_content", "") or "")

    async def end_call(self, reason: str, spoken_text: str | None = None) -> None:
        """A kind or apologetic ending, then a clean close and a note to the web page."""
        if self._ending:
            return
        self._ending = True
        clip = self._clips.apology() if spoken_text is None else None
        if spoken_text is not None:
            await self._session.say(spoken_text, add_to_chat_ctx=False).wait_for_playout()
        elif clip is not None:
            handle = self._session.say(
                clip.stem, audio=frames_from_wav(clip), add_to_chat_ctx=False
            )
            await handle.wait_for_playout()
        rejoin_minutes = self._settings.get_int("REJOIN_VALID_MINUTES")
        await self._notify_end(reason, rejoin_minutes)
        await self._session.aclose()

    async def _notify_end(self, reason: str, rejoin_minutes: int) -> None:
        offer = 0 if reason == "under_18" else rejoin_minutes * 60  # no way back for the age rule
        note = {"reason": reason, "rejoin_until": int(time.time()) + offer}
        try:
            await self._room.local_participant.publish_data(
                json.dumps(note), topic=END_TOPIC, reliable=True
            )
        except Exception:
            logger.exception("could not tell the web page the call ended")

