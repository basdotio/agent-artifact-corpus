# B. Explainer from a topic or script

`$S`, `$J` and the rules for every mode are in `SKILL.md`.

1. **Direction**: `$S/run.sh direction.py $J --mode explainer` picks a structure and an opening pattern
   that the last 5 explainers did not use, and lists theirs. Write the script to it, and never reuse a
   recent job's hook wording or scene order. A request that already fixes the structure (a finished
   script, a numbered list) wins: keep its structure, and say so in the report.
2. **Script** — if given only a topic, research it first (`SKILL.md`, Facts, sources and likenesses), then write the narration as natural speech in the confirmed narration language (short sentences,
   conversational, the hook in the first line, no greeting or outro, ~140 words per minute of target length). Save as `$J/script.txt`,
   paragraphs = scenes. `[pause 1.0]` on its own paragraph adds silence.
3. **Voice-over**: `$S/run.sh voiceover.py $J/script.txt $J/vo.wav` (consistent voice from `--voice "(description)"`;
   or clone with `--ref sample.wav --ref-text "transcript"`). First run downloads the model (~several GB).
4. **Word timings**: `$S/run.sh transcribe.py $J/vo.wav $J/vo --lang id` → `$J/vo/words.json` (`--lang` = the
   narration language, e.g. `en`). Whisper guesses the spelling of names, brands and symbols, so give the
   words the text you wrote: `$S/run.sh align.py $J/vo/words.json $J/captions.txt`. `captions.txt` is the
   script as captions should read (digits as digits, `%` as a symbol, names spelled right), which can
   differ from a `script.txt` that spells numbers out for the voice. `align.py` keeps Whisper's timings and lists
   what it could not place; read that list.
5. **Scenes**: write `$J/scenes.json` from the transcript timings — one scene per idea, 3–6 s each, with a point,
   highlight or sound effect every 2–4 s inside longer scenes:
   ```json
   [{"start": 0, "end": 4.2, "layout": "title", "kicker": "Tips", "title": "Edit 10x Lebih Cepat", "emoji": "⚡"},
    {"start": 4.2, "end": 11.8, "layout": "points", "title": "3 langkah",
     "points": [{"text": "Unggah video", "at": 5.1}, {"text": "Hapus teks", "at": 7.0}]}]
   ```
   Layouts: `title` (hook/section), `points` (lists; set each `at` to when the narrator says it), `big` (one stat or
   keyword), `quote`. Titles ≤ 6 words, points ≤ 5 words — the narration carries the detail.
6. **Music**: `$S/run.sh music.py $J/music --duration <vo duration> --words $J/vo/words.json`
7. **Check** (same arguments as the render, minus the output): `$S/run.sh check.py explainer $J/scenes.json --words $J/vo/words.json --duration <vo duration> --beats $J/music/beats.json --stills $J/stills-v1`
   It must print nothing. It fails on a scene that holds one picture over 6 s (a caption highlight does
   not count: the picture needs a new scene or a point), a point with under 0.8 s to be read, titles over
   6 words and points over 5, gaps between scenes, narration that starts over 1.5 s in, pauses longer than `--max-gap`
   (1.2 s; raise it for a scripted `[pause]`) or stops over 2 s early, text cropped or inside the 4% side
   margins, text in the caption band, and fonts that did not load. Fix `scenes.json` or the script and
   rerun; never loosen a rule to pass. Look at the stills (one settled frame per scene), then proofread
   every on-screen string for spelling, grammar and unsupported claims: the same command with `--texts`.
8. **Render**: `$S/run.sh remotion.py explainer $J/scenes.json $J/visual.mp4 --words $J/vo/words.json --duration <vo duration> --beats $J/music/beats.json`
   Scene changes snap to the nearest beat; accents pulse on the beat. Add `--format vertical` to both the
   check and the render for a vertical video.
   For a brand's look add `--theme $J/theme.json` = `{"palette": [...], "ink": "#…", "paper": "#…", "accent": "#…"}`.
   `paper` is the scene text, `ink` the frame and card text; for dark text on pale scenes pass the dark tone as
   `paper` and give `accent` a text-safe shade, since bright brand colours rarely read on a pale caption box.
9. **Mix**: `$S/run.sh mix.py $J/visual.mp4 $J/final.mp4 --voice $J/vo.wav --music $J/music/bed.wav`
