"""Builds the judge model: DeepSeek Flash V4 through OpenRouter (a different family than M1)."""

from __future__ import annotations

from typing import Any

from livekit.agents import llm
from livekit.plugins import openai

from settings import Settings, SettingsError


def build_judge(settings: Settings) -> llm.LLM[Any]:
    settings.require("JUDGE_PROVIDER", "JUDGE_MODEL")
    provider = settings.get("JUDGE_PROVIDER")
    if provider != "openrouter":
        raise SettingsError(f"JUDGE_PROVIDER={provider!r} has no connection yet; use openrouter.")
    key = settings.get("JUDGE_API_KEY") or settings.get_required("OPENROUTER_API_KEY")
    return openai.LLM.with_openrouter(model=settings.get("JUDGE_MODEL"), api_key=key)


def describe_judge(settings: Settings) -> dict[str, str]:
    return {"provider": settings.get("JUDGE_PROVIDER"), "model": settings.get("JUDGE_MODEL")}
