---
name: timeline-video
description: Write and render a timeline-scripted AI video — one generation up to 30 seconds, scripted second by second in six blocks (locked character, style, timed audio, timeline, camera rules, negatives), the format behind viral single-take ads such as the endless zoom-out reveal. Checks the script, prices it, renders it through OpenRouter (ByteDance Seedance 2.5 by default, any OpenRouter video model), and makes a contact sheet of one frame per beat. Use when asked to make a cinematic AI video, a single-take ad, a "zoom out" reveal, a Seedance / Veo / Kling video from a script, or "a video like this one" from a prompt someone shared.
---

# timeline-video

A long video model can hold one take for 30 seconds if the prompt tells it what happens in every second. This skill
is the scripting layer: the format, the craft that makes it land, and `scripts/timeline_video.py`, which checks a
script, prices it, renders it on OpenRouter's async video API and lays out a contact sheet to review. Python 3.8+
standard library; `ffmpeg` for the contact sheet only.

## The six blocks

A script is a Markdown file: optional front matter, then six blocks in this order. Everything after the front
matter is sent as the prompt, word for word.

```
---
duration: 30
aspect: 16:9
resolution: 720p
model: bytedance/seedance-2.5
---
[CHARACTER] Who, exactly: age, face, hair, eyewear, every garment, posture, what's in their hands, the vehicle or
prop and its colour, where they are. End with the lock: "Keep face, hair, outfit and <prop> identical for all 30 seconds."

[STYLE] Live-action or not, "one unbroken take", aspect, focus per shot size, time of day and the light it
gives, the palette as named colours, texture, one small constant motion (wind in the hair), the comic register,
and a ban on cuts, freeze frames and slow motion.

[AUDIO] The ambient bed as a list of specific sounds. Then cues on the clock: "0.8s: one crisp message alert."
"1.2–4.0s: <who>, off screen, <how it sounds>: "<the exact words>"." Then what the sound does as the picture
changes.

[TIMELINE]
0.0–1.0s — <framing> <action> <one detail>.
1.0–4.0s — ...
...                          (windows touch end to start, from 0 to the duration, no gaps)

[CAMERA RULES] The continuity laws: one unbroken move per stage, easing in and out, horizon level, subject near
centre, each stage farther than the last, which leading line stays where.

[NEGATIVE] No cuts or black frames, no other people, no text, captions, subtitles or logos, ...
```

`templates/script.md` is a blank to copy; `examples/the-sandbar.md` is a complete 30-second script.

## What makes it land

- **One premise, four beats.** Calm → a trigger you *hear* (a ping, then a voice note asking for something) →
  a deadpan reaction in close-up → the reveal. In the zoom-out shape the reveal *is* the punchline: each pull-back
  shows how impossible the request is from here.
- **The first second already shows the person.** No establishing shot; the scroll stops on a face.
- **Lock identity in writing.** Name every visible attribute once, then the "identical for all N seconds" line.
  Drift is what breaks a long take.
- **One saturated accent.** Mute the palette and give the subject's prop the only strong colour, so the eye finds
  it when it is three pixels wide at the end.
- **Escalate the reveal.** Each stage travels farther than the last, and each window names what becomes visible
  at that scale — the way in, the way out, the horizon. Geography tells the story.
- **Audio mirrors the camera.** Tight and close at the start, then only wind, wider and emptier as it pulls back.
- **Time the voice.** About 2.5 words a second: a 2.8-second window holds about seven words.
- **Leave the last third quiet.** Slow, wide and empty is where the copy goes afterwards.
- **Never ask the model for text, logos or brand marks.** It garbles them, and it paints badges on vehicles unless
  the negatives forbid it. Put the lines on afterwards in your own fonts, over the quiet wide.

Shapes besides the zoom-out: the **push-in** (the punchline is a detail), the **follow** (a long walk compresses
time), the **orbit** (the world changes around a still subject). Same six blocks; the camera rules change.

## Run it

```bash
S=<this skill's directory>/scripts/timeline_video.py
python3 $S check  film.md                          # parse the blocks, check the clock, print the beats
python3 $S models --model bytedance/seedance-2.5   # durations, resolutions, aspects, audio, price
python3 $S render film.md -o out/ --key-file ~/keys/openrouter.key   # price, submit, poll, download
python3 $S sheet  out/film.mp4 film.md             # one frame per beat → out/film_beats.jpg
```

| Flag (render) | Does |
|---|---|
| `-o DIR` | Where the MP4 and its sidecar go. The file name is the script's. |
| `--model`, `--duration`, `--resolution`, `--aspect` | Override the front matter. Each is checked against the model's published capabilities before anything is sent. |
| `--seed N` | Pass a seed (honoured only where the model supports it). |
| `--no-audio` | Ask for a silent video. Audio is on by default for models that make it. |
| `--key-file F` | Read the OpenRouter key from a file. Otherwise `OPENROUTER_API_KEY`. The key is never printed or saved. |
| `--dry-run` | Check and price only. |

**Cost.** `render` prints the price before it submits. Per-second models are exact. Seedance is priced per *video
token*, and OpenRouter does not publish the conversion, so its figure is labelled an estimate (tokens ≈ width ×
height × 24 fps × seconds ÷ 1024). Checked on a real job: 30s at 720p was estimated at $6.93 and charged $6.94. The
real charge is always in the sidecar's `usage.cost`. Render one, look at it, then decide on re-rolls.

**What you get:** `<name>.mp4` and `<name>.json` — model, parameters, the prompt and its SHA-256, the job and
generation ids, timings and the `usage` block. Keep them together; the sidecar is how a take is reproduced.

## Review before you use it

1. `ffprobe` the file: the duration you asked for, and an audio stream if you asked for one.
2. `sheet`, then look at every beat: same face, hair and outfit throughout; the accent colour holds; the reveal
   escalates; no text, logos or extra people appeared.
3. Listen: the trigger lands on its cue and the voice says the exact words.

A failed beat is a re-roll (new seed) or a script fix, usually a vaguer window made specific.

## When it fails

| Exit | Meaning |
|---|---|
| `0` | Done |
| `1` | OpenRouter refused or the job ended `failed`, `cancelled` or `expired`; its error is printed as given |
| `2` | The script or a parameter is wrong (missing block, gap in the clock, a duration the model doesn't offer) |
| `4` | No key |

A video job is not zero-data-retention: the provider keeps the output briefly for the download.

## Credit

The format follows the Seedance prompt @iamneubert shared with the breakdown of a viral single-take ad
(https://x.com/iamneubert/status/2099199895039336459). This skill contains none of that prompt or video.
