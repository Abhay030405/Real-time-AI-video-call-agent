import random
import wave
from pathlib import Path

from conductor.clips import ClipLibrary, audio_dir, frames_from_wav
from conductor.guard import SttGuard
from reliability.stt_failure_rule import SttAction, SttFailureRule


def make_wav(path: Path, seconds: float = 0.25, rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x01\x00" * int(rate * seconds))


def test_a_filler_is_never_repeated_twice_in_a_row(tmp_path: Path) -> None:
    for n in range(3):
        make_wav(tmp_path / "fillers" / f"hmm_0{n}.wav")
    library = ClipLibrary(tmp_path, rng=random.Random(1))
    picks = [library.pick_filler() for _ in range(40)]
    assert all(a != b for a, b in zip(picks, picks[1:], strict=False))


def test_no_fillers_means_no_pick(tmp_path: Path) -> None:
    library = ClipLibrary(tmp_path)
    assert library.pick_filler() is None
    assert library.apology() is None


def test_the_real_clips_exist_and_are_enough() -> None:
    library = ClipLibrary(audio_dir())
    assert len(library.fillers()) >= 6  # the Phase 1 plan asks for at least six variants
    assert library.apology() is not None
    assert library.ask_repeat() is not None


async def test_frames_from_wav_reads_all_audio(tmp_path: Path) -> None:
    path = tmp_path / "clip.wav"
    make_wav(path, seconds=0.35, rate=16000)
    frames = [f async for f in frames_from_wav(path, chunk_ms=100)]
    assert sum(f.samples_per_channel for f in frames) == int(16000 * 0.35)
    assert all(f.sample_rate == 16000 for f in frames)


class Clock:
    now = 100.0

    def __call__(self) -> float:
        return self.now


def make_guard(clock: Clock) -> SttGuard:
    rule = SttFailureRule(fails_in_a_row=2, no_response_limit_s=5, now=clock)
    return SttGuard(rule, min_speech_s=1.0, now=clock)


def test_a_short_sound_does_not_make_the_guard_wait_for_words() -> None:
    clock = Clock()
    guard = make_guard(clock)
    guard.on_user_state("listening", "speaking")
    clock.now += 0.3  # a cough
    guard.on_user_state("speaking", "listening")
    clock.now += 20
    assert guard.poll() is SttAction.NONE


def test_real_speech_with_no_transcript_ends_the_call() -> None:
    clock = Clock()
    guard = make_guard(clock)
    guard.on_user_state("listening", "speaking")
    clock.now += 3
    guard.on_user_state("speaking", "listening")
    clock.now += 5.1
    assert guard.poll() is SttAction.APOLOGISE_AND_END


def test_a_transcript_in_time_keeps_the_call_going() -> None:
    clock = Clock()
    guard = make_guard(clock)
    guard.on_user_state("listening", "speaking")
    clock.now += 3
    guard.on_user_state("speaking", "listening")
    clock.now += 1
    guard.on_transcript()
    clock.now += 30
    assert guard.poll() is SttAction.NONE


def test_stt_errors_ask_once_then_end() -> None:
    guard = make_guard(Clock())
    assert guard.on_error() is SttAction.ASK_REPEAT
    assert guard.on_error() is SttAction.APOLOGISE_AND_END
