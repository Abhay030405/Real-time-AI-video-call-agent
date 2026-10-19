# Version 0 — Overview & Build Plan

**A face-to-face AI companion you can talk to about anything for 20 minutes. No reading engine yet. This version is the foundation every later part sits on, and the "switched off" baseline we will compare the reading engine against.**

Status: Draft v0.2 · 19 Oct 2026

> Parent document: `Reading_Engine_Design_Document.md` (decisions RE-D1 to RE-D13). Build order and phase gates: `vaani_build_phase_v0.md`. Updated 19 Oct 2026 to match the decisions made that day.

Companion files: `V0_01_Architecture.md` · `V0_02_Character_and_Conversation_Modes.md` · `V0_03_Testing_and_Measurement.md` · `V0_04_Engineering_Blueprint.md` · `V0_05_Memory_and_Personalization.md` · `V0_06_Reliability_and_Data_Design.md` · `V0_07_Evaluation_Framework.md`

---

## 1. What version 0 is

A person opens a web link on their laptop, sees and hears Vaani, and talks to her about anything for up to 20 minutes, in English or Hinglish. Vaani adapts to the conversation through five conversation skills: light and playful when the talk is casual, focused when it turns serious, gentle and supportive when the person is going through something.

## 2. What version 0 is not

| Not included | Why | Comes in |
|---|---|---|
| Reading the user's face | v0 must first prove the basic call works; it is also the baseline for comparison | Version 0.5 |
| Interview practice | Keep v0 general; interviews are added on top | Version 1 |
| Memory across sessions | Keep v0 small (RE-D8). v0 only quietly saves consenting testers' session stories | Version 1 |
| Phone support | Laptop first | Later (but nothing in v0 may block it) |
| Our own avatar | Rented first, swappable | Much later |

## 3. Why build version 0 first (first-principles reasoning)

1. **Every later feature depends on the basic call feeling good.** If replies are slow or the voice is robotic, no reading engine can save it. Fix the foundation first.
2. **Random conversation is the hardest test of human feel.** It has more pauses, jokes, topic jumps and interruptions than an interview. If it feels human here, interviews will be easy.
3. **We need a fair baseline.** The proof of our edge is: "people prefer the companion with the reading engine over the same companion without it." Version 0 is the "without it" side, built with the best voice-only turn-taking available today, so the comparison is honest.
4. **It is the fastest way to find vendor problems** (Hinglish accuracy, avatar lag, cost) before building our own technology on top of them.

## 4. Engineering decisions for version 0

| # | Decision | Why | Revisit when |
|---|---|---|---|
| V0-D1 | Use a **chain of separate parts** (speech-to-text, then the AI brain, then text-to-speech), not a single all-in-one speech model | We need control: choose the Hinglish speech service, choose our voice, read the transcript for safety and memory, and later let our reading engine control turn-taking. All-in-one models hide these steps | All-in-one models offer the same control |
| V0-D2 | Run on **LiveKit Agents** | Proven real-time call framework, works with all our vendors, allows manual turn control for the reading engine later | Never for v0 |
| V0-D3 | **Sarvam is the only speech-to-text service, with no backup** (RE-D9). One lost turn: Vaani asks to repeat. Two errors in a row or nothing back for 5 s: a pre-recorded apology, the call ends, and a rejoin link works for 30 minutes | Sarvam is built for Indian speech and code-mixing. Hinglish accuracy is make-or-break; the founder accepts the risk of no backup | If Sarvam outages become frequent |
| V0-D4 | **Cartesia** for Vaani's voice (Pro plan while building, Startup plan from Phase 5), with **Sarvam Bulbul as the backup voice** (RE-D7) | Fastest first audio; price per session is close to Sarvam's, so speed and sound decide | Voice quality or cost complaints |
| V0-D5 | **M1:** a fast AI model, called directly and hosted in India. **M2:** a different model from a different provider, called through OpenRouter only when M1 errors or is too slow. **S1:** a cheaper helper model for background jobs | Speed of first word matters most; a fallback keeps calls alive when a provider fails. Details in `V0_04` section 9 | Each new model release |
| V0-D6 | Use **LiveKit's standard voice-only turn detection** as-is | This is the fair baseline the reading engine must beat | Version 0.5 replaces it |
| V0-D7 | **Voice first, face second:** the avatar is added only after the voice call works well | Isolates problems. If the avatar is added on day one, every delay and glitch has two suspects | Never for v0 |
| V0-D8 | Avatar from **LemonSlice** (via its LiveKit plugin), behind a swappable connection (RE-D2) | Strongest candidate for listening behaviour and gestures | Vendor checklist fails |
| V0-D9 | **Five conversation skills** (casual chat, curious deep-dive, serious discussion, support, playful banter). **Jev (TypeSafe) chooses the skill for the next turn in the background**, after the reply has started, so it never adds delay. Skills are "sticky": they switch only when Jev is clearly confident. If Jev is slow or down, Vaani keeps the current skill (RE-D10) | The way people talk changes through a conversation; a dedicated decision model chooses better than one long prompt, and running it in the background keeps replies fast | After version 0 evaluation |
| V0-D10 | **Measure everything from the first call:** timing of each step, cost, crashes, tester ratings | What is not measured cannot be improved, and v0 numbers become the baseline | Never |
| V0-D11 | **Testers are adults (18+) who give consent**; transcripts kept only for testing and deleted on a fixed schedule. If someone seems under 18 during a call, Vaani gently says the space is for adults, ends kindly, and the session is flagged | Safety and trust | Public launch |
| V0-D12 | **Everything hosted in Mumbai where vendors allow:** LiveKit Cloud agent region, speech-to-text, M1, voice | Every trip across continents adds delay to every reply | Never |
| V0-D13 | **Python** for the agent; LiveKit's ready-made web components for the page | LiveKit's main toolkit; works well with Claude Code | Never for v0 |
| V0-D14 | **Paid services from day one** | Accepted by the founder; testing costs are small | Cost review at the Phase 5 gate |
| V0-D15 | **Turn-taking test scripts are recorded with video from Phase 0** (RE-D13) | Version 0 and version 0.5 must be tested on exactly the same takes | Never |

## 5. Build plan

Version 0 is built in six phases. Each phase ends with something that runs, its own tests written and passing, and a hard gate before the next phase starts. Full detail in `vaani_build_phase_v0.md`.

| Phase | Name | What exists at the end |
|---|---|---|
| **0** | Foundations | Repository, accounts, the evaluation skeleton, recorded speech clips and video test scripts |
| **1** | Talking pipe and speed baseline | A voice call in English and Hinglish, every stage timed, M1/M2/S1 chosen, every fallback working |
| **2** | Vaani's mind: character, skills, safety | Vaani's character, five skills chosen by Jev, every safety rule passing |
| **3** | 20 minutes: coherence, memory, durable data | A full 20-minute conversation that stays coherent and loses nothing on a crash |
| **4** | The face and reliability | The avatar, graceful hiccups, every designed failure behaving as planned |
| **5** | Evaluation and release | All tests including hidden sets, 10+ human testers, the baseline report |

## 6. Exit criteria: when version 0 is finished

Every line of the scorecard in `V0_07` section 11 passes. In short:

- [ ] 20-minute sessions complete without crashes in at least 9 out of 10 attempts.
- [ ] All safety tests pass.
- [ ] Baseline numbers recorded: reply time, wrong stops, cut-offs, awkward silences, "felt human" score, cost per session.
- [ ] Testers say they would talk to it again (a clear majority, not politeness).

Then version 0.5 starts: the Reading Engine and its three key timing moments, compared against these exact numbers.

## 7. Top risks for version 0

| Risk | Fallback |
|---|---|
| Sarvam's Hinglish accuracy is not good enough | Phase 1 stops until it is solved (there is no backup service): tune Sarvam's settings and vocabulary, and test English-only while it is worked on |
| Sarvam goes down during a call | Pre-recorded apology, clean end, rejoin link (V0-D3) |
| Jev is slow, changes or goes down | Vaani keeps the current skill and the plain-code rules; nothing waits on Jev |
| Avatar adds too much delay or costs too much | Test the backup vendor; continue voice-only while it is solved |
| 20 minutes of open chat feels boring | Strengthen curiosity and question-asking in the character; the five skills exist partly for this |
| Emotional conversations go somewhere unsafe | Safety rules sit above every skill and are tested before any tester joins |
