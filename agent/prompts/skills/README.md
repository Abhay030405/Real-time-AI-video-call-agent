# The five conversation skills

One folder per skill: `casual_chat`, `curious_deep_dive`, `serious_discussion`, `support`, `playful_banter`. Behaviour of each skill is described in `docs/v0/V0_02_Character_and_Conversation_Modes.md` section 3.

## Rule: a skill exists only when it is complete

A skill's name is added to the skill chooser only after all three of these exist (`docs/v0/V0_04_Engineering_Blueprint.md` section 8):

1. **Spec** (`spec.md` in the skill's folder): when exactly it starts, what the person should feel by the end, what India-specific context matters, which rules it is most likely to break under pressure.
2. **Instruction text** (in the skill's folder): short, with at least one "what bad looks like" line.
3. **Tests** (in `evals/datasets/l2_single_replies/`): activation, quality and boundary cases. Any boundary failure means the skill does not ship.

## Where skill text goes in the instructions

Skill text always sits after layers 0 and 1, which never change during a session. Swapping a skill only changes the tail of the instructions, so the AI service can keep reusing its earlier work.
