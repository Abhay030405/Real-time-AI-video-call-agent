"""Builds the three models. M1 and S1 follow their provider setting; M2 is always OpenRouter."""

from __future__ import annotations

from typing import Any

from livekit.agents import llm
from livekit.plugins import openai

from reliability.m1_breaker import M1Breaker
from settings import Settings, SettingsError

from .fallback import BrainFallback


def _key_for(settings: Settings, provider: str, own_key_name: str) -> str:
    """The role's own key if one is set, otherwise the provider's shared key."""
    explicit = settings.get(own_key_name)
    if explicit:
        return explicit
    shared = {"sarvam": "SARVAM_API_KEY", "openrouter": "OPENROUTER_API_KEY"}.get(provider)
    if shared is None:
        raise SettingsError(f"Unknown provider {provider!r}; set {own_key_name} or add support.")
    return settings.get_required(shared)


def build_m1(settings: Settings) -> llm.LLM[Any]:
    """The main brain, called directly. Today that is Sarvam, which speaks the OpenAI format."""
    settings.require("M1_PROVIDER", "M1_MODEL", "M1_BASE_URL")
    provider = settings.get("M1_PROVIDER")
    return openai.LLM(
        model=settings.get("M1_MODEL"),
        base_url=settings.get("M1_BASE_URL"),
        api_key=_key_for(settings, provider, "M1_API_KEY"),
    )


def build_m2(settings: Settings) -> llm.LLM[Any]:
    """The fallback brain: a different model from a different provider, through OpenRouter."""
    settings.require("M2_MODEL", "OPENROUTER_API_KEY")
    return openai.LLM.with_openrouter(
        model=settings.get("M2_MODEL"), api_key=settings.get("OPENROUTER_API_KEY")
    )


def build_s1(settings: Settings) -> llm.LLM[Any]:
    """The cheaper helper for background jobs. It never sits on the reply path."""
    settings.require("S1_PROVIDER", "S1_MODEL")
    provider = settings.get("S1_PROVIDER")
    if provider != "openrouter":
        raise SettingsError(f"S1_PROVIDER={provider!r} has no connection yet; use openrouter.")
    return openai.LLM.with_openrouter(
        model=settings.get("S1_MODEL"), api_key=_key_for(settings, provider, "S1_API_KEY")
    )


def build_brain(settings: Settings) -> BrainFallback:
    """M1 with M2 behind it, using the reliability numbers from `.env`."""
    settings.require(
        "M1_SWITCH_AFTER_S", "M1_FAILS_BEFORE_BREAKER", "M2_STAY_MINUTES", "M2_FIRST_WORD_LIMIT_S"
    )
    breaker = M1Breaker(
        fails_before_open=settings.get_int("M1_FAILS_BEFORE_BREAKER"),
        stay_seconds=settings.get_float("M2_STAY_MINUTES") * 60,
    )
    return BrainFallback(
        build_m1(settings),
        build_m2(settings),
        switch_after_s=settings.get_float("M1_SWITCH_AFTER_S"),
        m2_first_word_limit_s=settings.get_float("M2_FIRST_WORD_LIMIT_S"),
        breaker=breaker,
    )


def describe_brain(settings: Settings) -> dict[str, dict[str, str]]:
    return {
        "brain_m1": {
            "provider": settings.get("M1_PROVIDER"),
            "model": settings.get("M1_MODEL"),
            "base_url": settings.get("M1_BASE_URL"),
        },
        "brain_m2": {"provider": "openrouter", "model": settings.get("M2_MODEL")},
        "helper_s1": {"provider": settings.get("S1_PROVIDER"), "model": settings.get("S1_MODEL")},
        "reliability": {
            "switch_after_s": settings.get("M1_SWITCH_AFTER_S"),
            "m2_first_word_limit_s": settings.get("M2_FIRST_WORD_LIMIT_S"),
            "fails_before_breaker": settings.get("M1_FAILS_BEFORE_BREAKER"),
            "m2_stay_minutes": settings.get("M2_STAY_MINUTES"),
        },
    }
