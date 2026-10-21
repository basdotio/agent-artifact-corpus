# Runtime: how a deck is built

## The idea

A deck is a function of three numbers: which slide, which step (build) of that slide, and how many seconds have passed since that step began. `render(slide, step, t)` draws everything, and it remembers nothing between frames. That gives four things for free:

- **rest frames.** `t = ∞` is every build finished. That is the PDF page, the PPTX slide, the overview tile and the "next" preview in presenter view;
- **jumping.** `#7.2` in the URL, the overview, the presenter's clicker all land on an exact state, with no replay;
- **a video timeline.** Holding each step for a few seconds and playing transitions in between turns the same deck into a GIF or MP4, frame-exact;
- **predictable edits.** Change an easing or a colour and re-export: the same deck with one difference.

The price is one rule: **no CSS transitions, no `@keyframes`, no `setTimeout` choreography on content.** Motion is declared with `data-anim` or computed in `frame(el, st)`.

## Skeleton

```html
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Deck title</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=...&display=block">
<style id="deck-kit-css">/* runtime/deck.css pasted here */</style>
<style>/* the deck's own theme */</style>
</head><body>
<div class="deck" data-transition="push" data-chrome="progress,number">

  <section class="slide" id="problem">
    <h2>Costs flattened after the switch</h2>
    <p data-step="1" data-anim="rise">Appears on the first click.</p>
    <aside class="notes"><p>Speaker notes.</p></aside>
  </section>

</div>
<script id="deck-kit-js">/* runtime/deck.js pasted here */</script>
<script>
Deck.slide('problem', {
  steps: 1,
  setup(el, D) { /* build SVG once */ },
  frame(el, st) { /* set attributes from st every frame */ },
});
</script>
</body></html>
```

`node scripts/sync-runtime.mjs --new my-deck.html` copies the template with the runtime already inlined; `node scripts/sync-runtime.mjs my-deck.html` refreshes the runtime in an existing deck.

The canvas is 1920×1080 CSS pixels (`data-w`/`data-h` on `.deck` to change it) and is scaled to fit the window, letterboxed. Lay slides out in those pixels.

## Markup reference

### `.deck`

| Attribute | Meaning |
|---|---|
| `data-transition` | default transition into every slide (`fade` if absent) |
| `data-transition-dur`, `data-dir`, `data-origin`, `data-color`, `data-lift` | default transition options |
| `data-chrome="progress,number"` | a progress bar and a slide counter drawn inside the slide (they appear in exports) |
| `data-controls="off"` | no on-screen controls (kiosk, embedded deck); keys still work |
| `data-annotate="off"` | no live annotation (pen, highlighter, laser; 11-presenting.md): no keys, no bar button, no layer. Use it for kiosks and embeds |
| `data-hold="3"` | seconds per step in the video timeline |
| `data-dim=".28"` | opacity of dimmed builds |
| `data-fps="30"` | frame rate reported to the video exporter |
| `data-w`, `data-h` | canvas size, default 1920×1080 |

### `section.slide`

| Attribute | Meaning |
|---|---|
| `id` | name used by `Deck.slide(id)`, by `#id` links and in reports |
| `data-transition` | how this slide **enters** (it plays reversed when you go back) |
| `data-transition-dur` | seconds |
| `data-dir` | `left right up down` for push, cover, wipe |
| `data-origin="x y"` | point for zoom and iris, in canvas pixels |
| `data-color` | colour for `dip` |
| `data-pos="x y [scale]"` | place in the world for `camera`, in slide units (`0 1.12` is one slide below, with a gap) |
| `data-lift` | how far `camera` pulls back mid-flight, 0 to 1.5 |
| `data-cell`, `data-seed` | for `dither`: cell size in px (default 14) and a shift of the pattern |
| `data-hold="2.4 2 3"` | video seconds per step |
| `data-title` | title for presenter view and PPTX alt text (default: first h1–h3) |
| `data-export="last"` | only the final step goes to `png`/`sheet` |
| `<aside class="notes">` | speaker notes, HTML allowed |

### Builds: any element inside a slide

| Attribute | Meaning |
|---|---|
| `data-step="n"` | appears at step n. Step 0 is "on entry"; a slide's step count is the largest n used |
| `data-anim` | the animation, below. Default `rise` |
| `data-delay`, `data-dur` | seconds, relative to the step start. Step-0 builds also wait for the transition to half-finish |
| `data-ease` | any name from `Deck.ease` |
| `data-out="n"` | leaves at step n (the same animation, reversed) |
| `data-dim="n"` | fades to `data-dim` opacity at step n: the "previous point dims" pattern |
| `data-stagger=".08"` | children animate in order, each 80 ms later; the container's `data-step`, `data-anim` etc. apply to every child. On `chars` and `scramble` it is the gap between characters instead |
| `data-order` | for stagger and `chars`: `reverse`, `center` (from the middle out), `random` (seeded) |
| `data-words="a\|b\|c"` | for `flip`: one word per step, starting at the element's `data-step` |
| `data-spread=".2"` | for `tracking`: how tight the letters start (fraction of their distance from the line centre) |
| `data-say="Setup:\|*payoff*"` | a statement: small setup line, large accent payoff (09-typography.md). Without a value the element's own text is used |
| `data-from` | for `count`: the start value, shown before the step |
| `data-morph="key"` | the element travels to the element with the same key on the next slide (`morph` transition) |
| `data-bleed` | allowed to touch the edges; the check skips it |
| `data-lint-skip` | an illustration made of text (a receipt, a code sample): the check ignores its text |
| `data-no-advance` | clicking it does not go to the next step |
| `data-fit` | shrink the element's font until its content fits its box; `data-fit="2"`: until the text takes at most 2 lines; `data-fit-min=".6"` is the floor. Runs once, after fonts load |

### Animations (`data-anim`)

| Name | What it does | Default |
|---|---|---|
| `rise` `drop` `left` `right` | fade + 44–64 px travel | .7 s outExpo |
| `fade` | opacity | .5 s outCubic |
| `scale` | fade + scale from .88 | .7 s outExpo |
| `pop` | spring scale with overshoot | .9 s |
| `blur` | fade + blur 18 px → 0 | .8 s |
| `wipe` `wipe-left` `wipe-up` `wipe-down` | clip reveal | .8 s inOutCubic |
| `mask` | the line rises out from under an invisible edge (content is wrapped automatically) | .9 s outExpo |
| `draw` | SVG strokes draw themselves; works on a shape or a group | 1.2 s inOutCubic |
| `chars` | each character rises .42 em and fades in, staggered (`data-stagger`, default .03 s) | .03 s per character + .55 s |
| `tracking` | letters spread from tight to loose around the centre of their line | 1.8 s outCubic |
| `scramble` | characters settle from seeded noise into the real text, left to right with jitter | .8 s + .03 s per character |
| `flip` | split-flap word swap, one word of `data-words` per step | .6 s per flip |
| `count` | counts up to the number written in the markup: `<b data-anim="count">$4.2M</b>` | 1.6 s outExpo |
| `type` | typewriter, plain text only | 35 ms per character |
| `highlight` | a marker sweeps behind already-visible text (`--dk-mark`) | .6 s |
| `strike` | a line sweeps through already-visible text (`--dk-strike`) | .5 s |
| `none` | appears instantly | |

`highlight` and `strike` do not hide the element before their step: they are emphasis on something already there. `count` and `type` write text; the authored text is always the rest frame.

The four kinetic ones (`chars`, `tracking`, `scramble`, `flip`) split the text once at load, measure it there, and put the real text in `aria-label` (the pieces are `aria-hidden`). The layout stays the authored one: kerning is restored, every character keeps its box, `flip` reserves the width of its widest word. At rest no inline style is left. With `prefers-reduced-motion` they degrade to a fade (`flip` swaps at once). Plain text and inline tags only; do not split a word across a tag. Taste and details: 09-typography.md.

Custom animation:

```js
Deck.anim('feed', { dur: 1.6, curve: Deck.ease.linear,
  f(el, e) {                         // e: eased progress 0..1
    const q = Math.floor(e * 36) / 36; // a printer feeds in steps
    return { transform: `translateY(${-(1 - q) * el.offsetHeight}px)` };
  } });
```

`f` returns any of `{opacity, transform, filter, clip}`; the runtime writes them and clears them at the rest frame. `info` is `{raw, lt, leaving, b, st}`: raw progress 0..1, seconds since the build started, whether it is leaving, the build (`b.step`, `b.dur`, `b.curve`) and the frame state `st`. `init(el, b)` runs once, after fonts and while every slide is laid out, so it may measure; its return value is `info.b.data`. Optional spec fields: `stagger: true` (the anim reads `data-stagger` itself instead of it meaning "a group of children") and `steps(b)` (extra steps after `b.step` that the anim uses, as `flip` does).

## Slide code

```js
Deck.slide('bars', {
  steps: 2,                    // optional: steps that exist only in code
  active: 3,                   // optional: seconds of motion driven by st.since() (default 4)
  ambient: 10,                 // optional: the slide reads st.T (line boil, drifting marks) but is redrawn at most 10 times a second
  setup(el, D) {               // once, before builds are parsed: build DOM/SVG here
    el._bars = data.map(d => D.svg('rect', { x: ..., width: ... }, el.querySelector('svg')));
  },
  frame(el, st) {              // every frame: a pure function of st
    el._bars.forEach((b, i) => {
      const p = st.p(0, i * .06, 1, Deck.ease.outExpo);  // step 0, delay, duration, curve
      b.setAttribute('height', h[i] * p);
    });
  },
});
```

Elements created in `setup` may carry `data-step`/`data-anim`: builds are parsed after setup.

`st` has:

| Field | Meaning |
|---|---|
| `st.step`, `st.last` | current step, last step of the slide |
| `st.t` | seconds since the step began (`Infinity` in a rest frame) |
| `st.T` | global clock, for ambient motion that should not restart per step |
| `st.p(n, delay, dur, curve)` | progress of something that starts at step n: 0 before, eased 0..1 during, 1 after |
| `st.since(n)` | raw seconds since step n began (`Infinity` if passed, `-Infinity` if ahead). Counts as motion for `active` seconds |
| `st.at(n)` | `step >= n` |
| `st.life(period, amp, phase)` | a sine for breathing and pulsing; returns 0 in rest frames so exports stay canonical |
| `st.rest` | true when rendering a rest frame for export |

Rules for `frame`:

- Set every property you animate on every frame. Never "set once when p reaches 1": the next frame may be an earlier state.
- Derive everything from `st`. Do not read the previous value back from the DOM.
- Ambient motion (`st.T`, `st.life`) must be decorative: in rest frames it freezes at its zero pose.
- The runtime knows when a step's motion ends from `st.p(...)`, the builds and `active`. After that, a slide that did not read `st.T` goes idle and costs nothing (13-performance.md).
- Never read layout (`offsetHeight`, `getBoundingClientRect`) in `frame`; measure in `setup`. Fonts are loaded before `setup` runs, so measurements there are final.

## Helpers

`Deck` exports what a chart or a diagram needs, so decks do not depend on a CDN library:

| Helper | |
|---|---|
| `svg(tag, attrs, parent)`, `el(tag, attrs, parent)` | create elements. `text:` sets textContent, `style:` takes an object. `fill`, `stroke`, `stroke-width`, `font-size`, `font-weight`, `font-family`, `text-anchor`, `letter-spacing`, `fill-opacity`, `stroke-opacity` are written to inline style, so they beat the stylesheet (see Gotchas) |
| `scaleLinear([d0, d1], [r0, r1])` | with `.ticks(n)`, `.nice()`, `.invert()` |
| `scaleBand(keys, [r0, r1], {padding})` | `f(key)` is the band start, `f.bw` the band width |
| `ticks(a, b, n)` | nice round tick values |
| `linePath(pts, 'monotone' \| 'linear' \| 'step')` | SVG path through points; monotone never overshoots |
| `areaPath(pts, y0, curve)` | closed area down to a baseline |
| `arcPath(cx, cy, r0, r1, a0, a1)` | donut or pie segment; radians, 0 at twelve o'clock, clockwise |
| `pointAt(path, p)` | point at fraction p of a path's length, for a moving head on a line |
| `fmt(v, {dec, prefix, suffix, compact})` | `fmt(4200000, {compact: true, dec: 1, prefix: '$'})` → `$4.2M` |
| `mix('#hex', '#hex', p)` | colour interpolation |
| `ease`, `spring(t, zeta, omega)`, `seg(t, a, b)`, `lerp`, `clamp`, `rng(seed)` | motion maths |
| `say(el, 'Setup:\|*payoff*')` | build a statement from code (what `data-say` does); warns in the console above 8 words |
| `fx.noise(seed)` | `{n(x, y), fbm(x, y, octaves)}`: seeded value noise, 0..1 |
| `fx.grain({fps, size, tiles, seed})` | film grain from pre-rendered tiles: `g.draw(ctx, S, amount, live)`, `g.warm()`, `g.fps`; frozen in rest frames and when `live` is false; `?nograin` disables |
| `fx.vignette(ctx, S, {strength, inner, color})` | darkened corners from one cached sprite |
| `fx.glow(ctx, x, y, r, color, {a, core, halo, op, to, t})` | two-layer glow from a sprite cached by look; `to`/`t` cross-fade to a second colour |
| `fx.boil(seed, T, fps)`, `fx.boil.pts(points, seed, T, amp, fps)` | hand-drawn jitter, new `fps` times a second (default 10) |

`Deck.fx` is opt-in: nothing in it runs, allocates or listens until a deck calls it. Recipes and the performance rules: 10-stage.md.

For something the helpers do not cover (a sankey, a map projection, force layout), load a d3 module from jsDelivr as a UMD `<script src>` so `bundle` can inline it, and run the layout once in `setup`.

## Modes

| URL | Mode |
|---|---|
| `deck.html` | live: keys, clicks, swipe |
| `deck.html#7.2` or `#pricing.1` | live, opened at slide 7 step 2 |
| `?presenter` | presenter view (opened with **P**; see 11-presenting.md) |
| `?embed`, `?embed&rest` | slide only, no input; `rest` shows rest frames. Used inside presenter view |
| `?render`, `?render&hold=1.2` | exporter: scale 1, no clock. `hold` overrides every step's hold in the timeline |
| `?perf` | live, with a frame-rate HUD (13-performance.md) |
| `?nograin` | `fx.grain` draws nothing (a deck with no other ambient motion then goes fully idle) |

Keys: → ↓ Space PgDn next · ← ↑ PgUp previous · Home/End · digits + Enter go to slide · **O** or **Esc** overview · **P** presenter · **F** fullscreen · **B** or **.** black screen · **?** help · **D** pen · **H** highlighter · **L** laser pointer · **E** erase this slide's marks · **1**–**4** pen colour while drawing (**Esc** leaves the drawing mode first). **H** used to open the help; it now draws (it still opens the help with `data-annotate="off"`).

Live annotation is drawn on a canvas that the runtime creates on first use, above the slide and below the control bar. It exists only in the live and presenter windows, never in `?render`, so no export can contain it. Pen colours come from the CSS variables `--dk-pen-1` … `--dk-pen-4` (defaults: `--accent`, `--ink`, yellow, white) and the laser from `--dk-laser`. Details and the presenter-view mirroring: 11-presenting.md.

Mouse and touch: a click on the right four-fifths of the screen goes forward, on the left fifth back (an arrow appears near the edge); swipe left/right. Moving the mouse shows the control bar: back/next, slide number and title, one dot per step, a scrubber with every slide (hover for its title, click to jump), overview, presenter view, fullscreen and help. It hides after 2.6 s without movement. A hint with the main keys shows for the first seconds; reaching either end of the deck shows a short message. `Deck.toast('text')` shows your own.

Going back lands on a step already finished (no replay), exactly as Keynote does. Pressing next during a transition completes it and moves on.

`prefers-reduced-motion` turns every transition into a 0.3 s fade.

## Export contract

The exporter drives the page through a small API. A deck built on the runtime has it automatically; a hand-written deck needs to expose the same:

```js
window.__deck = { W, H, slides, states(), show(i, step), buildPrint(list), timeline() };
window.__meta = { W, H, FPS, DURATION };   // video timeline length
window.__draw = T => {};                    // frame at time T of the timeline
window.__ready = true;                      // after fonts and images
```

## Gotchas

- **CSS beats SVG presentation attributes.** `.chart text { fill: #333 }` wins over `fill="red"` on one label. Pass colours and sizes through `Deck.svg` (it writes them to inline style) or set `el.style.fill`.
- **SVG transforms scale from the SVG origin.** Elements with a `data-*` build get `transform-box: fill-box` from the runtime CSS. When you transform an SVG child from `frame` yourself, give it `style: { transformBox: 'fill-box', transformOrigin: 'center' }`, or it flies in from the corner.
- **`clip-path: inset()` on SVG children** clips against the wrong box in some engines. Use `wipe` on HTML elements or on the whole `<svg>`, and `draw` or a `clipPath` rect for parts of a chart.
- **`morph` works on HTML elements.** Put the thing that travels in a `<div data-morph>`; an SVG `<g>` cannot leave its SVG.
- **IDs inside SVG** (`clipPath`, gradients) must be unique per deck; the PDF export renames them per page.
- **Canvas inside a slide** is fine; a WebGL canvas needs `preserveDrawingBuffer: true` to appear in the PDF.
- **Heavy SVG filters** on large areas cost frames in live mode. Test on the presentation laptop.

## data-fit

`data-fit` shrinks the element's font in 3% steps (at least 1 px) until the text fits, measuring the DOM after every step: `scrollWidth`/`clientWidth` for one unbreakable word that is too wide, and `offsetHeight` against the line height (`data-fit="2"`: at most two lines) or `scrollHeight` against the box. It runs once, after fonts load, before builds are parsed, so it costs nothing per frame.

**Decision: stays on DOM measurement; Pretext ([chenglou/pretext](https://github.com/chenglou/pretext), DOM-free text measurement) is not adopted.** Prototype and measurement (Chrome, the four decks in this repo: 4 + 11 + 8 + 6 `data-fit` elements, each fitted at 5 widths from 100% down to 40% so the loop really shrinks, 145 fits, 120 of them plain text): the chosen font size matched the DOM path within 1 px in 120 of 120 cases with fallback fonts and in 119 of 120 with the web fonts (one case off by 2.2 px, one step of the 3% loop). Time for the whole sweep: DOM 494 ms, Pretext 440 ms cold (first `prepare` per font size and text) and 104 ms warm, with fallback fonts; with web fonts DOM 321 ms and Pretext 371 ms cold. So it is not measurably faster on the first (and only) run that a deck makes, and in real use most titles fit at once: the DOM path was 1 ms for the whole template deck. It also loses on the things a deck needs: it measures plain text only (a `data-say` statement or a title with `<em>`/`<br>` matched in 19 of 25 cases), ignores `font-feature-settings` and `font-optical-sizing`, and ships as seven ES modules (126 KB unminified, no single-file build), which cannot be pasted into the classic inline runtime or loaded from `file://` without a bundler, and would be a CDN dependency for the offline path. Revisit it if a deck ever needs to measure text thousands of times (a live-resizing text box), not for `data-fit`.
