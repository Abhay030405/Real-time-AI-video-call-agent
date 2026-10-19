# Version 0 — Architecture

**One live call, a few rented parts, and our own thin layer in the middle that holds the character, the skills, the memory, the session clock and the measurements. Everything is chosen so the reading engine can slot in later without a rebuild.**

Status: Draft v0.2 · 19 Oct 2026

> Parent document: `Reading_Engine_Design_Document.md` (decisions RE-D1 to RE-D13). Build order and phase gates: `vaani_build_phase_v0.md`. Updated 19 Oct 2026 to match the decisions made that day.

Read after: `V0_00_Overview_and_Build_Plan.md`

---

## 1. The parts

| Part | What it does | Built or rented | Choice for v0 |
|---|---|---|---|
| Web page | Microphone, camera permission (used in v0 only for test recording), shows the avatar, consent screen, feedback form | Built (from LiveKit's ready-made web starter) | Simple web app |
| Call layer | Carries audio and video between the person and the agent with very little delay | Rented | LiveKit |
| Ears (speech-to-text) | Turns the person's speech into text as they talk | Rented | **Sarvam only, no backup** (RE-D9) |
| Turn detection | Decides when the person has finished speaking | Rented (built into LiveKit) | LiveKit's standard voice detection plus its multilingual turn detector |
| Brain (AI model) | Decides what to say | Rented | **M1** called directly (hosted in India); **M2**, a different model via OpenRouter, when M1 fails or is too slow; **S1** helper for background jobs |
| Decision model | Makes Vaani's background choices: which skill next, heavy-disclosure detection, Hinglish level, under-18 signs, hinted-crisis safety net | Rented | **Jev (TypeSafe)**, run after the reply starts (RE-D10) |
| Voice (text-to-speech) | Speaks the reply | Rented | **Cartesia**, with **Sarvam Bulbul** as the backup voice (RE-D7) |
| Face (avatar) | Turns the voice into a talking, listening face | Rented | LemonSlice |
| **Conductor** | Our own layer: builds the brain's instructions, runs the rules check, holds the current skill, keeps memory, runs the clock, applies safety rules, logs timings and cost | **Built by us** | Runs inside the LiveKit agent |

## 2. What happens in one turn

1. The person speaks. Audio travels through LiveKit to our agent.
2. The Ears turn speech into text, word by word.
3. Turn detection decides the person has finished.
4. The rules check (plain code, a few milliseconds) adds any override instructions.
5. The Conductor assembles the brain's instructions (section 4) and sends the conversation so far.
6. The Brain starts producing its reply. The first words go to the Voice **as soon as they exist**, without waiting for the full reply.
7. The Voice turns words into audio; the Face turns the audio into video. Both stream back to the person.
8. **After** the reply has started, in the background: Jev chooses the skill for the next turn and answers the other background questions, and the Conductor updates the memory summary. This never delays the reply.

If the person speaks while Vaani is talking, LiveKit's standard interruption handling stops her. In version 0.5, the reading engine takes over this decision.

## 3. Why a chain of parts, not one all-in-one speech model

All-in-one speech models hear audio and speak audio directly, and can be slightly faster. We still choose the chain (V0-D1) because:

- **Hinglish:** we choose the speech service that handles mixed Hindi and English best. Sarvam is built on Indian speech and advertises code-mixing support and fast first results ([Sarvam speech-to-text](https://www.sarvam.ai/speech-to-text)).
- **Control for the reading engine:** turn-taking must later be decided by our engine, not inside a sealed model. LiveKit allows manual turn control for exactly this.
- **Safety and memory:** we need the transcript as text to check for risk, summarise for memory, and evaluate answers in version 1.
- **Our own voice:** we choose Vaani's exact voice.

The cost is a little extra delay, which we measure and work down.

## 4. How the brain's instructions are built

Each AI call is built from layers: fixed layers first so the AI service can reuse its earlier work every turn quickly and cheaply, changing layers after, and the deeper layer always winning a conflict.

| Layer | Contents | Changes | Wins conflicts over |
|---|---|---|---|
| 0. Identity | Who Vaani is: personality, warmth, curiosity, humour, the two dials, honesty about being an AI | Never | Everything |
| 1. Rules | Crisis and safety rules, honesty rules, the age rule, language mirroring, the priority order for conflicts, how the five skills blend and move | Never | Layers 2 and 3 |
| 2. Session context | Summary of earlier conversation, open threads, the person's language style | Every few turns | Layer 3 |
| 3. Skill and mode note | The current skill's instructions, intensity, and any override from the rules check: "Current skill: support. Person sounds stressed about exams." | When the skill changes, and every turn for the note | Nothing |
| Session note | Warm-up done or not, open threads, minutes left, wrap-up due | Every turn | — |

**Rule:** layers 0 and 1 must be identical on every call, with no timestamps or changing details inside them, so the AI service can reuse its earlier work and reply faster. Anything that changes goes after them. The skill text sits after the fixed layers, so swapping a skill only changes the tail.

## 5. The skill chooser (Jev)

After each person's turn, once Vaani's reply has started, Jev reads the last few exchanges and answers, in one call:

- **(a)** Which of the five skills fits the next turn, and how intense (low, medium, high).
- **(b)** Did the person just share something heavy? (locks playfulness off)
- **(c)** The person's Hinglish level, for language mirroring.
- **(d)** Signs the person may be under 18.
- **(e)** A hinted crisis that keyword rules might miss (second safety net).

Rules for using the answers:

- **Sticky by default.** Vaani switches skill only when Jev's probability for the new skill is clearly high, above a threshold tuned from test data. This stops flip-flopping.
- **Never on the critical path.** Jev runs after the reply has started; its answer shapes the next turn.
- **If Jev is slow or down:** Vaani keeps the current skill and the plain-code rules. Nothing waits on Jev.
- **Safety never waits for Jev.** The crisis rules live in layer 1 and in the plain-code rules check, so they apply on the very turn they are needed. Jev's hinted-crisis answer triggers the crisis override on the next turn.
- **Repeated phrasing** is checked by plain code, not Jev.
- In version 0.5, the reading engine's behaviour note is passed to Jev as one more input.

## 6. Memory within one session

A 20-minute conversation is far too long to resend in full every turn without slowing down.

- The **last ~5 turns are kept word for word**, which keeps Vaani's rhythm and tone consistent.
- **Older turns are summarised** every ten or so turns into a short note: facts mentioned, the emotional arc, open threads. Anything the person asked to forget is removed, not summarised.
- Summaries are made by S1 in the background.
- Every turn is also appended to a durable session log in PostgreSQL; Redis is a fast cache of it (`V0_06` section 2.3).

## 7. The session clock

| Time | Behaviour |
|---|---|
| Start | Consent and age check on the web page, then a warm greeting from Vaani |
| Minute 17 to 18 | Vaani starts closing naturally, without abruptly announcing time |
| Minute 20 | Polite goodbye, call ends, feedback form appears |

A clean ending matters: an abrupt cut-off spoils an otherwise good conversation.

## 8. Where things run

- **LiveKit Cloud, agent hosted in Mumbai (ap-south).** LiveKit reports that keeping the agent and models in India cut about 1 second per reply compared with hosting them in another region ([LiveKit blog](https://livekit.com/blog/building-performant-voice-agents-india)).
- Speech-to-text, M1 and the voice also run in India wherever the vendor allows. M2 and Jev may run elsewhere: M2 because it is used rarely, Jev because it runs in the background.
- API keys live only on our server, never in the web page. Each call gets a short-lived access pass.

## 9. When something breaks

| Failure | What the user experiences |
|---|---|
| Avatar fails | Call continues voice-only with a still image; logged |
| Voice service fails | Switch to the backup voice (Sarvam Bulbul). If both fail, a pre-recorded apology plays and the call ends gracefully |
| Speech-to-text (Sarvam) fails | One lost turn: Vaani asks the person to repeat. Two errors in a row, or nothing back for 5 s: a pre-recorded apology in Vaani's voice, the call ends, and a rejoin link works for 30 minutes. There is no backup service (RE-D9) |
| Brain (M1) errors or is too slow | Switch to M2 through OpenRouter; one short pre-recorded filler ("hmm, give me a second") covers the gap. After two M1 failures in a row, stay on M2 for several minutes. Full rules in `V0_04` section 9 |
| Jev slow or down | Nothing visible: Vaani keeps the current skill and the plain-code rules |
| Internet drops | The browser plays a pre-recorded, mood-matched line in Vaani's voice; reconnects automatically; Vaani re-enters referencing the last topic. Full design in `V0_06` Part 1 |

## 10. What we log in every session (for `V0_03`)

- Timing of each step per turn: speech ended, turn detected, brain's first word, first audio, first avatar frame.
- Interruptions: who interrupted whom, and whether it was wanted (from tester notes).
- Skill changes (with Jev's probabilities), rules-check overrides, and safety-rule activations.
- Cost per session, split by vendor.
- Crashes, reconnects, and every fallback.
- Transcripts, **only for consenting testers**, deleted on a fixed schedule.

## 11. How the reading engine plugs in later (no rebuild needed)

| Version 0 slot | Version 0.5 change |
|---|---|
| LiveKit standard turn detection | Replaced by the reading engine's Decider through manual turn control |
| Skill and mode note (layer 3) | Also receives the reading engine's behaviour note |
| Avatar's idle behaviour | Receives listening cues (nods, smiles) from the engine |
| Web page | Adds the in-browser face tracker and sends numbers over the data channel; video still never leaves the laptop |

## Sources

- [LiveKit docs: video input and avatars](https://docs.livekit.io/agents/multimodality/vision/video)
- [Sarvam speech-to-text](https://www.sarvam.ai/speech-to-text)
- [LemonSlice docs](https://lemonslice.com/docs/introduction/index.md)
