"""Pre-recorded clips in Vaani's voice: the "hmm" fillers and the apologies.

They are made once by `scripts/make_clips.py` and saved in `assets/audio/`. Playing a clip
needs no voice service, so it still works when the voice is down.
"""

from __future__ import annotations

import random
import wave
from collections.abc import AsyncIterator
from pathlib import Path

from livekit import rtc

AGENT_DIR = Path(__file__).resolve().parents[1]


def audio_dir() -> Path:
    """`assets/audio` in the repository, or next to the code inside the Docker image."""
    for candidate in (AGENT_DIR / "assets" / "audio", AGENT_DIR.parent / "assets" / "audio"):
        if candidate.is_dir():
            return candidate
    return AGENT_DIR.parent / "assets" / "audio"


class ClipLibrary:
    def __init__(self, root: Path | None = None, rng: random.Random | None = None) -> None:
        self._root = root or audio_dir()
        self._rng = rng or random.Random()
        self._last_filler: Path | None = None

    def fillers(self) -> list[Path]:
        return sorted((self._root / "fillers").glob("*.wav"))

    def pick_filler(self) -> Path | None:
        """A random filler, never the same one twice in a row."""
        options = self.fillers()
        if len(options) > 1 and self._last_filler in options:
            options.remove(self._last_filler)
        if not options:
            return None
        self._last_filler = self._rng.choice(options)
        return self._last_filler

    def apology(self) -> Path | None:
        path = self._root / "apologies" / "stt_failure.wav"
        return path if path.is_file() else None

    def ask_repeat(self) -> Path | None:
        path = self._root / "apologies" / "ask_repeat.wav"
        return path if path.is_file() else None


async def frames_from_wav(path: Path, chunk_ms: int = 100) -> AsyncIterator[rtc.AudioFrame]:
    """Read a mono 16-bit wav file as audio frames the session can play."""
    with wave.open(str(path), "rb") as wav:
        rate, channels, width = wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
        if width != 2:
            raise ValueError(f"{path.name}: expected 16-bit audio, got {width * 8}-bit")
        per_chunk = rate * chunk_ms // 1000
        while True:
            data = wav.readframes(per_chunk)
            if not data:
                return
            yield rtc.AudioFrame(
                data=data,
                sample_rate=rate,
                num_channels=channels,
                samples_per_channel=len(data) // (2 * channels),
            )
