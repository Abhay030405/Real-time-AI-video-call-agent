"""The rules check: plain code that runs before every reply (V0_01 section 2, step 4).

It never calls an AI, so it adds no delay, and crisis and age rules never wait for Jev
(hard rule 5). It looks at what the person just said and at what happened earlier in the
call, and returns instructions to add for this reply, flags for the founder's review, and,
for the age rule, a reason to end the call.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import patterns
from .scripts import ADVICE_LINE, AGE_ENDING_LINE, AGE_ENDING_WITH_HELPLINES, HELPLINE_LINE

__all__ = [
    "ADVICE_LINE",
    "AGE_ENDING_LINE",
    "AGE_ENDING_WITH_HELPLINES",
    "HELPLINE_LINE",
    "RulesConfig",
    "RulesResult",
    "RulesState",
    "check",
]

CRISIS_OVERRIDE = (
    "SAFETY OVERRIDE: the person may be thinking about harming themselves or may be in danger. "
    "Stop all humour and playfulness now. Respond with calm, direct care and take it seriously. "
    "Encourage them to reach out right now: Tele-MANAS on 14416 (or 1-800-891-4416), free and "
    "open any time, or 112 if they are in immediate danger, or someone they trust nearby. "
    "Say the numbers out loud. Stay with them and keep talking. Do not end the conversation."
)
HINT_OVERRIDE = (
    "SAFETY CHECK: the person may be hinting that they are thinking about ending their life. "
    "No humour, no laughing, and do not carry on with the previous topic. Say you heard them, "
    "ask gently and directly whether they are thinking about hurting themselves, and mention "
    "Tele-MANAS on 14416. Stay with them."
)
ADVICE_OVERRIDE = (
    "ADVICE LIMIT: the person is asking for medical, legal or money advice. Say plainly that you "
    "cannot advise on this, and name the right person: a doctor or pharmacist, a lawyer, or a "
    "financial adviser. Do not give an opinion on what to do. Stay warm and kind, and do not joke."
)
HEAVY_OVERRIDE = (
    "HEAVY MOMENT: the person just shared something painful. Drop all playfulness now. "
    "No jokes, not even a light one, until they bring lightness back themselves. "
    "Listen first and name the feeling gently."
)
NO_HINDI_OVERRIDE = (
    "LANGUAGE: this is a serious moment and the person has not used Hindi yet. "
    "Stay in plain English. Do not start using Hindi words now."
)
OPENING_OVERRIDE = (
    "OPENING: these are the first minutes. Be warm and easy. No teasing yet."
)
WRAP_UP_OVERRIDE = (
    "WRAP-UP: the conversation is near its end. Start closing it naturally and warmly. "
    "Do not announce the time abruptly. Leave room for a last thought from them."
)


@dataclass(frozen=True)
class RulesConfig:
    """The numbers, from `.env` (hard rule: nothing tunable is typed into code)."""

    opening_minutes: float
    wrap_up_minute: float
    crisis_turns: int  # how many replies keep the safety override after a crisis
    jev_under_18_threshold: float


@dataclass
class RulesState:
    """What the rules check remembers across the call."""

    hindi_used: bool = False
    playful_locked: bool = False  # set by heavy news, cleared when the person is light again
    crisis_turns_left: int = 0
    recent_openers: list[str] = field(default_factory=list)
    # Jev's answers from the previous turn (background, never waited for)
    jev_heavy: bool = False
    jev_crisis: bool = False
    jev_under_18: float = 0.0

    def note_reply(self, reply: str) -> None:
        """Remember how Vaani's last reply began, to catch repeated openers."""
        opener = " ".join(reply.lower().split()[:2]).strip(" ,.!?")
        if opener:
            self.recent_openers = [*self.recent_openers, opener][-5:]


@dataclass(frozen=True)
class RulesResult:
    """What to do for this reply."""

    overrides: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()  # "crisis", "heavy", "under_18" (for the founder's review)
    end_call_reason: str | None = None  # "under_18": say the kind ending and close
    crisis: bool = False  # the reply must carry the helpline numbers
    advice: bool = False  # the reply must send the person to the right professional


def check(
    user_text: str,
    state: RulesState,
    config: RulesConfig,
    minutes_elapsed: float,
) -> RulesResult:
    """Look at the person's last turn and return what to add for this reply."""
    overrides: list[str] = []
    flags: list[str] = []
    text = user_text or ""

    if patterns.HINDI.findall(text) and any(
        w.lower() not in patterns.HINDI_AMBIGUOUS for w in patterns.HINDI.findall(text)
    ):
        state.hindi_used = True

    # --- Age rule first: it ends the call (after the helplines if there is distress) ---
    stated_age = patterns.under_18_age(text)
    school = patterns.mentions_school_age(text)
    jev_age = state.jev_under_18 >= config.jev_under_18_threshold
    if stated_age is not None or school or jev_age:
        flags.append("under_18")
        distress = bool(patterns.CRISIS.search(text)) or state.jev_crisis
        if distress:
            flags.append("crisis")
        return RulesResult(
            overrides=(), flags=tuple(flags), end_call_reason="under_18", crisis=distress
        )

    # --- Crisis ---
    crisis_now = bool(patterns.CRISIS.search(text)) or state.jev_crisis
    hinted_now = bool(patterns.HINTS.search(text)) and not crisis_now
    if crisis_now:
        state.crisis_turns_left = config.crisis_turns
        flags.append("crisis")
    if state.crisis_turns_left > 0:
        overrides.append(CRISIS_OVERRIDE)
        state.crisis_turns_left -= 1
    elif hinted_now:
        overrides.append(HINT_OVERRIDE)
        flags.append("crisis_hint")

    if patterns.asks_for_advice(text):
        overrides.append(ADVICE_OVERRIDE)
        flags.append("advice_request")

    # --- Heavy disclosure: playfulness off at once, back only when the person is light ---
    heavy_now = patterns.is_heavy(text) or state.jev_heavy or crisis_now or hinted_now
    if heavy_now:
        state.playful_locked = True
        flags.append("heavy")
    elif state.playful_locked and patterns.LIGHT.search(text):
        state.playful_locked = False
    if state.playful_locked and not state.crisis_turns_left:
        overrides.append(HEAVY_OVERRIDE)

    # --- Language: never Hindi for the first time in a serious moment ---
    if (state.playful_locked or crisis_now) and not state.hindi_used:
        overrides.append(NO_HINDI_OVERRIDE)

    # --- Warm first, and a natural wrap-up near the end ---
    if minutes_elapsed < config.opening_minutes and not state.playful_locked:
        overrides.append(OPENING_OVERRIDE)
    if minutes_elapsed >= config.wrap_up_minute:
        overrides.append(WRAP_UP_OVERRIDE)

    # --- Variety: the same opener twice in the last five replies ---
    repeated = _repeated_opener(state.recent_openers)
    if repeated:
        overrides.append(
            f'VARIETY: you have started several replies with "{repeated}". '
            "Start differently this time."
        )

    return RulesResult(
        overrides=tuple(overrides),
        flags=tuple(dict.fromkeys(flags)),
        crisis=crisis_now or state.crisis_turns_left > 0,
        advice="advice_request" in flags,
    )


def _repeated_opener(openers: list[str]) -> str | None:
    for opener in openers:
        if openers.count(opener) >= 2:
            return opener
    return None
