# Vaani

A face-to-face AI companion you can talk to about anything for 20 minutes, in English or Hinglish. Version 0 is the voice-only-turn-taking baseline; version 0.5 adds the Reading Engine, which reads face and voice together to decide turns.

Start here: `docs/reading_engine/Reading_Engine_Design_Document.md`, then `docs/v0/vaani_build_phase_v0.md`.

Private repository. Reference designs are used for ideas only and never named in project files.

---

## Folder map

```
vaani/
├── .env / .env.example           Server-side secrets for agent, evals, scripts (.env never committed)
├── .gitignore                    Keeps .env files and raw recordings out of the repository
├── AGENTS.md                     Rules for any AI coding agent working here (read first)
├── CLAUDE.md                     Loads AGENTS.md for Claude Code, plus a few Claude notes
├── docker-compose.yml            Local running: PostgreSQL (pgvector), Redis, agent, web
├── .dockerignore                 Keeps secrets, docs and test data out of the agent image
├── docs/                         All design documents (the source of truth for what gets built)
│   ├── reading_engine/           The parent document: decisions RE-D1 to RE-D13
│   ├── phase0/                   Phase 0 working documents (accounts checklist, recording kit, result record design)
│   └── v0/                       V0_00 to V0_07 and the build phases
│
├── agent/                        The LiveKit agent in Python, running in Mumbai
│   ├── Dockerfile                Agent image, used locally and for LiveKit Cloud deploys
│   ├── conductor/                Our own layer: one turn from start to finish, the session clock
│   ├── settings/                 The one place that reads .env (keys, models, paths, tunable numbers)
│   ├── prompts/                  Vaani's instructions, kept as text, versioned
│   │   ├── layer0_identity/      Who Vaani is (never changes in a session)
│   │   ├── layer1_rules/         Safety, honesty, age rule, priority order (never changes in a session)
│   │   └── skills/               The five conversation skills, one folder each
│   ├── rules_check/              Plain-code checks before each reply (crisis, heavy disclosure, wrap-up...)
│   ├── background_decisions/     Jev's background answers: next skill, heavy disclosure, Hinglish level, under-18, hinted crisis
│   ├── vendors/                  One swappable connection per outside service (RE-D2)
│   │   ├── speech_to_text/       Sarvam (only, no backup)
│   │   ├── brain/                M1, M2 through OpenRouter, S1 helper
│   │   ├── voice/                Cartesia, Sarvam Bulbul as backup
│   │   ├── avatar/               LemonSlice
│   │   └── decision_model/       Jev (TypeSafe)
│   ├── memory/                   Durable session log, Redis cache, compaction, "forget that", session stories
│   ├── reliability/              Fallbacks, graceful hiccups, rejoin, admission control
│   ├── telemetry/                Timing per stage (steady timers), cost per vendor, logs
│   └── tests/                    Unit tests for the agent's own code
│
├── web/                          The page the person opens (from LiveKit's ready-made starter)
│   ├── .env / .env.example       Page settings; only NEXT_PUBLIC_ names reach the browser, never secrets
│   ├── Dockerfile                Web page image
│   ├── consent/                  Adults only, what is recorded, vendor list
│   ├── call/                     The call itself: microphone, avatar, camera permission
│   ├── feedback/                 The six-question form after each session
│   └── hiccup/                   Hiccup clips that live in the browser for when the internet drops
│
├── assets/audio/                 Pre-recorded clips in Vaani's voice
│   ├── fillers/                  "Hmm..." for a slow reply (6+ variants)
│   ├── hiccup_lines/             Connection and service hiccups, per skill and language
│   └── apologies/                Clean-end lines (speech-to-text down, voice down)
│
├── evals/                        Everything that proves Vaani is good, safe and fast
│   ├── datasets/                 Test sets by level, each split into working/ and hidden/
│   ├── runner/                   Runs a named test set and saves a result record
│   │   └── tests/                Unit tests for the runner
│   ├── judge/                    The AI judge's instructions and its calibration against the founder
│   ├── results/                  One result record per run, with every version attached
│   └── reports/                  Comparisons against the accepted baseline; the baseline report
│
├── infra/                        Running the system
│   ├── database/migrations/      PostgreSQL schema changes (session log, session stories)
│   ├── deploy/                   LiveKit Cloud agent deployment, Redis, PostgreSQL
│   └── ci/                       The checks that run on every change
│
├── ops/dashboard/                Call success, latency percentiles, fallbacks, cost per call
└── scripts/                      Helpers: quick checks, key check, secret scan (and later recording and test-set helpers)
```

## Where each phase works

| Phase | Main folders |
|---|---|
| 0 Foundations | `infra/ci`, `evals/runner`, `evals/results`, `evals/datasets` (speech clips, video scripts) |
| 1 Talking pipe | `agent/conductor`, `agent/vendors`, `agent/telemetry`, `agent/reliability`, `assets/audio`, `web/call` |
| 2 Vaani's mind | `agent/prompts`, `agent/rules_check`, `agent/background_decisions`, `web/consent`, `evals/judge`, `evals/datasets/l2*`, `l5*` |
| 3 20 minutes | `agent/memory`, `infra/database`, `evals/datasets/l3*` |
| 4 Face and reliability | `agent/vendors/avatar`, `agent/reliability`, `web/hiccup`, `ops/dashboard`, `evals/datasets/l6*` |
| 5 Evaluation and release | `evals/` (all levels, hidden sets), `web/feedback`, `evals/reports` |

## Where recorded test material lives

Speech clips and video turn-taking scripts are kept in **local folders inside the project, ignored by git and Docker, so they are never pushed** (founder decision, 19 Oct 2026, after the Oracle sign-up failed on card verification). Recording them is postponed; see `docs/not_implemented_features.md`. The repository keeps only the file lists, versions and consent records under `evals/datasets/`. Everything stays in India.

**Storage rules (never lose a take):**

1. **Main copy:** `storage/main` on the founder's laptop (`TEST_MATERIAL_DIR` in `.env`). `storage/` is in `.gitignore` and `.dockerignore`, so recordings cannot be committed or copied into a Docker image.
2. **Second copy:** `storage/backup` (`TEST_MATERIAL_BACKUP_DIR`), updated after every recording session. It is on the same disk, so copy it to an external drive from time to time. The version 0 vs version 0.5 comparison depends on the exact same takes (RE-D13); a lost take can't be re-recorded.
3. **Every file is checked against its checksum** in the file list, so a damaged copy is noticed.
4. **Cloud storage in India comes later, before Phase 4**, when tests start running away from the laptop. Options: Oracle Mumbai (if the card issue is fixed) or DigitalOcean Spaces Bangalore. Only the `.env` settings change.

## Not created yet (by design)

The Reading Engine (version 0.5) gets its folders only when its build starts: the Eyes inside `web/`, the Decider inside `agent/`. Version 0 keeps the plug-in points ready (manual turn control, data channel, camera permission) without building machinery ahead of content.
