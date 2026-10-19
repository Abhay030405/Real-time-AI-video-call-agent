"""Sarvam realtime speech-to-text, turned into the LiveKit speech-to-text object."""

from __future__ import annotations

from typing import Any

from livekit.agents import stt
from livekit.plugins import sarvam

from settings import Settings

_NEEDED = ("SARVAM_API_KEY", "SARVAM_STT_MODE", "SARVAM_STT_LANGUAGE", "SARVAM_STT_STREAM_TYPE")


def build_speech_to_text(settings: Settings) -> stt.STT[Any]:
    settings.require(*_NEEDED)
    return sarvam.STTRealtime(
        api_key=settings.get("SARVAM_API_KEY"),
        language=settings.get("SARVAM_STT_LANGUAGE"),
        mode=settings.get("SARVAM_STT_MODE"),
        stream_type=settings.get("SARVAM_STT_STREAM_TYPE"),
        sample_rate=16000,
    )


def describe_speech_to_text(settings: Settings) -> dict[str, str]:
    """What goes into the result record and the logs. No secrets."""
    return {
        "provider": "sarvam",
        "model": "saaras:v3-realtime",
        "language": settings.get("SARVAM_STT_LANGUAGE"),
        "mode": settings.get("SARVAM_STT_MODE"),
        "stream_type": settings.get("SARVAM_STT_STREAM_TYPE"),
    }
