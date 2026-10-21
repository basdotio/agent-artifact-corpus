# Tech selection

> Status: decided · Last verified: 2026-10-02 · Owner: video-gaga

**Decision: build on plain Canvas 2D and a small zero-dependency runtime. Headless Chromium (Playwright) renders frames in parallel, ffmpeg (libx264) encodes them, Edge TTS provides narration, and a seeded arranger scores the video on the same beat grid, played by a General MIDI SoundFont through spessasynth_core. three.js is the supported route to 3D inside a composition (imported from a pinned CDN); GSAP and anime.js stay optional. None of them is required.**

## What we need

A coding agent writes one HTML file. We turn that file into a correct MP4 with:

1. **Determinism and frame accuracy.** Frame *N* must be a pure function of `t = N / fps`. That lets us seek to any frame, render out of order, and split the timeline across workers.
2. **Agent ergonomics.** It should be plain web tech the model already knows well, with no build step. A mistake should throw a readable error, not produce a silently wrong frame.
3. **Free and open source,** usable by companies of any size.
4. **Audio.** Narration has to drive the timeline, and we need to mix voice and music and mux them.
5. **Light dependencies.** Node, Chromium and ffmpeg. Nothing else.

## Candidates

| Option | Determinism / frame accuracy | Speed (1080p) | Dependency weight | Agent ergonomics | License | Audio |
|---|---|---|---|---|---|---|
| **Canvas 2D + own runtime + Playwright → ffmpeg** (chosen) | ✅ Exact. We call `drawFrame(n)` and nothing runs between frames | ≈50 ms/frame PNG, ≈14 ms JPEG per page. Scales linearly with parallel pages (see benchmark) | Playwright (Apache-2.0) and ffmpeg | ✅ The model already writes Canvas code. One HTML file, no build | MIT (ours) + Apache-2.0 + LGPL/GPL ffmpeg binary | ffmpeg filtergraph: adelay, amix, sidechain ducking, loudnorm |
| DOM/CSS + page screenshots (timecut/timesnap, puppeteer-screen-recorder) | ⚠️ timecut virtualises time, but CSS animations and transitions are hard to seek exactly. Screen recorders are real-time and drop frames | `page.screenshot` JPEG ≈21 ms, PNG ≈200 ms | Puppeteer | Good, but DOM layout and fonts can shift between frames | BSD-3 / MIT. timecut was last published in 2022 | none built in |
| **WebCodecs VideoEncoder + Mediabunny** (in-page encoding) | ✅ You encode exactly the frames you draw | Fast (hardware encoder) | Mediabunny (MPL-2.0). `mp4-muxer` is deprecated in favour of it | Medium: async encoder queue, codec strings, backpressure | MPL-2.0 | Needs AudioEncoder, or muxing afterwards |
| **Remotion** | ✅ Frame-based React (`useCurrentFrame`) | Good, with parallel rendering | React + bundler, heavy | Good, and it has official agent skills | ❌ **Not free for companies with 4 or more people.** Company License from remotion.pro | Excellent |
| **HyperFrames** (HeyGen) | ✅ Seekable HTML/GSAP compositions | Good | Node ≥ 22, a large CLI plus 21 skills | Built for agents | Apache-2.0 | Yes |
| **Motion Canvas** | ✅ Generator-based timeline | Good | Vite project and editor | Medium: its own scene/generator DSL | MIT | Yes, in the editor. Last npm publish was Feb 2025 |
| **Revideo** (Motion Canvas fork) | ✅ | Good, headless | Vite + renderer packages | Medium | MIT | Yes |
| **GSAP** (animation library only) | ✅ when paused and seeked with `tl.seek(t)` | n/a | 1 file | The model knows it well | "Standard no-charge" license: free, including commercial use | n/a |
| **anime.js v4** (animation library only) | ✅ with `seek()` | n/a | 1 package | Good | MIT | n/a |
| Theatre.js / Lottie | Theatre: seekable, needs a studio UI to author. Lottie: seekable, needs AE/JSON authoring | n/a | medium | Poor for text-first agents | Apache-2.0 / MIT | n/a |

### Verified facts (with sources)

- **Remotion.** Free for individuals, non-profits and for-profit companies with up to 3 people. Once 4 or more people work on the Remotion code for a project, you need a paid Company License (Creators seats; Automators ≥ $100/mo for prompt-to-video products; Enterprise ≥ $500/mo). [remotion.dev/docs/license/faq](https://www.remotion.dev/docs/license/faq) · [remotion.pro/license](https://www.remotion.pro/license) · npm license field: `SEE LICENSE IN LICENSE.md` (v4.0.529).
- **GSAP.** Since 2025-04-30, all of GSAP, including the former Club plugins (SplitText, MorphSVG, …), is free under Webflow's "Standard 'No Charge' License", commercial use included. The only notable restriction: you may not use it in a visual, no-code animation builder that competes with Webflow. [gsap.com/community/standard-license](https://gsap.com/community/standard-license/) · [webflow.com/updates/gsap-becomes-free](https://webflow.com/updates/gsap-becomes-free) · npm `gsap@3.15.0`. Because video-gaga is itself an animation-authoring tool, **we do not bundle GSAP**. A user can still use it inside their own composition.
- **anime.js.** v4.5.0, MIT (npm).
- **mp4-muxer.** v5.2.2 (MIT) is deprecated by its author in favour of **Mediabunny** (v1.60.0, MPL-2.0). [vanilagy.github.io/mp4-muxer](https://vanilagy.github.io/mp4-muxer/) · npm.
- **Motion Canvas.** `@motion-canvas/core@3.17.2`, MIT, last published 2025-02-16. **Revideo.** `@revideo/core@0.11.0`, MIT. The team now focuses on its commercial Midrender product. [github.com/midrender/revideo](https://github.com/midrender/revideo) · [midrender.com/revideo](https://midrender.com/revideo).
- **HyperFrames.** `hyperframes@0.8.80`, Apache-2.0, Node ≥ 22, HTML + seekable animations → MP4, and ships agent skills. [github.com/heygen-com/hyperframes](https://github.com/heygen-com/hyperframes). This is the closest alternative. See the section "Why not HyperFrames" below.
- **Playwright** `1.63.0` and **Puppeteer** `25.12.0` are both Apache-2.0.
- **edge-tts** `7.2.8` is LGPLv3; `srt_composer.py` is MIT. We call it as an external tool and do not vendor it. [github.com/rany2/edge-tts](https://github.com/rany2/edge-tts)
- **ffmpeg** is LGPL/GPL. Builds with libx264 are GPL. We invoke the user's installed binary and do not redistribute it.

### Local benchmark (Apple Silicon, 12 cores, Chromium 153 headless shell, 1920×1080 busy frame)

| Capture method | ms / frame | bytes / frame |
|---|---|---|
| `canvas.toDataURL('image/jpeg', .95)` | **13.5** | 240 KB |
| `canvas.toDataURL('image/png')` | 49.7 | 2.0 MB |
| `page.screenshot({type:'jpeg'})` | 20.7 | 169 KB |
| `page.screenshot({type:'png'})` | 199.7 | 756 KB |
| CDP `Page.captureScreenshot` png `optimizeForSpeed` | 66.9 | 1.7 MB |
| `getImageData` → base64 raw RGBA | 96.6 | 8.1 MB |

Capturing from the canvas beats page screenshots, and it also guarantees the output is exactly the canvas: no DOM chrome and no device-pixel scaling. Six parallel pages give roughly 6× throughput. A 12 s 1080p video renders in about 10–20 s with lossless PNG transfer.

WebCodecs check in the same headless shell: `avc1.640028` (H.264 High) is supported on macOS, `avc1.42001f` (Baseline) is not, and VP9/AV1 are supported. `VideoEncoder` exists only in a secure context, and `about:blank` is not one. Encoder availability depends on platform and build. **That platform variance is the main reason we keep libx264 in ffmpeg as the single encoding path.**

## Decision details

1. **Rendering: Canvas 2D first.** Text, shapes, gradients, clipping, filters (`ctx.filter`), `letterSpacing` and `OffscreenCanvas` all run in headless Chromium. A composition may create its own WebGL/WebGL2 context for shaders and `drawImage()` it onto the 2D canvas. SwiftShader is enabled as a headless fallback.
2. **Runtime: `runtime/video-gaga.js`,** one file, MIT, about 900 lines. It provides the scene timeline, transitions between offscreen buffers, easing (`cubic-bezier` and closed-form springs), keyframes, a seeded PRNG and noise, CJK-aware text layout, captions, and a preview player. We chose a small in-house runtime over GSAP or anime.js because the model then needs only one mental model: *draw(ctx, t) is pure*. It also avoids GSAP's competing-tool clause and keeps the skill at zero dependencies.
3. **Capture and encode.** N Playwright pages each take a contiguous frame range. They call `drawFrame(n)` and `toDataURL('image/png')`, and pipe the images into their own `ffmpeg -f image2pipe … libx264` segment. The segments are then joined with the concat demuxer (`-c copy`). Colour is converted explicitly with `scale=out_color_matrix=bt709` and tagged BT.709. Optional motion blur renders sub-frames and blends them with `tmix`.
4. **Audio.** Edge TTS runs once per scene segment with `boundary="WordBoundary"`. edge-tts ≥ 7 defaults to `SentenceBoundary`, and the CLI has no flag to change it, so we use the Python API. The runtime reads the real durations and places each scene so that `scene.duration = voiceDelay + speech + tail`. The renderer asks the runtime for the resolved timeline, then mixes the voice clips (`adelay` + `amix`), an optional music bed with sidechain ducking, and `loudnorm` to −16 LUFS. Everything is muxed as AAC 48 kHz.
5. **Subtitles.** Cues are built inside the runtime from word timings aligned to the original script text, so the burned-in captions and the exported SRT/VTT come from the same data. We burn in by drawing on the canvas, not with ffmpeg's `subtitles` filter. That filter needs libass, and the Homebrew ffmpeg 8.1 on the dev machine has neither `subtitles` nor `drawtext`. Drawing on the canvas also lets captions follow the preset's typography. A soft `mov_text` track is optional.

6. **3D: three.js, imported per composition.** `three@0.186.1` (MIT) is ESM-only, so a composition imports it through an import map pointing at a pinned jsdelivr URL. That works from `file://` in a normal browser (cross-origin modules with CORS) and in the renderer, with no install or bundling. `CV.three()` shares one `WebGLRenderer` across scenes and composites it onto the 2D frame. Verified on the dev machine: headless Chromium 153 renders it with SwiftShader, two pages rendering the same frames in shuffled order produce identical hashes (shadows + MSAA on), and a 1080p frame costs about 30 ms. We don't vendor three (1.2 MB) because fonts already need the network, and pinning the version keeps renders reproducible. Reflections come from a studio built in code (`gl.studio`: emissive panels placed in degrees, prefiltered with `PMREMGenerator.fromScene`), which is deterministic in SwiftShader too and lets a composition direct a glint; rebuilding it costs about 0.3 s per 1080p frame, so only a moving strip rebuilds it.
7. **Isometric figures: the anatomy kit's geometry, painted on Canvas.** [anatomy](https://github.com/wheresryan22/anatomy) (MIT) builds explanatory machines from solid parts as SVG path strings. Its geometry modules (`kit/iso-kit.mjs`, `lathe.mjs`, `tube.mjs`) are pure math with no DOM, so a composition imports them from jsDelivr pinned to a commit (CORS, works from `file://` like three.js), and `CV.iso` paints the strings with `Path2D` in the kit's order and tones, about 80 lines in the runtime. The frame stays a pure function of time: anatomy's live loop (per-frame springs, rAF, IntersectionObserver), its SVG pages and its `canvas-painter` (built for its interactive 3D mode) stay out. Drawing an `<svg>` per frame into an `Image` was rejected: decoding is asynchronous inside a synchronous `draw`, and every moving part would re-rasterise the whole figure. Verified on the dev machine: the dial-indicator example renders identically in shuffled order across pages, 378 frames at 1080p in about 9 s.
8. **Music: a score written per video and rendered in Node (`scripts/music.mjs`), played by sampled instruments (`scripts/soundfont.mjs`).** Bundling recorded music raises licensing questions, and an online generator adds cost, latency and non-determinism. Instead, the agent writes each video's score as a small module (`music.script`) that reads the timeline the runtime already resolves (scene boundaries snapped to the beat, every spoken word, sound effects) and places every note; the older pattern spec is arranged into notes from the same timeline. Either way, [spessasynth_core](https://github.com/spessasus/spessasynth_core) (Apache-2.0, pure JS + a WebAssembly Vorbis decoder) renders them offline from MuseScore General, an MIT-licensed General MIDI SoundFont (downloaded once, pinned by SHA-256). Our own Freeverb-style reverb, tempo-synced delay, ducking, bus compression and a look-ahead limiter finish the mix into a 48 kHz float WAV. It is deterministic, renders a 30 s score in 2–3 s, and the CLI measures the result (voice/music balance from separate stems, sync on the voice stem, mix balance per bus). The first version used raw oscillators only (band-limited saws, FM keys, Karplus–Strong plucks, noise drums): fully self-contained, but it sounded like a toy, and a vibrato bug made its sustained pads drift by more than an octave. That synth remains as the fallback when the samples can't be downloaded. The parts a score leans on most (piano, strings, harp) later moved to multi-sampled recordings (`scripts/samples.mjs`: Salamander Grand Piano, CC BY 3.0; VSCO 2 CE, CC0), fetched per note so a score downloads only what it plays, and the small sound effects to real CC0 recordings (`assets/sfx`), because a General MIDI piano and synthesized ticks were what made scores sound cheap. Since the CLI can't listen, it measures the failures listeners named (a ghostly, washed-out stretch, a buried melody, a flat score, effects lost or jumping out) from the rendered audio. We considered the browser's `OfflineAudioContext`, but its output isn't guaranteed bit-identical across Chromium builds and it would tie audio to a page. The trade-off is taste: a rule-arranged score is simpler than a composed track, so `--music track.mp3` remains for flagship pieces.

## Why not …

- **Remotion.** Excellent, but the company license conflicts with the goal of free and open source for everyone, and it adds a React build toolchain.
- **HyperFrames.** Open and agent-oriented, but it centres on DOM/CSS with GSAP, needs Node ≥ 22, and is a large framework. video-gaga instead aims to be a *single-file, zero-build skill*, in the spirit of frontend-slides. Frames are drawn directly on Canvas, so the pixels are identical on every machine, and the skill ships free narration and CJK subtitles in the box.
- **WebCodecs + Mediabunny.** Attractive (no ffmpeg for video), but the codec support differs by platform and headless build, it adds an MPL dependency, and we still need ffmpeg for audio mixing and loudness normalisation. We may add it later as an optional `--encoder webcodecs` fast path.
- **Motion Canvas / Revideo.** Good engines, but they bring their own DSL and a Vite project, and upstream maintenance has slowed.
