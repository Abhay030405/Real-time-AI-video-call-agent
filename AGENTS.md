# AGENTS.md — instructions for AI coding agents working on Vaani

This file is for any AI coding agent (Claude Code, Codex, Cursor and others) working in this repository. Read it fully before changing anything. `CLAUDE.md` loads this file.

## 1. What Vaani is

A face-to-face AI companion you talk to about anything for 20 minutes, in English or Hinglish, on a laptop. Version 0 is the full companion with voice-only turn-taking: the honest baseline. Version 0.5 adds the Reading Engine, which reads face and voice together to decide turns, and must beat version 0's numbers.

## 2. The design documents are the source of truth

Read these before working on any part. If code and documents disagree, the documents win; raise the conflict with the founder instead of guessing.

| Document | What it decides |
|---|---|
| `docs/reading_engine/Reading_Engine_Design_Document.md` | The parent: decisions RE-D1 to RE-D13 |
| `docs/v0/vaani_build_phase_v0.md` | The six phases (0 to 5) and their exit gates |
| `docs/v0/V0_00_Overview_and_Build_Plan.md` | Version 0 decisions V0-D1 to V0-D15 |
| `docs/v0/V0_01_Architecture.md` | The parts, one turn, the skill chooser, failures |
| `docs/v0/V0_02_Character_and_Conversation_Modes.md` | Vaani's character, five skills, crisis, age and honesty rules |
| `docs/v0/V0_03_Testing_and_Measurement.md` | Hard rules, fault tests, human testing |
| `docs/v0/V0_04_Engineering_Blueprint.md` | Instruction layers, rules check, model fallback |
| `docs/v0/V0_05_Memory_and_Personalization.md` | Memory design |
| `docs/v0/V0_06_Reliability_and_Data_Design.md` | Graceful hiccups, data design |
| `docs/v0/V0_07_Evaluation_Framework.md` | Test levels L1 to L7 and the V0 scorecard |

The folder map is in `README.md`.

## 3. Hard rules (never break these)

**Speed**
1. **One main AI call per turn.** No planner calls, no multi-agent chains before the reply.
2. **Nothing new on the critical path.** The path from "person stopped talking" to Vaani's first sound is: turn detection → rules check (plain code) → M1 → voice → avatar. Everything else (Jev, summaries, logging, memory writes) runs in the background after the reply has started.
3. **Instruction layers 0 and 1 never change during a session.** No timestamps, names or changing values in them. Changing parts go after them, always in the same order.
4. **Stream first words to the voice as soon as they exist.**

**Safety**
5. **Crisis and age rules never depend on Jev or any AI call.** They live in layer 1 and the plain-code rules check, and apply on the same turn.
6. **A skill is added to the chooser only when its spec, instructions and tests all exist** (`agent/prompts/skills/README.md`).
7. **Safety tests (L5) must pass 100%, 3 runs each,** before any change to prompts, skills, rules or memory is merged.

**Reliability**
8. **Every outside service sits behind its own swappable connection** in `agent/vendors/` (RE-D2). No vendor code anywhere else.
9. **No blind retries on the live path.** Switch to the fallback where one exists (M1 → M2, Cartesia → Bulbul); Sarvam has no backup and follows the clean-end rule (RE-D9).
10. **Durations use each machine's own steady timer.** Never subtract a browser time from a server time. Report speed at the 50th, 95th and 99th percentile.
11. **Every background job is keyed by session ID and safe to run twice.** Every stored record carries a format version.

**Data and privacy**
12. **Secrets live only in `.env` files, which are never committed.** Add every new setting to the matching `.env.example` with an empty value.
13. **In `web/`, a name starting with `NEXT_PUBLIC_` reaches the browser.** Never put a key behind it.
14. **Recorded audio and video never go into the repository.** They live in the private Oracle bucket in Mumbai; only file lists and consent records are committed.
15. **Video never leaves the person's laptop** (RE-D3). Only face numbers do, from version 0.5.
16. **"Forget that" removes every derived copy:** cache, session log, summaries, saved story.

**Project rule**
17. **Reference designs are used for ideas only and are never named** in code, comments, documents, commit messages or test names.

## 4. How we build

- **Follow the phases in order.** Work only on the current phase. A phase is done only when every item in its exit gate passes.
- **Tests come with the feature,** in the same change. Every real failure becomes a test case before it is fixed.
- **Every evaluation result is tied to exact versions** (code, each layer and skill, models, vendors, test set, judge). Tunable numbers (timeouts, thresholds, the session clock) live in versioned config files, not in `.env`.
- **Pick the cheapest option that does not hurt quality,** and say why.
- **Do not build ahead of the current phase.** In particular, no Reading Engine code until version 0 is finished; only keep its plug-in points (manual turn control, data channel, camera permission).

## 5. Working with the founder

- **The founder plans; you do what is asked.** Do not widen the task on your own.
- **Explain in simple English, without heavy technical words.** Before a large change, explain the approach, logic and trade-offs first.
- **Ask before deciding anything that is the founder's call** (a new vendor, a changed target, a skipped rule). Small, conventional choices: decide and mention them.
- **Do not create diagrams, HTML pages or visual extras unless asked.**
- **When a document must change because of the work,** say which document and which section, and update it in the same change.

## 6. Stack

| Part | Choice |
|---|---|
| Agent | Python, LiveKit Agents, LiveKit Cloud agent region Mumbai |
| Web page | LiveKit's ready-made Next.js starter |
| Speech-to-text | Sarvam (only, no backup) |
| Brain | M1 direct (India), M2 through OpenRouter, S1 helper — chosen in Phase 1 |
| Decision model | Jev (TypeSafe), background only |
| Voice | Cartesia; Sarvam Bulbul backup |
| Avatar | LemonSlice (Phase 4) |
| Data | PostgreSQL with pgvector (durable log, session stories), Redis (cache), hosted in India |
| Test material | Oracle Cloud Object Storage, Mumbai |
| Local running | Docker Compose (`docker-compose.yml`) |

## 7. Commands

Filled in as each phase creates them. Until then, these are the agreed shapes:

| Task | Command |
|---|---|
| Start everything locally | `docker compose up --build` |
| Start only the database and cache | `docker compose up postgres redis` |
| Run agent unit tests | to be added in Phase 0 |
| Run an evaluation set | to be added in Phase 0 (`evals/runner`) |
