"""What each call costs, per vendor, in rupees.

The units (tokens, characters, seconds) are counted exactly. The prices come from `.env`
and should be confirmed on each vendor's price page: the units are always logged, so a
wrong price never loses information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from settings import Settings

ROLES = ("m1", "m2", "s1")


@dataclass(frozen=True)
class Prices:
    usd_inr: float
    usd_inr_date: str
    m1_in_inr_per_m: float
    m1_out_inr_per_m: float
    m2_in_usd_per_m: float
    m2_out_usd_per_m: float
    s1_in_usd_per_m: float
    s1_out_usd_per_m: float
    stt_inr_per_hour: float
    bulbul_inr_per_10k_chars: float
    cartesia_usd_per_1k_chars: float

    @classmethod
    def from_settings(cls, s: Settings) -> Prices:
        return cls(
            usd_inr=s.get_float("USD_INR"),
            usd_inr_date=s.get_required("USD_INR_DATE"),
            m1_in_inr_per_m=s.get_float("PRICE_M1_INPUT_INR_PER_M"),
            m1_out_inr_per_m=s.get_float("PRICE_M1_OUTPUT_INR_PER_M"),
            m2_in_usd_per_m=s.get_float("PRICE_M2_INPUT_USD_PER_M"),
            m2_out_usd_per_m=s.get_float("PRICE_M2_OUTPUT_USD_PER_M"),
            s1_in_usd_per_m=s.get_float("PRICE_S1_INPUT_USD_PER_M"),
            s1_out_usd_per_m=s.get_float("PRICE_S1_OUTPUT_USD_PER_M"),
            stt_inr_per_hour=s.get_float("PRICE_SARVAM_STT_INR_PER_HOUR"),
            bulbul_inr_per_10k_chars=s.get_float("PRICE_BULBUL_INR_PER_10K_CHARS"),
            cartesia_usd_per_1k_chars=s.get_float("PRICE_CARTESIA_USD_PER_1K_CHARS"),
        )


@dataclass
class Units:
    """Everything counted since the last time the meter was read."""

    llm_in: dict[str, int] = field(default_factory=lambda: dict.fromkeys(ROLES, 0))
    llm_out: dict[str, int] = field(default_factory=lambda: dict.fromkeys(ROLES, 0))
    cartesia_chars: int = 0
    bulbul_chars: int = 0
    tts_audio_s: float = 0.0
    stt_audio_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "llm_tokens": {r: {"in": self.llm_in[r], "out": self.llm_out[r]} for r in ROLES},
            "cartesia_chars": self.cartesia_chars,
            "bulbul_chars": self.bulbul_chars,
            "tts_audio_s": round(self.tts_audio_s, 2),
            "stt_audio_s": round(self.stt_audio_s, 2),
        }


class CostMeter:
    def __init__(self, prices: Prices, models: dict[str, str]) -> None:
        """`models` maps a role (m1, m2, s1) to its model name, to tell the roles apart."""
        self._prices = prices
        self._role_of = {name: role for role, name in models.items() if name}
        self._units = Units()
        self.total = Units()

    def role_for(self, model_name: str) -> str | None:
        return self._role_of.get(model_name)

    def add_llm(self, model_name: str, tokens_in: int, tokens_out: int) -> str | None:
        role = self.role_for(model_name)
        if role is not None:
            for units in (self._units, self.total):
                units.llm_in[role] += tokens_in
                units.llm_out[role] += tokens_out
        return role

    def add_tts(self, provider: str, characters: int, audio_s: float) -> None:
        for units in (self._units, self.total):
            if "sarvam" in provider.lower():
                units.bulbul_chars += characters
            else:
                units.cartesia_chars += characters
            units.tts_audio_s += audio_s

    def add_stt(self, audio_s: float) -> None:
        for units in (self._units, self.total):
            units.stt_audio_s += audio_s

    def take(self) -> tuple[Units, dict[str, float]]:
        """Units and rupee cost since the last call, then start counting again."""
        units, self._units = self._units, Units()
        return units, self.cost_inr(units)

    def cost_inr(self, u: Units) -> dict[str, float]:
        p = self._prices
        usd = p.usd_inr
        cost = {
            "m1": (u.llm_in["m1"] * p.m1_in_inr_per_m + u.llm_out["m1"] * p.m1_out_inr_per_m)
            / 1e6,
            "m2": (u.llm_in["m2"] * p.m2_in_usd_per_m + u.llm_out["m2"] * p.m2_out_usd_per_m)
            / 1e6
            * usd,
            "s1": (u.llm_in["s1"] * p.s1_in_usd_per_m + u.llm_out["s1"] * p.s1_out_usd_per_m)
            / 1e6
            * usd,
            "speech_to_text": u.stt_audio_s / 3600 * p.stt_inr_per_hour,
            "voice": u.cartesia_chars / 1000 * p.cartesia_usd_per_1k_chars * usd
            + u.bulbul_chars / 10000 * p.bulbul_inr_per_10k_chars,
        }
        cost["total"] = sum(cost.values())
        return {k: round(v, 4) for k, v in cost.items()}
