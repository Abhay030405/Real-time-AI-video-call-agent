# AGENTS.md — instructions for AI coding agents working on Vaani

This file is for every AI coding agent (Claude Code, Codex, Cursor and others) working in this repository. **Read all of it before changing anything.** `CLAUDE.md` loads this file. If anything here conflicts with a request, ask the founder before acting.

---

## 1. What Vaani is

**Vaani is a face-to-face AI companion you can talk to about anything for 20 minutes.** A person opens a web link on their laptop, sees Vaani's face and hears her voice, and talks to her the way they would talk to a friend on a video call, in English, Hindi or Hinglish.

**Who she is:** warm, curious, quick to laugh, honest and comfortable with silence. Not a performer and not a therapist: a good conversation partner. She is always honest that she is an AI. She adapts through five conversation skills: casual chat, curious deep-dive, serious discussion, support, and playful banter. Safety rules (crisis, age, honesty) sit above every skill.

**What makes Vaani different:** today's voice AI decides when it's your turn mostly from silence, so it cuts people off mid-thought, stops at every cough and leaves awkward gaps. Vaani's **Reading Engine** reads the face and the voice together, the way people do, to know when someone has finished, when they are only thinking, and when a sound is not an interruption.

**The versions:**

| Version | What it is |
|---|---|
| **0** (being built now) | The full 20-minute companion with voice-only turn-taking. It is the honest baseline: its turn-taking numbers are what version 0.5 must beat |
| **0.5** | Adds the Reading Engine, measured on exactly the same recorded takes as version 0 |
| **1** | Interview practice and memory across calls |

**Who it is for:** adults (18+) in India, on laptops. Testers in version 0 are a small private group.

**What Vaani is not:** not a therapist, not an emotion detector, not a video recorder (video never leaves the person's laptop), and never pretending to be human.

## 2. The design documents are the source of truth

Read the document for the area you are touching before planning. If code and documents disagree, the documents win: raise the conflict with the founder instead of guessing.

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
| `docs/phase0/` | Phase 0 working documents: accounts, recording kit, result record design |

## 3. Where everything goes

**The folder structure is fixed. Do not rename, move or reorganise folders.** Put every new file in the folder that matches its purpose, using this map.

### 3.1 The map

| Folder | What goes here | What never goes here |
|---|---|---|
| `/` (root) | Only: `README.md`, `AGENTS.md`, `CLAUDE.md`, `.env`, `.env.example`, `.gitignore`, `.dockerignore`, `docker-compose.yml`, and `storage/` (local recordings, ignored by git and Docker, never pushed) | Code, scripts, notes, any other file |
| `docs/reading_engine/` | The parent design document | — |
| `docs/v0/` | Version 0 design documents (`V0_00` to `V0_07`, build phases) | Working notes for a single phase |
| `docs/` (top level) | `not_implemented_features.md`: what is postponed, why, and when it comes back | Anything else |
| `docs/phase<N>/` | Working documents for phase N (checklists, guides, designs), numbered `01_`, `02_`... | Code |
| `agent/` | `Dockerfile`, `pyproject.toml`, `uv.lock`, `main.py` (the entry point), and the folders below | Web code, test data |
| `agent/conductor/` | One turn from start to finish; assembling the instruction layers; the session clock | Vendor calls |
| `agent/settings/` | **The one place that reads `.env`** (section 4) | Hard-coded values |
| `agent/prompts/layer0_identity/` | Vaani's identity text | Anything that changes during a session |
| `agent/prompts/layer1_rules/` | Safety, honesty, age, priority-order text | Anything that changes during a session |
| `agent/prompts/skills/<skill>/` | One folder per skill: `spec.md` plus its instruction text | A skill without its tests |
| `agent/rules_check/` | Plain-code checks before each reply | AI calls |
| `agent/background_decisions/` | Jev's background questions and how their answers are used | Anything on the critical path |
| `agent/vendors/<part>/` | **All code that talks to an outside service**, one folder per part (`speech_to_text`, `brain`, `voice`, `avatar`, `decision_model`) | Business logic |
| `agent/memory/` | Session log, Redis cache, compaction, "forget that", session stories | — |
| `agent/reliability/` | Fallbacks, hiccup lines logic, rejoin, admission control | — |
| `agent/telemetry/` | Timing per stage, cost per vendor, logging | — |
| `agent/tests/` | Unit tests for agent code, mirroring the folder names (`tests/conductor/`, `tests/vendors/`...) | Evaluation test sets |
| `web/` | The Next.js page from LiveKit's starter, following its own folder rules (`app/`, `components/`, `hooks/`, `lib/`, `styles/`, `tests/`), plus `web/consent/`, `web/call/`, `web/feedback/`, `web/hiccup/` for our features | Secrets behind `NEXT_PUBLIC_` |
| `assets/audio/<kind>/` | Pre-recorded clips in Vaani's voice: `fillers/`, `hiccup_lines/`, `apologies/` | Test recordings |
| `evals/datasets/<level>_<name>/` | File lists, transcripts, labels and consent records for one test set, split into `working/` and `hidden/` | Audio or video files |
| `evals/runner/` | The test runner | — |
| `evals/judge/` | Judge instructions and `calibration/` | — |
| `evals/results/<YYYY-MM>/` | Result records (`docs/phase0/05_result_record_design.md`) | Edited records |
| `evals/reports/` | Comparisons with baselines; the baseline report | — |
| `infra/database/migrations/` | Database schema changes, numbered in order | — |
| `infra/deploy/` | Deployment files for LiveKit Cloud and hosted services | — |
| `ops/dashboard/` | The operations dashboard | — |
| `scripts/` | One-off helpers (building file lists, checking keys, converting recordings) | Code the agent imports |

**Planned but not created yet:** when version 0.5 starts, the Reading Engine gets `agent/reading_engine/` (the Decider) and `web/eyes/` (the in-browser face tracker). Do not create them earlier.

### 3.2 When something new isn't in the map

1. **Find the closest existing folder by purpose** and put it there. Most new things fit an existing folder.
2. **A new outside service** gets its own folder under `agent/vendors/`. **A new test set** gets `evals/datasets/<level>_<name>/` with `working/` and `hidden/`. **A new phase document** goes in `docs/phase<N>/` with the next number.
3. **A new sub-folder** inside an existing folder is fine when it clearly belongs there. Add one line for it to the folder map in `README.md` in the same change.
4. **A new top-level folder, or moving or renaming anything that exists: ask the founder first.** Never do it on your own.
5. **No loose files in the root, and no "misc", "utils" or "temp" folders.** A helper belongs to the folder of the thing it helps, or to `scripts/`.

### 3.3 Names

- Folders and Python files: `lower_snake_case` (`rules_check`, `session_clock.py`).
- Web files follow Next.js and the LiveKit starter's existing conventions.
- Documents: `NN_short_name.md` inside `docs/phase<N>/`.
- Test cases keep the IDs from their documents (`HG14`, `TT07`).

## 4. Settings: always from `.env`, never written by hand

1. **Every value that can change comes from `.env`:** keys, addresses, model names, voice IDs, folder paths, and tunable numbers (timeouts, thresholds, the session clock). **Never type these values into code, prompts, settings files or config files.**
2. **One place reads `.env`:** `agent/settings/` for the agent, evals and scripts, and the web page's own settings file for `web/`. Everything else gets values from there, never by reading `.env` directly.
3. **When a new setting is needed,** add it to the matching `.env.example` with a one-line comment and its default value (or empty, for secrets), add it to `agent/settings/`, and tell the founder to add it to their own `.env`.
4. **If a required setting is missing, stop with a clear message** naming the setting. Never fall back to a silent default for a secret, an address or a model name.
5. **Never print, copy, log or commit the contents of `.env`.** Result records save the non-secret settings that affected a run (for example timeouts and model names), never keys.
6. **Only the agent's server side holds keys.** In `web/`, a name starting with `NEXT_PUBLIC_` reaches the browser, so never put a key behind it.

## 5. Web design: always through `globals.css`

1. **All colours, fonts, font sizes, spacing, corner rounding and shadows are defined once, as named variables, in the web page's single global stylesheet, `globals.css`.**
2. **Components use those variables only.** No colour codes, pixel sizes or font names typed into components, and no inline styles.
3. **A new design value** (a new colour, say) is added to `globals.css` first, with a clear name, then used.
4. If the starter's styling tool (for example its utility classes) needs settings, it reads them from the `globals.css` variables, never its own copies.
5. Light and dark mode are handled in `globals.css`, not in components.

## 6. Git and GitHub

The repository is private on GitHub. `main` must always work.

**When to use a branch:**

| Work | Where |
|---|---|
| **A feature:** something that takes several steps and is finished only when its tests pass (a vendor connection, a skill, the test runner, the session clock, the consent screen) | Its own branch, merged into `main` when the feature is complete |
| **Small changes:** a typo, a document update, a one-file fix, a new setting in `.env.example` | Straight on `main` |

- **One branch per feature, not per small change.** Do not open a new branch for every few lines. A feature branch collects all the commits for that feature.
- **Branch names:** `phase<N>/<feature>`, for example `phase0/test-runner`, `phase1/talking-pipe`, `phase2/skill-support`.
- **Keep at most one or two branches open at a time.** Finish and merge before starting the next feature, unless the founder asks otherwise.

**Commits:**

- Commit in logical steps inside the branch, each with a clear message saying what changed and why, in simple English: `Add Sarvam connection with clean-end rule on two errors`.
- Each commit should leave the code working.
- Never commit `.env`, keys, recordings, or real names. Never name the reference designs (rule 17).

**Before merging a feature branch into `main`:**

1. Run the quick checks by hand (code style, type checks, unit tests, secret scan). There are no automatic checks.
2. If the change touches prompts, skills, rules or memory: run the quick evaluation set, including all safety tests (rule 7).
3. Update any document the feature changed, and the folder map in `README.md` if a folder was added.
4. Tell the founder what the feature does and what was tested, then merge into `main` and delete the branch.

**Never:** force-push to `main`, rewrite `main`'s history, or merge a branch whose checks failed.

## 7. Hard rules (never break these)

**Speed**
1. **One main AI call per turn.** No planner calls, no multi-agent chains before the reply.
2. **Nothing new on the critical path.** The path from "person stopped talking" to Vaani's first sound is: turn detection → rules check (plain code) → M1 → voice → avatar. Everything else (Jev, summaries, logging, memory writes) runs in the background after the reply has started.
3. **Instruction layers 0 and 1 never change during a session.** No timestamps, names or changing values in them. Changing parts go after them, always in the same order.
4. **Stream first words to the voice as soon as they exist.**

**Safety**
5. **Crisis and age rules never depend on Jev or any AI call.** They live in layer 1 and the plain-code rules check, and apply on the same turn.
6. **A skill is added to the chooser only when its spec, instructions and tests all exist** (`agent/prompts/skills/README.md`).
7. **Safety tests (L5) must pass 100%, 3 runs each,** before any change to prompts, skills, rules or memory is merged. There are no automatic checks: they are run by hand.

**Reliability**
8. **Every outside service sits behind its own swappable connection** in `agent/vendors/` (RE-D2). No vendor code anywhere else.
9. **No blind retries on the live path.** Switch to the fallback where one exists (M1 → M2, Cartesia → Bulbul); Sarvam has no backup and follows the clean-end rule (RE-D9).
10. **Durations use each machine's own steady timer.** Never subtract a browser time from a server time. Report speed at the 50th, 95th and 99th percentile.
11. **Every background job is keyed by session ID and safe to run twice.** Every stored record carries a format version.

**Data and privacy**
12. **Settings and secrets come only from `.env`** (section 4). `.env` is never committed.
13. **In `web/`, never put a key behind `NEXT_PUBLIC_`.**
14. **Recorded audio and video never go into the repository.** They live in `storage/main` (`TEST_MATERIAL_DIR`) with a backup copy in `storage/backup` (`TEST_MATERIAL_BACKUP_DIR`). `storage/` is ignored by git and Docker and is never pushed; only file lists and consent records are committed.
15. **Video never leaves the person's laptop** (RE-D3). Only face numbers do, from version 0.5.
16. **"Forget that" removes every derived copy:** cache, session log, summaries, saved story.

**Project rule**
17. **Reference designs are used for ideas only and are never named** in code, comments, documents, commit messages, branch names or test names.

## 8. How we build

- **Follow the phases in order.** Work only on the current phase. A phase is done only when every item in its exit gate passes.
- **Tests come with the feature,** on the same branch. Every real failure becomes a test case before it is fixed.
- **Every evaluation result is tied to exact versions** (code, each layer and skill, models, vendors, settings, test set, judge), as in `docs/phase0/05_result_record_design.md`.
- **Pick the cheapest option that does not hurt quality,** and say why.
- **Do not build ahead of the current phase.** In particular, no Reading Engine code until version 0 is finished; only keep its plug-in points (manual turn control, data channel, camera permission).

## 9. Working with the founder

- **The founder plans; you do what is asked.** Do not widen the task on your own.
- **Explain in simple English, without heavy technical words.** Before a large change, explain the approach, logic and trade-offs first, and wait for the go-ahead.
- **Ask before deciding anything that is the founder's call** (a new vendor, a changed target, a skipped rule, a new top-level folder). Small, conventional choices: decide and mention them.
- **Do not create diagrams, HTML pages or visual extras unless asked.**
- **When a document must change because of the work,** say which document and which section, and update it on the same branch.
- **When you hand over files outside git,** give each file with its exact path in the repository. Never resend the whole project.

## 10. Stack

| Part | Choice |
|---|---|
| Agent | Python, LiveKit Agents, LiveKit Cloud agent region Mumbai |
| Web page | LiveKit's ready-made Next.js starter, styled only through `globals.css` |
| Speech-to-text | Sarvam (only, no backup) |
| Brain | M1 direct (India), M2 through OpenRouter, S1 helper — chosen in Phase 1 |
| Decision model | Jev (TypeSafe), background only |
| Voice | Cartesia; Sarvam Bulbul backup |
| Avatar | LemonSlice (Phase 4) |
| Data | PostgreSQL with pgvector (durable log, session stories), Redis (cache), hosted in India from Phase 3 |
| Test material | Local folders `storage/main` and `storage/backup` inside the project, ignored by git and Docker; cloud storage in India added before Phase 4 |
| Local running | Docker Compose (`docker-compose.yml`) |
| Code hosting | Private GitHub repository |

## 11. Commands

Filled in as each phase creates them.

| Task | Command |
|---|---|
| Start everything locally | `docker compose up --build` |
| Start only the database and cache | `docker compose up postgres redis` |
| Start only the local call server (LiveKit) | `docker compose up livekit` |
| Quick checks (style, types, unit tests for agent and web, secret scan) | `python scripts/quick_checks.py` |
| Web page commands (run in `web/`) | `corepack pnpm@9.15.9 install`, `... dev`, `... test` |
| Check every key in `.env` works (needs the local LiveKit server running) | `python scripts/check_keys.py` |
| Check the test runner with the dummy set | `uv run --project agent python -m evals.runner --dummy --out <temp folder>` |
| Run a real evaluation set | added with each test set (`evals/runner`) |
