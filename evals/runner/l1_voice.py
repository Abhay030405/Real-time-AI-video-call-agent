"""L1 voice: 50 sentences with Hinglish words, Indian names, places and numbers.

For Cartesia and the Bulbul backup it measures the time to the first audio and saves each
clip, so the founder can listen and rate them 1 to 5. Ratings are read from a CSV file the
founder fills in (`ratings.csv` next to the clips). Target: average 4.0 or more and no word
rated 1.
"""

from __future__ import annotations

import asyncio
import csv
import json
import time
import wave
from pathlib import Path
from typing import Any

import aiohttp

from settings import REPO_ROOT, Settings
from telemetry import Prices
from vendors.voice.voice import build_bulbul, build_cartesia

from .l1_models import file_checksum
from .record import CaseResult
from .runner import TestSet

DATASET = REPO_ROOT / "evals" / "datasets" / "l1_voice"
ENGINES = ("cartesia", "bulbul")


def read_sentences(split: str) -> list[dict[str, str]]:
    path = DATASET / split / "sentences.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def clip_folder(settings: Settings, split: str) -> Path:
    root = Path(settings.get_required("TEST_MATERIAL_DIR"))
    return (root if root.is_absolute() else REPO_ROOT / root) / "l1_voice" / "v1" / split


def read_ratings(path: Path) -> dict[tuple[str, str], int]:
    """(sentence id, engine) -> rating 1 to 5, from the founder's CSV. Empty cells are skipped."""
    ratings: dict[tuple[str, str], int] = {}
    if not path.is_file():
        return ratings
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            for engine in ENGINES:
                value = (row.get(f"{engine}_rating") or "").strip()
                if value.isdigit() and 1 <= int(value) <= 5:
                    ratings[(row["id"], engine)] = int(value)
    return ratings


def write_rating_sheet(path: Path, sentences: list[dict[str, str]]) -> None:
    """A CSV for the founder to fill in. Never overwrites a sheet that already has ratings."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "text", "cartesia_rating", "bulbul_rating", "notes"])
        for s in sentences:
            writer.writerow([s["id"], s["text"], "", "", ""])


class _Speaker:
    def __init__(self, settings: Settings, split: str, sentences: list[dict[str, str]]) -> None:
        self.settings = settings
        self.folder = clip_folder(settings, split)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.loop = asyncio.new_event_loop()
        self.http = self.loop.run_until_complete(self._open_session())
        self.engines = {
            "cartesia": build_cartesia(settings, self.http),
            "bulbul": build_bulbul(settings, self.http),
        }
        self.prices = Prices.from_settings(settings)
        self.ratings = read_ratings(self.folder / "ratings.csv")
        write_rating_sheet(self.folder / "ratings.csv", sentences)
        for engine in ENGINES:  # one untimed sentence each, so no case pays for a new connection
            self.loop.run_until_complete(self._speak(engine, "Hello."))

    @staticmethod
    async def _open_session() -> aiohttp.ClientSession:
        return aiohttp.ClientSession()

    async def _speak(self, engine: str, text: str) -> tuple[bytes, int, float]:
        started = time.perf_counter()
        first: float | None = None
        data, rate = b"", 0
        async for event in self.engines[engine].synthesize(text):
            if first is None:
                first = time.perf_counter() - started
            data += bytes(event.frame.data)
            rate = event.frame.sample_rate
        return data, rate, (first or 0.0) * 1000

    def run_case(
        self, case_id: str, repeat: int, sentences: dict[str, dict[str, str]]
    ) -> CaseResult:
        engine, sentence_id = case_id.split(":")
        text = sentences[sentence_id]["text"]
        try:
            data, rate, first_ms = self.loop.run_until_complete(self._speak(engine, text))
        except Exception as error:
            return CaseResult(
                case_id, repeat, text, "spoken audio", hard_checks={"audio_produced": False},
                error=f"{type(error).__name__}: {error}"[:200],
            )
        seconds = len(data) / 2 / rate if rate else 0.0
        words = len(text.split())
        path = self.folder / f"{sentence_id}_{engine}.wav"
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate or 24000)
            wav.writeframes(data)
        soft: dict[str, float] = {}
        hard = {
            "audio_produced": seconds > 0,
            "plausible_length": 0.15 * words <= seconds <= 1.2 * words,
        }
        rating = self.ratings.get((sentence_id, engine))
        if rating is not None:
            soft[f"naturalness_{engine}"] = float(rating)
            hard["no_word_rated_1"] = rating > 1
        chars = len(text)
        usd = self.prices.usd_inr
        cost = (
            chars / 1000 * self.prices.cartesia_usd_per_1k_chars * usd
            if engine == "cartesia"
            else chars / 10000 * self.prices.bulbul_inr_per_10k_chars
        )
        return CaseResult(
            case_id=case_id,
            repeat=repeat,
            input=text,
            expected="clear speech, names and numbers right",
            output=path.name,
            hard_checks=hard,
            soft_scores=soft,
            timings_ms={f"{engine}_first_audio_ms": first_ms},
            cost_inr=round(cost, 4), cost_by={engine: round(cost, 4)},
        )

    def close(self) -> None:
        self.loop.run_until_complete(self.http.close())
        self.loop.close()


def l1_voice_test_set(settings: Settings, split: str = "working") -> TestSet:
    sentences = {s["id"]: s for s in read_sentences(split)}
    speaker = _Speaker(settings, split, list(sentences.values()))
    targets: dict[str, dict[str, Any]] = {
        "naturalness_cartesia": {"min": 4.0},
        "naturalness_bulbul": {"min": 4.0},
    }
    return TestSet(
        name="l1_voice",
        level="L1",
        version="v1",
        split=split,
        case_ids=[f"{engine}:{sid}" for engine in ENGINES for sid in sentences],
        run_case=lambda case_id, repeat: speaker.run_case(case_id, repeat, sentences),
        file_list_checksum=file_checksum(DATASET / split / "sentences.jsonl"),
        targets=targets,
        close=speaker.close,
    )
