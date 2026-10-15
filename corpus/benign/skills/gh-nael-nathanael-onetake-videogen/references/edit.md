# A. Edit a recording

`$S`, `$J` and the rules for every mode are in `SKILL.md`.

1. **Transcribe** (GPU, ~1 min per 18 min of audio):
   `$S/run.sh transcribe.py INPUT.mp4 $J --lang id` → `$J/words.json`, `$J/transcript.txt`
   Use `--lang en` / `--lang auto` when the speaker isn't speaking Indonesian.

2. **Decide the cuts** by reading `$J/transcript.txt`. Lines look like
   `#120-134 [00:04:12.0] text…`; `[eh,]` marks fillers (removed automatically);
   `(... 3.2s ...)` marks a pause (pauses > `--max-gap` are shortened automatically).
   Write `$J/cuts.json` = `{"delete": [[first, last], ...], "why": {"120-134": "retake"}}` deleting:
   - **Retakes / false starts** — when a sentence is said again, keep the *last* complete take
     (speakers redo until it's right). Typical cue: same opening words repeated, "eh maksud saya",
     "ulang ya", "sorry".
   - **Self-corrections** — delete the wrong part and the correction phrase, keep the corrected statement.
   - **Off-camera / meta talk** — "udah rekam belum?", "bentar", talking to someone else, mic checks.
   - **Whisper hallucinations** — text in the last seconds or in long silences that doesn't fit,
     classically "Terima kasih sudah menonton", "selamat menikmati", "subscribe". Low `prob` in words.json backs this up.
   - Keep content even if imperfectly phrased; don't over-trim personality. When unsure, keep.

3. **Cut + captions** (one NVENC pass, frame-accurate):
   `$S/run.sh cut.py INPUT.mp4 $J/words.json $J/cut.mp4 --cuts $J/cuts.json --captions`
   Writes `cut.words.json` (words re-timed to the edit — use it for music tempo and title timing).
   Options: `--max-gap 0.6` (tighter = punchier; 0.4 for fast-paced, 0.9 for calm tutorials), `--pad 0.12`,
   `--keep-fillers`, `--quality medium`, no `--captions` if the user doesn't want them.
   Portrait footage stays portrait (1080×1920 becomes 720×1280), with captions set for a phone.

4. **Music** (`SKILL.md`, Music): `$S/run.sh music.py $J/music --duration <cut duration> --words $J/cut.words.json`

5. **Title card** (optional, nice for the opening topic):
   `$S/run.sh remotion.py titlecard $J/title.mov --title "Judul" --subtitle "Subjudul" --seconds 4`
   (`--format vertical` over portrait footage)

6. **Mix**: `$S/run.sh mix.py $J/cut.mp4 $J/final.mp4 --music $J/music/bed.wav --overlay $J/title.mov@0.5`
