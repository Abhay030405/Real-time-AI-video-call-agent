"""A scripted call, with no human: joins a room like the web page does, listens to Vaani's
greeting, speaks one sentence (made with the Cartesia voice) and waits for her answer.

    uv run --project agent python scripts/smoke_call.py

Needs the local services running (`docker compose up -d livekit agent web`). Prints how long
each part took, measured on this machine's own clock. Costs a fraction of a rupee.
"""

from __future__ import annotations

import array
import asyncio
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

from livekit import rtc  # noqa: E402
from livekit.agents.utils import http_context  # noqa: E402

from settings import load_settings  # noqa: E402
from vendors.voice.voice import build_cartesia  # noqa: E402

SENTENCE = "Hello Vaani. Aaj mera din bahut accha tha, main bas thoda baat karna chahta hoon."
LOUD = 600  # average sample size that counts as sound, not silence
WAIT_GREETING_S = 25.0
WAIT_REPLY_S = 25.0


def get_pass(web_url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{web_url}/api/token", data=b"{}", headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data: dict[str, Any] = json.loads(response.read())
    return data


def is_loud(frame: rtc.AudioFrame) -> bool:
    samples = array.array("h", bytes(frame.data))
    return bool(samples) and sum(abs(s) for s in samples) / len(samples) > LOUD


class Listener:
    """Notes when the agent's audio is loud, with this machine's steady clock."""

    def __init__(self) -> None:
        self.sound_times: list[float] = []
        self.first_sound = asyncio.Event()

    async def listen(self, track: rtc.Track) -> None:
        async for event in rtc.AudioStream(track):
            if is_loud(event.frame):
                self.sound_times.append(time.perf_counter())
                self.first_sound.set()

    def sound_after(self, moment: float) -> float | None:
        return next((t for t in self.sound_times if t > moment), None)


async def main() -> int:
    settings = load_settings()
    web_url = "http://localhost:3000"
    connection = get_pass(web_url)
    room = rtc.Room()
    listener = Listener()
    tasks: list[asyncio.Task[None]] = []

    @room.on("track_subscribed")
    def on_track(track: rtc.Track, *_: Any) -> None:
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            tasks.append(asyncio.create_task(listener.listen(track)))

    async with http_context.open():
        speech: list[rtc.AudioFrame] = []
        async for event in build_cartesia(settings).synthesize(SENTENCE):
            speech.append(event.frame)

    joined = time.perf_counter()
    await room.connect(connection["serverUrl"], connection["participantToken"])
    rate = speech[0].sample_rate
    source = rtc.AudioSource(rate, 1)
    track = rtc.LocalAudioTrack.create_audio_track("mic", source)
    await room.local_participant.publish_track(
        track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    )

    problems = 0
    try:
        await asyncio.wait_for(listener.first_sound.wait(), WAIT_GREETING_S)
        print(f"OK      Vaani greeted us {listener.sound_times[0] - joined:.2f} s after joining")
    except TimeoutError:
        problems += 1
        print(f"FAILED  no greeting within {WAIT_GREETING_S:.0f} s (is the agent running?)")
        await room.disconnect()
        return 1

    await asyncio.sleep(6)  # let the greeting finish
    spoken_end = time.perf_counter()
    for frame in speech:
        await source.capture_frame(frame)
    await source.wait_for_playout()
    spoken_end = time.perf_counter()
    quiet = rtc.AudioFrame(b"\x00\x00" * (rate // 50), rate, 1, rate // 50)
    for _ in range(100):  # two seconds of quiet, so Vaani can tell we finished
        await source.capture_frame(quiet)
        await asyncio.sleep(0.02)

    deadline = time.perf_counter() + WAIT_REPLY_S
    while time.perf_counter() < deadline and listener.sound_after(spoken_end + 0.5) is None:
        await asyncio.sleep(0.1)
    reply_at = listener.sound_after(spoken_end + 0.5)
    if reply_at is None:
        problems += 1
        print(f"FAILED  no answer within {WAIT_REPLY_S:.0f} s after we spoke")
    else:
        print(f"OK      Vaani answered {reply_at - spoken_end:.2f} s after we stopped speaking")

    await asyncio.sleep(3)
    await room.disconnect()
    for task in tasks:
        task.cancel()
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
