# The figure API contract

Every topic figure exposes one global, `window.<api>` (name in `topic.config.json` → `figure.api`). The page runtime,
the film scene and the gate all drive the figure through it, so a figure that honours it plugs into everything.

## Methods

| method | meaning | used by |
|---|---|---|
| `set(settings, { snap, restart })` | change model settings; parts ease to them (`snap: true` = no easing). Partial updates keep the rest. Returns `get()`. | page, lab, film (`snap`) |
| `get()` | readable state: `{ settings, t, rate, T, state, run, ... }` (`state` = `stateAt(run, t)`; `state.y` is the headline quantity) | instruments, readouts, gate |
| `play()` / `pause()` | run / stop the model clock | page |
| `tour(on)` | the idle tour (loops when nobody touches it); the film turns it off | page, film |
| `onChange(fn)` → unsubscribe | called after every rendered change with `get()` | page instruments |
| `clock({ manual: true })` | frame-exact mode for video: nothing moves except on `advance` | film |
| `advance(ms)` | step everything (model, camera, focus fades) by ms in ≤ 1/60 s substeps, then render | film |
| `view({ region, zoom, dx, dy, shift }, { ms, ease })` | the virtual camera: all SVG layers' viewBox and the WebGL camera move together. `zoom > 1` goes closer; `shift` moves the subject left (0.17 when the instrument panel is on the right); `ms` 0 = cut | page steps, film shots |
| `focus(region, { ms })` | the spotlight: items outside the region fade toward a **mid-grey fog** (`--fk` 1 → 0.45); `null` = everything full | page steps, film |
| `frame({ aspect })` | `16/9` for the film: the full shot widens around the figure (full-bleed, no card), regions reframe | film |
| `regions`, `camera` | the screen rects of the regions, the current camera rect | debugging |
| topic extras | e.g. `time(t)` (pose model time exactly), `release()`, `rate(r)`, `restart()`, `pose(...)`, `shoot(...)`, `rays(...)` | film hooks, lab |

## What the kit gives you (figure/stage.js, inlined by `stageScript()`)

`XFigure({ root, stageEl, svgs, canvas, W, H, regions, project, step, render, get, set, tour, busy })` returns
`{ api, stage, run, clock }`: `api` already has set/get/play/pause/tour/onChange/clock/advance/view/focus/frame/regions/
camera. You write only:
- `step(dt, { playing, touring, t })`: advance your model time;
- `render()`: write attributes / live-slot SVG for the current state (never rebuild static art);
- `get()`, `set(s, opts)`, optionally `tour(t)` and `busy()` (keeps the rAF loop alive, e.g. while parts ease).
Then `window.<api> = Object.assign(api, { time, release, rate, ... })`. The scaffold's `figure/live.js` is a working
example. `XStage` alone (camera + focus + frame) exists for figures that keep their own loop (the five hand-built
ones have the same logic inline).

## Regions

`subject.mjs` exports `REGIONS` as world boxes `[x0, y0, z0, x1, y1, z1]` (projected, padded 8 %, fitted to the frame's
aspect). A region given as a **function** returning a box follows a moving subject (camera-lens's candle). `whole` is the
full frame and always exists. Name regions after what the narration talks about (`lens`, `sensor`, `escapement`),
because the timeline and the explainer steps use the names.

## Focus groups and the fog

Every drawn item is wrapped `<g class="it" data-sys="a b" data-mat="steel">`; `SYS` in `subject.mjs` maps region
names to item-name patterns, and an item belongs to every region whose pattern matches. `focusCss(root)` (build-helpers)
writes the colour-mix rules: under `[data-focus]` every token of an item mixes with `--xs-fog` by its `--fk`. Fog is
`#d3d2ce` in light and `#2b2b2d` in dark: the rest loses saturation and contrast and recedes, the focused part becomes
the most contrasty thing in the frame. Never fade toward the paper/white (the first crumple-zone and the pendulum-clock
weight shot: white-on-white; the gate's contrast check now fails it). WebGL layers fade with the focus too (`canvas`,
`glFull` lists regions in which the canvas stays full).

## Materials

`materialCss(root, { steel: { light: { paper, top, shade: [4 tones], line }, dark: {...} } })` gives items with
`data-mat` their own four tones. Use real material colours (painted body, dark steel, brass, rubber, concrete) with the
light theme designed first; the subject stays the lit part.

## Live slots

Moving parts are drawn in the slot where they physically sit in the painter's order: `put('subject.pin', at, '<g
data-live="pin">…</g>', shapes, { slot: 'pin' })`. `liveSvg(k, P, L, slot, state)` returns the slot's SVG for a model
state; it runs in Node for the rest pose (recorded for the audit) and in the page each frame (with the kit functions in
`K`). Parts that only translate are built once in Node (`L` = `DATA.live`) and moved with `translateAlong`. Record the
true shape at rest; list items whose drawing legitimately reaches past their shape in `cover` (e.g. a thread).

A machine display drawn glyph by glyph (odometer drums, a punched counter) puts its whole value on the group as
`data-value="1.30 × 10^122"`: the readouts gate reads `[data-value]` in the figure instead of the separate digits.

## Files

`node figure/build.mjs` writes `<name>.html`, `<name>-light.html` (standalone, for review and the line check) and
`<name>(-light).fragment.html` (embedded by the page and the film; the film uses the light one). The fragment's root is
`<div class="iso" id="<id>">` with the anatomy plate inside; the stage element carries `data-stage`, which the film's
full-bleed CSS targets (it hides the plate's corners, legend and caption).
