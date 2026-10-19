from pathlib import Path

import pytest
from livekit.agents import llm, stt, tts

from settings import REPO_ROOT, Settings, SettingsError, is_secret
from settings.settings import parse_env_file
from vendors.brain import BrainFallback, build_brain, build_m1, build_m2, build_s1, describe_brain
from vendors.speech_to_text import build_speech_to_text, describe_speech_to_text
from vendors.voice import build_voice, describe_voice

FAKE_SECRETS = {
    "SARVAM_API_KEY": "sk_fake_sarvam_value_1234567890",
    "CARTESIA_API_KEY": "sk_car_fake_value_1234567890",
    "OPENROUTER_API_KEY": "sk-or-v1-fake-value-1234567890",
}


def example_settings() -> Settings:
    """The defaults from .env.example, with fake keys: no real .env and no network needed."""
    values = parse_env_file(REPO_ROOT / ".env.example")
    values.update(FAKE_SECRETS)
    return Settings(values=values)


def test_speech_to_text_builds_a_livekit_stt() -> None:
    assert isinstance(build_speech_to_text(example_settings()), stt.STT)


def test_voice_is_cartesia_with_a_backup() -> None:
    voice = build_voice(example_settings())
    assert isinstance(voice, tts.FallbackAdapter)
    assert len(voice._tts_instances) == 2


def test_brain_is_m1_then_m2() -> None:
    brain = build_brain(example_settings())
    assert isinstance(brain, BrainFallback)
    assert isinstance(build_m1(example_settings()), llm.LLM)
    assert isinstance(build_m2(example_settings()), llm.LLM)
    assert isinstance(build_s1(example_settings()), llm.LLM)


def test_the_models_come_from_settings() -> None:
    s = example_settings()
    assert build_m1(s).model == s.get("M1_MODEL") == "sarvam-105b-conversations"
    assert build_m2(s).model == s.get("M2_MODEL")
    assert build_s1(s).model == s.get("S1_MODEL")


@pytest.mark.parametrize(
    "build",
    [build_speech_to_text, build_voice, build_m1, build_m2, build_s1, build_brain],
)
def test_a_missing_setting_stops_with_its_name(build) -> None:  # type: ignore[no-untyped-def]
    values = dict(example_settings().values)
    for name in ("SARVAM_API_KEY", "CARTESIA_API_KEY", "OPENROUTER_API_KEY"):
        values[name] = ""
    with pytest.raises(SettingsError, match="API_KEY"):
        build(Settings(values=values))


def test_unknown_m1_provider_is_refused() -> None:
    values = dict(example_settings().values)
    values["M1_PROVIDER"] = "mystery"
    with pytest.raises(SettingsError, match="mystery"):
        build_m1(Settings(values=values))


def test_descriptions_hold_no_secrets() -> None:
    s = example_settings()
    text = str(describe_speech_to_text(s)) + str(describe_voice(s)) + str(describe_brain(s))
    for secret in FAKE_SECRETS.values():
        assert secret not in text
    assert not any(is_secret(name) for name in describe_brain(s)["brain_m1"])


def test_the_example_settings_have_every_name_the_vendors_need() -> None:
    names = set(parse_env_file(Path(REPO_ROOT / ".env.example")))
    for needed in ("M1_BASE_URL", "CARTESIA_SAMPLE_RATE", "BULBUL_SPEAKER", "SARVAM_STT_MODE"):
        assert needed in names
