"""The six questions Jev answers about the conversation (V0_01 section 5, RE-D10).

(a) which skill fits the next turn, and how intensely
(b) did the person just share something heavy
(c) how much Hindi or Hinglish the person uses
(d) signs the person is under 18
(e) a hinted crisis that the keyword rules might miss (the second safety net)
"""

from __future__ import annotations

from typing import Any

SKILL_CRITERIA = {
    "casual_chat": "Small talk and everyday life: a greeting, the day, food, plans, light topics.",
    "curious_deep_dive": (
        "The person is excited about a topic they love and wants to go deeper: a hobby, an idea, "
        "a film, a sport, technology."
    ),
    "serious_discussion": (
        "The person is thinking through a decision, a work or study problem, the news or a big "
        "question, in a thoughtful mood and not in distress."
    ),
    "support": (
        "The person is stressed, sad, lonely, heartbroken, overwhelmed or under pressure and "
        "needs someone to listen."
    ),
    "playful_banter": (
        "The person is joking, teasing or testing, in a light and mischievous mood."
    ),
}

INTENSITY_CRITERIA = {
    "low": "Mild: the mood is faint or only just starting.",
    "medium": "Moderate: the mood is clear but not strong.",
    "high": "Strong: the mood is intense, with strong emotion or energy.",
}

HINGLISH_CRITERIA = {
    "none": "The person writes only in English.",
    "light": "The person is mostly English with a few Hindi words.",
    "heavy": "The person mixes Hindi and English freely, or mostly uses Hindi.",
}

HEAVY_QUESTION = (
    "Did the person just share something heavy or painful, such as a death, an illness, a "
    "job loss, a breakup, abuse, or deep distress?"
)
UNDER_18_QUESTION = (
    "Are there signs the person may be under 18, such as their age, school, a class like "
    "class 10, or being a student who lives with strict parents?"
)
CRISIS_QUESTION = (
    "Does the person hint, even indirectly, at hurting themselves, at suicide, or at not "
    "wanting to live?"
)


def build_questions(ready_skills: list[str]) -> dict[str, Any]:
    """The question set. Only skills that are complete may be offered (hard rule 6)."""
    return {
        "skill": {
            "type": "choice",
            "instructions": (
                "Which conversation style fits the person's NEXT turn, judging from the last "
                "few exchanges?"
            ),
            "criteria": {name: SKILL_CRITERIA[name] for name in ready_skills},
        },
        "intensity": {
            "type": "choice",
            "instructions": "How strong is the person's current mood or energy?",
            "criteria": INTENSITY_CRITERIA,
        },
        "heavy": {"type": "noul", "instructions": HEAVY_QUESTION},
        "under_18": {"type": "noul", "instructions": UNDER_18_QUESTION},
        "hinted_crisis": {"type": "noul", "instructions": CRISIS_QUESTION},
        "hinglish": {
            "type": "choice",
            "instructions": "How much Hindi or Hinglish does the person use?",
            "criteria": HINGLISH_CRITERIA,
        },
    }
