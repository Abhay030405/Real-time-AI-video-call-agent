# Not Implemented Features

**Things the founder has chosen to do later. Nothing here is built, tested or required by a phase gate until it is moved back into a phase.**

Status: v0.1 · 19 Oct 2026

How to use this file: when the founder postpones something, add a row here with the reason and what it affects. When it comes back, remove the row and update the phase documents in the same change.

---

## Postponed

| What | Why it is postponed | What it affects | When it comes back |
|---|---|---|---|
| **Recorded speech clips and the speech-to-text evaluation (L1)**: the 200+ clips from `docs/phase0/03_speech_clip_list.md` and the word error rate and meaning-error rate measured on them | The clips only check that the speech model hears different voices correctly and behaves the same for each. Not needed to start building the talking pipe. Founder decision, 19 Oct 2026 | `vaani_build_phase_v0.md`: Phase 0 exit gate (clips stored), Phase 1 exit gate (Sarvam meaning-error rate 5% or less). `V0_07`: L1 speech-to-text and scorecard line 6 (Hinglish speech) | Founder decides. Folders `storage/main` and `storage/backup` are ready |
| **Recorded turn-taking video scripts and the turn-taking evaluation (L4)**: the ~30 filmed scripts from `docs/phase0/04_turn_taking_scripts.md` and the tests that use them | The founder will evaluate turn-taking later and correct what is found. Founder decision, 19 Oct 2026 | `vaani_build_phase_v0.md`: Phase 0 gate (video scripts stored). The Reading Engine document's RE-D13 ("scripts recorded with video from the start") and `V0_07` L4 still describe them as recorded early; they are needed before the Phase 5 turn-taking baseline and before version 0.5 | Founder decides; at the latest before the Phase 5 baseline report |
| **Model comparison test**: testing 2 or 3 fast models on the same English and Hinglish snippets to choose M1, M2 and S1 | The founder chose the models directly (M1 Sarvam-105B, M2 `google/gemini-3.6-flash`, S1 `google/gemini-3.1-flash-lite`). The comparison will be done later | `vaani_build_phase_v0.md`: Phase 1 "Model choice" and the L1 models test (reply-quality part). First-word time and cost are still measured for the chosen models | Founder decides |
