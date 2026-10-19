"""Speech-to-text. Sarvam only, no backup service (RE-D9)."""

from .sarvam_stt import build_speech_to_text, describe_speech_to_text

__all__ = ["build_speech_to_text", "describe_speech_to_text"]
