"""What Jev answered, read into plain values."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Decision:
    skill: str
    skill_probabilities: dict[str, float]
    intensity: str
    heavy: float  # probability of yes
    under_18: float
    hinted_crisis: float
    hinglish: str
    latency_ms: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def skill_probability(self) -> float:
        return self.skill_probabilities.get(self.skill, 0.0)


def parse_decision(answers: dict[str, Any], latency_ms: float = 0.0) -> Decision:
    """Turn Jev's typed answers into a Decision. Raises KeyError if an answer is missing."""
    skill = answers["skill"]
    return Decision(
        skill=skill["choice"],
        skill_probabilities={k: float(v) for k, v in skill["probabilities"].items()},
        intensity=answers["intensity"]["choice"],
        heavy=float(answers["heavy"]["noul"]),
        under_18=float(answers["under_18"]["noul"]),
        hinted_crisis=float(answers["hinted_crisis"]["noul"]),
        hinglish=answers["hinglish"]["choice"],
        latency_ms=latency_ms,
        raw=answers,
    )
