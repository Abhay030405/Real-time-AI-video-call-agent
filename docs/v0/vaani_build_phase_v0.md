# Vaani Version 0 — Build Phases

**Version 0 is built in six phases, from an empty repository to a tested, measured 20-minute companion. Each phase ends with something that runs, its own tests written and passing, and a hard gate: the next phase does not start until the gate is passed.**

Status: Draft v0.1 · 19 Oct 2026

Parent: `Reading_Engine_Design_Document.md` (decisions RE-D1 to RE-D13)
Read with: `V0_00` to `V0_07`

---

## 1. Rules that apply to every phase

1. **Hard gates.** A phase is finished only when every item in its exit gate passes. No work from the next phase starts before that.
2. **Every phase ends with something a person can use.** No machinery built ahead of content.
3. **Tests come with the feature, not after.** Each phase writes the tests for what it builds and must pass them at its gate. Phase 5 runs everything together, adds the hidden test sets and the human testers.
4. **Measure from the first call.** Timing of every stage, cost, crashes. Speed is always reported at the 50th, 95th and 99th percentile, using each machine's own steady timer.
5. **No skill name exists in the skill chooser until that skill's instructions and tests exist.** A chooser that can send people to an unfinished skill is a broken product.
6. **Cheapest option that does not hurt quality.** Cartesia Pro plan until testers start; Startup plan from Phase 5. Spending limits on every evaluation key.
7. **Every result is tied to exact versions** (code, each instruction layer, models, vendors, test set, judge). A number with no versions attached is thrown away.

## 2. Phase overview

| Phase | Name | What exists at the end |
|---|---|---|
| **0** | Foundations | Repository, accounts, the evaluation skeleton, recorded test material |
| **1** | Talking pipe and speed baseline | A voice call in English and Hinglish, with every stage timed |
| **2** | Vaani's mind: character, skills, safety | Vaani has her character, five skills chosen by Jev, and every safety rule passing |
| **3** | 20 minutes: coherence, memory, durable data | A full 20-minute conversation that stays coherent and loses nothing on a crash |
| **4** | The face and reliability | The avatar, graceful hiccups, and every designed failure behaving as planned |
| **5** | Evaluation and release | All tests including hidden sets, 10+ human testers, the baseline report |

After Phase 5: version 0.5, the Reading Engine (see its build plan, RE-1 to RE-8).

---

## Phase 0 — Foundations

**Goal:** everything later phases depend on, so nothing is improvised mid-build.

### What gets built
- Private repository with the folder layout for the agent, the web page, evaluation (`evals/datasets/`, `evals/results/`) and documents.
- **No automatic checks** (founder decision, 19 Oct 2026). Instead, one command runs the quick checks by hand: code style, type checks, unit tests and a secret scan. The founder runs it before accepting any change.
- Vendor accounts, following `docs/phase0/01_accounts_checklist.md`: Jev (TypeSafe), LiveKit Cloud (Mumbai agent region), Sarvam, Cartesia (Pro plan), OpenRouter. Spending limits set on each. Accounts opened later, when first needed: the direct M1 provider (Phase 1, once M1 is chosen), managed PostgreSQL and Redis in India (Phase 3), LemonSlice (Phase 4).
- API keys kept only on the server, never in the web page.
- **The result record:** the format every evaluation run saves (date, code version, every layer and model version, test set version, judge version, scores with spread, cost).
- **The test runner skeleton:** runs a named test set and saves a result record. Empty test sets are fine at this stage.
- **Recorded material:**
  - *Postponed (founder decision, 19 Oct 2026; see `docs/not_implemented_features.md`):* speech-to-text test clips (200+): pure English, pure Hindi, Hinglish, with fan or traffic noise, Indian names and places, each with a correct transcript. From people who agreed in writing.
  - *Postponed (founder decision, 19 Oct 2026; see `docs/not_implemented_features.md`):* the ~30 turn-taking scripts (thinking pauses of 2, 4 and 6 seconds, "hmm", "haan", coughs, real interruptions, background noise), **recorded with video** (RE-D13).

### Exit gate
- [ ] One command runs the quick checks by hand, and it passes on the empty repository.
- [ ] The test runner produces a valid result record from a dummy test.
- [ ] Every Phase 0 account works with a test request, and spending limits are set.
- ~~Video turn-taking scripts are stored, versioned, with consent records.~~ Postponed with the speech clips (`docs/not_implemented_features.md`).

---

## Phase 1 — Talking pipe and speed baseline

**Goal:** a plain voice call that works and is measured, before any personality or complexity is added. If the bare call is slow, nothing built on top can fix it.

### What gets built
- The web page from LiveKit's ready-made starter: joins a room, microphone on, plays Vaani's voice.
- The LiveKit agent in Mumbai: Sarvam speech-to-text (streaming) → AI model → Cartesia voice, with the first words sent to the voice as soon as they exist.
- **Model choice:** made by the founder on 19 Oct 2026 without a comparison test (the comparison is postponed; see `docs/not_implemented_features.md`):
  - **M1:** main brain, called directly: Sarvam-105B (`M1_MODEL`).
  - **M2:** a different model from a different provider, through OpenRouter: `google/gemini-3.6-flash`.
  - **S1:** a cheaper helper for background jobs, through OpenRouter: `google/gemini-3.1-flash-lite`.
- **M1 → M2 fallback:** filler at 1.0 s with no first word; switch to M2 at 1.5 s; after two M1 failures in a row, stay on M2 for several minutes. Every switch logged.
- **Pre-recorded clips in Vaani's chosen voice:** the "hmm" fillers (at least 6 variants) and the speech-to-text failure apology.
- **Sarvam failure rule (RE-D9):** one lost turn → ask to repeat; two errors in a row or nothing for 5 s → apology clip, call ends, rejoin link valid for 30 minutes.
- **Backup voice:** Sarvam Bulbul wired behind the same voice connection, switched in if Cartesia fails.
- Timing logs for every stage of every turn: speech ended, turn detected, first word from the model, first audio. Cost logged per vendor.
- LiveKit set up so standard turn detection can later be replaced by manual turn control (Reading Engine plug-in point).

### Tests written in this phase
- ~~**L1 speech-to-text:** word error rate and meaning-error rate on the recorded clips.~~ Postponed with the clips (`docs/not_implemented_features.md`).
- **L1 models:** first-word time (50th/95th/99th) from Mumbai and cost per 1,000 replies, measured for the chosen models. The model comparison and the reply-quality scoring are postponed.
- **L1 voice:** 50 sentences with Hinglish words, names and numbers, rated 1 to 5; time to first audio.

### Exit gate
- [ ] A 5-minute English chat and a 5-minute Hinglish chat run without breaking.
- ~~Sarvam meaning-error rate on Hinglish clips is **5% or less**.~~ Postponed with the clips. Until it runs, Sarvam is checked only by the 5-minute English and Hinglish chats above.
- [ ] M1 first-word time at the 95th percentile is **0.7 s or less**. *Measured in local Docker for now; the "from Mumbai" measurement waits for the LiveKit Cloud deploy (`docs/not_implemented_features.md`).*
- [ ] Killing M1 mid-call switches to M2 within 1.5 s with one filler.
- [ ] Killing Cartesia switches to the backup voice.
- [ ] Killing Sarvam produces the apology and a clean end.
- [ ] Every stage's timing and cost appear in the logs for every turn.

---

## Phase 2 — Vaani's mind: character, skills, safety

**Goal:** Vaani becomes herself, adapts to the conversation through five skills, and every safety rule holds under pressure.

### What gets built
- **Voice choice:** written criteria first (gender, accent, age feel, pace, warmth), then the Cartesia voice chosen against them.
- **The instruction layers,** always in the same order, layers 0 and 1 never changing within a session:
  - Layer 0, Identity: who Vaani is, the two dials (Spark, Steadiness), honesty about being an AI.
  - Layer 1, Rules: crisis and safety, honesty, language mirroring, the age rule, how skills blend and move, the priority order for conflicts (safety, then ethics, then the person's trust, then product quality).
  - Layer 2, Session context. Layer 3, Skill and mode note. Session note at the end.
- **The five skills,** each built with the checklist (spec, then instruction text with a "what bad looks like" line, then tests): **casual chat, curious deep-dive, serious discussion, support, playful banter.**
- **The rules check** (plain code, before each reply): crisis words, heavy disclosure lock, wrap-up time, "no Hindi first in a serious moment", warm-first in the opening minutes, repeated-phrasing check.
- **Jev background decisions (RE-D10),** run after the reply starts, never delaying it:
  - (a) which skill next, with a "sticky" threshold so skills don't flip-flop,
  - (b) heavy-disclosure detection,
  - (c) the person's Hinglish level,
  - (d) signs the person may be under 18,
  - (e) second safety net for hinted crises.
  - If Jev is slow or down: keep the current skill and the plain-code rules.
- **Age rule:** if the person seems under 18, Vaani gently says the space is for adults, ends kindly, and the session is flagged.
- **Consent screen** on the web page: adults only, what is recorded, who the vendors are (including Jev's US-based maker), that crisis sessions are reviewed by the founder.
- **The AI judge:** chosen from a different model family than M1, with written score descriptions; calibrated against the founder's own scores before its scores are used.

### Tests written in this phase
- **L1 Jev:** 30 conversations tagged by the founder with the right skill. Jev must agree at least 85% of the time.
- **L1 S1:** summaries keep at least 90% of key facts.
- **L2 single replies:** about 40 cases per skill (activation, quality, boundary), code checks plus judge.
- **L5 safety red team:** about 150 cases, each run 3 times, all 3 must pass. Includes hinted crises in English and Hinglish, the age rule, and identity attacks.
- **Judge calibration:** founder scores 50 replies; judge agrees at least 80% on pass/fail and is within one point at least 85% on 1-to-5 scores.
- Blind dial test: replies at low and high Spark and Steadiness rated blind. If raters can't tell them apart, rewrite the instructions.

### Exit gate
- [ ] Every skill passes its activation, quality and boundary tests. Any boundary failure means that skill isn't ready.
- [ ] L5 safety: **100%** pass, 3 runs each.
- [ ] Honesty about being an AI: **100%** pass.
- [ ] Jev skill choice agrees with the founder at least 85%; switching to "Jev down" keeps Vaani working.
- [ ] Judge calibration passes.
- [ ] Reply time has not grown more than the measured cost of the larger instructions.

---

## Phase 3 — 20 minutes: coherence, memory, durable data

**Goal:** a full 20-minute conversation that stays coherent, ends well, and never loses data, even if something crashes.

### What gets built
- **Durable session log** in PostgreSQL: every turn appended as an event during the call. This is the source of truth.
- **Redis** as a fast cache of the log (recent turns, running summary, session note, skill state). If Redis restarts, the session is rebuilt from the log within one turn. Managed Redis with a standby copy.
- **Compaction:** the last ~5 turns kept word for word; older turns summarised every ~10 turns by S1 in the background.
- **The session note:** warm-up done or not, open threads, minutes left, wrap-up due. Placed at the end of the instructions.
- **The session clock:** natural wrap-up from minute 17 to 18; polite goodbye at minute 20; feedback form appears.
- **"Forget that":** removed immediately from the current call and from every derived copy (cache, log, summaries, saved story), lightly: "Done, it's gone."
- **Session stories** saved to PostgreSQL for consenting testers only (cross-call memory itself stays deferred, RE-D8).
- Every stored record carries a format version. Every background job is keyed by session ID and safe to run twice.

### Tests written in this phase
- **L3 whole conversations** in text with a simulated person, 12 personas (quiet student, chatty professional, Hinglish-heavy speaker, worried about a decision, hobby lover, teaser, sudden heavy disclosure, "are you real?", topic jumper, rule breaker, "forget what I said", tired and wants to leave early).
- Recall of a detail planted in the first 5 minutes; wrap-up timing; skill stability; repetition; character holding at minutes 5, 10, 15 and 20.

### Exit gate
- [ ] Recall of an early detail in **90%** or more of simulated 20-minute conversations.
- [ ] Wrap-up on time in **100%** of runs.
- [ ] "Forget that" leaves no copy anywhere.
- [ ] Redis restarted mid-call: session rebuilt within one turn.
- [ ] A background job run twice changes nothing.
- [ ] Character score at minute 20 averages **4.0** or more (judge).

---

## Phase 4 — The face and reliability

**Goal:** Vaani gets her face, and every designed failure behaves gracefully instead of going silent or robotic.

### What gets built
- **The avatar (LemonSlice)** behind a swappable connection, added only now that the voice call works well.
- **Avatar vendor checklist** (Reading Engine document, section 12): steering while silent, delay, cost, Enterprise-only features, lip match on Hinglish, failure behaviour. One backup vendor tested the same way.
- **Avatar failure:** the call continues voice-only with a still image.
- **Graceful hiccup mode:** pre-recorded lines in Vaani's voice, at least 6 variants per situation, matched to the current mood and language, never the same twice in a row, fillers at most about once a minute.
  - Stored in the browser (for the person's internet dropping) and on the server (for our services failing).
- **Reconnect and resume:** short drop → local line plays, then Vaani re-enters on the last topic; drop over about 45 s → gentle close and a rejoin link valid for 30 minutes.
- **Admission control:** when a vendor's limit on simultaneous calls is reached, new users see "Vaani is busy right now" instead of every live call getting worse.
- **Reading Engine readiness** (Reading Engine document, section 14): data channel between browser and agent, camera permission step, avatar able to receive cue commands.
- **Operations dashboard:** call success rate, 95th and 99th percentile per stage, fallback and hiccup counts, cost per call, with alerts.

### Tests written in this phase
- **L1 face:** 20 recorded replies rated for lip match; added delay measured.
- **L6 fault injection:** kill M1, Sarvam, Cartesia, Redis, the avatar; cut the person's internet for 10 s and for 60 s.

### Exit gate
- [ ] Lip match averages **4.0** or more.
- [ ] Reply time with the face: 95th percentile **2.5 s** or less.
- [ ] Every fault-injection test behaves exactly as designed; no silent failure.
- [ ] Hiccup lines never repeat twice in a row and match the mood.
- [ ] Rejoin link resumes the same session.

---

## Phase 5 — Evaluation and release

**Goal:** prove version 0 is good, safe and fast with numbers we trust, and record the honest baseline that version 0.5 must beat.

### What gets built
- **The L4 audio test robot:** joins a real LiveKit room and plays the recorded scripts into the live pipeline, measuring reply time, cut-offs, wrong stops, slow stops and awkward silences.
- **Full runs including the hidden test sets** (about 30% of every set, untouched until now).
- **Human testing:** 10 to 15 adults, a mix of students and professionals, English-dominant and Hinglish-dominant speakers. Each does at least one full 20-minute session; some do two, a few days apart. Same scenario checklist and six-question feedback form as `V0_03`.
- **Founder review:** 20 full transcripts read, every unnatural moment marked.
- Cartesia moved to the Startup plan before testers start.
- **The baseline report:** every number, with versions attached, and the top five unnatural moments handed to version 0.5 planning.

### Exit gate: the V0 scorecard
Every line of the scorecard in `V0_07` section 11 passes, including:
- [ ] Safety red team **100%**, hidden set included.
- [ ] Reply time, voice only: 50th ≤ 1.3 s, 95th ≤ 2.0 s, 99th ≤ 3.0 s.
- [ ] 20-minute sessions without a crash: at least 9 out of 10 with testers.
- [ ] At least 10 adults finished a 20-minute session.
- [ ] At least 50% say yes (not maybe) to "would talk to it again".
- [ ] Turn-taking numbers (cut-offs, wrong stops, slow stops, silences) **recorded** per 10 minutes. No target: this is what version 0.5 must beat.
- [ ] Baseline report written.

---

## 3. Decisions made on 19 Oct 2026

These are recorded in the Reading Engine document and change parts of the V0 files.

| Decision | Owned by |
|---|---|
| Read face and voice together | RE-D1 |
| Video never leaves the laptop | RE-D3 |
| Jev is the primary turn Decider; hand-tuned rules are the fallback and safety default | RE-D4 |
| Cartesia voice (Pro while building, Startup from Phase 5); Sarvam Bulbul as backup voice | RE-D7 |
| Sarvam is the only speech-to-text, no backup; failure rule as in Phase 1 | RE-D9 |
| Five skills (the five modes), chosen by Jev in the background, plus decisions (b) to (e) | RE-D10 |
| Turn-taking test scripts recorded with video from the start | RE-D13 |
| Age rule: under-18 signs lead to a kind ending and a flag | Phase 2 |
| Repository is private; reference designs are used for ideas only and never named in project files | Project rule |

## 4. Changes needed in the V0 files (cleanup pass)

| File | Change |
|---|---|
| All V0 files | Remove every mention of the reference design by name; keep the ideas in our own words. Remove the pointer to a "What we took from ..." section |
| `V0_00` | V0-D3: Sarvam only, no backup. V0-D9: replace "all modes in one prompt, no router" with five skills chosen by Jev in the background. Replace the brick plan with these phases. Fix references to "D2", "D13", "D14" of the parent to RE-D numbers |
| `V0_01` | Section 1 and 9: speech-to-text has no fallback; failure rule per RE-D9. Section 5: the mode tracker is now Jev's background skill choice |
| `V0_02` | Add the age rule. Modes are now skills. Add the priority order for conflicts |
| `V0_03` | Fault test "speech-to-text killed": expect apology and clean end, not a switch |
| `V0_04` | Remove the reference-design framing. Rules check and skill chooser updated for Jev. Skill construction checklist kept |
| `V0_05` | "Deferred (D14)" becomes RE-D8 |
| `V0_06` | Speech-to-text failure row updated per RE-D9 |
| `V0_07` | L1: add the Jev test (85% agreement). L4: scripts are recorded with video from Phase 0 (RE-D13). "Phase 0" now exists as defined here |
