# Phase 0 — Result Record Design

**What every test run saves, so any number in the project can be traced back to exactly what produced it. This is the design; the code that writes these records comes in the Phase 0 code step.**

Status: v1 · 19 Oct 2026 · Part of Phase 0 · Rules from `docs/v0/V0_07_Evaluation_Framework.md` sections 2, 7 and 9

---

## 1. The rules the record must serve

1. **A number with no versions attached is thrown away.** Every record holds every version that could change the result.
2. **Run more than once.** Soft scores carry an average and a spread, so "better" means better by more than the spread.
3. **Hard checks and soft scores are never mixed.** One hard failure fails the run, whatever the averages say.
4. **Speed is reported at the 50th, 95th and 99th percentile.**
5. **Records are never edited after they are written.** A wrong run is replaced by a new run, not fixed by hand.
6. **The hidden test sets stay hidden.** Their records keep scores, not Vaani's replies, so nobody reads them while tuning.

## 2. Files

Each run writes two files into `evals/results/<YYYY-MM>/`:

| File | What it holds | Size |
|---|---|---|
| `<run_id>.json` | **The summary:** versions, settings, every score with spread, pass or fail, cost, comparison with the baseline | small; always read first |
| `<run_id>.cases.jsonl` | **The details:** one line per test case per repeat: inputs, outputs, scores, timings, errors | can be large |

**Run ID:** `<date>_<time>_<level>_<test set>_<4 random letters>`, in Indian time, for example `2026-11-02_2214_L1_stt-hinglish_k3pq`.

Both files go into the repository. They never contain secrets, raw audio or video, or real names.

## 3. What the summary holds

### 3.1 About the run

| Field | Meaning |
|---|---|
| `record_format_version` | Version of this design (starts at 1). Readers ignore fields they don't know |
| `run_id` | As above |
| `started_at`, `finished_at` | Time stamps, with time zone |
| `duration_s` | How long the run took, from the machine's steady timer |
| `machine` | Which computer ran it (for example "founder laptop") and where (city) |
| `triggered_by` | "founder, by hand", or "phase gate", or "release" |
| `purpose` | One line from the founder, for example "Sarvam with new vocabulary setting" |

### 3.2 What was tested

| Field | Meaning |
|---|---|
| `level` | L1 to L7 |
| `test_set.name`, `test_set.version` | For example `l1_speech_to_text`, `v1` |
| `test_set.split` | working or hidden |
| `test_set.file_list_checksum` | A fingerprint of the file list, so a silently changed test set is caught |
| `test_set.case_count` | How many cases were run |
| `repeats` | How many times each case was run (3 to 5 for soft scores) |

### 3.3 Every version that could change the result

| Field | Meaning |
|---|---|
| `code.commit` | The exact code version, and whether there were unsaved changes ("dirty"). A dirty run can never become a baseline |
| `prompts.layer0`, `prompts.layer1` | A fingerprint of each fixed instruction layer |
| `prompts.skills.<name>` | A fingerprint of each skill's instructions |
| `settings` | The non-secret settings from `.env` that affected this run (timeouts, thresholds, the session clock, model names), plus a fingerprint of them. Keys are never saved |
| `vendors.<role>` | For each part used: provider, model or voice name, model version if given, and the settings that matter (language, temperature, sample rate). Roles: `speech_to_text`, `brain_m1`, `brain_m2`, `helper_s1`, `decision_model`, `voice`, `backup_voice`, `avatar` |
| `judge` | Judge model, judge instruction version, and the calibration run that cleared it for use |

### 3.4 Results

One entry per measure:

| Field | Meaning |
|---|---|
| `name` | For example `meaning_error_rate`, `first_word_time_ms`, `safety_pass` |
| `kind` | `hard` (pass or fail), `soft` (1 to 5 score), `rate` (share of cases), `time_ms` (timing) or `count` |
| `value` | The headline number |
| `spread` | For soft scores and rates: standard deviation, lowest, highest across repeats |
| `percentiles` | For timings: 50th, 95th, 99th, plus how many samples |
| `n` | How many cases went into it |
| `target` | The target from the scorecard or phase gate, if there is one |
| `passed` | true, false, or empty when there's no target |

Then the overall verdict:

| Field | Meaning |
|---|---|
| `hard_failures` | List of case IDs that failed any hard check. Any entry means the run fails |
| `verdict` | pass, fail, or "recorded" (for measures with no target, such as the turn-taking baseline) |

### 3.5 Cost

| Field | Meaning |
|---|---|
| `cost.<vendor>` | Cost of this run per vendor, in rupees |
| `cost.total_inr` | Total |
| `cost.exchange_rate` | The dollar-to-rupee rate used, and its date |

### 3.6 Comparison with the baseline

| Field | Meaning |
|---|---|
| `baseline_run_id` | The accepted baseline this run is compared with |
| `changes` | For each measure: old value, new value, difference, and whether the difference is bigger than the spread |
| `regressions` | Any hard check that newly fails, or any soft score down by more than 0.3 (`V0_07` section 9) |

### 3.7 Notes

| Field | Meaning |
|---|---|
| `notes` | Free text from the founder, added only when the run is written |

## 4. What each case line holds

One line per case per repeat in `.cases.jsonl`:

| Field | Meaning |
|---|---|
| `case_id`, `repeat` | For example `HG14`, `2` |
| `input` | What was given: the clip name, the conversation so far, or the script ID |
| `expected` | The correct transcript, or what a good reply must and must not do |
| `output` | What came back: the transcript, or Vaani's reply. **Left out for hidden sets** |
| `scores` | Every check for this case, with the judge's reasoning where a judge was used. **For hidden sets, only pass or fail and the number, not the reasoning** |
| `timings_ms` | Each stage's duration, from steady timers |
| `cost_inr` | Cost of this case |
| `error` | Any error or fallback, with the vendor's message |

## 5. Baselines

- The accepted baselines are listed in `evals/results/baselines.json`: one line per test set, giving the run ID and why it was accepted.
- **Only the founder changes this file**, with a written reason.
- A run can become a baseline only if it is not dirty and every hard check passed.

## 6. A small example of a summary

```json
{
  "record_format_version": 1,
  "run_id": "2026-11-02_2214_L1_stt-hinglish_k3pq",
  "started_at": "2026-11-02T22:14:05+05:30",
  "finished_at": "2026-11-02T22:21:40+05:30",
  "machine": "founder laptop, Mumbai",
  "triggered_by": "founder, by hand",
  "purpose": "First Sarvam run on Hinglish clips",
  "level": "L1",
  "test_set": { "name": "l1_speech_to_text", "version": "v1", "split": "working",
                "file_list_checksum": "sha256:…", "case_count": 53 },
  "repeats": 1,
  "code": { "commit": "a1b2c3d", "dirty": false },
  "vendors": { "speech_to_text": { "provider": "sarvam", "model": "…", "settings": { "language": "…" } } },
  "judge": { "model": "…", "instructions_version": "j1", "calibration_run": "…" },
  "results": [
    { "name": "meaning_error_rate", "kind": "rate", "value": 0.038, "n": 53, "target": "<= 0.05", "passed": true },
    { "name": "word_error_rate", "kind": "rate", "value": 0.162, "n": 53, "target": "<= 0.18", "passed": true },
    { "name": "time_to_final_transcript_ms", "kind": "time_ms",
      "percentiles": { "p50": 410, "p95": 690, "p99": 820, "samples": 53 } }
  ],
  "hard_failures": [],
  "verdict": "pass",
  "cost": { "sarvam": 4.2, "judge": 6.8, "total_inr": 11.0, "exchange_rate": "88.1 on 2026-11-02" },
  "baseline_run_id": null,
  "notes": ""
}
```

The `…` parts are filled in when the real models and settings are chosen.
