# onetake-videogen

A [Claude Code](https://claude.com/claude-code) skill that turns raw recordings or a plain topic into a finished,
captioned, music-backed video. It runs locally on an NVIDIA GPU and needs no editing by hand.

It is built on [OneTake](https://github.com/leejersey/OneTake), a text-based video editor where deleting words
deletes the matching video. This repo adds a patch that makes OneTake fast and reliable on long videos, plus the
skill and tooling around it:

| Step | What it does | Tech |
|---|---|---|
| Transcribe | Word-level timestamps; fillers (`eh`, `em`, `um`, `呃`…) are flagged | faster-whisper `large-v3-turbo` on CUDA |
| Decide cuts | Claude reads the transcript and removes retakes, false starts, off-camera talk and Whisper hallucinations | the skill |
| Cut | Frame-accurate cut in one pass; long pauses shortened; downscaled to 720p | ffmpeg `select`/`setpts` + NVENC |
| Captions | Word-by-word "pop" captions, active word highlighted. For a generated voice-over, `align.py` keeps Whisper's timings and takes the spelling from the written text, so names, brands and `%` read as written | ASS + libass, burned in during the cut pass |
| Music | Royalty-free tracks (CC0 / CC BY) picked to match the speaking pace, time-stretched to one tempo, crossfaded on bar lines, ending exactly on the last frame, ducked under speech | Openverse, librosa, rubberband |
| Voice-over | Indonesian (and 29 other languages) narration with a consistent or cloned voice | [VoxCPM2](https://github.com/OpenBMB/VoxCPM) |
| Motion graphics | Title cards, and full animated explainer videos where scene changes snap to the beat. All motion, captions included, uses one rig: staggered springs, parts that trail their parent, area-preserving squash, eased exits, calm idle motion. Rules: [`references/motion.md`](references/motion.md) | [Remotion](https://www.remotion.dev) |
| Illustrated animation | Kurzgesagt-style scenes: Gemini flat-vector art traced to SVG (`split.py`), soft bodies from a deterministic physics sim, anticipation and overshoot on every event, motion blur. Worked example: the `Cell` composition (a cell dividing, 20 s). Guide: [`references/illustrated-animation.md`](references/illustrated-animation.md) | Remotion, vtracer |
| Sound effects | CC0 / CC BY sounds searched and fetched with a licence manifest (`sfx.py`), each cue's loudest point placed on its frame, tonal cues tuned to the music, music ducked under big hits; `cuecheck.py` verifies every cue within one frame | Openverse, ffmpeg |
| Mix | Speech + music (+ sound effects), loudness normalised to −14 LUFS | ffmpeg |
| Check gate | Before a generated video renders, `check.py` must print nothing: no text cropped, in the side margins or under the captions, every font loaded, no scene holding one picture over 6 s, no dead air in the narration. `--texts` lists every on-screen string to proofread | Remotion stills, a DOM text walk |
| Vertical | Explainers, title cards and edited recordings also come out 720×1280 for TikTok, Reels and Shorts, with captions raised clear of the app's controls | Remotion, ffmpeg |
| Post package | `post.json` (title, hook, caption, hashtags, sources, what is AI-generated, chapters) is checked against platform limits, then written out as paste-ready `post.txt` with the music credits, plus `cover.jpg` for the thumbnail | the skill, ffmpeg |

Output: 720p (1280×720, or 720×1280 vertical), H.264/AAC MP4. Generated video is 60 fps; an edited
recording keeps its own frame rate.

The skill also holds rules the scripts cannot enforce: claims come from a source and are listed, an edit
never changes what the speaker meant, and no generated likeness or logo is shown as real. `direction.py`
gives each explainer or illustrated scene a structure and opening that the last five did not use.

## Examples

Six frames from the 20 s `Cell` composition (`examples/cell/`):

![A cell dividing, six frames](examples/cell/sheet.jpg)

The same explainer scenes in both formats:

![Two explainer scenes, landscape and vertical](examples/explainer/formats.jpg)

## Speed (RTX 3070 Ti, Ryzen 5 7500F)

- **Transcribe:** a 61 s clip takes 3–4 s, including loading the model.
- **Cut + encode:** an 18-minute 720p60 source with 278 cuts takes about 1.8 min at `high` quality and 1.4 min at `medium`.
- **Before the patch:** stock OneTake used libx264 `slow` with a 5-minute ffmpeg timeout, so exports longer than about 15 minutes failed. Its concat-demuxer cuts also drifted about 0.6 s over 65 cuts.

## Requirements

- Linux with an NVIDIA GPU and a recent driver. It works on CPU too, just slowly. VoxCPM2 needs about 8 GB of VRAM.
- `ffmpeg` built with `libass`, `librubberband` and ideally `h264_nvenc` (Ubuntu's ffmpeg package has all three).
- Python 3.10–3.12.
- Node.js 20+.
- Google Chrome. This is optional: Remotion downloads its own headless shell if Chrome isn't installed.
- For illustrated animation: [vtracer](https://github.com/visioncortex/vtracer) (`cargo install vtracer`; `install.sh` does this when Rust is present) and [Bun](https://bun.sh) for the headless simulation check. `scripts/image.py` generates the art through `agy` (the Antigravity CLI), signed in to a Google account; no API key is needed.

## Install

```bash
git clone https://github.com/Nael-Nathanael/onetake-videogen ~/oss/onetake-videogen
cd ~/oss/onetake-videogen
./install.sh            # add --no-tts to skip VoxCPM2/PyTorch
```

`install.sh` is idempotent; re-run it after pulling to pick up new dependencies. It does the following:

1. Clones OneTake into `$ONETAKE_HOME` (default `~/OneTake`), pinned to the commit the patch targets.
2. Applies `patches/onetake-gpu-longvideo.patch`.
3. Creates the Python envs and installs the npm dependencies.
4. Symlinks the skill into `~/.claude/skills/onetake-videogen`.

## Use

In Claude Code:

```
/onetake-videogen edit ~/Videos/rekaman-mentah.mp4
/onetake-videogen bikin video explainer 2 menit tentang cara kerja kompresi video
/onetake-videogen animasi kayak Kurzgesagt: sel membelah diri
```

Plain requests in any wording work too, such as "potong bagian yang salah ucap di video ini, kasih caption dan musik".
The skill works out the plan from the request and the files (mode, length, tone, captions, voice, music, sound
effects) and asks you to confirm it once. Then it cuts and renders on its own and reports what it removed and which
music it used.

Every job writes to `~/OneTake/storage/jobs/<name>/`:

- `final.mp4`: the finished video
- `transcript.txt`, `cuts.json`: what was cut and why
- `music/CREDITS.txt`: attribution text to paste into the video description
- `post.txt`, `cover.jpg`: the title, caption, hashtags, sources and credits to paste, and the thumbnail

The scripts in `scripts/` can also be run by hand. `SKILL.md` holds the rules for every mode, and
`references/edit.md`, `references/explainer.md` and `references/illustrated-animation.md` hold each mode's
steps. Every script takes `--help`. The tests for the checks run with
`python -m unittest discover -s tests`.

The patched OneTake web editor is still available for manual edits: `~/OneTake/start_local.sh`, then open http://localhost:5173.

## What the OneTake patch changes

- **Export:** NVENC with automatic libx264 fallback, no ffmpeg timeout, and export runs off the event loop.
- **Cutting:** frame-accurate `select`/`setpts` time mapping, which is also safe for variable-frame-rate phone footage. Audio is trimmed sample-accurately from PCM. Ubuntu's ffmpeg 8.0.1 `aselect` passes every frame, so it isn't used.
- **Uploads:** streamed to disk instead of read into RAM twice. The limit is raised from 500 MB to 20 GB, `.mkv` is accepted, and retention is configurable.
- **Transcription:** CUDA is detected through CTranslate2, so PyTorch is no longer a dependency. Uses pip `nvidia-cublas`/`nvidia-cudnn`, pins `av<17` (PyAV 17 breaks faster-whisper 1.2), and adds anti-hallucination settings.
- **Web UI:** a language picker. Upstream hardcoded Chinese, so every upload was transcribed as Chinese. Adds an Indonesian filler list and a `large-v3-turbo` model option.

## Acknowledgements

Several parts of this skill come from [video-gen-skill](https://github.com/vincentfranstyo/video-gen-skill)
by [Vincent Franstyo](https://github.com/vincentfranstyo):

- **The check gate:** his `render.ts check` refuses to render until the layout and the narration are
  clean, and `texts` lists every on-screen string. `check.py` does the same for Remotion, and the text
  walk in `remotion/src/layoutReport.tsx` is ported from his `layout-check.ts`.
- **Vertical as a first-class format,** with captions kept clear of the phone app's controls.
- **The post package:** `post.json` with title, hook, caption, hashtags, sources and chapters.
- **The rules on facts and likenesses:** no invented facts, sources listed, and no generated logo,
  person or document shown as real.
- **Variety between jobs:** `direction.py` adapts his `directions.ts`: a seeded pick of structure and
  hook that avoids the recent jobs.
- **Captions that read as written,** with only the timings taken from the voice.
- **One file of steps per kind of video.**

His skill takes a different route to the video (HTML stages screenshotted in Chromium, a free online
voice, vertical 1080×1920) and is worth reading on its own.

Reading measurements out of a Remotion render through `onBrowserLog` follows
[blobatar](https://github.com/Alain00/blobatar)'s `check-gaze.ts`.

## Licensing notes

- **This repo:** MIT (see `LICENSE`).
- **video-gen-skill:** MIT, © 2026 vincentfranstyo. The files that port or adapt its code say so in their
  header; its licence is in `LICENSES/video-gen-skill-MIT.txt`.
- **OneTake:** by [leejersey](https://github.com/leejersey/OneTake). Its README states MIT. This repo ships only a patch against it, not its source.
- **Plus Jakarta Sans:** SIL Open Font License, see `assets/fonts/OFL.txt`.
- **Remotion:** free for individuals, non-profits and companies with up to 3 people. Larger companies need a [company license](https://www.remotion.dev/license).
- **Music:** fetched at run time and limited to CC0 and CC BY. CC BY requires attribution, which is why `CREDITS.txt` is written. Some Jamendo tracks are registered with YouTube Content ID and can still get claimed. For monetised channels, prefer your own library in `~/Music/bgm` (for example, YouTube Audio Library downloads).
- **Models:** faster-whisper/Whisper weights are MIT. VoxCPM2 is Apache-2.0.
- **Cell example assets:** the part SVGs in `remotion/public/illustrated/cell/` were generated with Google Gemini and traced with vtracer (see `CREDITS.md` there). The sound effects in `examples/cell/audio/` are CC0 (listed in `CREDITS.txt` for provenance). The example's music is CC BY 3.0 and is not committed; `sfx.py fetch --refetch` downloads it from the manifest.
