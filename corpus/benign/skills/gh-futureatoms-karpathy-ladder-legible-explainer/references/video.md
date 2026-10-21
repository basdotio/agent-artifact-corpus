# Tier 4: explainer video

A narrated video is the richest tier and the slowest to make. Use it when the
user asks for a video, or when the subject unfolds in time (a protocol
exchange, an algorithm step by step, an idea that builds up) and the user
wants something to watch.

## Pick the engine

| The user asks for | Engine | Why |
|---|---|---|
| "3b1b style", "3Blue1Brown", math or mechanism shown as geometry | **Manim Community Edition** with LaTeX | It is the tool that look comes from: LaTeX type, vectors as arrows on a plane, objects that transform into the next state |
| Any other explainer look (typographic, diagram-led, data-viz, a brand style) | The **`hyperframes`** skill, `faceless-explainer` workflow | HTML compositions, captions, music and a full review loop |

## Workflow

1. **Get the content right first.** Collect and verify the facts as for a sheet. For a subject with several parts, plan the sheet panels (`references/spec-sheet.md`) even if you do not build the sheet: each scene comes from a panel. Recompute every number you show.
2. **Write the message**: one sentence that the viewer must remember.
3. **Plan the film in three parts** (see Structure below): a title card with a one-line intro, the body, then a recap card.
4. **Choose the voice** (below). When the user has not heard the options, render a 10-second sample of 4 to 6 candidate voices into one small HTML page with a player for each, open it, and let them pick by number.
5. **Write the narration** and **the scene plan** (below) in a brief folder: `<delivery folder>/<slug>-video/explainer-narration.md` and `explainer-scenes.md`. Keep these names: hyperframes owns `STORYBOARD.md`, and on a case-insensitive disk `storyboard.md` is the same file.
6. **Build** with the engine (below).
7. **Verify the render** (below).
8. **Deliver** only what the user needs: the `.mp4`, an `.srt`, the narration, the scene plan, and the source in `<slug>-video/source/` (scene code and a build script). Keep framework working files (presets, packets, captures, caches) out of the delivery folder.

## Voice

- `ELEVENLABS_API_KEY` is set: ElevenLabs.
- The user asks for free and local, or there is no key: Kokoro on-device. With Manim, use `kokoro-onnx` in a Python venv and its model files (`kokoro-v1.0.onnx`, `voices-v1.0.bin` from the kokoro-onnx release). With hyperframes, use `media-use` with `--local-only`. espeak-ng stores its data path in a short buffer: if Kokoro fails with a "phontab" error, copy the espeak-ng data folder to a short path and point to it.
- Pick the voice that suits the named style and name the other option in one line. With Kokoro, start from `af_heart` (the voice users preferred in testing; `am_michael` sounded flat to them), at `speed` 0.8.
- Leave room to think: about 1.1 s of silence after each sentence and about 1.9 s between scenes. Users found the default pace (speed 1.0, 0.3 s gaps) far too fast for a math explainer.
- Nothing works: macOS `say -v Samantha -o narration.aiff`, and tell the user it is a placeholder.

Generate the voice one sentence at a time and record each clip's length; time the animation from those lengths, so each visual lands on the sentence that names it.

## Narration

Spoken English is the one place where STE yields. Keep its discipline (short
sentences, one idea in each, one word for one thing, active voice, no
progressive or perfect forms) but write the way a good teacher talks:
"Here is the trick.", "Now watch what happens to bank." Do not label the
narration as STE unless the user asked for STE.

- At the pace above, narration runs at about 100 words a minute including pauses. Target words = seconds x 1.6: 60 s is about 95 words, 90 s about 145.
- At most 15 to 18 words in a sentence.
- Say what is on the screen: "This arrow is the query. It points at each key in turn."
- Define each term the first time you say it, then never change the word.
- Lint it with `ste_lint.py explainer-narration.md --mode 80` and fix the grammar findings.

## Structure

Every video has three parts, so a viewer knows what they will learn, follows it, and leaves with the point.

1. **Title card, 6 to 9 s.** It is also the thumbnail, so it is the first frame: the topic in large type, a one-line subtitle ("in about a minute"), one visual hint of the subject, and a footer with the source or maker when the user wants one. The narration says what the viewer is about to see in one sentence: "In the next minute, you will see how a model finds the meaning of a word from the words around it."
2. **The body**, built from the scene plan.
3. **Recap card, 12 to 20 s.** The steps as a short chain of boxes with arrows, and the key formula or result. The narration starts "So, to recap." and repeats the steps in one or two sentences, then names the idea. Hold 2 to 3 s after the last word, with the music fading out.

Crossfade between the parts (about 0.6 s). Never open on a black or half-drawn frame.

## Music

A quiet bed helps a long explainer; a harsh one ruins it.

- Prefer a real track: `media-use resolve --type bgm --intent "calm minimal piano, no drums"` (needs the HeyGen CLI and its OAuth sign-in; ask the user once).
- Without a catalog, synthesize a sparse soft piano locally: single notes about once a second on a slow four-chord progression, short decays, a low-pass around 2 kHz and a little reverb. Never use sustained synth pads or detuned sine stacks; users found them painful.
- Mix it about 20 dB under the voice (measure the music-only stretches with `volumedetect`), duck it gently under speech (ratio about 2.5, attack 250 ms, release 1.2 s), fade in over 2 s and out over 3 s.
- When the user says the music hurts or distracts, remove it at once and offer a catalog track.

## Scene plan

A table with one row for each scene. Each scene shows one idea.

| # | Seconds | Narration (exact words) | On screen | Motion |
|---|---|---|---|---|
| 1 | 0 to 6 | "Attention lets each word look at the other words." | A sentence of 5 tokens in a row | Tokens fade in from left to right |

## Look (3Blue1Brown style)

- Dark background, light ink, one accent colour for the thing being explained, a second accent only for contrast.
- Show mechanisms as geometry: vectors as arrows on a plane, a dot product as alignment between two arrows, weights as bar lengths.
- Build up, do not cut: objects move, split, combine and transform into the next state. Fade out a text label before you transform its object, so no garbled glyphs show mid-morph.
- One new object or change at a time, timed to the word that names it. Start each visual on the first word of its sentence, so no second of the video is empty.
- Show where each new quantity comes from when it first appears (for attention: q = W_Q x, k = W_K x, v = W_V x).
- Use one symbol for one thing in narration and on screen (for example √d_k everywhere, with "d_k is the key size" on screen once).
- Math in LaTeX (`MathTex`), set in pieces as the narration reaches them.
- Labels at 28 px or more at 1080p; keep everything inside a 5% title-safe margin.
- Burn the captions in: X, LinkedIn and most feeds autoplay muted and drop soft subtitle tracks. Use a small sans font at the bottom margin, clear of every on-screen label (check the frames where labels sit low). On the title and recap cards, leave an empty band above the footer and place those captions in it with a larger bottom margin. Also ship the `.srt`.
- Hold the final state for 2 to 3 seconds with the message on screen.

## Build with Manim

- Create a venv (`uv venv` or `python3 -m venv`) in scratch and install `manim`; it needs ffmpeg, cairo and pango, and a LaTeX install for `MathTex`.
- One `Scene` class with a section for each row of the scene plan; read the clip lengths from the timings file and use them as `run_time` and `wait` values.
- Render at 1080p (`manim -qh`). Render the title and recap cards as still frames (`manim -s`) in the same colours and fonts.
- Assemble with ffmpeg: title card, body and recap card with `xfade`; the intro, body and recap narration placed at their offsets; the music bed ducked under the narration; captions burned in with `subtitles` (a build of ffmpeg with libass; a container image such as `linuxserver/ffmpeg` has it when the local one does not). Take the length from the video so the closing hold is kept.
- Put `scene.py`, `narrate.py` and a `build.sh` that rebuilds everything in `source/`.

## Build with hyperframes

1. Create the film project in a new, empty folder, for example `<slug>-video/film/`: `npx hyperframes init <that folder> --skill=faceless-explainer`. `init` refuses a folder that has files in it.
2. Write `BRIEF.md` at the root of the film project, in the hyperframes brief format:

```markdown
---
workflow: faceless-explainer
flow: automation
storyboard: no            # yes when the user wants to review the plan before the build
message: "<the one sentence>"
destination: youtube
aspect: 1920x1080
language: en
length: 45s
angle: concept
audience: "<who watches>"
voice: <the voice you chose>
---

## Intent

<One short paragraph: what the video teaches, for whom, the tone.>

## Assets

- ../explainer-narration.md: final narration. VO_MODE: verbatim.
- ../explainer-scenes.md: scene plan with timings; build one frame for each row.

## Notes

- The narration is final. Do not rewrite it.
- Captions: burned in, small, at the bottom margin, clear of labels; also export an .srt.
- <When the user is not present:> The user is not available for questions. Proceed with these answers.
```

3. Load the `hyperframes` skill and ask it to build and render the project. A `BRIEF.md` on disk lets it run without its interview.

## Verify the render

```bash
ffprobe -v error -show_entries format=duration:stream=codec_type -of json <video.mp4>
```

- The duration is within 15% of the requested length; there is an audio stream.
- The first frame is the title card, and its text reads at phone size.
- Captions never overlap a label or the card footer; check a frame from every scene and both cards.
- Pauses: the gaps between sentences are 0.7 s or longer (`silencedetect` on the narration track). Music: the music-only stretches sit 18 to 22 dB under the speech.
- Extract frames (`ffmpeg -vf fps=0.5`) and look at them at full size: text is readable, nothing is cut off at the edges, no glyph is garbled mid-transform, each scene matches its row.
- Transcribe the audio locally (whisper.cpp when installed) and compare with the narration.

## Hand over

Lead the chat reply with the file path, the length and the voice, then two or
three lines on what the video shows. When the user asked for a free or local
tool, name it, its licence, and the one command that installs it on their
machine, even when it was already installed on yours. Put install and rebuild notes in a
`README.md` next to `source/`, not in the chat.
