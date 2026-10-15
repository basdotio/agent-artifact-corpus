---
name: onetake-videogen
description: >-
  Local video production on an NVIDIA GPU, built on OneTake. Edits raw talking-head and screen recordings (Whisper transcript → removes fillers, retakes and long pauses → frame-accurate NVENC cut), burns word-by-word captions, adds tempo-matched royalty-free music, sound effects on every beat, voice-over (VoxCPM2, Indonesian and 29 more languages), animated explainers from a topic or script, and Kurzgesagt-style illustrated animation (AI-generated flat-vector art, soft-body physics in Remotion). Use it whenever the user's goal involves making, editing or improving a video, in any language or wording, with or without a file: cutting mistakes, adding captions, music, sound effects, a voice-over or an intro, or turning a topic into an animation. It works out the right workflow from the request and confirms a short plan with the user before rendering. Output 720p60 MP4, landscape or vertical (TikTok, Reels, Shorts), -14 LUFS, with the caption, hashtags and thumbnail to post it.
---

# OneTake videogen

Everything runs locally from `$ONETAKE_HOME` (default `~/OneTake`, OneTake patched for GPU +
long videos by `install.sh`). Call every script through `scripts/run.sh`: it picks the right venv,
sets the CUDA library path, and keeps temp files on disk (`/tmp` is often a RAM-backed tmpfs —
never stage video there).

```bash
S=<this skill's directory>/scripts              # e.g. ~/.claude/skills/onetake-videogen/scripts
J=~/OneTake/storage/jobs/<short-name>           # one folder per video job; all outputs here
```

If `run.sh` reports a missing venv, the environment isn't installed: run `install.sh` from the
skill directory (see README.md).

**Confirm once, then run automatically** (see "Understand the request" below): one short plan
confirmation before any heavy work, then every editorial decision is yours until the video is done.

Production format is **720p**: 1280×720 landscape, or 720×1280 vertical for TikTok, Reels and Shorts.
Sources above 720p are downscaled on their short side, so portrait footage stays portrait. An edited
recording keeps its own frame rate (30 fps stays 30 fps); generated video (explainers, title cards,
illustrated scenes) renders at 60 fps. Explainers and title cards take `--format vertical`: type, margins
and captions follow the frame, with captions raised clear of the app's controls. Illustrated scenes
(C) are landscape.

## Motion (all modes)

Every animated element follows `references/motion.md`, whatever the mode. Read it before adding or
changing any animation. Remotion code goes through the shared rig in `remotion/src/motion.ts`, and the
ASS captions follow the same rules. In short:

- one motion onset at a time, with related parts staggered 4–5 frames
- children rigged on their own lagging springs, never welded to their parent
- springs for arrivals, eased exits, never linear
- squash and stretch that keeps the area
- slow, small idle motion
- colours that ease instead of snapping

Check motion in frame strips, not single stills.

## Keep it exciting, keep it short (all modes)

Viewers decide in the first seconds and leave at the first dull stretch. Every video:

- **Hook in the first 3 s.** Open on the payoff, a surprising claim or a question; never a greeting,
  logo or slow intro. A title card, if any, is short and lands on a sound effect.
- **Something changes every 2–4 s:** a new scene, a point popping in, a caption highlight, a sound
  effect. No static stretch over 4 s.
- **No dead air.** Cut silences, warm-ups and repeats; one idea said once.
- **Short.** Cut to the shortest version that still delivers the point. When in doubt, shorter.
- **Energy carries through.** Upbeat music, sound effects on every visual event, captions on: defaults
  for B and C; for an edit (A), recommend them as extras in the plan.
- **End on the payoff,** then stop: no long outro.

Excitement comes from pace and change, not from jittery motion: the motion rules still hold, so each
change stays easy to read.

## Facts, sources and likenesses (all modes)

A video that states something false, or shows something fake as real, harms the person publishing it.

- **Never invent** a fact, number, price, date, quote, feature or testimonial. Each one comes from the
  user, a file they gave, or a source you read. Cut a claim with no source, or ask about it in the
  plan confirmation.
- **Research a factual topic before writing the script**: primary and reputable sources, the date of
  the information for anything recent, disputed points marked as disputed. Every source goes in
  `post.json` `sources`, and a number on screen matches its source to the digit.
- **An edit keeps the speaker's meaning.** No cut joins words into a statement they did not make.
- **Nothing fake shown as real**: no real person's likeness in generated art, no cloned voice except from a
  sample the user gave of a voice they may use, no generated brand logo (use the file the user gave),
  no generated document, screenshot or app screen shown as the real one. Real people and events are
  drawn as plain illustration or symbols.
- **Say what is generated.** List voice, illustrations and music made by a model in `post.json`
  `generated` and in the report.

## Understand the request, confirm once, then run

Work from what the user wants the viewer to get, not from keywords in the request.

1. **Look at the inputs.** Probe any file (`ffprobe`): duration, frame rate, whether it has speech,
   camera or screen recording, aspect. Check whether it is **raw or already finished**: encoder or
   `comment` metadata from an editor or Remotion, embedded or sidecar subtitles, music under the speech,
   a script-clean transcript. Mode A on a finished video cuts its music bed mid-phrase; say so in the plan
   and offer what still helps (captions, sound effects, a different file). Cheap checks:
   `ffmpeg -af silencedetect=n=-40dB:d=1` (no silences at all under speech suggests a music bed) and
   transcribing a 30 s sample (`ffmpeg -t 30` first). Read any script or outline.
   Note the request's language and any audience, length or style it mentions.
2. **Draft the plan.** Pick the mode by what the content needs:

   | Signal | Mode |
   |---|---|
   | Raw footage with speech to clean up (camera, screen capture, podcast) | **A. Edit** |
   | Information to explain: steps, lists, comparisons, numbers, from a topic, outline or script | **B. Explainer** |
   | Something to *show* moving or transforming: biology, physics, a process, a creature, a story, or a Kurzgesagt-like look | **C. Illustrated animation**, narrated when it explains |
   | Footage plus an intro or narration | A, then a B or C intro, or `voiceover.py` + `mix.py --voice` |

   B or C: pick C when understanding depends on *seeing* something move or change (light scattering, a
   cell dividing, an engine turning); pick B when the content is facts, steps or numbers that read well as
   text. When both fit, recommend one and offer the other in the confirmation.

   Then fill in the rest, each with a default you can justify from the request:
   - **Length:** from the footage, the script (~140 words per minute) or the request; otherwise 45–90 s
     for B, 20–45 s for C.
   - **Format:** vertical when the request names TikTok, Reels, Shorts or a phone, or the footage is
     portrait; landscape otherwise.
   - **Language** of narration and captions: the request's language unless stated.
   - **Tone:** upbeat and punchy by default; calm and documentary only when asked. It sets the motion feel, the music `--query` and
     how many sound effects.
   - **Captions** on or off, **voice** (generated, cloned from a sample, or none), **music** mood,
     **sound effects** (none, light, or one per event). For an edit (A), add only what the request asks
     for; list the rest as optional extras, off by default. Generated videos (B, C) default to music and
     sound effects on.
   - For A: how hard to cut. Default tight and fast (`--max-gap 0.4`); keep more only when asked.
3. **Confirm in one step.** Show the whole plan as one short list, in the request's language, so the user
   can correct anything. Then ask with `AskUserQuestion` when available (without it, one short message):
   - Ask only about choices that are still open and would materially change the video: at most 4 questions, 2–4
     options each, your pick first and marked "(Recommended)", headers of 12 characters or less. A
     finished file where raw footage was expected, an unclear audience or a B-or-C call are open; things
     the request already fixed are not.
   - When nothing is open, ask a single question: go with this plan, or adjust.
   - When the user said not to ask (for example "langsung aja", "just do it"), don't ask: show the plan in
     one line and start. The exception is an input that contradicts the request, such as a finished file
     sent as a raw recording; ask that one question anyway, because the requested work would damage it.
     Only confirmed evidence counts as a contradiction: editor or Remotion metadata, subtitles, or music
     heard in the 30 s sample. Missing silences alone is a hint, not proof: run the sample check (it is
     cheap, so run it even after "langsung aja"), and if it finds nothing, note the hint in the plan and
     proceed.
4. **Run without stopping.** After the answer, make every editorial decision yourself (what to cut,
   scene timing, cue placement) and don't ask again mid-pipeline. Ask again only if an input turns out
   missing or unusable (no file, corrupt file, no speech where speech was expected).

## The steps for each mode

After the plan is confirmed, read the file for the mode and follow its steps in order. The steps live
only there.

| Mode | Read |
|---|---|
| **A. Edit a recording** | `references/edit.md` |
| **B. Explainer from a topic or script** | `references/explainer.md` |
| **C. Illustrated animation** | `references/motion.md`, then `references/illustrated-animation.md` |

Footage plus an intro: A's file, then B's or C's for the intro. The sections below
(music, sound effects, post package, report) apply to every mode.

## Music: tempo-matched, royalty-free

`music.py` picks tracks and builds a bed exactly as long as the video:
- **Target tempo** comes from the speaking pace in the words file (≈130 wpm → ~100 BPM, ≈170 wpm → ~124 BPM),
  i.e. the pop/explainer range. Override with `--bpm`.
- **Sources**: `~/Music/bgm` first (drop YouTube Audio Library downloads there), then Openverse (Jamendo,
  Freesound…) limited to **CC0 / CC BY**. BY-SA/NC/ND are excluded on purpose.
- Tracks within ±8% of the target are time-stretched (rubberband) to one tempo, cut on bar lines, chained with
  one-bar crossfades for long videos (variety = less monotonous), and the tempo is nudged ≤3% so the last bar
  ends on the last frame.
- `--query` changes the mood ("chill lofi,acoustic" for calm topics). Default is upbeat pop.
- **Always give the user `$J/music/CREDITS.txt`** — CC BY requires attribution in the video description.
  Jamendo tracks can still trigger YouTube Content ID claims; mention it if they monetise.

## Sound effects (any mode)

Motion lands harder with a sound on it: a pop for a title card, a tick per list point, a whoosh on a
scene change, a cue per event in an illustrated scene. Pass absolute paths (`run.sh` changes directory).

1. **Search**: `$S/run.sh sfx.py search $J/sfx-search.json "bubble pop" "water drop" [--max-dur 6]`. CC0 and
   CC BY only; pick ids from the printed table.
2. **Fetch**: `$S/run.sh sfx.py fetch $J/audio name=OPENVERSE_ID ... [--music name=ID]`. Writes
   `manifest.json` (licence, credit, sha256, measured peak offset) and `CREDITS.txt`. It refuses creators
   whose account is deleted, because their licence can no longer be checked. Check the source page of any
   CC BY item. `--refetch` restores missing files from a manifest.
3. **Cues**: write `$J/cues.json`. `at` is where the sound's loudest point lands (seconds = frame / fps).
   `gain_db` is relative to the speech/music level: big hits about +9 to +11, light ones +4 to +6.
   ```json
   {"manifest": "audio/manifest.json", "cues": [
     {"name": "burst", "file": "burst-squish", "at": 4.0, "gain_db": 9, "lowpass_hz": 7000, "duck_db": 4},
     {"name": "chime", "file": "chime-kalimba-e5", "at": 4.95, "gain_db": 4, "pan": 0.4,
      "pitch_hz": 587.33, "source_hz": 666.0, "lowpass_hz": 5000, "keep_s": 1.6}]}
   ```
   Optional fields: `pan` (-1..1), `pitch_hz` (tune tonal cues to the music's key; give `source_hz` for
   chirpy sounds), `lowpass_hz`, `keep_s`, `duck_db` (music dip, 3–5 dB for big hits).
4. **Mix**: `$S/run.sh mix.py VIDEO $J/final.mp4 [--voice ...] [--music ...] --sfx $J/cues.json`. Each cue's
   loudest point is placed on its `at` after processing; the loudness pass must stay linear (reported in
   `final.mp4.sfx.json`). `--sfx` is optional; without it `mix.py` mixes speech and music only.
5. **Check**: `$S/run.sh cuecheck.py $J/final.mp4` must print PASS (every cue within one frame).

Give the user `$J/audio/CREDITS.txt` with the music credits.

## Post package (any mode)

A finished video ships with what gets pasted when it is published. Write `$J/post.json` in the video's
language:

```json
{"title": "What gives AI fiction away?", "hook": "A novel pulled for AI",
 "caption": "…", "hashtags": ["ai", "writing", "fiction"],
 "sources": ["https://…"], "generated": ["voice (VoxCPM2)"],
 "chapters": [{"at": "0:00", "title": "The pulled novel"}]}
```

- `title`: up to 100 characters. `hook`: the opening title exactly as it reads on screen.
- `caption`: up to 2200 characters. The hook line, 2–4 short lines of what the viewer gets, and a call
  to action when the video has one.
- `hashtags`: 3–8, no `#`, no spaces.
- `sources`: every URL or document a claim rests on; `[]` when the video makes none.
- `generated`: what is AI-made (voice, illustrations, music); `[]` for an edit of real footage.
- `chapters`: only for a video with at least 3 parts that start 10 s or more apart, the first at 0:00.
  Long edited recordings need them most.

Then `$S/run.sh post.py $J/post.json --video $J/final.mp4 [--scenes $J/scenes.json]`. It prints one line
per problem; fix the file until it prints none. It writes `$J/post.txt` (paste-ready: title, caption,
hashtags, chapters, sources, the music and sound credits, the AI disclosure) and `$J/cover.jpg` for the
thumbnail. With `--scenes` the cover is the first scene once its title has landed; otherwise pass
`--cover-at <seconds>` for the frame that shows the hook.

## Report back

When done, tell the user: final path, `post.txt` and `cover.jpg`, any place where you departed from the confirmed plan and why,
duration before → after, a short list of what was cut (counts + the
notable retakes), the music track(s) with tempo and the credits text, the sources behind the claims, what
is AI-generated, anything you could not verify, and render times. With sound effects,
add cuecheck's worst offset, the loudness and whether the loudness pass stayed linear. Keep job folders;
`~/OneTake/storage/jobs` is not auto-cleaned (disk is the user's call).

## Troubleshooting

- **CUDA/cuDNN errors in transcribe**: always go through `run.sh` (sets `LD_LIBRARY_PATH`).
- **`metadata_errors` error**: PyAV ≥17 in the OneTake venv; `pip install "av<17"`.
- **Out of VRAM in voiceover**: VoxCPM2 needs ~8 GB; stop the OneTake server (`pkill -f start_local.sh; pkill -f run.py`)
  and other GPU apps, then retry.
- **NVENC fails** (e.g. 10-bit HDR phone footage): the cut falls back to libx264 automatically; it's slower, not broken.
- **Remotion**: uses an installed Chrome (`REMOTION_BROWSER_EXECUTABLE`, default `/usr/bin/google-chrome`) when present,
  otherwise downloads its own headless shell. It does not need Playwright browsers.
  Remotion is free for individuals and companies ≤3 people; larger companies need a Remotion company licence.
- **`No module named 'PIL'`, missing `@remotion/motion-blur`, or `vtracer: command not found`**: the install
  predates illustrated mode; rerun `install.sh`. vtracer needs Rust (`cargo install vtracer`).
- **`image.py`: `agy made no image`**: agy is signed out (run `agy` once and log in) or the account's image
  quota is used up; the message after the colon is agy's own reply.
- **`cuecheck.py` FAIL**: a cue's source file changed or `at` points past the video; rerun `mix.py --sfx` and
  check `OUT.sfx.json` for the placed times.
- Fresh machine or broken env: rerun `install.sh` (idempotent).
