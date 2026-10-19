# Reliability & Data Design Review

**Two additions: (1) a "graceful hiccup" mode so Vaani never goes silent or robotic when a connection or service fails, inspired by how Alexa handles losing the internet; and (2) a review of our whole design against the principles in *Designing Data-Intensive Applications* (Martin Kleppmann), with every correction listed.**

Status: Draft v0.2 · 19 Oct 2026

> Parent document: `Reading_Engine_Design_Document.md` (decisions RE-D1 to RE-D13). Build order and phase gates: `vaani_build_phase_v0.md`. Updated 19 Oct 2026 to match the decisions made that day.

Read with: `V0_01`, `V0_04`, `V0_05`

---

## Part 1 — Graceful hiccup mode (the Alexa idea, done better)

### 1.1 What Alexa does, and where we improve

When Alexa loses the internet, the device itself still notices you spoke and plays a short message saying it's having trouble connecting. The key idea: **the device keeps a small amount of ability locally, so failure never means silence.**

| Alexa | Vaani |
|---|---|
| One fixed error message | A bank of varied lines, never the same twice in a row |
| Same tone every time | Matches the current skill: gentle in support, light in casual chat |
| English only | Matches the person's language style (English or Hinglish) |
| Starts fresh after reconnecting | Picks up exactly where the talk left off |
| Face irrelevant | The avatar keeps a calm, attentive look instead of freezing |

### 1.2 The core trick: lines recorded in advance

When things fail, the voice service itself may be the thing that's down. So hiccup lines are **pre-recorded in Vaani's voice** and stored in two places:

- **In the person's browser**, downloaded when the call starts, for when **their internet** drops.
- **On our server**, for when **one of our services** fails.

Pre-recorded clips also start instantly (no waiting for a voice service), so even the normal "hmm" filler for a slow reply uses them.

### 1.3 The situations and what Vaani does

| Situation | Who notices | What the person experiences |
|---|---|---|
| **Brain is slow** (no first word by 1.0 s) | Server | A short pre-recorded filler: "Hmm...", "Let me think about that...", or in Hinglish, "Hmm, ek second..." |
| **Person's internet drops** | Browser, within about 1 to 2 s | Browser plays a local clip: "Oh, I think my connection just dipped... give me a second." The avatar shows a calm, pre-recorded attentive loop and a small "reconnecting" sign appears |
| **Internet comes back** | Server | Vaani re-enters naturally, using the saved session note: "Sorry, lost you for a moment. You were telling me about your mock test?" |
| **Dropped for more than about 45 s** | Browser | Gentle close: "Looks like the connection isn't cooperating. Let's pick this up when it's back." A rejoin link resumes the same session for the next 30 minutes |
| **One speech-to-text turn lost** | Server | "Sorry, I didn't catch that properly. Could you say it once more?" |
| **Speech-to-text (Sarvam) down:** two errors in a row, or nothing back for 5 s | Server | A pre-recorded apology in Vaani's voice ("I'm having trouble hearing you right now, something on my side isn't working. Let's pick this up in a little while."), the call ends cleanly, and a rejoin link resumes the same session for the next 30 minutes. There is no backup speech service (RE-D9) |
| **Both brains (M1 and M2) fail** | Server | "Give me a moment, something on my side is acting up." Retries in the background; if still failing after about 30 s, apologises and offers to continue later |
| **Voice service (Cartesia) fails** | Server | Switch to the backup voice (Sarvam Bulbul). If both fail, play a pre-recorded apology and end gracefully |
| **Decision model (Jev) slow or down** | Server | Nothing visible: Vaani keeps the current skill and the plain-code rules |
| **Avatar fails** | Server | The call continues voice-only with a still image |

### 1.4 Rules that keep it human

1. **Never repeat the same line twice in a row**; pick at random from at least 6 variants per situation, skipping the last two used.
2. **Match the skill:** in support, softer lines ("Take your time... I'm right here, just a small connection blip"); in playful banter, lighter ones ("My internet has chosen violence today, one second").
3. **Match the language style** of the conversation so far.
4. **Never claim to have heard what it didn't.** After a drop, Vaani asks the person to repeat, rather than pretending.
5. **Fillers at most about once a minute.** Constant "hmm" sounds broken.
6. **Every hiccup is logged** (what failed, for how long) so we fix causes, not just symptoms.

**Later idea:** the browser could keep the last few seconds of the person's speech during a short drop and send it after reconnecting, so Vaani can respond to what was said. That's more complex; it waits until after v0.

---

## Part 2 — Review against *Designing Data-Intensive Applications*

The book's three big goals are systems that are **reliable** (keep working when things go wrong), **scalable** (cope with growth) and **maintainable** (easy to run, understand and change). Here's what each principle found in our design.

### 2.1 Reliability

| Book principle (paraphrased) | What was weak in our design | Correction |
|---|---|---|
| **A fault is one part going wrong; a failure is the whole system stopping. Design so faults don't become failures.** | We had fallbacks for some parts but no single picture of degraded behaviour | Added Part 1: every fault has a defined, graceful experience |
| **Deliberately trigger faults to prove tolerance works.** | Fallbacks were designed but never tested | **Added fault-injection tests:** deliberately kill M1, Sarvam, Cartesia, Jev, the avatar, Redis and the person's connection during test calls, and check Vaani behaves as designed (in `V0_03`) |
| **Networks have no guaranteed delivery time, so timeouts must be chosen from measured delays.** | Already done for M1 (1.5 s, then tuned from real data) | Extended the same rule to every outside service: speech, voice, avatar, Jev, memory lookups |
| **Retries can make things worse; a request may have succeeded even if no reply arrived.** | Not addressed | **Live path: no blind retries.** Switch to the fallback where one exists (M1 to M2, Cartesia to Bulbul); where none exists (Sarvam), follow the clean-end rule. **Background jobs:** retry with growing waits plus a little randomness, and make every job safe to run twice (see 2.3) |

### 2.2 Scalability and speed

| Book principle (paraphrased) | What was weak | Correction |
|---|---|---|
| **Averages hide the slow cases; use percentiles (the 50th, 95th, 99th). The slowest few requests often belong to the most engaged users.** | `V0_03` tracked "typical and slowest 10%" | **Track the 50th, 95th and 99th percentile for every stage** (speech end, first word, first audio, first face frame) |
| **When one request depends on several services in a row, the chance of hitting at least one slow one grows ("tail latency amplification").** | Every turn passes through four services in a row: speech-to-text, brain, voice, avatar. Their slow moments stack | Set a **per-stage time budget** that adds up to under 2 s at the 95th percentile; alert when any stage's 99th percentile drifts; this is also why fillers matter. Jev runs in the background, so it is not part of this chain |
| **Describe load with clear numbers before planning growth.** | We never defined load | **Load measures defined:** calls happening at the same time, call-minutes per day, and turns per minute. Each live call uses one agent worker and one slot at each vendor |
| **When at capacity, refuse new work cleanly rather than slowing everyone.** | No plan for hitting vendor limits | **Added admission control:** if a vendor's limit on simultaneous calls is reached, new users see "Vaani is busy right now, try again in a few minutes" instead of every live call degrading |

### 2.3 Data: logs, memory and deletion

This is where the review found the most important gaps.

| Book principle (paraphrased) | What was weak | Correction |
|---|---|---|
| **Treat an append-only log of events as the source of truth; everything else is derived from it.** | In `V0_05`, the transcript lived only in Redis until the after-call job ran. If the agent crashed at call end, or Redis expired the data first, the call's memory was lost forever | **Each turn is appended as an event to a durable session log** during the call (in PostgreSQL). Redis becomes a fast **cache** of that log, not the only copy. The after-call memory job reads from the durable log |
| **Derived data can be rebuilt from the source.** | Memories were a one-way extraction | Because the transcript log is the source, **memories can be re-extracted** when we improve the extraction logic, within the transcript retention window. After that window, the memories themselves become the record. This trade-off is now explicit |
| **Messages may be processed more than once; make processing safe to repeat.** | The after-call job could run twice after a crash and create duplicate memories | **Every job is keyed by session ID**, and each memory carries a fingerprint of its source, so running the job twice changes nothing |
| **A user must see their own changes immediately ("read your own writes").** | "Forget that" was applied to long-term memory only after the call, by the background job. A person who started a new call quickly could hear the forgotten thing again | **Forget is applied immediately and directly** to long-term memory (marked deleted) before the call ends, not left to the background job. New calls always read from the main database copy, never from a possibly-behind replica |
| **Deleting data means deleting every derived copy.** | Forgetting covered Redis and the memory table only | **Forget now reaches every copy:** session cache, session log, extracted memories, search vectors and analytics. Each memory records **which session and turn it came from**, so deleting a source also deletes everything derived from it. Backups expire on a fixed schedule so deleted data ages out |
| **Data formats change over time; old and new versions must keep working together.** | No versioning of memory records or session events | **Every stored record carries a format version**, and readers ignore fields they don't understand. Instruction-layer versions are already recorded per session |
| **Clocks on different machines disagree; never rely on them to order events or measure durations.** | Timing logs mixed browser and server timestamps | **Durations are measured with each machine's steady internal timer**, never by subtracting timestamps from two different machines. Event order comes from the session log's sequence numbers, not clock times. The Reading Engine follows the same rule for face numbers (Reading Engine document, section 6.3) |

### 2.4 Maintainability

| Book principle (paraphrased) | Our application |
|---|---|
| **Operability: make the system easy to run.** | One dashboard: call success rate, 95th and 99th percentile per stage, fallback and hiccup counts, cost per call. Alerts when any of these drift |
| **Simplicity: avoid needless complexity.** | Deliberately only three infrastructure pieces: LiveKit Cloud, Redis, PostgreSQL. **No message queue system like Kafka** in v0; a solo founder can't run it, and PostgreSQL plus simple background workers handle our load |
| **Evolvability: make change easy.** | Every vendor sits behind a swappable connection (RE-D2); data formats are versioned (above) |
| **Data systems carry ethical responsibility; collect only what you need.** | Video never leaves the laptop (RE-D3), no ID or bank details stored, consent first, a "what Vaani remembers" page |

### 2.5 Redis specifically

| Question | Decision |
|---|---|
| What if Redis restarts mid-call? | The session is rebuilt from the durable log; the person notices at most one slow turn |
| Single point of failure? | Use a managed Redis with a standby copy |
| Does Redis need full durability settings? | No, it's a cache now. Moderate persistence is enough; the session log is the real record |

---

## Summary of everything changed or added

**Added**
1. Graceful hiccup mode with pre-recorded, varied, skill-matched lines in the browser and on the server.
2. Session resume within 30 minutes after a dropped connection or a speech-to-text outage.
3. Fault-injection tests.
4. Admission control when vendors reach capacity.
5. A durable, append-only session log as the source of truth.
6. Format versions on all stored records.
7. An operations dashboard with alerts.

**Changed**
1. Latency tracking moved from "slowest 10%" to the 50th, 95th and 99th percentile per stage.
2. Redis demoted from "only copy of the call" to "fast cache of the log".
3. "Forget" now applies immediately and reaches every derived copy.
4. After-call jobs are safe to run twice.
5. Timing uses each machine's steady internal timer, not cross-machine clocks.
6. Retries are banned on the live path and controlled in background jobs.
7. The filler "hmm" moved from generated speech to pre-recorded clips, so it plays instantly.
8. Speech-to-text has no backup service (RE-D9); its failure now leads to a clean end with a rejoin link.

## Source

- Martin Kleppmann, *Designing Data-Intensive Applications* (O'Reilly, 2017): principles paraphrased from the chapters on reliability, scalability and maintainability; trouble with distributed systems; stream processing; and the future of data systems.
