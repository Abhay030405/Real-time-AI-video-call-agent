# Phase 2 — Voice Criteria

**What Vaani's voice should be like, written down so the voice can be checked and, if it is ever replaced, replaced against the same list.**

Status: v0.1 · 20 Oct 2026 · Part of Phase 2 (`docs/v0/vaani_build_phase_v0.md`)

The build plan asks for written criteria first and the voice chosen against them. The founder chose the voice first and judged it "perfect" in a real call (19 Oct 2026). These criteria describe that voice, so a replacement would be held to the same list.

## The voice in use

- Cartesia voice `28ca2041-5dda-42df-8123-f58ea9c3da00` ("Palak"), model `sonic-3.6`, language setting `hi`.
- Backup voice: Sarvam Bulbul `bulbul:v3`, speaker `priya`, used only when Cartesia fails.

## The criteria

| Quality | What we want | Why |
|---|---|---|
| Gender and age feel | A young adult woman's voice | Matches the character: a friend one meets and keeps talking to |
| Accent | Natural Indian English that moves easily into Hindi words, with a slight neutral edge | People speak English and Hinglish to her; neither should sound foreign |
| Pace | Unhurried, conversational, not a presenter's pace | Silence and thinking are comfortable for her |
| Warmth | Friendly and smiling in the sound, never salesy or flat | "Easy to talk to" in the first minutes |
| Clarity | Names, numbers and Hindi words are pronounced correctly | The L1 voice test checks 50 sentences with names, places and numbers |
| Range | Can sound light, and can drop to calm and gentle for serious moments | Skills change; the voice must carry both |
| Speed | First audio within 300 ms | Part of the reply-time budget |

## How it is checked

- First-audio time on every run of the L1 voice test (`evals/results/`).
- The founder listens: the real call on 19 Oct 2026 was judged "perfect". The 1-to-5 rating sheets for the 50 test sentences were left empty, so there are no scores yet.
- If a new voice is ever tried, it must meet every row above, and the L1 voice test and the founder's rating sheets are run again.
