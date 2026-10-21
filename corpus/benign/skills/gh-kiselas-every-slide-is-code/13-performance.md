# Performance

A deck runs on whatever laptop is plugged into the projector, often on battery, often with a second window open for presenter view. It must stay smooth there, and it must not burn a core while a slide just sits on screen.

## What the runtime already does

- **Idle slides cost nothing.** Once every build of the current step has finished and nothing read the clock, the frame loop skips rendering until the state changes. On the demo, a still chart slide went from ~470 ms of main-thread work per second to ~28 ms.
- **The stage redraws only when it has to**: when the camera moved, the canvas was resized, or the drawing reads `S.T`.
- **Layers are promoted to the GPU only while they move.** `will-change` is set on the two layers of a transition and cleared at the end; permanent promotion of every slide would cost memory.
- **Slides are isolated.** `contain: layout paint style` on each slide keeps a change on one slide from re-laying out the others; inactive slides are `display: none`.
- **Styles are written only when they change.** Builds cache the last value of opacity, transform, filter and clip.
- **Fonts and layout are warmed up before the first frame**, so the first transition does not stutter on a font swap or a first layout.
- **Resize is debounced to one frame.**

## Rules for deck code

1. **Never read layout inside `frame`.** `offsetHeight`, `getBoundingClientRect`, `getComputedStyle`, `getTotalLength` force a synchronous layout after the writes of the same frame. Measure once in `setup` (or in an animation's `init`) and keep the number. `Deck.pointAt` caches path lengths for this reason.
2. **Declare how long code-driven motion lasts.** `st.p(n, delay, dur)` tells the runtime when the motion ends. Motion driven by `st.since(n)` counts as active for `hook.active` seconds (default 4): set `active` on the slide spec to the real duration. Reading `st.T` or `st.life()` keeps the slide animating for as long as it is on screen, so use them only for real ambient motion.
3. **Set what changed, not everything.** In `frame`, write attributes that depend on `st`; static attributes belong in `setup`.
4. **Animate transform and opacity.** They are composited. Animating `width`, `height`, `top`, `left`, `font-size` or `box-shadow` triggers layout or paint on every frame. SVG geometry attributes (`height` of a bar, `d` of a path) are fine: they repaint only the SVG.
5. **Filters are paint-heavy.** `blur` builds, the `zoom` transition's blur and the `dissolve` SVG filter repaint the whole element every frame. Keep blurred elements small, and at most one filtered thing moving at a time.
6. **Keep the DOM per slide modest.** A few hundred nodes are fine; a thousand SVG points are not. For dense scatter plots or particle effects, draw into a `<canvas>` inside the slide.
7. **Big raster images: size them for 1920×1080.** A 6000-pixel photo scaled down costs decode time and memory on every transition.
8. **The stage is one full-screen draw.** Pre-render textures into a pattern once; never do per-pixel work in `draw`. If the stage reads `S.T`, it redraws every frame for the whole deck.
9. **`backdrop-filter` and large `box-shadow` on slide content** are expensive while layers move. Prefer a solid or semi-transparent fill.
10. **Presenter view runs the deck twice** (current and next). A deck that is borderline on one window will drop frames with presenter view open. Test with it open.

## Measuring

**In the browser**: open the deck with `?perf`. A small HUD shows the frame rate, how many frames per second were actually drawn (0 on an idle slide), the average and worst frame cost of the runtime's own work, whether the slide is idle, animating or in a transition, and the DOM size of the slide.

```
deck.html?perf#6.3
60 fps · drawn 0/s · 0.21 ms (worst 0.9) · idle · 45 nodes
```

If "drawn" stays at 60/s on a slide where nothing moves, something reads the clock (`st.T`, `st.life`, a stage that uses `S.T`) or a `since()` slide has no `active` limit.

**From the command line**:

```bash
node export/deck.mjs perf deck.html
```

For every step and every transition, it reports the median and worst main-thread cost of a frame (the runtime's script plus the style and layout it causes), the number of DOM nodes on screen and the number of elements with a live filter. Budget: under 8 ms (a warning above), never over 16 ms (an error: that frame misses 60 fps on its own). Paint and compositing are not in this number; filters and huge images show up in `?perf` on a real screen.

**Chrome DevTools, Performance panel**: record a transition with CPU throttling at 4×. That approximates an old office laptop.

## Rendering GIF and MP4 (`export/deck.mjs`)

`node export/deck.mjs mp4 deck.html part.mp4 --from 30 --to 40 --profile` prints the ten slowest frames by timecode (with slide and step) and the mean cost of a frame for every second of the timeline. The draw call of a deck is usually 1 to 5 ms; the capture is where the browser finishes the frame, so heavy filters, big blurs and large images show up there. On the demo, a GIF frame costs 1.4 ms of draw call, 68 ms of capture and 75 ms of GIF encoding.

What changed in the exporter, on the demo deck, seconds 0 to 10 at 1080p (best of three runs on a shared machine with 20 logical CPUs; the ratios matter, not the seconds):

| Step | MP4, 300 frames | GIF, 120 frames |
|---|---|---|
| before: `page.screenshot`, one process | 56.7 s | 15.1 s |
| CDP `Page.captureScreenshot` (`optimizeForSpeed`), still one worker | 40.5 s | 10.7 s |
| chunks on 4 browsers (the default), joined without re-encoding | 15.8 s | 6.4 s |
| `--draft`, 4 workers (half size, half frame rate, JPEG, x264 veryfast / 63-colour GIF) | 5.4 s | 4.4 s |
| `--draft`, 1 worker | 7.0 s | 4.5 s |

- **Workers are limited by the GPU, not the cores.** The default is `min(4, max(1, cpus / 4))`. On the machine of the sister project (every-frame-is-code) 6 workers were the best of 2 to 12; here every run competed with other processes, so measure `--workers` once on yours.
- **The output does not depend on the worker count.** Chunk boundaries are a function of the frame range only, so `--workers 1` and `--workers 4` produce the same frames in the same order. Checked on the first 4 seconds of the demo (MP4, GIF, and both with `--draft`) by comparing per-frame signatures (`--signatures`, `sigdiff`): 0 frames beyond tolerance. The frames themselves are not bit-identical from run to run, even with the same settings: the GPU rounds a few dozen pixels by 1 to 2 levels, and jumping straight to a time gives the same picture as playing up to it (checked at 16 points of the demo timeline, 0 to 138 pixels off by at most 2 levels).
- **A capture after `__draw` needs no extra wait** in this pipeline: waiting for one or two animation frames or 400 ms did not change how often two renders of the same time differed, so the rest-frame double `requestAnimationFrame` is kept only where the deck switches state with `show()`.
- **Start-up is a fixed cost.** Each browser loads the deck, lays out every slide and waits for the fonts: about 2 to 3 s here. That is why `--draft` gains less on a short range with many workers, and why `check` without `--timeline` uses one browser.
- **PNG vs JPEG capture.** Full-size PNG (lossless, the default for the final render) costs about 130 ms a frame in one worker; half-size JPEG about 45 ms. Both end up as H.264 4:2:0, so use `--draft` to iterate and the default for the cut.
- **The GIF encoder** stays single-pass per chunk, so each chunk starts with a full frame and a parallel GIF is a few KB larger per chunk than a serial one would be. Its palette is built from at most about 120,000 changed pixels (an even stride), which keeps a full-frame change cheap.

To keep a deck cheap to render: every rule above (no layout reads in `frame`, small filters, few nodes) applies, because `__draw(T)` runs once per output frame in every worker.


## Live annotation costs nothing when unused

The pen, highlighter and laser (11-presenting.md) are built to leave the rules above intact:

- **Lazy.** Until the first key press there is no canvas, no pointer pad, no listener and no timer. `?render` and every export never create it.
- **No frame loop.** A stroke is redrawn on the browser frame after a pointer move, from the vector points of the current slide and step (one canvas, cleared and stroked again; a few hundred points per stroke are cheap). Between strokes nothing runs, so a still slide stays "idle" in `?perf` with marks on it, and `check`/`perf` are not affected.
- **An empty canvas is not composited**: it is `display: none` on slides without marks, and hidden during transitions and in the overview.
- **The laser is one absolutely positioned element** moved with a transform (rounded to 0.01 px) on pointer moves; its fade is one CSS opacity transition on that dot, started by a single timer 1.1 s after the pointer stops.
- **Mirroring to presenter view** sends the new points of a stroke at most once per frame (`postMessage`, plain numbers), and the laser position once per frame. Presenter view already runs the deck twice: the second copy only strokes what it receives.