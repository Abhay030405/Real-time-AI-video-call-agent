"""Cartesia with Sarvam Bulbul behind it. LiveKit's voice fallback switches if Cartesia fails."""

from __future__ import annotations

from typing import Any

import aiohttp
from livekit.agents import tts
from livekit.plugins import cartesia, sarvam

from settings import Settings

_NEEDED = (
    "CARTESIA_API_KEY",
    "CARTESIA_VOICE_ID",
    "CARTESIA_MODEL",
    "CARTESIA_LANGUAGE",
    "CARTESIA_SAMPLE_RATE",
    "CARTESIA_WORD_TIMESTAMPS",
    "SARVAM_API_KEY",
    "BULBUL_MODEL",
    "BULBUL_SPEAKER",
    "BULBUL_LANGUAGE",
)


def build_cartesia(
    settings: Settings, http_session: aiohttp.ClientSession | None = None
) -> tts.TTS[Any]:
    return cartesia.TTS(
        api_key=settings.get("CARTESIA_API_KEY"),
        model=settings.get("CARTESIA_MODEL"),
        voice=settings.get("CARTESIA_VOICE_ID"),
        language=settings.get("CARTESIA_LANGUAGE"),
        sample_rate=settings.get_int("CARTESIA_SAMPLE_RATE"),
        word_timestamps=settings.get("CARTESIA_WORD_TIMESTAMPS") == "true",
        http_session=http_session,
    )


def build_bulbul(
    settings: Settings, http_session: aiohttp.ClientSession | None = None
) -> tts.TTS[Any]:
    return sarvam.TTS(
        api_key=settings.get("SARVAM_API_KEY"),
        model=settings.get("BULBUL_MODEL"),
        speaker=settings.get("BULBUL_SPEAKER"),
        target_language_code=settings.get("BULBUL_LANGUAGE"),
        speech_sample_rate=settings.get_int("CARTESIA_SAMPLE_RATE"),  # same rate on both voices
        http_session=http_session,
    )


def build_voice(settings: Settings) -> tts.TTS[Any]:
    """The voice used in the call: Cartesia, with Bulbul taking over if Cartesia fails."""
    settings.require(*_NEEDED)
    return tts.FallbackAdapter(
        [build_cartesia(settings), build_bulbul(settings)],
        sample_rate=settings.get_int("CARTESIA_SAMPLE_RATE"),
    )


def describe_voice(settings: Settings) -> dict[str, dict[str, str]]:
    return {
        "voice": {
            "provider": "cartesia",
            "model": settings.get("CARTESIA_MODEL"),
            "voice_id": settings.get("CARTESIA_VOICE_ID"),
            "language": settings.get("CARTESIA_LANGUAGE"),
            "sample_rate": settings.get("CARTESIA_SAMPLE_RATE"),
        },
        "backup_voice": {
            "provider": "sarvam",
            "model": settings.get("BULBUL_MODEL"),
            "speaker": settings.get("BULBUL_SPEAKER"),
            "language": settings.get("BULBUL_LANGUAGE"),
        },
    }
