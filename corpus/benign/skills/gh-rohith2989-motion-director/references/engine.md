# The engine

A film is a web page whose every pixel is a pure function of time. Headless Chrome poses it at exact times,
screenshots each (sub)frame, averages shutter samples in linear light (real motion blur) and pipes frames to
FFmpeg as a lossless FFV1 master. Sound is declared by the picture (cues) and synthesized in Python.

```
comp/
  config.json          width, height, fps, duration, bpm, gridOffset, shutter, finish, narrated
  index.html, main.js  entry (loads vo.json if narrated, imports scenes/index.js, boots)
  core/                runtime (scene, cue, cut, bar, beat, renderAt), anim (h, css, clamp, lerp, keys…),
                       ease (expoOut, quintOut, inOutSoft, heavyInOut, spring…), rand (seeded), fx (grain)
  sys/                 reusable motion systems (below)
  scenes/              the film: one module per section, listed in scenes/index.js
  css/                 theme.css (the subject's tokens + fonts) and base.css (engine classes)
  data/                vo.json (narrated films)
tools/   render.js · probe.js · server.js · sheet.py · strip.py · assemble.py · ff.py
audio/   synth.py · inst.py · sfx.py · score.py (+ score_plan.json) · mix.py · analyze.py
voice/   tts.py · cast.py · align.py · vo_build.py   (+ script.txt, style.txt, hints.txt, vo_plan.json)
review/  watch.py · listen.py
```

## The scene contract
```js
import { scene, cue, cut, bar, beat, W, H, FPS } from "../core/runtime.js";
scene({
  id: "s03", start: bar(8), end: bar(12) + 0.6, z: 30,         // z orders scenes; later sections on top
  samples: (lt, t, s) => (t < s.start + 1 ? 10 : 2),            // motion-blur samples this scene needs at t
  build(root, s) {                                              // once, after fonts load, while laid out
    s.title = h("div", { class: "abs t-hero" }); root.append(s.title);
    s.rect = offsetIn(s.title, root);                            // MEASURE HERE, never in update()
    cue(bar(8) + 0.95, "panel");                                 // sounds are declared by the picture
  },
  update(lt, t, s) { /* pose EVERYTHING this scene owns for time t; no state from previous frames */ },
});
```
- `bar(n)` / `beat(n)` put events on the music grid (`config.bpm`, `config.gridOffset`). Sections start on bars.
- `cut(t)` marks a hard cut so shutter samples never blend across it (scene edges count unless `softEdges`).
- `cue(t, type, params)` → `audio/cues.json` (via `node tools/probe.js 0 "window.getCues()"`) → `audio/mix.py`.
- The runtime shows a scene only inside `[start, end)`. Overlap scenes to transition (the incoming one on top).

## Systems (comp/sys)
| Module | What | Key calls |
|---|---|---|
| `reveal.js` | word/letter mask reveals | `new Words(el, ["Line *accent*"]).in(t0,{stagger,dur}).out(t1)`, `.update(t)`; `Letters` |
| `cam.js` | camera keys, world→screen, blur from speed | `camAt(t, keys)`, `camTf(c)`, `toScreen(c,x,y)`, `camSpeed`, `samplesFor`, `track` |
| `cursor.js` | a pointer with intent (arcs, hand, dips) | `createCursor(layer,{scale})`, `.at/.to/.click/.hand/.show`, `.update(t, map)`, `.speed(t)` |
| `type.js` | human typing schedules + key sounds | `schedule(text, t0, {cps, until})`, `typedAt(s,t)`, `keyCues(s)`, `caretOn(s,t)` |
| `stage.js` | backgrounds and the panel grammar | `stage("page"/"soft"/"ink"/"brand"/"night"/"dawn")`, `slideIn`, `recede`, `panelTf`, `circleWipe`, `maskReveal` |
| `light.js` | living light (drifting pools) | `livingLight(parent, {base, colors, count, speed})` |
| `particles.js` | dust, bokeh, sparks (seeded, wrapping) | `particles(parent, {n, size, speed, color, opacity})` |
| `ui.js` | press, hover, enter, spinner, checks, count-ups, callouts | `pressScale`, `hoverAt`, `enter`, `drawnCheck`, `countUp(el,t,t0,d,a,b,fmt)`, `createCallout` |
| `chart.js` | bars, lines, donuts | `barChart({values, labels, highlight})`, `lineChart`, `donut` |
| `highlight.js` | marker underline, spotlight, glow ring | `withHighlight(text, phrase)`, `setHighlight(hl,u)`, `spotlight(els, keep, k)`, `glowRing` |
| `window.js` | browser / app windows, window poses | `browserWindow({x,y,w,h,url})`, `appWindow`, `poser(el)`, `slideX` |
| `morph.js` | one card morphing through screens | `createMorph(frameEl, cards, steps)` |
| `rig.js` | layout measuring | `offsetIn(el, root)`, `windowRig` |
| `vo.js` | the voice clock | `w(line, "word")`, `wEnd`, `say0`, `say1`, `lineOf` |
| `captions.js` | word-synced captions | `captionsScene({ phrases, skip })` |
| `logos.js` | 3,400+ brand marks (simple-icons) | `await loadLogos(["hubspot","stripe"])` in build, `brandMark`, `appTile`, `creamTile` |

CSS classes in `base.css`: `t-mega/t-giant/t-hero/t-title/t-cap/t-label`, `acc` (accent), `fill`, `abs`, `tab`
(tabular), windows (`win`, `win-bar`, `win-url`, `win-body`), `cap`, `hl`, `co-pill`, chart classes.

## Pattern: a product walkthrough world (windows + camera + cursor)
```js
const world = h("div", { style: { position: "absolute", left: 0, top: 0, width: `${W}px`, height: `${H}px`, transformOrigin: "0 0" } });
const screen = h("div", { class: "fill", style: { zIndex: 40 } });          // cursor + click rings: screen space
const B = browserWindow({ x: 190, y: 140, w: 1540, h: 900, url: "app.example.com/onboarding" });
world.appendChild(B.el);  /* build the real UI into B.body; measure targets with offsetIn(el, world) */
const CAM = [[0, { x: 960, y: 590, z: 0.88 }], [6.3, { x: rName.cx, y: rName.cy + 60, z: 1.6 }], /* … */];
const cur = createCursor(screen, { scale: 1.5 });
cur.show(5.9, 19.6).at(5.9, x0, y0).to(5.95, 6.32, rName.x + 210, rName.cy).click(6.35);
// update(t): world.style.transform = camTf(camAt(t, CAM)); cur.update(t, (x, y) => toScreen-mapped {x, y})
```
- Keep close-ups inside the window: clamp each key's centre so `[x ± 960/z, y ± 540/z]` stays in the window.
- Scroll long pages by translating the page content (a scroll track with keys), and settle the scroll
  before a click lands; compute click targets at the scroll value of the click time.
- Window poses (`poser`) are pure functions pushed per chapter: the first that answers for `t` wins, else rest.
- App switch: the second window slides in from the right (`slideX`), camera re-frames on it.

## Pattern: voice-keyed events (narrated films)
`config.narrated: true`, `comp/data/vo.json` from `voice/vo_build.py`, then key everything to words:
```js
import { w, wEnd } from "../sys/vo.js";
const T = { slack: w(2, "slack"), allow: w(2, "allow") + 0.04, hl0: w(3, "your") - 0.05, hl1: wEnd(3, "acme") + 0.15 };
```
Highlights sweep across the words' span; typing fits between two words (`schedule(text, t0, { until })`); a
page appears on the verb that causes it. Moving a line in `voice/vo_plan.json` moves its pictures.

## Pattern: card morph (one object through a multi-step flow)
Render each step's card content absolutely at its own position; one frame element draws the card. At build,
record each card's rect; `createMorph(frame, cards, [[t1, 0, 1, 0.7], [t2, 1, 2, 0.7]])` interpolates the frame
rect and clips the contents to it while they cross-fade (outgoing 0.2 s, incoming from +0.1 s, rising 10 px).

## Pattern: cutdowns and re-edits by time-remap
To make a short version of a finished film (e.g. 0:00–1:09 + 2:19–2:35): cut on section boundaries; render
only the *bridge* (≈1 s) on a second entry page that loads the two scenes (`?only=s08,s15`) and overrides
`window.renderAt` to pose the second scene at `t + offset` on top of the first; splice master ranges + bridge
by frame index; regenerate the score on the new timeline (same plan, remapped bars) and remap the cues.
Verify the joins: frame-to-frame mean difference across each splice ≈ the film's normal frame difference.

## Rendering
```bash
node tools/render.js --stills 1,4.5,8 --dir renders/stills/a [--blur] [--query only=s02]
node tools/render.js --scale 0.5 --sub 1 --workers 4 --out renders/preview.mkv      # ~0.03 s/frame
node tools/render.js --workers 4 --out renders/master.mkv                           # ~0.2–0.4 s/frame with blur
node tools/render.js --from 11.5 --to 20.5 --out renders/fix.mkv                    # re-render a range
```
- Chrome comes from puppeteer (or `CHROME_PATH`), FFmpeg from ffmpeg-static (or `FFMPEG_PATH`).
- Workers render contiguous chunks; chunks are concatenated losslessly. Browsers are closed hard (a stuck
  close once held a finished render for minutes).
- Live scrubbing: `npm run serve` → `/comp/index.html?debug&t=12.5` (space = play, ←/→ = frame, shift = 1 s).
- Upgrade path if you ever need it: Chrome's `HeadlessExperimental.beginFrame` with `--deterministic-mode`
  runs one layout→paint→composite→screenshot atomically; the default `renderAt` + 2×rAF + screenshot is
  already deterministic for this engine.

## Determinism checklist
Seeded randomness only (`mulberry32`, `noise1`, `fbm1`) · ids are counters, never random · no `Date`/
`performance.now()` in scenes · fonts loaded before build (the runtime does it) · images decoded before use
(`waitFor`) · every element posed every frame · no CSS transitions/animations (time comes from `t` only) ·
layout measured at build · scene ranges overlap where a transition needs both.

## Performance
Prefer transforms and opacity; avoid animating layout properties on large trees (width animations are fine on
small elements). Large blurs (`filter: blur`) are expensive — bake them into radial gradients. Keep DOM per
scene modest; hide what isn't on screen. Motion blur cost = samples per frame: give `samples` only where
motion is fast.
