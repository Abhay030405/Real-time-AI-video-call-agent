"""The brain's instructions, built in the same order every turn (V0_04 section 4).

    Layer 0  Identity      fixed          \\  one block, identical on every call so the
    Layer 1  Rules         fixed          /  model's earlier work can be reused (rule 3)
    Layer 2  Session context  changes every ~10 turns (summary of earlier turns)
    Layer 3  Skill and mode note, plus any override from the rules check
    ...the recent turns, word for word...
    Session note   changes every turn, placed last where attention is strongest

Layers 0 and 1 never hold a time, a name or any changing value.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from livekit.agents import llm

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
LAYER0_FILE = PROMPTS / "layer0_identity" / "identity.md"
LAYER1_FILE = PROMPTS / "layer1_rules" / "rules.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def fixed_instructions() -> str:
    """Layers 0 and 1 as one block."""
    return _text(LAYER0_FILE) + "\n\n" + _text(LAYER1_FILE)


def fingerprints() -> dict[str, str]:
    """A fingerprint of each fixed layer, for the result records (every score names its layers)."""

    def sha(path: Path) -> str:
        return "sha256:" + hashlib.sha256(_text(path).encode()).hexdigest()[:16]

    return {"layer0": sha(LAYER0_FILE), "layer1": sha(LAYER1_FILE)}


@dataclass
class TurnContext:
    """The parts that change, set by the Conductor before each reply."""

    session_context: str = ""  # layer 2
    skill_note: str = ""  # layer 3
    overrides: tuple[str, ...] = ()  # from the rules check, part of layer 3
    session_note: str = ""  # last

    def layer3(self) -> str:
        parts = [self.skill_note, *self.overrides]
        return "\n".join(p for p in parts if p)


def assemble(base: llm.ChatContext, turn: TurnContext) -> llm.ChatContext:
    """Fixed block first, then layers 2 and 3, then the turns, then the session note."""
    ctx = base.copy()
    # The fixed block is the first system message; the changing layers go right after it
    position = 1 if ctx.items and getattr(ctx.items[0], "role", None) == "system" else 0
    for text in (turn.session_context, turn.layer3()):
        if text:
            ctx.items.insert(position, llm.ChatMessage(role="system", content=[text]))
            position += 1
    if turn.session_note:
        ctx.add_message(role="system", content=turn.session_note)
    return ctx


def session_note(minutes_elapsed: int, minutes_total: int, turns_so_far: int) -> str:
    """Where we are in the call, in plain words."""
    left = max(minutes_total - minutes_elapsed, 0)
    opening = "yes, still warming up" if minutes_elapsed < 2 else "no"
    return (
        f"Session note: minute {minutes_elapsed + 1} of {minutes_total} ({left} minutes left). "
        f"Turns so far: {turns_so_far}. Opening minutes: {opening}."
    )
