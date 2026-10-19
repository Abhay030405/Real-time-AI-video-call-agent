# Phase 0 — Accounts Checklist

**Which accounts to open now, in which order, and what to do in each one. Do them top to bottom: the first two can make you wait, so start them first.**

Status: v0.1 · 19 Oct 2026 · Part of Phase 0 (`docs/v0/vaani_build_phase_v0.md`)

---

## Rules for every account

1. **Use one email for all Vaani accounts**, and turn on two-step login wherever it is offered.
2. **Set a spending limit the same day you open the account.** Where a service has no hard limit, use a budget alert, or keep only a small prepaid balance.
3. **Name every key `vaani-dev`.** Later, testers get separate `vaani-prod` keys.
4. **Paste keys only into `.env`** (root) or `web/.env`. Never into chat, documents, screenshots or code.
5. **Tick the box here when done**, and write the date.

---

## Open now (Phase 0)

### 1. Jev (TypeSafe) — start first, it may take days

- [ ] Request early access on TypeSafe's website. Describe the use: "Real-time voice companion: background choice between 5 conversation skills, heavy-disclosure detection, and turn-taking decisions, called from India."
- [ ] When access arrives: create a key named `vaani-dev`, set a monthly limit.
- [ ] Fill in: `TYPESAFE_API_KEY`, `JEV_MODEL`.

**If access is slow:** Jev is also offered through other gateways (Vercel's AI Gateway, Cloudflare Workers AI, ZenMux). Don't switch yet; we only need Jev from Phase 2. In Phase 2 we measure every path from Mumbai and use the fastest (Reading Engine document, section 7.2).

### 2. Test recording storage — local folders, no account needed

- [ ] Create two folders: the main one (`TEST_MATERIAL_DIR`) and a backup (`TEST_MATERIAL_BACKUP_DIR`). Currently these are `storage/main` and `storage/backup` in the project folder, ignored by git and Docker. See `02_recording_guide.md` section 7.
- [ ] Fill in both paths in the root `.env`.
- Cloud storage in India (Oracle was the earlier choice) is moved to later and is chosen again before Phase 4.

### 3. LiveKit Cloud

- [ ] Sign up and create a project named `vaani-dev`.
- [ ] Check the agent can be deployed to the **Mumbai** region.
- [ ] Set a usage limit or alert.
- [ ] Create an API key.
- [ ] Fill in: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` in **both** `.env` and `web/.env`.

### 4. Sarvam

Covers speech-to-text, the backup voice (Bulbul), and Sarvam-30B as an M1 candidate.

- [ ] Sign up (new accounts get some free credits).
- [ ] Add a small prepaid balance only; no automatic top-up.
- [ ] Create a key named `vaani-dev`.
- [ ] Fill in: `SARVAM_API_KEY`.

### 5. Cartesia

- [ ] Sign up and take the **Pro plan** ($5 a month). Move to Startup only in Phase 5, when testers start.
- [ ] Keep overage (extra usage beyond the plan) switched off.
- [ ] Create a key named `vaani-dev`.
- [ ] Fill in: `CARTESIA_API_KEY`. Leave `CARTESIA_VOICE_ID` empty; the voice is chosen in Phase 2.

### 6. OpenRouter

One account to try many AI models: M2 (the fallback brain), candidates for M1 and S1 in Phase 1, and the AI judge.

- [ ] Sign up and add a small prepaid balance; no automatic top-up.
- [ ] Create a key named `vaani-dev` with a credit limit on the key itself.
- [ ] Fill in: `OPENROUTER_API_KEY`.

---

## Open later (not now)

| Account | When | Why wait |
|---|---|---|
| Direct provider for M1 | Phase 1, after the model test picks M1 | We don't know which provider yet |
| Managed PostgreSQL and Redis, hosted in India | Phase 3 | Until then they run on your laptop through Docker |
| LemonSlice | Phase 4 | The face is added only after the voice call works; opening it now wastes any trial |

---

## Phase 0 gate for this part

- [ ] All five accounts above are open (test storage is local folders), with spending limits or alerts set.
- [ ] Every key is in the right `.env` file and nowhere else.
- [ ] Each key works with one test request. Use the service's own playground for now; Claude will add a single "check all keys" command when you ask for the Phase 0 code.
