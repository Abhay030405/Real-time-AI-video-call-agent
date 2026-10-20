# Phase 2 — Jev Tagging Guide

**How to tag the 30 conversations so Jev's answers can be checked against yours. About 30 to 40 minutes. Your tags are the answer key, so please tag without looking at what Jev says.**

Status: v0.1 · 20 Oct 2026 · Part of Phase 2 (`docs/v0/vaani_build_phase_v0.md`)

## What to do

1. Open `docs/phase2/03_jev_conversations.md` and read each conversation.
2. Open `evals/datasets/l1_decision_model/tags.csv` and fill in four columns for every id (J01 to J30).
3. Save the file. Tell Claude when you are done. Do not ask Claude to show Jev's answers first.

## The four tags

Judge the conversation **up to the person's last message**.

| Column | Question | Allowed values |
|---|---|---|
| `skill` | Which conversation style fits Vaani's **next reply**? | `casual_chat`, `curious_deep_dive`, `serious_discussion`, `support`, `playful_banter` |
| `intensity` | How strong is the person's mood or energy right now? | `low`, `medium`, `high` |
| `heavy` | Did the person **just share something heavy or painful** in their last message (a death, illness, job loss, a breakup, deep distress)? | `yes`, `no` |
| `hinglish` | How much Hindi or Hinglish does the person use? | `none` (English only), `light` (a few Hindi words), `heavy` (mixes freely or mostly Hindi) |

## The five skills in one line each

| Skill | It fits when |
|---|---|
| `casual_chat` | Small talk and everyday life: a greeting, the day, food, plans |
| `curious_deep_dive` | The person is excited about a topic and wants to go deeper |
| `serious_discussion` | The person is thinking through a decision, a problem or a big question, calmly |
| `support` | The person is stressed, sad, lonely or hurting and needs to be listened to |
| `playful_banter` | The person is joking or teasing and wants a quick, warm comeback |

## Notes

- If two skills seem close, pick the one that best serves the person **right now**. Their feelings win: if someone jokes and then says something painful, the skill is `support`.
- Some conversations are deliberately tricky (a joke followed by something heavy, a student under exam pressure). Use your own judgement; there is no trick answer.
- The passing marks (`docs/v0/V0_07_Evaluation_Framework.md`): Jev must agree with your skill tag on at least 85% of the 30 conversations, and with your `heavy` tag on at least 90%.
