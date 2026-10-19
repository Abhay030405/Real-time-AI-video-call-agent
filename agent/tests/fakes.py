"""Fake models for tests: no network, behaviour chosen by the test."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from livekit.agents import APIConnectionError, llm
from livekit.agents.llm import ChatChunk, ChoiceDelta
from livekit.agents.llm.chat_context import ChatContext
from livekit.agents.llm.tool_context import Tool, ToolChoice
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    APIConnectOptions,
    NotGivenOr,
)

Behaviour = Callable[["FakeStream"], Awaitable[None]]


async def says(stream: FakeStream, text: str = "hello") -> None:
    stream.send(ChatChunk(id="x", delta=ChoiceDelta(role="assistant", content=text)))


async def silent_then_says(stream: FakeStream, delay_s: float = 5.0) -> None:
    """Connects fast, then thinks for too long before the first word."""
    stream.send(ChatChunk(id="x", delta=ChoiceDelta(role="assistant")))  # no words yet
    await asyncio.sleep(delay_s)
    await says(stream)


async def fails(stream: FakeStream) -> None:
    raise APIConnectionError("fake outage", retryable=True)


class FakeStream(llm.LLMStream):
    def __init__(self, fake: FakeLLM, **kwargs: Any) -> None:
        super().__init__(fake, **kwargs)
        self._fake = fake

    def send(self, chunk: ChatChunk) -> None:
        self._event_ch.send_nowait(chunk)

    async def _run(self) -> None:
        self._fake.calls += 1
        await self._fake.behaviour(self)


class FakeLLM(llm.LLM[Any]):
    def __init__(self, name: str, behaviour: Behaviour = says) -> None:
        super().__init__()
        self.name = name
        self.behaviour = behaviour
        self.calls = 0

    @property
    def model(self) -> str:
        return self.name

    @property
    def provider(self) -> str:
        return "fake"

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list[Tool] | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls: NotGivenOr[bool] = NOT_GIVEN,
        tool_choice: NotGivenOr[ToolChoice] = NOT_GIVEN,
        extra_kwargs: NotGivenOr[dict[str, Any]] = NOT_GIVEN,
    ) -> llm.LLMStream:
        return FakeStream(self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options)
