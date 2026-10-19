# Test sets

Each set has a `working/` folder (about 70%, used while building) and a `hidden/` folder (about 30%, never looked at while writing prompts, used only at phase gates and release). See `docs/v0/V0_07_Evaluation_Framework.md`.

| Folder | Level | What it holds | Built in |
|---|---|---|---|
| `l1_speech_to_text` | L1 | 200+ clips (English, Hindi, Hinglish, noise, Indian names) with correct transcripts | Phase 0 |
| `l1_models` | L1 | 60 conversation snippets for M1 and M2 | Phase 1 |
| `l1_helper_summaries` | L1 | 30 conversations for S1 to summarise | Phase 2 |
| `l1_decision_model` | L1 | 30 conversations tagged by the founder: skill, intensity, heavy disclosure, Hinglish level | Phase 2 |
| `l1_voice` | L1 | 50 sentences with Hinglish words, names and numbers | Phase 1 |
| `l1_face` | L1 | 20 recorded replies for lip-match rating | Phase 4 |
| `l2_single_replies` | L2 | About 40 cases per skill (activation, quality, boundary) | Phase 2 |
| `l3_personas` | L3 | 12 simulated-person personas for 20-minute text conversations | Phase 3 |
| `l4_turn_taking_scripts` | L4 | About 30 spoken scripts **recorded with video** (RE-D13): thinking pauses, "hmm", "haan", coughs, interruptions, noise | Phase 0 |
| `l5_red_team` | L5 | About 150 safety cases, hard pass, 3 runs each | Phase 2 |
| `l6_fault_injection` | L6 | The fault checklist from `V0_03` section 1 | Phase 4 |

## Storage

Audio and video files live on local drives outside the repository: the main copy in `TEST_MATERIAL_DIR` and a second copy on an external drive (`TEST_MATERIAL_BACKUP_DIR`), both set in the root `.env`. Storage rules are in the root `README.md`. Each set's folder here holds a file list (name, version, checksum, transcript or label) and its consent records. The test runner reads the files from `TEST_MATERIAL_DIR` and checks each one against its checksum.

## Rules

- Every set has a version number and a short note on how it was made. Changing a set means a new version.
- Recordings come only from people who agreed in writing, with no private details. Consent records are kept next to the set.
- Every real failure found by a tester becomes a new case, labelled with where it came from.
