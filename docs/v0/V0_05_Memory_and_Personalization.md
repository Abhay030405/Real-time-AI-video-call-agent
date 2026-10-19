# Memory & Personalization Design

**Vaani uses two kinds of memory, kept in two places: a fast, short-lived memory for the current call in Redis, and a durable long-term memory across calls in PostgreSQL. New memories are written only after a call ends, by a background process that adds, updates or deletes facts. Nothing about memory is allowed to slow down a reply.**

Status: Draft v0.2 · 19 Oct 2026

> Parent document: `Reading_Engine_Design_Document.md` (decisions RE-D1 to RE-D13). Build order and phase gates: `vaani_build_phase_v0.md`. Updated 19 Oct 2026 to match the decisions made that day.

Read with: `V0_01` (architecture), `V0_04` (engineering blueprint), `V0_06` (reliability and data)

---

## 1. What the industry has settled on

The serious memory systems for AI agents all make the same basic split.

- **Two tiers.** Mem0, Letta and Zep all separate a working memory for the current session from a long-term store that keeps facts, decisions and preferences across months ([Mem0 guide](https://guide.mem0.ai/task/faq/memory-platforms-ai-assistants)). Redis's own agent memory product uses the same two tiers: session memory with an expiry time, and long-term memory extracted from past sessions and stored with search vectors ([Redis Agent Memory](https://redis.io/docs/latest/operate/rc/context-engine/agent-memory/)).
- **Extract after, retrieve before.** Mem0's published research describes a system that pulls out the important facts from conversations, merges them with what it already knows, and retrieves them later ([Mem0 paper](https://arxiv.org/html/2504.19413v1)).
- **The main design fork:** either the AI manages its own memory during the conversation (Letta's approach) or a separate background pipeline manages it (Mem0's approach) ([Klu overview](https://klu.ai/glossary/agent-memory-architectures)).
- **Where Redis fits:** the same overview lists in-memory stores like Redis as best for working and short-term memory, valued for very low delay and session state, but not built for complex querying, with limited durability and no understanding of meaning by itself.

## 2. Decisions, with reasons

| # | Decision | Why |
|---|---|---|
| MEM-1 | **Redis holds a fast cache of the current call** (recent turns, running summary, session note, current skill) | It's in the hot path of every turn. Redis reads and writes in under a millisecond, and data can expire automatically after the call. Since the reliability review, Redis is a **cache** of the durable session log, not the only copy (`V0_06` section 2.3) |
| MEM-2 | **PostgreSQL (with the pgvector add-on) holds the durable session log and long-term memory** | Long-term memory is a record people trust us with. It needs to be durable, backed up, queryable ("show me everything about this person", "delete all of it"), auditable, and hosted in India. That's what a database of record is for. pgvector adds search by meaning in the same database, so there's one source of truth |
| MEM-3 | **Not Redis for long-term memory** | Redis can store vectors, but keeping everything in memory is costly as data grows, and durability is optional, not its default strength. Mixing hot session data with irreplaceable personal memories in one place makes backups and deletion harder |
| MEM-4 | **Background pipeline, not the AI managing its own memory** (the Mem0 pattern, not the Letta pattern) | Letting Vaani edit her memory mid-conversation means extra AI steps during the call, which costs speed (one main AI call per turn is a core rule, `V0_04` P2). It also lets a live conversation write unchecked data. A background step after the call is slower to learn but safer and free on speed |
| MEM-5 | **Build a thin memory layer ourselves, following the Mem0 pattern, rather than adopting a framework** | Our memory rules are product-specific (the door rule, sensitive topics, instant forgetting). Our data must stay in India in our own database. And Redis's open-source memory server repository states it is not officially supported and has no long-term maintenance plans ([GitHub](https://github.com/redis-developer/agent-memory-server)), a dependency risk for a core feature. Revisit Mem0's self-hosted version if building takes too long |
| MEM-6 | **Memory never sits on the reply's critical path** | Loading happens at call start; mid-call lookups run in the background and are ready for the next turn; writing happens after the call |

## 3. The five kinds of memory

| Kind | Examples | Stored where | When Vaani uses it |
|---|---|---|---|
| **Profile facts** | Name, language style, city, what they do, main interests | PostgreSQL, structured fields | Loaded every call; used naturally |
| **Session stories** | One summary per call: topics, emotional arc, open threads, things they said they'd do | PostgreSQL | Last 1 or 2 loaded at call start |
| **Facts learned** | "Preparing for GATE", "has a younger sister", "loves football" | PostgreSQL with meaning-search vectors | Retrieved when the topic comes up |
| **Personal and sensitive context** | Family stress, a breakup, a health worry | PostgreSQL, marked **door-locked** | Only after the person brings the topic up again (the door rule) |
| **How they like to talk** | Humour level, Hinglish level, preferred dial settings | PostgreSQL, structured | Shapes Vaani's style silently; never mentioned aloud |

**Never stored:** passwords, ID numbers (Aadhaar, PAN), bank or card details, other people's private details shared as gossip, anything the person asked to forget. Crisis disclosures are not turned into memories to bring up later; only a restricted safety-review flag is kept. Nothing the Reading Engine sees is ever stored as memory (RE-D3).

## 4. During a call (the read path)

1. **Call start, before Vaani's first words:** load the profile, the last 1 or 2 session stories, open threads, and a few of the most relevant learned facts. These go into Layer 2 of the instructions and **stay fixed for the whole call**, which keeps the AI service's reuse of earlier work (the Manus cache lesson, `V0_04` M1) intact.
2. **Each turn:** recent turns and the running summary come from the Redis cache (rebuilt from the durable log if Redis restarts).
3. **When the topic shifts:** a background search looks for related memories. If one is found, it's added to the "recalled memories" note near the end of the instructions, ready for the **next** turn. The current reply never waits for it.

In version 0, steps 1 and 3 only apply once cross-call memory is switched on in version 1 (RE-D8). Version 0 uses step 2 only.

## 5. After a call (the write path)

**From the reliability review (`V0_06` section 2.3):** each turn is appended to a durable session log in PostgreSQL during the call, so a crash at call end loses nothing. Redis is only a fast cache of that log. The job is keyed by session ID and safe to run twice. "Forget that" is applied to long-term memory immediately, not left to this job, and deletes every copy derived from the forgotten turn.

1. The call ends; the full transcript is in the durable session log (and cached in Redis).
2. A background job using the S1 helper model **extracts candidate memories**: only what the person actually said, never guesses. The rule is strict: "never infer; only extract what was explicitly stated; leave a field empty if it was not said."
3. For each candidate, it finds similar existing memories and decides one of four actions, following the Mem0 pattern:
    - **Add** (new fact),
    - **Update** (changed fact, for example a new job),
    - **Delete** (no longer true),
    - **Ignore** (already known).
4. It writes the session story and the changes to PostgreSQL, with labels: kind, sensitivity, door-locked or not, which call and turn it came from, when, and a format version.
5. The Redis cache for that call expires automatically; the durable log stays until the transcript retention period ends.

**Changes keep history.** An update keeps the old value with a date, never overwriting it, so Vaani can one day say "you've come a long way since..." with real data.

## 6. How Vaani uses memory without being creepy

These rules matter more than the technology:

- **Door rule:** personal topics come up only after the person raises them.
- **The friend test:** before using a memory, ask "would a good friend bring this up right now?"
- **Feelings, not facts:** "you've had a lot going on", not "your father was diagnosed in March".
- **No dates, no lists:** never "on 3 March you said..."; never reading back several facts at once.
- **One callback per call at most**, about something the person would be glad to have remembered (a goal, a joke), never a moment they would rather forget.
- **Check, don't assume:** "Last time you were preparing for GATE. Still on, or has something changed?"
- **Forget means forget:** "forget that" removes it from the current call and from long-term memory at once, lightly: "Done, it's gone."
- **Honest gaps:** if memory fails to load, Vaani says so, rather than pretending to remember.

## 7. Personalization, step by step

| When | What personalises |
|---|---|
| First call | Nothing stored yet; Vaani learns language style within the first 3 or 4 turns (in-call only; Jev estimates the Hinglish level) |
| Second call | Greets by name, picks up one open thread, uses known language style |
| Around the third call | Settles each person's preferred dial positions (more playful or more steady) |
| Ongoing | Callbacks to earlier conversations; noticing growth over time |

## 8. The person stays in control

- A clear consent screen explains that Vaani remembers across calls, with an option to turn it off.
- A "what Vaani remembers about me" page, with delete for any item or everything.
- Retention: transcripts deleted after a fixed period (suggest 30 to 90 days); memories kept until the person deletes them.
- These support India's data protection law; a legal review is needed before public launch.

## 9. How we test memory

| Test | Pass when |
|---|---|
| Recall | Something said in call 1 is used correctly in call 2 |
| Door rule | A personal topic from call 1 is not raised in call 2 unless the person raises it |
| Forget | After "forget that", the item is gone from the call and from every stored copy |
| No invention | Facts never stated are never stored |
| Not creepy | Testers never feel "watched" (feedback question) |
| No delay | Reply times are the same with memory on and off |

## 10. What belongs in version 0

Memory across calls is deferred to version 1 (RE-D8).

- **Build in v0 (Phase 3):** the durable session log in PostgreSQL, the Redis cache of it, compaction, and "forget that" reaching every copy. All of this is needed for 20-minute coherence and reliability anyway.
- **Also build in v0, quietly (Phase 3):** save each consenting tester's session story to PostgreSQL. It costs little, and gives real data to test the extraction pipeline offline before the feature goes live.
- **Build in version 1:** extraction, retrieval, the memory page and cross-call personalization.

## Sources

- [Mem0: memory platforms for AI assistants](https://guide.mem0.ai/task/faq/memory-platforms-ai-assistants)
- [Mem0 research paper](https://arxiv.org/html/2504.19413v1)
- [Klu: Agent memory architectures](https://klu.ai/glossary/agent-memory-architectures)
- [Redis Agent Memory on Redis Cloud](https://redis.io/docs/latest/operate/rc/context-engine/agent-memory/)
- [Redis agent-memory-server on GitHub](https://github.com/redis-developer/agent-memory-server)
