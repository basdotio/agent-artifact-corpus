# video-gaga

**Describe a video, get a motion-designed MP4.** video-gaga is an agent skill for Claude Code and other coding agents. The agent asks you a few sharp questions, shows you style frames, writes the storyboard, and then designs every shot in HTML Canvas or three.js, picking the engine shot by shot (three.js where form, material or depth is the point). It renders them frame-exactly, scores them with generated music on the same beat grid as the cuts, and adds free Edge TTS narration and subtitles.

[中文说明 →](README.zh-CN.md)

<p align="center">
  <img src="docs/media/studio-3d.gif" width="49%" alt="Studio 3D preset">
  <img src="docs/media/clear-explainer.gif" width="49%" alt="Clear Explainer preset">
</p>

- **Canvas, deterministic.** Each frame is `draw(ctx, t)`, a pure function of time. It renders in parallel headless Chromium pages, is encoded with ffmpeg (H.264, BT.709) and comes out frame-exact.
- **The voice is the clock.** Microsoft Edge neural voices (free, no API key, 300+ voices, strong Chinese) with **word-level timestamps**. Scene lengths come from the speech, and visuals land on the words (`s.when('forty')`, or `fx.wordReveal({ sync: s })` for a headline that appears as it is said).
- **Music on the same beat.** Every video gets its own score, composed by the agent as one piece of music and written note by note in a small score module (`music.script`) that reads the video's timeline: its scenes, every spoken word and the beat grid. It has its own form and a theme that comes back, underscores the voice, and meets the picture only where the story turns, not on every action. Cuts land on the beat, and every line starts on an eighth note. The score dips under the voice, the tune steps back further, and the last chord rings out with the final frame. Sound effects are few and real (recorded, CC0). The older pattern spec (layers switched by scene energy) still works and the preset examples use it. It is played by real instrument samples: a multi-sampled grand piano (Salamander, CC BY 3.0) and strings, upright piano and harp (VSCO 2 CE, CC0), with guitars, mallets, bass, brass and eight drum kits from an MIT-licensed General MIDI SoundFont, rendered offline and deterministically; samples download once on first use. The render measures what ears would catch: a ghostly stretch, a buried melody, a flat score, effects lost or too loud.
- **Room to breathe.** Narration is not wall-to-wall: music-only pre-rolls, held beats before the payoff, end cards that ring out (`beats: 6`, `narration: false`).
- **Real transitions and exits.** 22 transition types (whip, stripes, split, iris, ink, cube, light leak, …), each with its natural sound, plus exit choreography so cuts happen on action. A 3D bridge (`CV.three`) uses three.js for product turns, exploded views and globes, with deterministic WebGL. Every three.js shot gets real surfaces: `gaga asset find` / `gaga asset` pull CC0 HDRIs, scanned PBR sets and models from Poly Haven, and `gaga texture --prompt` has Codex generate a one-of-a-kind albedo (or a matcap) and derives normal, roughness and ao from it.
- **Subtitles done properly.** Cues are built from the same word timings. CJK line breaking follows kinsoku rules, and long lines split into balanced chunks. Captions are burned in with the video's own typography (or karaoke-highlighted) and also exported as `.srt`, `.vtt` or a soft track.
- **Designed, not generated-looking.** Thirteen distinct motion-design presets, two of them in 3D, plus a written motion-design guide covering easing, timing, hierarchy, camera, transitions, sound and anti-patterns. The agent follows it and checks its own probe frames against it.
- **Asks before it builds.** 4–7 questions tailored to the video type. Each has three concrete options, one marked *recommended*, with the reason.
- **Verifies itself.** `gaga check` reports duration, fps, the audio track, loudness, caption overlaps, dead holds, glitches and flashing in the **picture**, **A/V sync** (speech onsets vs caption onsets, measured on the voice stem) and the **music/voice balance**. After a render it also checks that every voice clip starts where the timeline put it, including lines without a caption.
- **Free & open.** MIT. The stack is Node, Playwright (Apache-2.0), ffmpeg and edge-tts. It needs no Remotion license, no build step, and no account.

## Style gallery

Every example below was rendered by the skill's own CLI from the files in [`presets/`](presets/), music included. The GIFs are short excerpts; click through for the full video with sound (compressed 720p). Re-render them all with `npm run examples && npm run showcase`.

| | |
|---|---|
| <img src="docs/media/launch-keynote.gif" width="100%"><br>**Launch Keynote** · 16:9 · 24 s · 🔊 EN (AndrewNeural) · `keynote` score<br>A point of light opens the stage, the chip lights up on its spoken name (riser + one hit), specs count on the word, then a silent "thinking" beat match-cuts to the end card.<br>[▶ video](docs/media/launch-keynote.mp4) · [source](presets/launch-keynote/video.html) | <img src="docs/media/studio-3d.gif" width="100%"><br>**Studio 3D** · 16:9 · 27 s · 🔊 EN (AndrewNeural) · `keynote` score · three.js<br>A fictional speaker on a seamless sweep, in a real studio HDRI with a generated speckled-stoneware glaze and a scanned knit: camera arrive-push and orbit, an exploded view where each layer lifts on its word, colour-ways swapping on the beat.<br>[▶ video](docs/media/studio-3d.mp4) · [source](presets/studio-3d/video.html) |
| <img src="docs/media/clear-explainer.gif" width="100%"><br>**Clear Explainer** · 16:9 · 26 s · 🔊 ZH (YunxiNeural) · `explainer` score<br>A 30-year ruler builds in the pre-roll, an equation assembles on the words, the camera follows a compound-interest curve, and an iris opens from the final value into a music-only beat.<br>[▶ video](docs/media/clear-explainer.mp4) · [source](presets/clear-explainer/video.html) | <img src="docs/media/blueprint.gif" width="100%"><br>**Blueprint** · 16:9 · 29 s · 🔊 EN (AndrewNeural) · `kinetic` score<br>A cyanotype drawing of a four-stroke engine builds itself, cuts into section, names its parts, then runs with real kinematics, one stroke per beat.<br>[▶ video](docs/media/blueprint.mp4) · [source](presets/blueprint/video.html) |
| <img src="docs/media/data-globe.gif" width="100%"><br>**Data Globe** · 16:9 · 26 s · 🔊 ZH (YunyangNeural) · `ambient` score · three.js<br>A dot-matrix globe turns to each airport as it is named; arcs draw from Atlanta, numbers count on the word, and a wordless ranking beat makes the gap the point (ACI 2023 data).<br>[▶ video](docs/media/data-globe.mp4) · [source](presets/data-globe/video.html) | <img src="docs/media/editorial.gif" width="100%"><br>**Editorial** · 16:9 · 24 s · 🔊 EN (ChristopherNeural) · `documentary` score<br>The 1969 "LO" message as a magazine page: a masthead built over the pre-roll, a halftone map that prints, a teletype tape, a pull quote revealed word by word with the voice.<br>[▶ video](docs/media/editorial.mp4) · [source](presets/editorial/video.html) |
| <img src="docs/media/paper-sketch.gif" width="100%"><br>**Paper Sketch** · 16:9 · 24 s · 🔊 ZH (XiaoxiaoNeural) · `acoustic` score<br>Hand-drawn strokes that "boil" on threes, watercolour washes, page slides with a paper sound, a music-only bar where the drawing closes its loop.<br>[▶ video](docs/media/paper-sketch.mp4) · [source](presets/paper-sketch/video.html) | <img src="docs/media/swiss-kinetic.gif" width="70%"><br>**Swiss Kinetic** · 1:1 · 15 s · music only · `kinetic` score · motion blur<br>A 12-column grid, one red, every move on a 104 BPM beat, a 12-strip blinds cut, and a match cut where the square becomes the full stop.<br>[▶ video](docs/media/swiss-kinetic.mp4) · [source](presets/swiss-kinetic/video.html) |
| <img src="docs/media/neon-circuit.gif" width="45%"><br>**Neon Circuit** · 9:16 · 18 s · 🔊 ZH (YunjianNeural) · `synthwave` score<br>Night city and HUD, an RGB split only on hits, a terminal with a beat-blinking caret, a music-only "countdown armed" beat, glitch cuts with glitch sounds.<br>[▶ video](docs/media/neon-circuit.mp4) · [source](presets/neon-circuit/video.html) | <img src="docs/media/pop-collage.gif" width="45%"><br>**Pop Collage** · 9:16 · 20 s · 🔊 ZH (XiaoyiNeural) · `pop` score<br>Cut-paper stickers that land on the beat with springs, palette-coloured stripe transitions, karaoke captions, a music-only recap where three tips land one per beat.<br>[▶ video](docs/media/pop-collage.mp4) · [source](presets/pop-collage/video.html) |
| <img src="docs/media/pixel-retro.gif" width="100%"><br>**Pixel Retro** · 16:9 · 66 s · 🔊 ZH (YunxiNeural) · chiptune score, E dorian → G major<br>《隐藏关卡》, an 8-bit short about finding your voice. Every frame is painted on a 384×216 grid locked to 12 colours. The grey main quest resets every day and one status meter sits empty, the only colour on screen. Words collapse into dots, the player takes one step left, a wall breaks and colour floods in, everything they make becomes a brick, and the meter fills.<br>[▶ video](docs/media/pixel-retro.mp4) · [source](presets/pixel-retro/video.html) | <img src="docs/media/ink-wash.gif" width="100%"><br>**Ink Wash** · 16:9 · 76 s · 🔊 ZH (XiaoxiaoNeural) · felt piano, koto and flute score<br>别怕落笔, a story: a child's drawing gets a teacher's red cross, twenty years of copybooks fill with 正, then a brush trembles and a drop of ink seeps into the paper. It becomes the summit of a mountain, the painting grows a stroke per beat while the camera pulls out, and the red comes back as the painter's own seal.<br>[▶ video](docs/media/ink-wash.mp4) · [source](presets/ink-wash/video.html) |
| <img src="docs/media/cinematic-film.gif" width="100%"><br>**Cinematic Film** · 2.39:1 in 16:9 · 94 s · 🔊 ZH (XiaoxiaoNeural, YunjianNeural for the father) · 76 BPM E♭ major score (felt piano, music box, brushed kit)<br>《第三十六张》: a daughter finds a roll in her father's old camera with 35 of 36 frames shot. A print comes up in the darkroom and comes alive, the roll advances through 1999, the clear 36th frame sits on a lightbox, and on the same beach his shadow lifts the camera again before we pull back to the whole contact sheet.<br>[▶ video](docs/media/cinematic-film.mp4) · [source](presets/cinematic-film/video.html) | |

These presets are examples, not the menu. The agent builds each video's look from references it can name (a film, a studio, a print medium, an era), so you can ask for one by name ("like a riso zine", "上海美影的水墨动画", "a PC-98 adventure game") or hand it a frame, a clip or your own work to match. During style discovery it shows three directions, each standing on a different reference, previewed with your own title. A preset only sets the look and the motion grammar; the script, the scene structure, the choreography and the music are designed for each video. See [STYLE_PRESETS.md](STYLE_PRESETS.md).

### Longer videos

The presets show 15–30 s pieces. [`examples/take-your-time`](examples/take-your-time/video.html) (慢慢说) is a three-minute personal story in the Swiss Kinetic style: a man who stutters, the wall his words hit, and the wedding toast that took eight seconds to start (33 scenes in six chapters, two Chinese voices). It shows a chapter card and a corner tag per chapter, music-only breaths, a score whose harmony changes per chapter (`music.parts`), and motifs that come back: the red caret, the wall, the opening line. SKILL.md (*Useful numbers*) covers planning one. [▶ video](docs/media/take-your-time.mp4)

[`examples/first-level`](examples/first-level/score.mjs) (第一关) shows the score written as one piece: a mother tells how her seven-year-old drew her workday as a game level on graph paper. The [score module](examples/first-level/score.mjs) is 36 bars in F with its own form (piano alone on the page, the band when the drawing boots into a game, a D-minor bridge for the boss, the theme in full over the wordless montage, back to the piano at the turn, the theme home on a music box), and it meets the picture at four moments only. The whole film has three sound effects. [▶ video](docs/media/first-level.mp4)

## How it works

```
 you: "make a 30-second video explaining compound interest"
   │
   ├─ 1. Questions ── 4–7 × three options (one recommended, with the reason)
   ├─ 2. Style frames ─ 3 directions rendered with your real title, side by side on one
   │                    moodboard page (motion, palette, type, music direction) → you pick
   ├─ 3. Storyboard ── scene / what it adds / voice line (or music only) / focal point / sync word /
   │                    exit / transition / music energy · sfx
   ├─ 4. Build ─────── video.html (Canvas or three.js scenes) + narration.json
   │                    Edge TTS → word timings → scene lengths + caption cues
   │                    beat grid → cuts and voice onsets snapped to the music
   │                    gaga music → a score arranged from the timeline (+ sfx)
   │                    gaga still --sheet --phone → the agent reviews probe frames (text size,
   │                    contrast, a repeat render), fixes
   └─ 5. Render ────── N× headless Chromium → PNG → ffmpeg x264 segments → concat
                        voice clips (adelay/amix) + score → loudnorm → AAC
                        → out/video.mp4 + .srt + .vtt → gaga check (sync, balance, loudness…)
```

## Install

Requirements: **Node ≥ 18**, **ffmpeg** (with libx264) and **uv** (recommended) or Python with `pip install edge-tts`. Network access is needed for fonts and TTS.

### Claude Code

```bash
git clone https://github.com/chrishan17/video-gaga.git ~/.claude/skills/video-gaga
cd ~/.claude/skills/video-gaga && npm install
npx playwright install chromium        # only if you don't already have it
node scripts/gaga.mjs doctor             # checks everything
```

Then just ask: *"Use video-gaga to make a 15-second launch teaser for …"* (or type `/video-gaga`).

### Other agents (Codex, Gemini CLI, Cursor, OpenCode, …)

Point the agent at this repo and ask it to follow `SKILL.md`. Everything is plain files plus one CLI: `node scripts/gaga.mjs`.

## Usage

Things to try:

```text
Use video-gaga: a 20-second product teaser for "Halo", a smart desk lamp. Dark, premium, my brand color is #FF6A3D.
用 video-gaga 做一个 30 秒的知识讲解：为什么天空是蓝色的？要配音和字幕。
Make a 9:16 hype short for our hackathon on Oct 24 in Shanghai, with karaoke captions.
Kinetic typography of "Stay hungry, stay foolish", square, no voice.
```

### CLI

```bash
node scripts/gaga.mjs doctor                         # environment check
node scripts/gaga.mjs init my-video --preset clear-explainer [--ratio 9:16]
node scripts/gaga.mjs tts my-video                   # Edge TTS → build/narration.js (cached)
node scripts/gaga.mjs music my-video                 # the generated score → build/music.wav (the preview plays it)
node scripts/gaga.mjs still my-video --sheet --subs  # probe frames + contact sheet for review (--phone: at 390 px wide)
node scripts/gaga.mjs moodboard .gaga-previews/style-a .gaga-previews/style-b .gaga-previews/style-c --wait  # pick a style on one page
node scripts/gaga.mjs render my-video --subs burn    # → my-video/out/my-video.mp4 (+ .srt/.vtt)
node scripts/gaga.mjs check my-video/out/my-video.mp4 --srt my-video/out/my-video.srt
node scripts/gaga.mjs gif my-video/out/my-video.mp4 --width 480
node scripts/gaga.mjs voices --lang zh-CN
```

Render options: `--subs file|burn|soft|burn+soft|none` · `--music track.mp3` (a licensed track instead of the score, side-chain ducked) · `--no-music` · `--motion-blur 5` · `--scale 0.5` (draft) or `2` (4K) · `--from/--to` · `--workers` · `--format png|jpeg` · `--crf`.

Re-render every gallery example: `npm run examples`, then `npm run showcase` for the GIFs and posters.

### A composition in 20 lines

```html
<script src="build/narration.js"></script>
<script src="video-gaga.js"></script>
<script>
const { ease, fx } = CV;
CV.create({
  width: 1920, height: 1080, fps: 30, background: '#050506',
  music: {                                    // a score designed for this video + the beat grid
    bpm: 92, key: 'A', mode: 'minor', progression: [0, 5, 2, 6],
    layers: [
      { inst: 'epiano', notes: [0, 1, 2, 1], pattern: 'X.x.X.x.', vel: 0.12 },
      { inst: 'bass', kind: 'synth', octave: -1, pattern: 'XxXxXxXx', vel: 0.2, from: 0.3 },
      { inst: 'kick', pattern: 'X.........x.....', vel: 0.55, from: 0.4 },
    ],
  },
  subtitles: { style: { box: 'rgba(0,0,0,.6)' } },
  scenes: [{
    id: 'hook', voiceDelay: 1.3, energy: 0.4, // narration.json "hook" drives its length; a beat of music first
    draw(ctx, s) {
      ctx.font = '800 120px "Geist"'; ctx.fillStyle = '#fff';
      fx.wordReveal(ctx, 'Think ahead.', s.W / 2, s.H / 2, s.t, { sync: s, align: 'center', exit: s.out(0.4) });
      ctx.fillStyle = '#4D7CFF';
      ctx.fillRect(s.W / 2 - 300, s.H / 2 + 60, 600 * s.at(s.when('ahead'), 0.6, ease.enter), 6);
    },
  }],
});
</script>
```

Open it in a browser for a live preview player (Space, ←/→, scrubbing, narration audio). See [docs/runtime-api.md](docs/runtime-api.md).

## Docs

- [SKILL.md](SKILL.md) — the agent workflow: questions, style discovery, storyboard, build, verify, deliver
- [STYLE_PRESETS.md](STYLE_PRESETS.md) — the thirteen presets and how to design a custom one
- [docs/craft.md](docs/craft.md) — story, picture and the self-review loop the agent runs before delivering
- [docs/motion-design.md](docs/motion-design.md) — motion language: easing, principles, camera, transitions, type, mechanical checks
- [docs/narration-and-subtitles.md](docs/narration-and-subtitles.md) — Edge TTS voices, writing for the ear, caption rules
- [docs/music-and-sound.md](docs/music-and-sound.md) — what a good score sounds like and how to write one (`music.script`), the beat grid, sound effects, pacing and silence
- [docs/three-d.md](docs/three-d.md) — Canvas or three.js, decided per shot; a studio built in code, materials, light, camera and springs in numbers; how to check a 3D shot
- [docs/prompt-templates.md](docs/prompt-templates.md) — prompt patterns collected from X/GitHub (with sources) and ready-made templates
- [docs/tech-selection.md](docs/tech-selection.md) — why Canvas + Playwright + ffmpeg + Edge TTS + a sampled score + three.js (vs Remotion, HyperFrames, Motion Canvas, WebCodecs…)

## Credits

- Structure inspired by [zarazhangrui/frontend-slides](https://github.com/zarazhangrui/frontend-slides): show-don't-tell style discovery and anti-slop design rules, applied here to video.
- Narration by [rany2/edge-tts](https://github.com/rany2/edge-tts) (LGPLv3, used as an external tool) and Microsoft Edge's online TTS service. Check that the service terms fit your use.
- Rendering by [Playwright](https://playwright.dev) and [FFmpeg](https://ffmpeg.org). 3D by [three.js](https://threejs.org) (MIT, loaded from a pinned CDN by compositions that use it). Fonts from [Google Fonts](https://fonts.google.com) (OFL).
- Prompt patterns credited in [docs/prompt-templates.md](docs/prompt-templates.md).

## License

[MIT](LICENSE) © 2026 Chris Han
