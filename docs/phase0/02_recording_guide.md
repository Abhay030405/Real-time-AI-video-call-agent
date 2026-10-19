# Phase 0 — Recording Guide

**How to record the speech clips and the filmed turn-taking scripts, name the files, write the correct transcripts, and keep two safe copies. Read this once before the first session; keep it open during sessions.**

Status: v0.1 · 19 Oct 2026 · Part of Phase 0 (`docs/v0/vaani_build_phase_v0.md`)
Read with: `03_speech_clip_list.md`, `04_turn_taking_scripts.md`

---

## 1. Who records what

| Who | Speech clips (`03`) | Filmed scripts (`04`) |
|---|---|---|
| S01 (founder) | about 33 clips | — |
| S02 to S07 (volunteers) | about 33 clips each | three of them (F1, F2, F3) film 10 scripts each |

- Only adults (18+) record, and only people who have given consent.
- If only 5 volunteers turn up, the founder records S07's lines too.
- **Never use real names in files.** Each person gets a code (S01 to S07, F1 to F3). Keep the list of who is who in one private note, not in the repository.

**Speaker sheet** (fill once per person, kept in `evals/datasets/l1_speech_to_text/speakers.md`):

| Code | Gender | Age range (18–24, 25–34, 35+) | First language | Mostly speaks (English / Hinglish / Hindi) | Region (state) |
|---|---|---|---|---|---|

A good mix (men and women, English-first and Hinglish-first, different regions) makes the test fair. If the group is unbalanced, tell Claude and the line assignment will be adjusted.

## 2. Equipment: use what testers will use

- **The person's own laptop, with its built-in microphone and camera.** No headset, no phone, no studio mic. Real testers will use laptops, so the test must sound like laptops.
- **Speech clips:** record in a normal room. Fans and the TV off, except for the lines marked "noise" in the clip list.
- **Filmed scripts:** sit as on a video call, about an arm's length from the screen, eyes roughly level with the camera, head and shoulders in frame. Light in front of the face, not behind (no window behind you). Plain background, and nobody else in the frame.

**Tools (free):**
- Audio: **Audacity**. Set it to **Mono** and record at its default rate. Export each clip as **WAV**.
- Video: the laptop's own camera app (Windows Camera, or Photo Booth or QuickTime on a Mac). Record at **720p or 1080p**, keep the file as it comes (MP4 or MOV).

Don't convert or edit files beyond trimming silence. A script will make the final copies the tests use; the originals stay untouched.

## 3. How to record a speech clip

1. Open your list in `03_speech_clip_list.md` (your section only).
2. For each line: press record, **wait one second**, say the line once at your normal speed, **wait one second**, stop.
3. **Speak the way you normally talk.** Don't read slowly or extra-clearly. Small hesitations are fine.
4. **You may change a word to sound natural to you** (for example "gaya" to "gayi", or "bro" to "yaar"). That's good, not a mistake. Just note the change so the transcript matches what you actually said (section 5).
5. If you stumble badly, say the whole line again in the same recording; keep only the good take when trimming.
6. **Noise lines:** say the same line again with the named noise switched on (ceiling fan at full speed, TV at normal volume, window open to traffic, people talking in the next room, or kitchen sounds).
7. **Free-speech clips:** read the question to yourself, then answer it out loud for 10 to 20 seconds in whatever language comes naturally. Don't plan the answer.

About 20 to 25 minutes per person.

## 4. How to film a turn-taking script

Full instructions are in `04_turn_taking_scripts.md`. The short version:

- Each script has **one or two segments**. Film each segment as its own clip.
- Start every segment with **2 seconds of quietly looking at the screen**, as if listening. End it with **3 seconds of the same**.
- **Pauses are timed.** Count them silently ("one thousand one, one thousand two...") or watch a stopwatch on a phone placed just below the camera. Being within half a second is fine.
- Do the face actions as written (look up while thinking, nod, smile). They don't matter for version 0, but version 0.5 is tested on these exact takes, so do them naturally now.

About 30 to 40 minutes per filmed person.

## 5. Writing the correct transcript

The correct transcript is **exactly what was said in the recording**, not what the list says. For read lines, start from the list line and fix any word the speaker changed. For free speech, listen and write it down.

**Rules:**

1. **English letters only.** Hindi words are written the way people type them on WhatsApp ("kal milte hain"), never in Hindi script.
2. **Numbers in words, the way they were spoken.** "flat three zero two" and "flat three hundred two" are different, so write what you hear.
3. **Write fillers that were spoken**: "umm", "hmm", "matlab", "you know".
4. **Don't write coughs, laughs or noises.** If a word was unclear even to you, write `[unclear]` and keep the clip anyway.
5. **Normal punctuation is fine**; the scoring script ignores capital letters and punctuation.
6. **Use the fixed spellings below** for common Hinglish words. If a word isn't in the table, spell it the way most people would type it, and add it to the table so everyone uses the same spelling.

**Fixed spellings** (kept up to date in `evals/datasets/l1_speech_to_text/spellings.md`):

| Write | Not |
|---|---|
| hai, hain | he, hein, hen |
| nahi | nahin, nai, nhi |
| kya, kyun, kaise, kab, kahan | kia, kyu/kyon, kese, kb, kaha |
| main (I), mein (in) | mai, me, mei |
| mujhe, mera, meri, mere | muje, mra |
| tum, tumhe, tumhara | tm, tumhein |
| aap, aapka | ap, apka |
| hum, humara | ham, hamara |
| yaar | yar |
| accha | acha, achha |
| theek | thik, theekh |
| bahut | bohot, bhut, bahot |
| abhi, aaj, kal | abi, aj, kl |
| ghar, kaam, baat | ghr, kam (for work), bat |
| matlab | mtlb |
| haan | han, haa |
| bas | bus (for "enough") |
| thoda, thodi | thora, thori |
| zyada | jyada, zada |
| sab, sabko | sb |
| kuch, kuchh | write **kuch** |
| woh, yeh | wo, ye, voh |
| toh | to (for "so/then") |
| karna, karo, karun, karunga | krna, kro |
| chahiye | chaiye, chahie |
| lagta, lagti | lgta |
| pata | pta |
| sach | such |

## 6. File names

| Kind | Pattern | Example |
|---|---|---|
| Speech clip | `stt_<speaker>_<lineID>.wav` | `stt_S03_HG14.wav` |
| Noise clip | `stt_<speaker>_<noiseID>.wav` | `stt_S03_NZ05.wav` |
| Free speech | `stt_<speaker>_<FS-ID>.wav` | `stt_S03_FS07.wav` |
| Filmed segment | `tt_<filmer>_<scriptID>_<segment>.mp4` (or `.mov`) | `tt_F2_TT14_s2.mp4` |

Line IDs, noise IDs and script IDs come from the lists in `03` and `04`. One file per clip or segment; no spaces in names.

## 7. Folders and the two copies

Recordings live in the `storage/` folder inside the project. It is ignored by git and Docker, so recordings are never pushed.

```
<TEST_MATERIAL_DIR>/   (storage/main)
├── l1_speech_to_text/v1/original/     the WAV files exactly as recorded and trimmed
└── l4_turn_taking_scripts/v1/original/ the video files exactly as recorded and trimmed
```

1. **Main copy:** the folder set as `TEST_MATERIAL_DIR` in the root `.env` (on the founder's laptop).
2. **Second copy:** the same folders in `storage/backup` (`TEST_MATERIAL_BACKUP_DIR`). It is on the same disk, so also copy it to an external drive from time to time. **Copy after every session, the same day.**
3. Volunteers send their files to the founder (pen drive, or a private shared folder deleted after copying). Don't leave copies sitting in chat apps.
4. Never edit a file once it's in `original/`. To redo a clip, record it again with a new file and note it.

## 8. After each session (founder, 10 minutes)

- [ ] Listen to or watch three random files from the session: clear, right person, right line.
- [ ] Write or correct the transcript for every clip (section 5). Use the session sheet below.
- [ ] Copy everything to both drives.
- [ ] Tick the person off in the speaker sheet.

**Session sheet** (one per session, kept in `evals/datasets/l1_speech_to_text/sessions/`): date, speaker code, laptop model, room (quiet / noisy), list of files, any changed words, any problems.

When all sessions are done, Claude's Phase 0 code builds the file lists: name, version, checksum, length, type, transcript, working or hidden. These lists are the only part that goes into the repository.

## 9. Working and hidden clips

About 30% of clips are marked **hidden** in the lists. They're recorded exactly like the others. The only difference: nobody uses them while tuning Sarvam's settings or anything else. They're used only at phase gates and at release, so our numbers stay honest.
