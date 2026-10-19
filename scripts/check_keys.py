"""Check that every key and model in `.env` works, with one tiny real request each.

    python scripts/check_keys.py

Prints OK or FAILED per account and never prints a key. Exit code is non-zero if any fail.
A few requests cost a tiny amount (the Sarvam and Jev calls use a handful of tokens).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

from settings import Settings, SettingsError, load_settings  # noqa: E402

TIMEOUT_S = 30


def http(
    method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None = None
) -> tuple[int, Any]:
    """One request. Returns (status, parsed JSON or text). Status 0 means no connection."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            raw = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as err:
        raw, status = err.read().decode(), err.code
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        return 0, str(err)
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def livekit_token(key: str, secret: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    claims = {"iss": key, "exp": int(time.time()) + 300, "video": {"roomList": True}}
    payload = _b64(json.dumps(claims).encode())
    signature = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64(signature)}"


def check_livekit(s: Settings) -> str:
    s.require("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
    base = s.get("LIVEKIT_URL").replace("wss://", "https://").replace("ws://", "http://")
    token = livekit_token(s.get("LIVEKIT_API_KEY"), s.get("LIVEKIT_API_SECRET"))
    status, body = http(
        "POST", f"{base}/twirp/livekit.RoomService/ListRooms",
        {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, {},
    )
    if status == 0:
        raise RuntimeError(f"server not reachable at {base}; is it running?")
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {str(body)[:120]}")
    return "key and secret accepted"


def check_cartesia(s: Settings) -> str:
    s.require("CARTESIA_API_KEY", "CARTESIA_VOICE_ID")
    status, body = http(
        "GET", f"https://api.cartesia.ai/voices/{s.get('CARTESIA_VOICE_ID')}",
        {"X-API-Key": s.get("CARTESIA_API_KEY"), "Cartesia-Version": "2025-04-16"},
    )
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {str(body)[:120]}")
    return f"voice found: {body.get('name', 'unnamed')}"


def check_openrouter(s: Settings) -> str:
    s.require("OPENROUTER_API_KEY", "M2_MODEL", "S1_MODEL")
    headers = {"Authorization": f"Bearer {s.get('OPENROUTER_API_KEY')}"}
    status, _ = http("GET", "https://openrouter.ai/api/v1/auth/key", headers)
    if status != 200:
        raise RuntimeError(f"key rejected: HTTP {status}")
    status, models = http("GET", "https://openrouter.ai/api/v1/models", headers)
    if status != 200:
        raise RuntimeError(f"model list failed: HTTP {status}")
    known = {m["id"] for m in models["data"]}
    missing = [m for m in (s.get("M2_MODEL"), s.get("S1_MODEL")) if m not in known]
    if missing:
        raise RuntimeError("model(s) not on OpenRouter: " + ", ".join(missing))
    return "key valid; M2 and S1 models exist"


def check_sarvam(s: Settings) -> str:
    s.require("SARVAM_API_KEY")
    headers = {"api-subscription-key": s.get("SARVAM_API_KEY"), "Content-Type": "application/json"}
    status, body = http(
        "POST", "https://api.sarvam.ai/translate", headers,
        {"input": "Hello", "source_language_code": "en-IN", "target_language_code": "hi-IN"},
    )
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {str(body)[:120]}")
    return "key valid (translate worked)"


def check_m1(s: Settings) -> str:
    s.require("M1_PROVIDER", "M1_MODEL")
    if s.get("M1_PROVIDER") != "sarvam":
        raise RuntimeError(f"no check written yet for M1_PROVIDER={s.get('M1_PROVIDER')}")
    s.require("SARVAM_API_KEY")
    status, body = http(
        "POST", "https://api.sarvam.ai/v1/chat/completions",
        {"api-subscription-key": s.get("SARVAM_API_KEY"), "Content-Type": "application/json"},
        {"model": s.get("M1_MODEL"), "messages": [{"role": "user", "content": "Hi"}],
         "max_tokens": 5},
    )
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {str(body)[:160]}")
    return f"model {s.get('M1_MODEL')} answered"


def check_jev(s: Settings) -> str:
    s.require("TYPESAFE_API_KEY", "JEV_MODEL")
    status, body = http(
        "POST", "https://api.typesafe.ai/v1/systemone",
        {"Authorization": f"Bearer {s.get('TYPESAFE_API_KEY')}",
         "Content-Type": "application/json"},
        {"state": "I had a rough day.", "model": s.get("JEV_MODEL"), "questions": {"mood": {
            "type": "choice", "instructions": "Which fits?",
            "criteria": {"low": "Person is down", "high": "Person is upbeat"}}}},
    )
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {str(body)[:120]}")
    return f"answered with {body.get('model', s.get('JEV_MODEL'))}"


CHECKS: list[tuple[str, Callable[[Settings], str]]] = [
    ("LiveKit", check_livekit),
    ("Cartesia (key and voice ID)", check_cartesia),
    ("OpenRouter (key, M2, S1)", check_openrouter),
    ("Sarvam (key)", check_sarvam),
    ("M1 model", check_m1),
    ("Jev (TypeSafe)", check_jev),
]


def main() -> int:
    settings = load_settings()
    failed = 0
    for label, check in CHECKS:
        try:
            print(f"OK      {label}: {check(settings)}")
        except (RuntimeError, SettingsError) as err:
            failed += 1
            print(f"FAILED  {label}: {err}")
    print(f"\n{len(CHECKS) - failed} of {len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
