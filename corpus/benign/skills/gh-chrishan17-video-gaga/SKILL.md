---
name: video-gaga
description: Design and render motion-graphics videos (MP4) from a plain-language request. The agent writes the story, designs each shot in HTML Canvas or three.js, choosing per shot by what it must show, and renders it deterministically, with a score composed for the video on the same beat grid as the cuts, sound effects, Edge TTS narration and burned-in or file subtitles. Use when the user wants a video, animation, explainer, product teaser, kinetic typography, social short or animated infographic, or asks to turn a script, article, data or an idea into a video. It asks a few questions, shows style frames before building, and judges its own output before delivering.
---

# Video Gaga

Turn "I want a video about X" into a finished MP4 that helps someone say what they mean. You are the writer, director, designer, motion designer, composer and editor. The runtime draws every frame with Canvas 2D or three.js (you choose per shot, [docs/three-d.md](docs/three-d.md)) as a pure function of time, renders it frame-exactly in headless Chromium and encodes it with ffmpeg; Edge TTS speaks the narration and sets the clock; the score shares its beat grid.

## What good looks like

The video is compared with what people scroll past every day, and correct is not enough. [docs/craft.md](docs/craft.md) describes the target in full; read it before you write anything. In short, a good video:

- **is about one specific thing, told by someone.** A person, a moment, an object, a number; a turn where something changes; a landing that pays off the opening; concrete lines, no slogans; one line worth repeating. An explainer answers one question in the viewer's words: it opens on what most people get wrong, builds the smallest correct model, changes one variable at the turn, and lands on the opening image read correctly ([docs/craft.md](docs/craft.md), *When the video explains*).
- **is carried by one visual idea** that recurs and changes with the story, in frames that would each work as a poster, in a look that stands on references you can name (a work, a studio, a medium, an era) rather than on adjectives, and whose feeling fits what the story is about. On a phone the subject and every word to be read are whole in the frame.
- **moves with weight and character.** Every move has a job, holds stay alive, cuts happen on action, a few signature moves are its own ([docs/motion-design.md](docs/motion-design.md)).
- **sounds produced.** A score composed as one piece of music for this video: a reference, a theme that comes back, a form with its own arc, underscoring a clear, unhurried voice and meeting the picture only where the story turns; few sound effects; silence where a line needs to land ([docs/music-and-sound.md](docs/music-and-sound.md) §1).
- **is judged on what was rendered,** not on what was intended, and delivered only when it meets the target.

The look is chosen for this story ([docs/craft.md](docs/craft.md), *The look has a name*). The 13 presets ([STYLE_PRESETS.md](STYLE_PRESETS.md)) are worked examples of named looks and a toolbox of helpers, one option among many rather than the starting point. The story, the structure, the choreography and the score belong to this brief, and the result should not resemble a preset's example video.

## What the user experiences

- They are asked only what changes the video (usually length, format, voice, captions, and whatever about the content can't be inferred), in one round, in their language. Each question has three concrete options, one marked **(Recommended)** with a reason tied to their brief, and they can answer in their own words. What the request already says is confirmed as an assumption. If they say "just make it" / "直接做" or don't answer, the recommendations stand, and every call made without asking goes into the brief's *Calls made*, one line each.
- Before the build they see their own opening in three directions (the best fit, a contrast, a wildcard), each standing on a different named reference, side by side, and pick one; the frames look like the real start of their video, never like a demo. They are spared this when they named a style, chose quick mode, or are editing.
- When they bring a reference (a frame, a clip, a link, a folder of their own work), their video visibly belongs with it: its palette, type, pacing and transitions, with their own subject.
- They see the brief and storyboard ([docs/craft.md](docs/craft.md), *The brief*) and can change the script or the visuals before it is built.
- They get the MP4 with an honest account (below).

## The contract (every composition)

- One `video.html` that loads `video-gaga.js` and calls `CV.create({...})`; each scene's `draw(ctx, s)` is a **pure function of time**: no wall clock, no `Math.random`, no state between frames. That is what makes parallel, frame-exact rendering possible.
- Designed at the output size: 1920×1080, 1080×1920, 1080×1080 or 1080×1350 (even sizes), 30 fps unless asked otherwise.
- Fonts from Google Fonts `<link>` with `display=block`.
- Nothing internal on screen: no "Scene 1", "Option A", preset names, placeholders or file names.
- Captions never collide with content; text holds long enough to read; the last frame is a resolved still held ≥ 1 s.
- A three.js shot stands in an environment and its hero surfaces are real materials: an HDRI (or a studio built in code), and maps that are scanned, generated or a matcap, chosen in the brief and fetched or generated before the build (`gaga asset find`, `gaga asset`, `gaga texture --prompt`), with credits in `assets/CREDITS.md` and the recipe in `assets/assets.json` (git keeps it and `assets/src/`; the rest is restored on render). Only a look that is flat on purpose goes without, and the brief says so ([docs/three-d.md](docs/three-d.md), *Surfaces*).
- Data and claims are accurate, with a source or calculation on screen when numbers are shown. Every number in the video is listed in `<project>/SOURCES.md` with its source or calculation; one without is cut.

## The tools

`gaga` is `node <skill-dir>/scripts/gaga.mjs`, where the skill directory holds this file.

| Command | What it gives you |
|---|---|
| `gaga doctor` | Checks node, ffmpeg, Playwright/Chromium, Edge TTS and the instrument samples, and fetches the samples (without them the score falls back to a much cheaper synth). Fix with `npm install` in the skill dir, `npx playwright install chromium`, ffmpeg, `uv` or `pip install edge-tts`. In a sandbox, `doctor`, `still`, `moodboard`, `render`, `tts` and `voices` need permission (Chromium, network); ask once, up front |
| `gaga init <dir> [--ratio 9:16]` | A blank project: the render contract and nothing else, for a look designed from its references. `--preset <slug>` starts from a preset's style instead (THEME, KIT helpers, transition, captions, overlay). Any preset's KIT can be borrowed; `presets/<slug>/video.html` shows how its helpers are called |
| `gaga tts <project>` | Narration from `narration.json` (segments = scene ids), cached; `build/voice/<id>.json` has the word timings ([docs/narration-and-subtitles.md](docs/narration-and-subtitles.md)) |
| `gaga voicetrack <project> --audio <take>` | One take: the whole narration made in one pass (a narrator, a cloned voice, a recording) is aligned to `narration.json` with Whisper, its pauses lengthened, and cut into one slice per scene; the scenes then follow the take ([docs/narration-and-subtitles.md](docs/narration-and-subtitles.md) §7) |
| `gaga music <project>` | Renders the score (`music.script`, or the older pattern spec) on its own: the mix by part, listening checks (ghostly stretches, a buried melody, flat range, sfx levels), every cut and sfx, warnings. An error names what to fix |
| `gaga still <project> --sheet [--subs] [--phone]` | Three probes per scene (entering, middle, settled) on contact sheets of six scenes. `--at 3.0,3.1,3.2,…` for exact moments (a strip of close probes shows a move's weight), `--scenes a,b` or `a..c` to re-probe part, `--phone` for probes at 390 px wide, the size a phone shows. Ends with a `text:` line (text cut off by the frame edge, in the caption band, too small on a phone or under 4.5:1 contrast, where it is still so 0.3 s later) and a `repeat:` line (a few probes drawn again in a fresh page, in reverse order, must come out identical; if not, a frame depends on something other than time) |
| `gaga moodboard <previewA> <previewB> <previewC> --title "…" [--wait]` | The style directions side by side for the user to pick (each preview: a `gaga init` project with one real scene and a `moodboard.json` with `name`, `pitch`, `recommended`, `keywords`, `motion`, `music`). `--wait` serves it and returns their click; without it, send them the HTML. A direction with a 3D opening is previewed with its real environment and surfaces, not untextured stand-ins |
| `gaga render <project> --subs burn` | The MP4 (`file`, `soft`, `burn+soft`, `none` for captions). `--scale 0.5 --format jpeg` for drafts, `--from/--to` for a range, `--motion-blur 5` for snappy moves, `--music track.mp3` for a licensed track, `--scale 2` for 4K. Ends with `gaga check` |
| `gaga asset find <words> [--type hdris\|textures\|models]` · `gaga asset <project> polyhaven:<id>` · `gaga asset restore <project>` | For every three.js shot: search Poly Haven (CC0) for an id, then fetch the HDRI, scanned PBR set or glTF model into `assets/` (credited in `assets/CREDITS.md`, recorded in `assets/assets.json`, cached for all projects) · rebuild `assets/` from the manifest (render and still do it when something is missing) |
| `gaga texture <project> --prompt "<surface>" --name <n> [--seamless] [--neutral] [--matcap]` · `gaga texture <image>` | A one-of-a-kind surface: Codex CLI generates the albedo and normal, roughness and ao are derived into `assets/<n>/` for `gl.pbr()`; `--matcap` makes a lit sphere for `MeshMatcapMaterial`. Without Codex, generate the picture with any model and pass the file ([docs/three-d.md](docs/three-d.md), *Surfaces*) |
| `gaga check <mp4>` · `gaga gif <mp4>` · `gaga voices --lang zh-CN` | Re-check an encode (with a `picture:` scan of the frames: stretches ≥ 1.5 s where nothing moves, one-frame glitches, blank frames, flashing; after `render`, a still frame while its words are read is a `read:` line, not a dead hold) · a GIF preview · list voices |

Writing a composition: [docs/runtime-api.md](docs/runtime-api.md) (scenes, `s.at`, `s.when('spoken words')`, `s.onBeat(i)`, `fx` reveals, `s.out()` exits, transitions, captions), [docs/music-and-sound.md](docs/music-and-sound.md) (what a good score is, writing it in `score.mjs` against the timeline, sfx, pacing, mix), [docs/three-d.md](docs/three-d.md) (which shots are three.js and why, a studio built in code, surfaces from maps (scanned, generated or matcap) and real HDRIs, 3D directed in numbers; each storyboard row names its engine), [docs/iso-figures.md](docs/iso-figures.md) (when an explainer's idea is a mechanism: one isometric machine built with the anatomy kit, painted by `CV.iso` on Canvas, shot several ways, its readout from the same model). Several voices in a row: one scene per clip, joined by `cut`s over an identical layout. Key symbols (⌘ ⌥ ⇧) are missing from most fonts: draw them.

Useful numbers: speech runs ≈ 4.3 CJK characters/s or ≈ 2.5 English words/s, and each voiced scene adds about 1 s (voice delay, decay, beat snapping), so a length target is met by cutting words, not by speeding up the voice. A long piece (over ~90 s) reads best in 3–6 chapters, each a section of the score with its own harmony, a sense of where the viewer is, and a callback at the end; it measured 128 s of speech + 26 scenes → 182 s ([examples/take-your-time](examples/take-your-time/BRIEF.md)). A 1080p render takes about twice the video's length on 4 cores.

## A good delivery

- The MP4 (and .srt/.vtt) paths, length, format, voice and style.
- The checks, each in a line, from runs that actually happened: duration, fps and resolution; audio present and matching the video (±0.1 s); captions (count, no overlaps, last cue inside the video); A/V sync (median < 120 ms) and per-clip voice sync; music 10–18 dB under the voice while it speaks and ≈ −2…−6 dB in the gaps; the `picture:` line, with each `look:` either fixed or explained (a still before the big hit is meant; a dead hold is not); the last `gaga still` run's `text:` line, each pointer fixed or explained (text dimmed so it is not read is meant), and its `repeat:` line.
- How it reads muted and audio-only, and what the cold review by a subagent said ([docs/craft.md](docs/craft.md), *How you know*).
- Each fix made after review as a pair of frames, before and after, at the same moment.
- The score in one line: feel, reference, BPM, key, the theme, and where it meets the picture.
- Which part is weakest and what you would try next.
- A request to listen: you can't hear the audio, so name the 8 seconds around the key mood change and ask how they feel and which part of the music or sound is off.
- Credits, when the score used the `piano`: *Piano: Salamander Grand Piano by Alexander Holm, CC BY 3.0*.
- How to tweak (open `video.html`: Space plays, ←/→ steps frames; colours and fonts in `T`; words in `narration.json`) and the natural next steps: another ratio, a GIF, 4K. `.gaga-previews/` is cleaned up once a style is picked.

## Files

| File | What |
|---|---|
| [docs/craft.md](docs/craft.md) | What good looks like: the whole, story, picture, motion, sound; the brief |
| [STYLE_PRESETS.md](STYLE_PRESETS.md) | 13 worked examples of named looks (what each stands on, palette, type, motion, KIT) and how to design a look of your own |
| [docs/motion-design.md](docs/motion-design.md) | Motion language: easing, camera, transitions, type, readability |
| [docs/music-and-sound.md](docs/music-and-sound.md) | What a good score is, the score module (`music.script`) and its timeline, sfx, pacing, mix |
| [docs/music-spec.md](docs/music-spec.md) | The older pattern spec (layers, lead, parts) the preset examples use |
| [docs/narration-and-subtitles.md](docs/narration-and-subtitles.md) | Voices, writing for the ear, captions |
| [docs/runtime-api.md](docs/runtime-api.md) | The runtime API |
| [docs/three-d.md](docs/three-d.md) | Canvas or three.js per shot; three.js directed in numbers (model, materials, light, camera, springs), surfaces with maps, HDRIs and models, and checked |
| [docs/iso-figures.md](docs/iso-figures.md) | Isometric machines that explain by working (the anatomy kit on Canvas): when to use one, scope, building it, motion as a function of time |
| [examples/take-your-time](examples/take-your-time/BRIEF.md) | A three-minute piece and its brief |
| [docs/tech-selection.md](docs/tech-selection.md), [docs/prompt-templates.md](docs/prompt-templates.md) | Why this stack; prompts people have used (for users) |
