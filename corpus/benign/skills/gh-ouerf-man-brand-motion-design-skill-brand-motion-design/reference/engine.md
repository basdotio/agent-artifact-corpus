# Engine: HyperFrames, the clock and the kit

HyperFrames renders a web page to video by seeking one paused GSAP timeline per composition, frame by frame, in headless Chrome. This skill adds a thin layer on top: one linear "clock" tween whose `onUpdate` calls your `draw(t)`, so every style is a pure function of the time in seconds, exactly like a Remotion component reads its frame. Springs, magic moves, cursors, cameras and punchlines are small pure functions of `t`.

Read `/hyperframes-core` (installed with `npx hyperframes skills update`) when you need the full HyperFrames contract: clips, tracks, sub-compositions, media. The rules below are what a product film needs.

## Workspace

- **Where it lives.** `videos/<film>/` next to (or inside) the product repo, so it can read the product's tokens, fonts and SVGs. `videos/BRAND.md` is shared by every film.
- **Set it up.** `node <skill>/scripts/setup.mjs videos/<film> --size 1080x1920 [--katex]`:
  - `npx hyperframes init` (Node 22+ and FFmpeg are required; `npx hyperframes doctor` checks them)
  - the kit in `kit/`, starters `index.html` and `cues.js`
  - GSAP (and KaTeX) vendored into `vendor/`: nothing loads from a CDN at render time
  - a `.gitignore` for `renders/`, `review/`, `out/`, `snapshots/` and licensed audio
- **Fonts.** Copy the product's font files into `assets/fonts/` and declare an `@font-face` per family (lint requires it). Variable fonts: one face with `font-weight: 100 900`.
- **Tokens.** Copy the product's tokens into `:root` as hex. Anything that animates is interpolated with `PF.mix` from hex, never from `color-mix()` or a CSS variable.
- **Product components.** HyperFrames renders HTML, not React. Three ways to use real UI:
  1. Copy the rendered markup and its CSS (the product's built stylesheet, or Tailwind output) into the scene. Best for static components: exact look, no build step.
  2. Rebuild the component as a small HTML twin with the product's class names and tokens. Best when it animates (a spinner, a typing field, a chart).
  3. For a large React surface, build it once to static HTML (the product's own SSR, Storybook static export, or a one-off `renderToStaticMarkup`) and paste the result.
  Write in `BRAND.md` which one each component uses, and why.
- **Tailwind.** Either link the product's compiled CSS, or `npx hyperframes init --tailwind` (see `/hyperframes-core` → `references/tailwind.md`).

## The composition (`index.html`)

```html
<div id="root" data-composition-id="main" data-start="0" data-duration="25" data-width="1080" data-height="1920">
  <div id="words" class="layer"></div>
  <section id="scene-a" class="scene">...</section>
  <!-- pf:audio -->  (written by place-audio.mjs)  <!-- /pf:audio -->
</div>
<script>
  const b = PF.grid(CUES.grid);             // b(bar, beat, fraction) -> seconds
  const EASE = { enter: PF.ease("cubic-bezier(0, 0, .2, 1)") };  // the product's tokens
  function setup() { /* build DOM, render KaTeX, measure with PF.rectOf */ }
  function draw(t) { /* every style from t */ }
  PF.film({ duration: CUES.duration, setup, draw,
            register: (tl) => { window.__timelines["main"] = tl; } });
</script>
```

- Root `data-duration` equals `CUES.duration` (HyperFrames reads it once, before scripts).
- Scenes are plain elements shown and hidden by `draw(t)` (`PF.show`), not HyperFrames clips: the clock owns them. Use HyperFrames clips only for media (`<audio>`, `<video>`) and for sub-compositions you want editable in Studio.
- One owner per property. If you add ordinary GSAP tweens with `build(tl)`, never let a tween and `draw(t)` touch the same property.
- Keep the file readable: when it passes ~400 lines, move scene builders into `scenes/*.js` (loaded with `<script src>`), or split scenes into sub-compositions.

## The kit (`kit/*.js`, browser globals under `PF`)

| File | What it gives |
|---|---|
| `film.js` | `PF.film({duration, setup, draw, register, build})` the clock; `PF.grid(grid)` the beat grid `b(bar, beat, fraction)` with `b.label(t)`; `PF.bezier`, `PF.ease("cubic-bezier(...)")` (the product's own curves); `PF.progress`, `PF.tween`, `PF.clamp01`, `PF.lerp`, `PF.mix` (hex), `PF.random(seed)`; `PF.loadImages({key: src})` + `PF.img.key` (the user's images, decoded before setup), `PF.css` (sets only changed styles), `PF.show` (keeps slots, uses `inherit`), `PF.rectOf` (a box in composition px) |
| `motion.js` | `PF.step` closed-form spring, `PF.track` a value that retargets (one spring per key), `PF.critical`, `PF.springs`; `PF.move` + `PF.travel` magic moves; `PF.swap`/`PF.swapStyle` enter-hold-leave; `PF.enter` rise-and-fade; `PF.camera`, `PF.worldTransform`, `PF.project` |
| `words.js` | `PF.punchlines(parent, cards, theme)` word-by-word cards with kept slots; `PF.captions(parent, lines, band, theme)` one line at a time in a fixed band (per-line `y`, `size`, `weight` for a tagline) |
| `draw.js` | `PF.drawable(svgEl)` a stroke that draws itself (`pathLength=1`); `PF.fnPath(f, x0, x1, px, py)` a function curve as a path; `PF.axes(window, box)`; `PF.along(el, p)`; `PF.bayerPath` ordered-dither reveals |
| `cursor.js` | `PF.cursorAt(t, keys)` glides that arrive exactly on the cue, with click squash; `PF.makeCursor`/`PF.placeCursor` the OS arrow; `PF.pathAt` free Hermite paths |
| `fx.js` | The showreel toolkit ([showreel.md](showreel.md)): `PF.flood`, `PF.iris`, `PF.blinds`; `PF.slam`/`PF.slamStyle`, `PF.ring` shockwaves; `PF.shake`; `PF.grain`, `PF.vignette`; `PF.hud` viewfinder + `PF.timecode`; `PF.typewriter`; `PF.wordWall`; `PF.swarm` particles settling onto targets |
| `three.js` | Rich 3D from the clock: `PF.three.stage` (renderer, env map, bloom, `newScene`/`use` per chapter), `PF.three.lights`, `PF.three.mat` (gloss, glass, satin, metal, glow), `PF.three.ramp`, `PF.three.orbit` and `PF.three.shots` (camera cuts with drift), `PF.three.field` (instanced columns), `PF.three.tube` (a curve that draws itself), `PF.three.canvasTexture`/`card` (paper, UI, exact swatches), `PF.three.photo` (a user's photo or screenshot as a 3D card), `PF.three.sticker`, `PF.three.samplePoints` + `PF.three.particles` (dust, particles converging into a logo). Vendored by `setup.mjs` by default; needs `waitFor: [PF.signal("three")]` ([showreel.md](showreel.md)) |
| `debug.js` | `PF.debug({grid, safe})`: with `--debug` stills, prints `t`, bar.beat and every `[data-target]` box into the frame, and outlines the safe zone |

Theme the words from the product's motion tokens: `{ font, color, accent, weight, enter: {length, rise, blur, ease}, exit: {length, blur, fall} }`. Defaults are a soft blur-rise; set `blur: 0` for a brand that never blurs.

## Rules for scene code

- `setup()` runs once after every declared font has loaded: create elements, render KaTeX, measure (`PF.rectOf`) and store the numbers. Never measure in `draw`.
- `draw(t)` only reads `t`, the cues and what `setup` stored. Each scene checks its window and hides itself outside it. End a scene when its content has faded, not at the next scene's start.
- Timeline in `cues.js`, read as `b(bar, beat, fraction)`. Scene code never holds a literal time.
- **Layers, bottom to top:** world scenes under the camera; screen-space textures; scenes above the texture (an app window); the brand element if it moves across scenes; the product's cursor; words; the user's cursor.
- Use `transform` and `opacity`. Never `will-change` on anything a camera scales (text blurs).
- **Magic moves.** A traveler renders in the destination's style, sits at the destination box with `transform-origin: 0 0`, and `PF.travel(PF.move(t, start, from, to), to)` scales it from the source. Hide the source from the handoff; fade every other text out before the move starts; the traveler stays as the element when it lands.
- **The brand's one highlight** (an accent, an "orange point"): one per scene if the brand says so. Land it with the brand's own curve.

## Frame-driven twins

Re-create an element when it runs its own clock: CSS `@keyframes` or transitions (animated SVG logos often do), `requestAnimationFrame`, `setInterval`, video you cannot seek, Lottie or Rive not registered with HyperFrames, shaders on their own time. Copy the structure, classes and tokens; change only the clock. Example: an SVG logo whose CSS draws the stroke, fades the letters and lands a dot becomes `drawW(p)`, a letters opacity and a dot radius, all from `t`. Write in the file which asset it twins and why.

## An animated logo or mascot (only if chosen)

- One element, driven by `t`: draw the outline with `PF.drawable`, then reveal the fill (fade, wipe, or a `bayerPath` clip for a dithered rise).
- Poses and moves as keyed tracks summed with `PF.track`: `[t, x]`, `[t, y]`, `[t, rotate]`, `[t, scale]`.
- One instance across the film: a `placement(t)` with named spots and arcing leaps between them.

## Math, charts and data

- Plot in 3D: `PF.three.field` columns settling onto the function read as the graph from the front, or `PF.three.tube` drawing the curve with a glowing point riding it ([showreel.md](showreel.md)).
- Set formulas with KaTeX (`--katex` vendors it): `katex.render(tex, el, { output: "html", trust: true })`. `\htmlId{name}{...}` marks a term you can measure and move.
- Plot with `PF.axes` and `PF.fnPath`; clip the curve to the plot box; draw it with `PF.drawable` left to right on the brand's curve.
- Check every formula and every plotted value by hand. A wrong sign on screen is a false claim.

## Measuring (never guess positions)

- `data-target="name"` on anything a cursor clicks or a traveler lands on.
- `node <skill>/scripts/stills.mjs videos/<film> b5.3 b6.1 --debug` prints each target's centre and size into the frame.
- Re-measure after any layout change upstream of a target.

## Coming from the Remotion version

| Remotion | Here |
|---|---|
| `useCurrentFrame() / fps` | `draw(t)` receives seconds |
| React components and props | HTML built in `setup()`, styles set in `draw(t)` with `PF.css` |
| `interpolate`, `Easing.bezier` | `PF.progress`, `PF.ease` / `PF.bezier` |
| `spring()` | `PF.step`, `PF.track` (closed form, same numbers) |
| `<Img>`, `staticFile` | `<img src="assets/...">` (HyperFrames waits for images) |
| `calculateMetadata` fps | `render.mjs --fps 60 --blur 4` (the master renders at 240) |
| `npx remotion still` | `stills.mjs` (`npx hyperframes snapshot`) |
| Studio | `npx hyperframes preview` (Studio with a timeline) |
| Remotion company license | HyperFrames is Apache 2.0 |
