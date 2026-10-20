"""Runs Jev in the background after the reply has started, and applies its answers to the next turn.

Rules (V0_01 section 5):
- Never on the critical path: the call is started as a background task and never awaited by a reply.
- Sticky: the skill changes only when Jev's probability for a new skill is clearly high.
- If Jev is slow, down or wrong, nothing changes: Vaani keeps the current skill and the plain-code
  rules, which never needed Jev.
- Safety never waits for Jev: its hinted-crisis and under-18 answers are a second safety net that
  feeds the rules check for the NEXT turn.
- Safe to run twice: a result is applied only if no newer turn has already been applied.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from rules_check import RulesState
from vendors.decision_model import DecisionModelError

from .decision import Decision, parse_decision
from .questions import build_questions

logger = logging.getLogger("vaani.jev")

LANGUAGE_NOTES = {
    "none": "The person writes in English so far. Stay in English.",
    "light": "The person uses a few Hindi words. Mirror that lightly.",
    "heavy": "The person mixes Hindi and English freely. Mirror their mix.",
}


@dataclass(frozen=True)
class DecisionConfig:
    enabled: bool
    window_turns: int  # how many recent exchanges Jev reads
    skill_switch_threshold: float
    heavy_threshold: float
    crisis_threshold: float


class SkillTarget(Protocol):
    """What the decider changes: the agent's skill and the language note in layer 2."""

    skill: str
    rules_state: RulesState

    def set_skill(self, skill: str, intensity: str = ...) -> None: ...
    def set_language_note(self, note: str) -> None: ...


class Asker(Protocol):
    async def ask(self, state: str, questions: dict[str, Any]) -> tuple[dict[str, Any], float]: ...


def apply_decision(decision: Decision, target: SkillTarget, config: DecisionConfig) -> list[str]:
    """Apply one decision. Returns short notes about what changed (for the logs)."""
    notes: list[str] = []
    state = target.rules_state
    # Safety answers first: they feed the plain-code rules check on the next turn
    state.jev_heavy = decision.heavy >= config.heavy_threshold
    state.jev_crisis = decision.hinted_crisis >= config.crisis_threshold
    state.jev_under_18 = decision.under_18
    if state.jev_crisis:
        notes.append("jev:crisis_hint")
    # Skill: sticky. Switch only when Jev is clearly sure about a different skill.
    sure = decision.skill_probability >= config.skill_switch_threshold
    if decision.skill != target.skill and sure:
        target.set_skill(decision.skill, decision.intensity)
        notes.append(f"jev:skill->{decision.skill}")
    elif decision.skill == target.skill:
        target.set_skill(target.skill, decision.intensity)  # same skill, new intensity
    target.set_language_note(LANGUAGE_NOTES.get(decision.hinglish, ""))
    return notes


def format_window(history: list[tuple[str, str]], window_turns: int) -> str:
    """The last few exchanges as plain text for Jev. Older turns are left out on purpose."""
    recent = history[-(window_turns * 2) :]
    return "\n".join(f"{'Person' if role == 'user' else 'Vaani'}: {text}" for role, text in recent)


class BackgroundDecider:
    def __init__(
        self,
        model: Asker,
        config: DecisionConfig,
        ready_skills: list[str],
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._model = model
        self._config = config
        self._questions = build_questions(ready_skills)
        self._on_event = on_event
        self._applied_turn = -1
        self._tasks: set[asyncio.Task[None]] = set()

    def schedule(self, turn: int, history: list[tuple[str, str]], target: SkillTarget) -> None:
        """Start a background decision for this turn. Returns at once; never awaited by a reply."""
        if not self._config.enabled or not history:
            return
        task = asyncio.create_task(self._run(turn, history, target), name=f"jev-turn-{turn}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, turn: int, history: list[tuple[str, str]], target: SkillTarget) -> None:
        state_text = format_window(history, self._config.window_turns)
        try:
            answers, latency_ms = await self._model.ask(state_text, self._questions)
            decision = parse_decision(answers, latency_ms)
        except (DecisionModelError, KeyError, ValueError) as error:
            logger.warning("Jev unavailable (turn %s), keeping the current skill: %s", turn, error)
            self._emit(
                "jev_failed",
                {"turn": turn, "reason": type(error).__name__, "detail": str(error)[:120]},
            )
            return
        if turn <= self._applied_turn:  # a newer decision is already in: ignore this late one
            return
        self._applied_turn = turn
        notes = apply_decision(decision, target, self._config)
        self._emit(
            "jev",
            {
                "turn": turn,
                "latency_ms": round(latency_ms, 1),
                "skill": decision.skill,
                "skill_probability": round(decision.skill_probability, 3),
                "intensity": decision.intensity,
                "heavy": round(decision.heavy, 3),
                "under_18": round(decision.under_18, 3),
                "hinted_crisis": round(decision.hinted_crisis, 3),
                "hinglish": decision.hinglish,
                "changes": notes,
            },
        )

    def _emit(self, kind: str, fields: dict[str, Any]) -> None:
        if self._on_event is not None:
            self._on_event(kind, fields)

    async def wait_idle(self) -> None:
        """For tests: wait until every background decision has finished."""
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)
