"""Gives a model a deadline for its first word.

LiveKit's own timeout only covers the network, so a model that connects fast but then thinks
for seconds would never be given up on. This wrapper enforces the rule from V0_04 section 9
directly: no first word within the time limit counts as a failure, and the fallback adapter
above it switches to M2. The limit is the `timeout` the adapter passes in (`M1_SWITCH_AFTER_S`).
"""

from __future__ import annotations

import asyncio
import dataclasses
import time
from typing import Any

from livekit.agents import APITimeoutError, llm
from livekit.agents.llm import ChatChunk
from livekit.agents.llm.chat_context import ChatContext, MetricsMetadata
from livekit.agents.llm.tool_context import Tool, ToolChoice
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    APIConnectOptions,
    NotGivenOr,
)


class FirstWordGuard(llm.LLM[Any]):
    def __init__(self, inner: llm.LLM[Any], limit_s: float | None = None) -> None:
        """`limit_s` is this model's own first-word limit. Without it, the limit is whatever
        the fallback adapter passes in (M1's switch time)."""
        super().__init__()
        self._inner = inner
        self._limit_s = limit_s
        inner.on("metrics_collected", self._forward_metrics)

    @property
    def model(self) -> str:
        return self._inner.model

    @property
    def provider(self) -> str:
        return self._inner.provider

    @property
    def metrics_metadata(self) -> MetricsMetadata:
        return self._inner.metrics_metadata

    def _forward_metrics(self, *args: Any, **kwargs: Any) -> None:
        self.emit("metrics_collected", *args, **kwargs)

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
        return _GuardedStream(
            self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
            parallel_tool_calls=parallel_tool_calls,
            tool_choice=tool_choice,
            extra_kwargs=extra_kwargs,
        )

    async def aclose(self) -> None:
        self._inner.off("metrics_collected", self._forward_metrics)
        await super().aclose()


class _GuardedStream(llm.LLMStream):
    def __init__(
        self,
        guard: FirstWordGuard,
        *,
        chat_ctx: ChatContext,
        tools: list[Tool],
        conn_options: APIConnectOptions,
        parallel_tool_calls: NotGivenOr[bool],
        tool_choice: NotGivenOr[ToolChoice],
        extra_kwargs: NotGivenOr[dict[str, Any]],
    ) -> None:
        super().__init__(guard, chat_ctx=chat_ctx, tools=tools, conn_options=conn_options)
        self._guard = guard
        self._parallel_tool_calls = parallel_tool_calls
        self._tool_choice = tool_choice
        self._extra_kwargs = extra_kwargs

    async def _run(self) -> None:
        limit = self._guard._limit_s or self._conn_options.timeout
        conn_options = dataclasses.replace(self._conn_options, timeout=limit)
        started = time.monotonic()
        seen_first_word = False
        async with self._guard._inner.chat(
            chat_ctx=self._chat_ctx,
            tools=self._tools,
            conn_options=conn_options,
            parallel_tool_calls=self._parallel_tool_calls,
            tool_choice=self._tool_choice,
            extra_kwargs=self._extra_kwargs,
        ) as stream:
            chunks = stream.__aiter__()
            while True:
                try:
                    if seen_first_word:
                        chunk: ChatChunk = await chunks.__anext__()
                    else:
                        remaining = max(limit - (time.monotonic() - started), 0.0)
                        chunk = await asyncio.wait_for(chunks.__anext__(), timeout=remaining)
                except StopAsyncIteration:
                    return
                except TimeoutError:
                    raise APITimeoutError(
                        f"no first word within {limit} s", retryable=True
                    ) from None
                if chunk.has_response():
                    seen_first_word = True
                self._event_ch.send_nowait(chunk)
