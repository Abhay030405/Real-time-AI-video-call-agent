"""Makes the pre-recorded clips in Vaani's voice (fillers and apologies).

    uv run --project agent python scripts/make_clips.py

Uses the Cartesia voice from `.env` and saves 16-bit mono wav files in `assets/audio/`.
Run it again whenever the voice or the model changes, then listen to the clips before
committing them. The files are small and are part of the repository (they are not test
recordings).
"""

from __future__ import annotations

import asyncio
import sys
import wave
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "agent"))

from livekit.agents.utils import http_context  # noqa: E402

from settings import load_settings  # noqa: E402
from vendors.voice.voice import build_cartesia  # noqa: E402

CLIPS: dict[str, str] = {
    "fillers/hmm_01": "Hmm...",
    "fillers/hmm_02": "Hmm, ek second.",
    "fillers/hmm_03": "Mm, let me think.",
    "fillers/hmm_04": "Achha... hmm.",
    "fillers/hmm_05": "Hmm, interesting.",
    "fillers/hmm_06": "Umm... bas ek second.",
    "apologies/stt_failure": (
        "Sorry, I am having trouble hearing you right now. Let us try again in a moment."
    ),
    "apologies/ask_repeat": "Sorry, I did not catch that. Could you say it again?",
}


async def main() -> int:
    settings = load_settings()
    voice = build_cartesia(settings)
    out_root = REPO_ROOT / "assets" / "audio"
    async with http_context.open():
        for name, text in CLIPS.items():
            data = b""
            rate = 0
            async for event in voice.synthesize(text):
                data += bytes(event.frame.data)
                rate = event.frame.sample_rate
            path = out_root / f"{name}.wav"
            path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(rate)
                wav.writeframes(data)
            seconds = len(data) / 2 / rate
            print(f"{name}.wav  {seconds:.1f} s  {text!r}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
