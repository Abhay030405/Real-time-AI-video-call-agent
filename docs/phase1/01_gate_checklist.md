# Phase 1 — Gate Checklist

**Where each Phase 1 exit-gate item stands, with the evidence. Items marked FOUNDER need a person: they cannot be checked by a script.**

Status: v0.1 · 20 Oct 2026 · Part of Phase 1 (`docs/v0/vaani_build_phase_v0.md`)

All numbers below come from **local runs on the founder's laptop with the services in Docker**. They are not Mumbai numbers: the LiveKit Cloud deploy is pending (`docs/not_implemented_features.md`).

---

## The gate

| # | Gate item | Status | Evidence |
|---|---|---|---|
| 1 | A 5-minute English chat and a 5-minute Hinglish chat run without breaking | **FOUNDER** | A scripted call works end to end (greeting, hearing, answer). A person has not yet done the two 5-minute chats. How: `docker compose up -d livekit agent web`, open `http://localhost:3000`, press "Start talking", talk for 5 minutes in English, then 5 minutes in Hinglish. Then run `scripts/timing_report.py` and read the numbers |
| 2 | Sarvam meaning-error rate on Hinglish clips is 5% or less | **Postponed** | Needs the recorded clips (`docs/not_implemented_features.md`). Until then, Sarvam is checked by the scripted call: a Hinglish sentence came back as "Haan yaar main bilkul theek hoon. Aaj ka din kaisa tha tumhara?" |
| 3 | M1 first word at the 95th percentile is 0.7 s or less | **Passed locally** | 182 ms (working set, 40 replies) and 175 ms (hidden set, 20 replies). Records: `evals/results/2026-10/…_L1_l1-models_uxoj.json` and `…_naek.json`. Re-measure from Mumbai after the deploy |
| 4 | Killing M1 switches to M2 within 1.5 s with one filler | **Passed** | `scripts/fault_checks.py`: M2 answered, one filler played (first word 1,546 ms after the request, so M1 was given up on at once and the filler covered the wait). Also `agent/tests/test_faults.py`. The fault exists from the start of the call; it is not switched on in the middle of one |
| 5 | Killing Cartesia switches to the backup voice | **Passed** | `scripts/fault_checks.py`: Bulbul spoke 129 characters in the call. Also `agent/tests/test_faults.py` |
| 6 | Killing Sarvam gives the apology and a clean end | **Passed** | `scripts/fault_checks.py`: the agent ended the call with reason `stt_failure` and sent the note to the web page. Also the rule's unit tests |
| 7 | Every stage's timing and cost appear in the logs for every turn | **Passed** | `storage/telemetry/*.jsonl` and `scripts/timing_report.py`: turn detection, first word, first audio, total; units and rupees per vendor |

## The Phase 1 tests

| Test | Status | Numbers |
|---|---|---|
| L1 models | Run (working and hidden) | M1 first word p50 163 ms, p95 182 ms. M2 first word p50 1,161 ms, p95 1,932 ms. S1 first word p50 1,249 ms, p95 2,469 ms. Cost per 1,000 replies is about ₹8 for M1 (see the price warning below). Reply-quality scoring is postponed |
| L1 voice (speed) | Run (working and hidden) | Cartesia first audio p50 146 ms, p95 209 ms. Bulbul (backup) p50 847 ms, p95 1,152 ms. One Bulbul sentence took 5.5 s in the hidden set |
| L1 voice (rating) | **FOUNDER** | 70 clips are saved in `storage/main/l1_voice/v1/working/` and 30 in `…/hidden/`. Listen and fill in `ratings.csv` (1 to 5 for each voice). Then run `uv run --project agent python -m evals.runner l1_voice --split working` again; the average must be 4.0 or more and no sentence rated 1 |
| L1 speech-to-text | Postponed | Needs the recorded clips |

## What a person should also do

- Listen to the six fillers and the two apologies in `assets/audio/`. They were checked by transcription only (for example "Hmm", "Accha hmm", "Bas ek second"), not by listening.
- Confirm the prices in `.env` (`PRICE_*`). The Sarvam page lists two different price sets for the 105B model, and Cartesia's metering (per character or per second) is unclear. The units are always logged, so costs can be recomputed.

## Findings worth knowing

- **`sarvam-105b` returns no text:** it spends its tokens on hidden reasoning. `sarvam-105b-conversations` is used for M1 (decision D1).
- **M2 is slow as a fallback:** its first word takes about 1.1 s at the median, so a reply that falls back to M2 takes about 3.5 s from the end of the person's speech.
- **Turn detection is the largest stage** at about 840 ms. It is the first thing to tune if the total reply time misses the 1.3 s target (50th percentile) in Phase 5.
- **A new connection to M1 costs about 0.8 s.** The agent sends one tiny request before the call starts so the greeting is not slow.
- **Bulbul is a slow backup** (about 0.85 s to first audio) but only matters when Cartesia fails.
