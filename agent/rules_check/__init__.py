"""The rules check: plain code that runs before every reply (V0_01 section 2, step 4).

It never calls an AI, so it adds no delay. Phase 1 only keeps the place ready: the checks
(crisis words, heavy-disclosure lock, wrap-up time and so on) are written in Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RulesResult:
    """Extra instructions to add for this turn. Empty means nothing to add."""

    overrides: tuple[str, ...] = ()


def check(user_text: str) -> RulesResult:
    """Look at what the person just said and return any overrides for this turn."""
    return RulesResult()
