"""The five conversation skills and the dials (V0_02 section 3, V0_04 sections 7 and 8).

A skill is a folder in `agent/prompts/skills/<name>/` with `spec.md`, `instructions.md` and
`skill.json` (its default Spark and Steadiness). Hard rule 6: a skill enters the chooser only
when its spec, its instructions and its tests all exist. `ready_skills()` is that gate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from settings import REPO_ROOT

PROMPTS_SKILLS = Path(__file__).resolve().parents[1] / "prompts" / "skills"
# The L2 test files also ship in the agent image, so the "tests exist" rule can be checked there
DATASETS = REPO_ROOT / "evals" / "datasets" / "l2_single_replies"

SKILLS = ("casual_chat", "curious_deep_dive", "serious_discussion", "support", "playful_banter")
DEFAULT_SKILL = "casual_chat"  # every call starts in light conversation

LEVELS = ("low", "medium", "high")  # both dials are never below "low": never zero
INTENSITIES = ("low", "medium", "high")

# The AI never sees numbers, only a written instruction for each range (V0_04 section 7)
SPARK_WORDS = {
    "low": "Spark is low: calm, few jokes, mostly listening.",
    "medium": "Spark is medium: some humour, and curiosity about their world.",
    "high": "Spark is high: quick, teasing, full of questions.",
}
STEADINESS_WORDS = {
    "low": "Steadiness is low: light and casual.",
    "medium": "Steadiness is medium: notice feelings and check in.",
    "high": "Steadiness is high: grounded, patient, fully present.",
}


@dataclass(frozen=True)
class Skill:
    name: str
    title: str
    spark: str
    steadiness: str
    primary_dial: str | None  # the dial that defines this skill, moved by intensity
    spec: str
    instructions: str


def load_skill(name: str, root: Path = PROMPTS_SKILLS) -> Skill:
    folder = root / name
    meta = json.loads((folder / "skill.json").read_text(encoding="utf-8"))
    return Skill(
        name=name,
        title=meta["title"],
        spark=meta["spark"],
        steadiness=meta["steadiness"],
        primary_dial=meta["primary_dial"],
        spec=(folder / "spec.md").read_text(encoding="utf-8").strip(),
        instructions=(folder / "instructions.md").read_text(encoding="utf-8").strip(),
    )


def missing_parts(
    name: str, min_test_cases: int, root: Path = PROMPTS_SKILLS, datasets: Path = DATASETS
) -> list[str]:
    """What a skill still lacks before it may enter the chooser."""
    folder = root / name
    missing = []
    if not (folder / "spec.md").is_file() or not (folder / "skill.json").is_file():
        missing.append("spec")
    if not (folder / "instructions.md").is_file():
        missing.append("instructions")
    cases = 0
    for split in ("working", "hidden"):
        path = datasets / split / f"{name}.jsonl"
        if path.is_file():
            cases += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line)
    if cases < min_test_cases:
        missing.append(f"tests ({cases} of {min_test_cases} cases)")
    return missing


def ready_skills(
    min_test_cases: int, root: Path = PROMPTS_SKILLS, datasets: Path = DATASETS
) -> list[str]:
    """Only complete skills may be offered to the skill chooser (hard rule 6)."""
    return [n for n in SKILLS if not missing_parts(n, min_test_cases, root, datasets)]


def _shift(level: str, steps: int) -> str:
    index = max(0, min(len(LEVELS) - 1, LEVELS.index(level) + steps))
    return LEVELS[index]


def dials_for(skill: Skill, intensity: str) -> tuple[str, str]:
    """Spark and Steadiness for this moment. Intensity moves only the skill's main dial."""
    if intensity not in INTENSITIES:
        raise ValueError(f"intensity must be one of {INTENSITIES}, got {intensity!r}")
    step = {"low": -1, "medium": 0, "high": 1}[intensity]
    spark, steadiness = skill.spark, skill.steadiness
    if skill.primary_dial == "spark":
        spark = _shift(spark, step)
    elif skill.primary_dial == "steadiness":
        steadiness = _shift(steadiness, step)
    return spark, steadiness


def skill_note(skill: Skill, intensity: str = "medium") -> str:
    """Layer 3's skill part: the skill's text and where the dials are right now."""
    spark, steadiness = dials_for(skill, intensity)
    return f"{skill.instructions}\n{SPARK_WORDS[spark]} {STEADINESS_WORDS[steadiness]}"
