"""Live check of our own vendor connections (agent/vendors), with tiny real requests.

    uv run --project agent python scripts/check_vendors.py

Round trip: the Cartesia voice speaks a sentence, Sarvam speech-to-text hears it, the brain
answers it. Also tries the backup voice and the helper. Prints timings, never a key.
Costs a fraction of a rupee. Not part of the quick checks, which stay offline.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

from livekit import rtc  # noqa: E402
from livekit.agents import llm, stt  # noqa: E402
from livekit.agents.utils import http_context  # noqa: E402

from settings import Settings, load_settings  # noqa: E402
from vendors.brain import build_brain, build_s1  # noqa: E402
from vendors.speech_to_text import build_speech_to_text  # noqa: E402
from vendors.voice.voice import build_bulbul, build_cartesia  # noqa: E402

SENTENCE = "Haan yaar, main bilkul theek hoon. Aaj ka din kaisa tha tumhara?"


async def speak(engine: Any, text: str) -> tuple[list[rtc.AudioFrame], float]:
    """Returns the audio frames and the time to the first audio."""
    started = time.perf_counter()
    first: float | None = None
    frames: list[rtc.AudioFrame] = []
    async for event in engine.synthesize(text):
        if first is None:
            first = time.perf_counter() - started
        frames.append(event.frame)
    return frames, first or 0.0


async def hear(settings: Settings, frames: list[rtc.AudioFrame]) -> str:
    stream = build_speech_to_text(settings).stream()
    finals: list[str] = []

    async def read() -> None:
        async for event in stream:
            if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT and event.alternatives:
                finals.append(event.alternatives[0].text)

    reader = asyncio.create_task(read())
    rate = frames[0].sample_rate
    for frame in frames:
        stream.push_frame(frame)
        await asyncio.sleep(frame.duration)  # at the speed of speech
    stream.push_frame(rtc.AudioFrame(b"\x00\x00" * rate * 2, rate, 1, rate * 2))  # 2 s quiet
    stream.end_input()
    await asyncio.wait_for(reader, 20)
    await stream.aclose()
    return " ".join(finals)


async def ask(brain: llm.LLM[Any], text: str) -> tuple[str, float]:
    context = llm.ChatContext()
    context.add_message(role="system", content="You are a warm friend. Answer in one short line.")
    context.add_message(role="user", content=text)
    started = time.perf_counter()
    first: float | None = None
    answer = ""
    async with brain.chat(chat_ctx=context) as stream:
        async for chunk in stream:
            if chunk.delta and chunk.delta.content:
                if first is None:
                    first = time.perf_counter() - started
                answer += chunk.delta.content
    return answer.strip(), first or 0.0


async def main() -> int:
    settings = load_settings()
    failures = 0

    async def step(label: str, work: Any) -> Any:
        nonlocal failures
        try:
            result = await work
            print(f"OK      {label}")
            return result
        except Exception as err:  # a failed step must not hide the others
            failures += 1
            print(f"FAILED  {label}: {type(err).__name__}: {str(err)[:160]}")
            return None

    voice = await step("Cartesia voice", speak(build_cartesia(settings), SENTENCE))
    if voice:
        print(f"        first audio {voice[1]:.2f} s, {len(voice[0])} frames")
    backup = await step("Bulbul backup voice", speak(build_bulbul(settings), SENTENCE))
    if backup:
        print(f"        first audio {backup[1]:.2f} s")
    if voice:
        heard = await step(
            "Sarvam speech-to-text (hears the Cartesia voice)", hear(settings, voice[0])
        )
        if heard is not None:
            print(f"        heard: {heard!r}")
            if "yaar" not in heard.lower():
                failures += 1
                print("FAILED  transcript does not contain 'yaar'")
    answer = await step(
        "Brain M1 (through the fallback)", ask(build_brain(settings), "Aaj bahut thak gaya yaar.")
    )
    if answer:
        print(f"        first word {answer[1]:.2f} s: {answer[0][:80]!r}")
    helper = await step("Helper S1", ask(build_s1(settings), "Say hello in two words."))
    if helper:
        print(f"        first word {helper[1]:.2f} s: {helper[0][:60]!r}")

    print(f"\n{'all passed' if not failures else str(failures) + ' problem(s)'}")
    return 1 if failures else 0


async def run() -> int:
    async with http_context.open():  # the plugins need a shared HTTP session outside the worker
        return await main()


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
