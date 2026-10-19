"""Entry point of the Vaani agent: a LiveKit worker that joins each call room.

    uv run main.py start            run the worker (what the Docker image does)
    uv run main.py dev              run with auto-reload while developing
    uv run main.py download-files   fetch the models the agent needs (done at image build)
"""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Callable
from typing import Any

from livekit.agents import AgentSession, JobContext, JobProcess, WorkerOptions, cli
from livekit.plugins import silero

from conductor.session import CallRunner, build_session
from settings import load_settings
from vendors.brain import BrainFallback

logger = logging.getLogger("vaani.agent")


def prewarm(proc: JobProcess) -> None:
    """Load the voice detector once per worker process, before any call arrives."""
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext) -> None:
    settings = load_settings()
    await ctx.connect()
    brain_events: list[Callable[[str], None]] = []
    session = build_session(
        settings,
        voice_detector=ctx.proc.userdata["vad"],
        on_brain_event=lambda what: _tell(brain_events, what),
    )
    runner = CallRunner(settings, session, ctx.room)
    brain_events.append(runner.brain_event)
    poller = runner.connect_events()
    ctx.add_shutdown_callback(lambda: _stop(poller))
    warm_up = asyncio.create_task(_warm_up_brain(session))
    await session.start(agent=runner.agent, room=ctx.room)
    await warm_up
    # The first words of the call: Vaani greets the person (one brain call, like any turn)
    session.generate_reply(instructions="Greet the person warmly in one short sentence.")


async def _warm_up_brain(session: AgentSession[Any]) -> None:
    brain = session.llm
    if isinstance(brain, BrainFallback):
        await brain.warm_up()


def _tell(listeners: list[Callable[[str], None]], what: str) -> None:
    for listener in listeners:
        listener(what)


async def _stop(task: object) -> None:
    task.cancel()  # type: ignore[attr-defined]


def main() -> None:
    settings = load_settings()
    if "download-files" not in sys.argv:  # downloading models needs no LiveKit settings
        settings.require("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            ws_url=settings.get("LIVEKIT_URL"),
            api_key=settings.get("LIVEKIT_API_KEY"),
            api_secret=settings.get("LIVEKIT_API_SECRET"),
            agent_name=settings.get("AGENT_NAME"),
        )
    )


if __name__ == "__main__":
    main()
