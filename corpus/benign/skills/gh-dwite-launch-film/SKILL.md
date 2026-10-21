---
name: launch-film
displayName: Launch film rendered in code
description: >-
  Make an Apple-style product launch, promo or ad video rendered frame by frame in code: an HTML page paints any
  moment through seek(t), headless Chrome captures it (one process per worker, 4-sample motion blur) and ffmpeg
  encodes. Cuts lock to the measured beat grid of a generated score; ElevenLabs music, voiceover and sound effects;
  Gemini/GPT art; speech-to-text verifies every voice line; a still-by-still critique loop. Use when asked for a
  product video, launch film, app trailer, promo or ad video, motion presentation, or animated explainer made from
  code, or to add music, voiceover or sound to such a film.
---

# Launch film rendered in code

Produces a 30–70 s film (16:9, 1080p60 by default) plus a voiceover cut, an alternate-voice cut, a music-only
cut, captions, posters and a contact sheet. A full 1080p60 render with motion blur takes about 2 minutes on
12 workers, so iterate freely.

## Prerequisites

Google Chrome, `ffmpeg`, Node 18+, `python3` with Pillow, and `uv` (for `librosa`/`requests`). Keys in the
environment, never written into the project: `ELEVENLABS_API_KEY` (music, voice, sound effects, speech-to-text),
optionally `GEMINI_API_KEY` (images, Lyria music) and `OPENAI_API_KEY` (images with transparency).

## Start

`new_film.sh` sits next to this file (global install: `~/.claude/skills/launch-film/`, project install:
`./.claude/skills/launch-film/`).

```sh
bash <this skill's folder>/new_film.sh <film-dir>     # copies template/, npm install
cd <film-dir> && node scripts/render.mjs stills 1,4,8,12,18 && python3 scripts/sheet.py review/stills review/sheet.jpg 5 400
```

The template renders a working 20 s film (title → phone with pop-out and tap → end card). Everything is timed from
`timeline.json`, which both `src/stage.js` and the audio scripts read.

## Gates — do not skip

1. **Study.** References: download the videos the user points to, tile frames with ffmpeg (`fps=N,tile=4x4`), and
   write down pacing, type and transitions shot by shot. Product: collect real screens and screen recordings (extract
   frames with ffmpeg), the brand fonts, colors and icon, and the claims the film may make (only claims the product
   backs). Check the current UI in code: captures go stale (a rebuilt button, a new flow).
2. **Brief.** Fill `BRIEF.md`: logline, three brand colors, headline + accent fonts, one background, beat sheet with
   a state list per shot, claims. One idea per shot.
3. **Score first.** Fill `audio.json` → `musicGen` (sections in bars), run `scripts/gen_music.py` (2–3 seeds), then
   `scripts/analyze_music.py`. You cannot listen: pick by grid fit and dynamics (quiet intro, lift, peak, drop).
   Put the measured `bpm`/`firstBeat` in `timeline.json` and place cuts on measured events (bass entry, two-bar
   swells, the drop). Trim a silent or sparse opening by whole bars (`musicStart`), lift the rest (`introLift`).
4. **Rig and stills.** Build shots in `src/stage.js`. Render stills at key times, make a contact sheet, score every
   shot out of 10, fix the three worst problems, repeat until nothing is under 8.
5. **Animatic.** `render.mjs video --fps 30 --scale 0.5`, then tile frames around each transition
   (`ffmpeg -ss A -to B -vf "fps=8,scale=480:-2,tile=6x4"`) and check the hand-offs.
6. **Voice.** Write lines in `audio.json` → `voice`, run `scripts/gen_vo.py main alt`, then `scripts/qa_speech.py`.
   Lines are placed by speech-to-text word timings; anchor the key word to its beat; split one take instead of
   stitching fragments; no silence longer than ~1.5 s in the first 10 s.
7. **Sound and mix.** `scripts/gen_sfx.py`, then `scripts/mix_audio.py` (per-cue loudness, voices duck the score,
   −14 LUFS). Check the mix without ears: speech-to-text on the first 15 s, per-second levels, a spectrogram with cue
   markers.
8. **Final.** `render.mjs video --fps 60 --sub 4 --shutter 0.5 --workers 12`, mux each mix, write SRT captions from
   the measured voice timings, render poster stills, a contact sheet, and a README with sources and open claims.

## Rules

Detail and reasons: `references/craft.md`. Bugs already paid for: `references/pitfalls.md` (read before writing
code). Short version:

- Every value is a pure function of `t` (closed-form springs from `src/lib/motion.js`); nothing reads a clock, no
  CSS transitions, no unseeded randomness.
- Type enters per word (blur 14 → 0 px, rise 28 px, heavy spring) and exits blurring up. One accent phrase per
  headline, in the accent font and color. Headline position stays the same shot to shot.
- No hard cuts: each shot hands an object or the camera to the next one.
- Real product UI over mock UI; pop real crops out of the screen. Rebuild stale components in HTML from the code.
- The voiceover speaks the headlines in its own words and goes quiet for the product's own sounds.
- Deliver a voiceover cut and a music-only cut; the first seconds must work muted (autoplay).

## Commands

```sh
node scripts/render.mjs stills 2.5,8,14 [--scale 0.5] [--dir review/x]
node scripts/render.mjs video --fps 30 --scale 0.5 --out out/animatic.mp4
node scripts/render.mjs video --fps 60 --sub 4 --shutter 0.5 --workers 12 --out out/master.mp4
uv run --with requests python3 scripts/gen_music.py [lyria]
uv run --with librosa --with matplotlib python3 scripts/analyze_music.py assets/audio/music/*.mp3
uv run --with requests python3 scripts/gen_vo.py main alt [chorus] [--only id,id]
uv run --with requests python3 scripts/qa_speech.py assets/audio/vo/main
uv run --with requests python3 scripts/gen_sfx.py
python3 scripts/mix_audio.py out/mix_vo.wav --vo main        # no --vo for the music-only mix
ffmpeg -i out/master.mp4 -i out/mix_vo.wav -map 0:v -map 1:a -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
  -c:a aac -b:a 256k -movflags +faststart -shortest out/film.mp4
```
