from pathlib import Path

import pytest

from settings import SettingsError, is_secret, load_settings
from settings.settings import parse_env_file


def write_env(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_skips_comments_and_blank_lines(tmp_path: Path) -> None:
    path = write_env(tmp_path, "# note\n\nA=1\nB = two \nC=\n")
    assert parse_env_file(path) == {"A": "1", "B": "two", "C": ""}


def test_missing_file_gives_no_values(tmp_path: Path) -> None:
    assert parse_env_file(tmp_path / "nope") == {}


def test_require_names_every_missing_setting(tmp_path: Path) -> None:
    settings = load_settings(write_env(tmp_path, "M1_MODEL=sarvam-105b\nM2_MODEL=\n"))
    with pytest.raises(SettingsError) as err:
        settings.require("M1_MODEL", "M2_MODEL", "S1_MODEL")
    message = str(err.value)
    assert "M2_MODEL" in message and "S1_MODEL" in message and "M1_MODEL" not in message


def test_public_settings_hide_secrets(tmp_path: Path) -> None:
    env = "M1_MODEL=sarvam-105b\nSARVAM_API_KEY=sk_secret_value\nDATABASE_URL=postgres://u:p@h/db\n"
    settings = load_settings(write_env(tmp_path, env))
    assert settings.public() == {"M1_MODEL": "sarvam-105b"}
    assert "sk_secret_value" in settings.secret_values()


def test_fingerprint_changes_with_public_values_only(tmp_path: Path) -> None:
    a = load_settings(write_env(tmp_path, "M1_MODEL=x\nSARVAM_API_KEY=aaaaaaaa\n"))
    b = load_settings(write_env(tmp_path, "M1_MODEL=x\nSARVAM_API_KEY=bbbbbbbb\n"))
    c = load_settings(write_env(tmp_path, "M1_MODEL=y\nSARVAM_API_KEY=aaaaaaaa\n"))
    assert a.fingerprint() == b.fingerprint() != c.fingerprint()


def test_get_float_rejects_text(tmp_path: Path) -> None:
    settings = load_settings(write_env(tmp_path, "FILLER_AFTER_S=1.0\nBAD=abc\n"))
    assert settings.get_float("FILLER_AFTER_S") == 1.0
    with pytest.raises(SettingsError):
        settings.get_float("BAD")


@pytest.mark.parametrize(
    ("name", "secret"),
    [("OPENROUTER_API_KEY", True), ("LIVEKIT_API_SECRET", True), ("REDIS_URL", True),
     ("M1_MODEL", False), ("LIVEKIT_URL", False), ("TEST_MATERIAL_DIR", False)],
)
def test_secret_names(name: str, secret: bool) -> None:
    assert is_secret(name) is secret
