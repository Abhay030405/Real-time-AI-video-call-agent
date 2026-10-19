# Reading Engine — Design Document

**The Reading Engine lets Vaani read the person's face and voice together, the way people do, so she knows when someone has finished, when they are only thinking, and when a sound is not an interruption. It is the one part of Vaani that is truly ours. Everything in version 0 exists so we can prove, with numbers, that this engine makes conversation feel more human.**

Status: Draft v0.1 · 19 Oct 2026

Child documents: `V0_00` to `V0_07` (version 0, the baseline without the engine)
Decision numbering: decisions in this document are **RE-D1, RE-D2, ...**. Version 0 decisions are **V0-D1, V0-D2, ...**. When a V0 file says "D2 of the parent document", it means RE-D2 here.

---

## 1. The problem in one paragraph

Today's voice AI decides turns mostly from **silence**. If the person stops making sound for a set time, it assumes they are done and starts talking. If the person makes any sound while it talks, it assumes an interruption and stops. People don't work like this. We look at the other person's face: a closed mouth and eyes coming back to us mean "your turn"; eyes drifting up and a half-open mouth mean "wait, I'm thinking"; a small "haan" with a nod means "keep going". Because voice AI is blind to all of this, it cuts people off mid-thought, stops talking at every cough, and leaves awkward gaps. The Reading Engine gives Vaani eyes for exactly these moments.

## 2. What the Reading Engine is not

| Not this | Why |
|---|---|
| An emotion detector | Guessing feelings from faces is unreliable and feels invasive. The engine reports only what is visible (smiling, looking away), never "sad" or "anxious" (RE-D5) |
| A video recorder | Video never leaves the laptop. Only a few numbers per frame do (RE-D3) |
| An interview assessor | Reading eye contact or nervousness for interview practice belongs to version 1, in its own document (RE-D12) |
| A memory system | Nothing the engine sees is remembered after the call |
| Something Vaani talks about | Vaani never says "you look tired" or "I can see you smiling" |

## 3. Where it sits in the roadmap

| Version | What it adds | Turn-taking |
|---|---|---|
| **0** | The 20-minute companion: voice, character, five skills, memory within a call, the face (avatar) | Voice only (LiveKit standard detection). This is the **baseline** |
| **0.5** | **The Reading Engine** | Face plus voice, decided by the Reading Engine |
| **1** | Interview practice | Same engine, plus interview-specific reading (separate document) |
| Later | Memory across calls, phone support, our own avatar | — |

## 4. Decisions

| # | Decision | Why | Revisit when |
|---|---|---|---|
| **RE-D1** | **Read face and voice together** | Face alone is weak (people look away while still talking). Voice alone is what version 0 already does. The edge is in combining them | Never |
| **RE-D2** | **Every outside vendor sits behind a swappable connection** (speech-to-text, AI models, voice, avatar, decision model) | Vendors change price, quality and availability. Swapping one must never mean a rebuild | Never |
| **RE-D3** | **The face tracker runs inside the person's browser. Only a few numbers per frame leave the laptop, never video or images.** Nothing the engine sees is stored after the call, except anonymised timing logs for consenting testers | A firm privacy promise, stated publicly on the consent screen | Never |
| **RE-D4** | **Jev (TypeSafe) is the primary Decider for the three timing moments. Hand-tuned rules are the fallback and the safety default** | The founder expects Jev to be more accurate than rules written by hand, and it returns typed decisions with confidence. Rules stay ready because turn decisions must be fast, and Jev is new (see section 7) | After the head-to-head test (section 7.5) |
| **RE-D5** | **Observable behaviour only, never emotion labels; never mentioned aloud** | Scientific honesty and the person's comfort | Never |
| **RE-D6** | **When the face signal is unclear, fall back silently to voice-only turn-taking** (version 0 behaviour) | Camera denied, dark room, face out of frame: the call must still work exactly as well as version 0 | Never |
| **RE-D7** | **Cartesia for Vaani's voice** (Pro plan while building, Startup plan once testers start); Sarvam Bulbul as the backup voice | Fastest first audio; price per session is close to Sarvam's, so speed and sound decide | Voice quality or cost complaints |
| **RE-D8** | **Memory across calls is deferred to version 1.** Version 0 only quietly saves each consenting tester's session story (see `V0_05`) | Keep version 0 small; the saved stories give real data for later | Version 1 planning |
| **RE-D9** | **Sarvam is the only speech-to-text service, with no backup.** One lost turn means Vaani asks to repeat. Two errors in a row, or nothing back for 5 seconds, means a pre-recorded apology in Vaani's voice, the call ends, and a rejoin link works for 30 minutes | Sarvam is built for Indian speech and code-mixing; the founder accepts the risk of no backup | If Sarvam outages become frequent |
| **RE-D10** | **Jev also makes Vaani's background decisions:** which of the five skills to use next, how intense, heavy-disclosure detection, the person's Hinglish level, signs the person may be under 18, and a second safety net for hinted crises. These run after the reply has started and never delay it. If Jev is down, Vaani keeps the current skill and the plain-code rules. Repeated phrasing is checked by plain code | One fast, typed decision model for every "choose between options" moment | After version 0 evaluation |
| **RE-D11** | **Success criteria are fixed before building** (section 13) | Prevents moving the goalposts after seeing results | Never for v0.5 |
| **RE-D12** | **Interview-specific reading is out of scope here** | Belongs to version 1 | Version 1 planning |
| **RE-D13** | **Record the turn-taking test scripts on video from the start of version 0** | Version 0 and version 0.5 must be tested on the exact same takes. Adding video later would mean new takes, which breaks a fair comparison | Never |

## 5. The three key timing moments

These three moments map directly to the three numbers version 0 records as its baseline.

### Moment A — Finished, or just thinking?

| | |
|---|---|
| **When** | The person stops making sound |
| **The question** | Are they done, or gathering a thought? |
| **Face signals** | Mouth closed vs half open; eyes coming back to the screen vs drifting up or away; head still vs small "thinking" movement |
| **Voice signals** | Pitch falling at the end of the phrase (sounds finished) vs level or rising; a trailing filler ("umm", "matlab", "so...") just before the pause; a breath that suggests more is coming |
| **Decision** | `speak now` or `keep waiting` |
| **Cost of a wrong answer** | Speaking too early is a **cut-off**: the worst feeling in a conversation. Waiting too long is a small awkward gap |
| **Metric it improves** | Cut-offs |

### Moment B — Real interruption, or just a sound?

| | |
|---|---|
| **When** | The person makes a sound while Vaani is talking |
| **The question** | Do they want the floor, or was it "hmm", "haan", a laugh or a cough? |
| **Face signals** | A nod or smile with a short sound means "keep going". Mouth opening wide, leaning in, or a raised hand means "my turn" |
| **Voice signals** | Short and low ("hmm", "haan") vs words that keep coming; a cough's sound shape vs speech |
| **Decision** | `keep talking` or `stop and listen` |
| **Cost of a wrong answer** | Stopping at every "haan" is a **wrong stop**: it makes Vaani feel jumpy and broken. Not stopping for a real interruption is rude, so this side must lean toward stopping when unsure |
| **Metric it improves** | Wrong stops, and slow stops |

### Moment C — Done, so reply now

| | |
|---|---|
| **When** | Moment A has decided "finished" with high confidence |
| **The question** | Can Vaani start immediately instead of waiting out a fixed silence timer? |
| **Signals** | All of Moment A's "finished" signals agreeing strongly, for example falling pitch, mouth closed, eyes back on screen, and a direct question just asked |
| **Decision** | `start now` (skip the remaining wait) |
| **Cost of a wrong answer** | Same as a cut-off, so this only fires when confidence is high |
| **Metric it improves** | Awkward silences, and typical reply time |

## 6. How it is built

### 6.1 The four parts

| Part | Runs where | What it does |
|---|---|---|
| **The Eyes** | The person's browser | A face tracker reads the camera and turns each frame into a handful of numbers (list below). No image ever leaves the browser |
| **The Ears' cues** | Our server, beside speech-to-text | Reads timing and voice cues from the audio: voice activity, pitch at phrase ends, filler words from Sarvam's live partial transcript |
| **The Decider** | Our server, inside the LiveKit agent | At each timing moment, combines the latest face and voice signals and decides (section 7) |
| **The Outputs** | Our server | Turn decisions to LiveKit's manual turn control; listening cues to the avatar; a behaviour note to the instruction layers |

### 6.2 What the Eyes send (numbers only)

| Signal | Form |
|---|---|
| Face present, and how confident the tracker is | yes/no plus 0 to 1 |
| Mouth openness | 0 to 1 |
| Lip movement (talking-like motion) | 0 to 1 |
| Eyes on screen or away (and roughly which way) | on/away plus direction |
| Head nod or shake in the last moment | none / nod / shake |
| Smile | 0 to 1 |
| Frown | 0 to 1 |
| Leaning in or back | small / none / large |

Sent several times per second over the call's data channel. **If several faces are in frame** (common in Indian homes), the engine follows the largest, most central face and ignores the rest.

### 6.3 Timing and clocks

Face numbers and audio arrive from two machines. Following `V0_06`, we **never compare the browser's clock with the server's clock**. Each face reading carries how old it is, measured by the browser's own steady timer; the server places it on its own timeline by arrival time minus that age. Decisions and their outcomes are logged with the session log's sequence numbers.

## 7. The Decider: Jev first, rules as the safety net

### 7.1 How Jev is asked

Jev is asked **only when a timing moment begins**, never on every frame:

- **Moment A/C:** when the person goes silent. Ask: "Is the person finished?" (yes/no with probability), using the last few seconds of face and voice signals plus the last sentence they said.
- **Moment B:** when the person makes a sound during Vaani's speech. Ask: "Is this a request to take the turn?" (yes/no with probability).

Asking only at these moments keeps cost low and keeps Jev's job small and clear.

### 7.2 The time budget

Turn decisions are only useful if they arrive in time.

| Moment | Answer needed by | If Jev is late |
|---|---|---|
| A / C | About 0.4 s after the silence starts (tuned from data) | Use the rules' answer for this moment |
| B | About 0.25 s after the person's sound starts (tuned from data) | Use the rules' answer, which leans toward stopping |

Jev's maker states 70 to 500 milliseconds from request to answer, before the extra trip from India. So **we measure from Mumbai first**, both through Jev's direct service and through any provider that hosts it closer to India (for example an edge network with a Mumbai location), and use the fastest path.

### 7.3 Confidence thresholds

Jev returns a probability, not just yes/no. Starting thresholds, tuned later from test data:

- **Moment C (start now):** only when "finished" is very likely, about 0.85 or above.
- **Moment A (speak now):** "finished" about 0.6 or above; otherwise keep waiting, up to a maximum wait so silence never drags on.
- **Moment B (stop):** "taking the turn" about 0.4 or above. This threshold is low on purpose: when unsure, Vaani stops, because ignoring a real interruption is worse than a wrong stop.

### 7.4 The hand-tuned rules

Always computed (they cost nothing), used whenever Jev is late, down, or the head-to-head says rules win. Starting rules:

| Moment | Rule |
|---|---|
| A | Finished if: silence over 0.5 s **and** mouth closed **and** eyes on screen. Still thinking if: eyes away or up **or** trailing filler **or** mouth half open; then wait up to 3 s before speaking |
| B | Keep talking if: sound is short (under about 0.6 s) **and** (a nod or smile **or** the word is a known backchannel like "hmm", "haan", "acha", "right"). Otherwise stop |
| C | Start now if: falling pitch **and** mouth closed **and** eyes on screen **and** the last sentence was a question |

### 7.5 The head-to-head: deciding Jev or rules

Before testers see version 0.5, both deciders run on the same recorded video scripts (RE-D13). **Jev stays primary only if:**

1. it beats the rules on cut-offs and wrong stops combined, **and**
2. its 95th-percentile decision time fits the budget in section 7.2 from Mumbai.

Otherwise the rules become primary and Jev is retried with each new Jev release.

## 8. Listening cues to the avatar

While the person talks, a good listener nods and reacts. The engine sends cues to the avatar:

- **Nod:** at the end of the person's phrases during long turns, at most about once every few seconds.
- **Small smile:** when the person smiles, never during heavy or sad content (the support skill blocks it).
- **Attentive look:** the default while listening.

Whether this works depends on whether the avatar can be steered while silent: the first item on the avatar vendor checklist (section 12).

## 9. The behaviour note

Every few turns, the engine writes one short line into the mode slot (layer 3 of Vaani's instructions), for example: *"Looking away often, short answers in the last two minutes."*

- Only observable behaviour, never emotion labels (RE-D5).
- It nudges tone. It never decides a skill on its own, and Vaani never mentions it aloud.
- It is also passed to Jev's background skill choice (RE-D10) as one more input.

## 10. When the face cannot help

The engine switches silently to voice-only turn-taking (RE-D6) when:

- the camera is denied or off,
- the tracker's face confidence stays low (dark room, face out of frame, strong backlight),
- the laptop is angled away.

It switches back once the face is clear and steady for a few seconds. Every switch is logged, so we learn how often real homes defeat the camera (lighting, glasses, angle).

## 11. Privacy and consent

- The consent screen explains, in plain words, that the camera is used only inside the browser to read turn-taking signals, and that no video or images are sent or saved.
- The person can turn the camera off at any time; Vaani keeps working with voice only.
- Face numbers are not stored after the call. Consenting testers' timing logs keep only decisions and their timing, never face images.
- Every vendor that receives conversation data is listed on the consent screen, including Jev's maker (US-based).

## 12. Avatar vendor checklist

Run for LemonSlice in version 0 (Brick 5), and for any backup vendor:

1. **Can we steer it while it is silent?** (nods, smiles, attentive look on command)
2. **How fast** does it react to a command, and how much delay does it add to Vaani's speech?
3. **What does it cost** per minute for a 20-minute session?
4. **Which features are Enterprise-only?**
5. Do lips match Indian English and Hinglish words well?
6. What happens when it fails: can the call continue with a still image?

## 13. How we know it worked

Measured on the same recorded video scripts and with the same kind of testers as version 0 (`V0_03`, `V0_07`).

| Measure | Target for version 0.5 vs version 0 |
|---|---|
| Cut-offs | Down at least **40%** |
| Wrong stops | Down at least **40%** |
| Awkward silences | Down at least **30%** |
| Typical reply time (50th percentile) | No more than **0.1 s** slower |
| Blind side-by-side preference | At least **60%** of testers prefer version 0.5 |
| Decider accuracy per moment | Recorded against the founder's hand labels |
| Fallback to voice-only | Recorded: how often, and why |

## 14. What version 0 must not block

Version 0 is built so the engine plugs in without a rebuild:

| Version 0 must have | Why |
|---|---|
| LiveKit set up so manual turn control can replace standard detection | The Decider takes over turns |
| A data channel between browser and agent | Face numbers travel on it |
| A camera permission step on the web page (unused in v0 except for test recording) | The Eyes need it |
| The avatar connection able to receive cue commands | Listening cues |
| A mode slot that can take extra notes | The behaviour note |
| Turn-taking test scripts recorded **with video** | Fair head-to-head (RE-D13) |
| Turn decisions logged with what happened next | Data to tune thresholds and rules |

## 15. Build plan for version 0.5

Each step ends with something that runs and a check that passes.

| Step | What | Done when |
|---|---|---|
| RE-1 | The Eyes in the browser | Face numbers update several times a second on a test page; no image leaves the browser (checked in network logs) |
| RE-2 | Signals reach the agent, aligned on one timeline, and are logged | Face and voice signals line up correctly on recorded scripts |
| RE-3 | The rules Decider | Rules run on the recorded scripts; first numbers recorded |
| RE-4 | The Jev Decider with time budgets and rules fallback | Jev decisions measured from Mumbai; late answers fall back cleanly |
| RE-5 | The head-to-head (section 7.5) | Primary decider chosen with numbers |
| RE-6 | Listening cues to the avatar | Nods and smiles appear at sensible moments, never in heavy moments |
| RE-7 | The behaviour note | Note appears in layer 3; tone shifts are visible in test conversations |
| RE-8 | Testers and blind side-by-side | Every target in section 13 measured |

## 16. Risks

| Risk | Fallback |
|---|---|
| Jev is too slow from India for turn timing | Rules become primary (section 7.5); retry Jev on closer hosting or new releases |
| Jev is new and its service changes or goes down | Rules always computed; switch is automatic |
| Poor lighting and cheap webcams in real homes | Silent fallback to voice-only; measure how often; tune tracker thresholds |
| People look away while still talking (thinking, reading notes) | Never decide "finished" from the face alone; voice cues must agree |
| Avatar cannot be steered while silent | Ship turn decisions and the behaviour note first; listening cues wait for a vendor that supports them |
| Testers feel watched | Clear consent wording, camera-off option, Vaani never mentions the face; add a feedback question about it |
| Cultural differences in nodding and eye contact | Test with a mix of testers; thresholds tuned on Indian testers, not imported defaults |

## 17. Open questions for later

1. Exact time budgets for each moment, from real measurements.
2. Whether Jev can be reached from a location close to India.
3. How well the face tracker handles glasses, beards, dupattas and low light.
4. Whether nod frequency should adapt to each person over a session.
5. What interview practice (version 1) adds on top of this engine.
