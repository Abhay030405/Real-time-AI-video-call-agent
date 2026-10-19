# Version 0 — Engineering Blueprint

**The engineering principles that turn Vaani's personality into a reliable, fast system: how her instructions are built each turn, what runs in the background, how skills are chosen, how models fall back, and what we deliberately leave out of version 0.**

Status: Draft v0.2 · 19 Oct 2026

> Parent document: `Reading_Engine_Design_Document.md` (decisions RE-D1 to RE-D13). Build order and phase gates: `vaani_build_phase_v0.md`. Updated 19 Oct 2026 to match the decisions made that day.

Read with: `V0_00` to `V0_03`

---

## 1. How to read this file

For every principle, we answer:

1. **What is the principle?**
2. **What does it mean for Vaani?**
3. **Do we build it in version 0, or later?**

---

## 2. Design principles for a voice character

| # | Principle | What it means for Vaani | v0 or later |
|---|---|---|---|
| P1 | **Layered instructions with priority:** identity, rules, person context, current skill. The deeper layer always wins a conflict | Our layers: identity, rules, session context, skill and mode note, session note (section 4) | **v0** |
| P2 | **One main AI call per turn.** Multi-agent and "plan then generate" designs add 0.5 to 2 seconds per extra call, fatal for voice | One main call per turn; everything else runs in the background | **v0** |
| P3 | **A rules check before the AI call:** plain code, not AI, a few milliseconds, that adds override instructions when rules are at risk | Safety, heavy-disclosure lock, wrap-up time, language rule, warm-first opening (section 6) | **v0** |
| P4 | **Dials turned into concrete instructions.** The AI never sees "0.6"; each dial range maps to a written behaviour | Our two dials, Spark and Steadiness (section 7) | **v0** |
| P5 | **Compaction:** keep the last ~5 turns word for word, summarise older ones every ~10 turns with a cheap model | Same, for our 20-minute sessions | **v0** |
| P6 | **A live session checklist** updated by code after each turn, not by the AI | Our "session note": warm-up done, open threads, minutes left, wrap-up due | **v0** |
| P7 | **Background analysis runs separately.** "Warm and funny" and "analytical" goals degrade each other inside one call | Jev's skill choice, the summariser and the safety logger run in the background, never inside the main reply | **v0** |
| P8 | **Hard tests vs soft scores.** Identity and rule breaks are pass or fail; quality gets 1 to 5 scores | In `V0_03` and `V0_07` | **v0** |
| P9 | **Skill construction checklist:** spec, then instructions, then tests (activation, quality, boundary). Any boundary failure means do not ship | Applies to all five skills (section 8) | **v0** |
| P10 | **Memory manners:** door rule, "would a good friend bring this up now?", "forget that" deletes at once, reference feelings not facts | Applied within one session in v0; across sessions in version 1 | **v0 (in-session)** |
| P11 | **Relationships deepen in stages** (stranger to trusted friend) | Only the first stage matters in v0: warm first, no teasing in the first minutes | **v0 (first stage only)** |
| P12 | **A skill chooser that is sticky by default,** with fast rules first for urgent cases | Jev chooses the next skill in the background; it switches only when clearly confident; rules handle urgent shifts on the same turn (section 5) | **v0** |
| P13 | **Voice selection criteria written before choosing a voice** (gender, accent, age feel, pace around 160 words per minute, warm but direct) | Written in Phase 2, then the Cartesia voice is chosen against them | **v0 (Phase 2)** |
| P14 | **Proactive outreach, messaging channels, cross-session memory, personalised dials** | Valuable, but they need a returning-user product first | **Later** |

### Build lessons (just as important)

- **Do not build machinery ahead of content.** A chooser that can send people to skills whose instructions do not exist leaves the product broken. **Our rule: no skill name exists in the chooser until its instructions and tests exist; every phase ends with something a person can actually use.**
- **Measure bare speed first.** Measure the plain call speed before adding complexity, because voice cannot ship above about 2 seconds. That is why Phase 1 is a plain talking pipe with timing logs.
- **Hard gates between phases.** The next phase does not start until the current phase's exit gate passes.

## 3. Lessons from Manus (public)

Source: [Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus), Yichao "Peak" Ji, 18 July 2025.

| # | Manus lesson | What it means for Vaani | v0 |
|---|---|---|---|
| M1 | **Design around reuse of the AI's earlier work ("cache").** Manus calls the cache hit rate the single most important production metric, because it cuts both delay and cost. Even one changed word early in the instructions spoils the reuse from that point on | Layers 0 and 1 never change during a session. **No time, date or changing values in them.** The clock, minutes left and the current skill go in later layers | Yes |
| M2 | **Only add to the conversation; never edit earlier parts. Keep the order of everything identical every time** | The conversation history only grows (until compaction). Instruction layers always come in the same order | Yes |
| M3 | **Do not add or remove tools mid-conversation; block them instead** | v0 has very few tools (for example, ending the call). They are fixed from the first turn | Yes |
| M4 | **Use outside storage as memory;** drop bulky details from the conversation only when they can be fetched again | Full transcripts live in our database. Only the summary and session note go into the AI's instructions | Yes |
| M5 | **Recite the goals at the end.** Keep the goals at the end of what the model reads, inside its recent attention | Our session note goes at the **end** of the instructions, just before the latest turns | Yes |
| M6 | **Keep mistakes visible.** Leaving a failed step in view lets the model adjust and not repeat it | If speech was misheard or a tool failed, that stays in the history so Vaani can say "sorry, I missed that" naturally | Yes |
| M7 | **Do not get stuck copying examples.** Models imitate patterns in front of them; small variations break the rhythm | Few, varied examples in our instructions. A plain-code check flags repeated openers ("That's interesting...") and nudges variety | Yes |
| M8 | **Stay independent of any one model** | Our layers work with any model, which is what makes the M1 and M2 fallback possible | Yes |

## 4. The instruction layers in version 0

Built fresh every turn by the Conductor, always in this order:

| Order | Layer | Contents | Changes | Why here |
|---|---|---|---|---|
| 1 | **0. Identity** | Who Vaani is: personality, the two dials, honesty about being an AI | Never | Unchanging start keeps the cache (M1) |
| 2 | **1. Rules** | Crisis and safety rules, honesty rules, the age rule, the priority order for conflicts, how the five skills blend and move, language mirroring, memory manners | Never | Same reason; rules always present (P1) |
| 3 | **2. Session context** | Summary of older turns, the person's language style, open threads | Every ~10 turns | Changes rarely, so it sits before frequently changing parts |
| 4 | **3. Skill and mode note** | The current skill's instructions, intensity and dial positions, plus any override from the rules check | When the skill changes; note every turn | Fresh guidance for this turn |
| 5 | **Session note** | Warm-up done or not, open threads, minutes left, wrap-up due | Every turn | At the end, where attention is strongest (M5) |
| 6 | Recent turns | Last ~5 turns word for word | Every turn | Keeps rhythm and tone (P5) |

**Size target:** keep the whole package small; speed matters more than detail. Measure first-word time as layers grow.

## 5. What happens in one turn (the Conductor pipeline)

1. Turn detection decides the person has finished.
2. **Rules check** (plain code, a few milliseconds) adds override instructions if needed (section 6).
3. The Conductor assembles the layers (section 4) with the current skill.
4. **Main AI call to M1.** The first words stream to the voice straight away.
5. In the background, never delaying the reply:
    - **Jev** answers, in one call: (a) which skill next and how intense, (b) heavy disclosure, (c) the person's Hinglish level, (d) under-18 signs, (e) hinted crisis,
    - the summariser compacts history every ~10 turns,
    - the safety logger flags crisis-rule activations,
    - the plain-code repetition check looks for repeated phrasing,
    - timing and cost are logged.

**Skill switching rules:** switch only when Jev's probability for a new skill is clearly high (threshold tuned from test data). If Jev is slow or down, keep the current skill. Jev's heavy-disclosure, under-18 and hinted-crisis answers feed the rules check for the next turn.

## 6. The rules check

| Situation | Override added | Why |
|---|---|---|
| Crisis words detected in the person's last turn, or Jev flagged a hinted crisis last turn | Force crisis rule: no humour, share Tele-MANAS 14416 and 112, stay present | Safety beats everything |
| Heavy disclosure in the last turn (keyword rule, or Jev last turn) | Lock playfulness off until the person brings lightness back | Character rule from `V0_02` |
| Under-18 signs (stated age or school, or Jev flag) | Apply the age rule: gentle explanation, kind ending, flag | Age rule from `V0_02` |
| Minute 17 or later | Begin natural wrap-up | Clean ending |
| Hindi not yet used and the mood is serious | Do not start Hindi now | Language rule from `V0_02` |
| First 2 minutes of the session | Warm first, no teasing | First-stage rule (P11) |
| Same opener in the last five replies | Ask for a different opening | Variety (M7) |

Lower layer always wins: a rule in Layer 1 overrides anything the skill note suggests.

## 7. Turning the two dials into instructions

The AI never sees numbers. It sees a written instruction for each range.

| Dial range | Spark (playfulness, curiosity) | Steadiness (calm, care) |
|---|---|---|
| Low | Calm, few jokes, mostly listening | Light and casual |
| Medium | Some humour, asks about their world | Notices feelings, checks in |
| High | Teasing, quick, many questions | Grounded, patient, fully present |

Default positions come from the skill table in `V0_02`. **Test:** generate replies at low and high settings and have people rate them blind. If raters cannot tell the difference, rewrite the instructions.

## 8. Skill construction checklist

Before any skill counts as done, and before its name is added to the chooser:

1. **Spec:** when exactly it starts, what the person should feel by the end, what India-specific context matters, which rules it is most likely to break under pressure.
2. **Instruction text:** short, with at least one "what bad looks like" line.
3. **Tests:**
    - **Activation:** does Jev choose this skill at the right moments?
    - **Quality:** does the reply match the intended feel?
    - **Boundary:** do the rules hold under pressure? **Any boundary failure means the skill does not ship.**

## 9. Model choice and fallback (M1 and M2)

| Role | What | Path |
|---|---|---|
| **M1 (main brain)** | The fast model we finalise after testing in Phase 1 | Direct call, hosted in India |
| **M2 (fallback brain)** | A **different** model from a **different** provider | Through OpenRouter |
| **S1 (helper)** | A cheaper model for background jobs (summaries) | Any reliable path; never blocks the reply |
| **Jev (decision model)** | Typed background decisions (section 5) | TypeSafe's service or the fastest host measured from Mumbai; never blocks the reply |

Phase 1 tests 2 or 3 fast models for M1, including Sarvam-30B as a candidate.

**When to switch from M1 to M2**

1. M1 returns an error, **or**
2. M1 has not produced its first word within the time limit. A slow model hurts a live conversation as much as a broken one, so timeouts count as failures.

**Decided time limits:**

| Moment | Rule | Reason |
|---|---|---|
| No first word after **1.0 s** | Play one short pre-recorded filler ("hmm...") | A benchmark of voice agents found natural conversation needs replies under about 1.5 s, which means the AI's first word should come within about 0.7 s ([Murf, citing Daily's benchmark](https://murf.ai/blog/best-llm-for-voice-ai)). At 1.0 s, M1 is already late, so a filler covers the silence without switching yet |
| No first word after **1.5 s** | Abandon M1, switch to M2 | Waiting longer rarely pays off. Switching earlier (say 1.0 s) would fire on M1's normal slow moments and send us to M2, which is slower through OpenRouter, so we'd lose more than we gain |
| After 2 weeks of real timing data | Reset the switch point to M1's slowest-normal time (its 99th percentile) plus 0.2 s, **never above 2.0 s** | Set from real numbers, not guesses. The 2.0 s cap protects the person: M2 also needs time, so the total wait must stay bearable |

**How to switch gracefully**

- If M1 is slow, Vaani plays one short pre-recorded filler while M2 takes over. Used once, never repeatedly.
- **Circuit breaker:** if M1 fails twice in a row, use M2 for the next several minutes instead of retrying M1 every turn. Otherwise every turn pays the timeout again.
- **Both models must pass the same hard tests.** A fallback that breaks the safety rules is worse than a short delay.
- Every switch is logged, so we know how often M1 fails.

LiveKit has a built-in fallback adapter for the AI model and the voice ([LiveKit fallback strategies](https://docs.livekit.io/agents/logic/fallback-strategies/)), so we do not build this from scratch. By default, the AI fallback does not switch once part of the reply has already been sent, which is the safe behaviour for us.

**Accepted trade-off:** OpenRouter may route outside India, so M2 is slower. That is fine, because it only runs when M1 fails.

**The other parts**

- **Speech-to-text:** Sarvam only, no backup. Failure rule as in RE-D9: one lost turn means ask to repeat; two errors in a row or nothing for 5 s means a pre-recorded apology, a clean end and a rejoin link.
- **Voice:** Cartesia primary, Sarvam Bulbul as the backup voice.
- **Face:** if the avatar fails, the call continues voice-only with a still image.
- **Jev:** if slow or down, Vaani keeps the current skill and the plain-code rules.

## 10. What we deliberately leave out of version 0

| Left out | Why |
|---|---|
| A large catalogue of skills | Five skills cover open conversation; more come only with clear need and full tests |
| Long persona documents at runtime | Vaani's character must stay compact for speed |
| Changing tone based on the person's guessed gender | Risky and easy to get wrong |
| Specific statistics quoted with confidence | Vaani must never invent numbers |
| Proactive messages, messaging channels, cross-session memory | Need a returning-user product first |

## Sources

- [Manus: Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [LiveKit: Fallback strategies](https://docs.livekit.io/agents/logic/fallback-strategies/)
- [Murf: best LLM for voice AI (citing Daily's benchmark)](https://murf.ai/blog/best-llm-for-voice-ai)
