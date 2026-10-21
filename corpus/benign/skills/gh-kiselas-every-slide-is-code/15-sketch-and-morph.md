# Sketch and path morph (optional plugin)

`runtime/sketch.js` + `runtime/sketch.css` add two independent things: **hand-drawn SVG** (`data-sketch`) and **path morph** (one shape turning into another, in a build or in the `morph` slide transition). No dependencies, offline, deterministic. The core stays as it is; a deck without the slots is unchanged. Example: `examples/sketch/deck.html`.

## When to use

- Hand-drawn: whiteboard and lab-notebook decks, early-stage ideas ("this is a sketch, not a spec"), architecture talks where boxes and arrows should look like thinking, not like a diagram tool. Not for financial charts that must read as exact.
- Morph: a shape that is the same thing in a new role (a bar becomes a ring slice, an icon becomes another icon, a blob becomes the logo). The vertex counts, holes and subpaths may differ. Not for unrelated shapes: that is noise (06-transitions.md).
- One idea per slide still holds. Wobble is texture, not content: labels stay text, numbers stay readable.

## Enable

Two slots, plugin script before the deck script that calls `Deck.slide` (as in 14-code-slides.md):

```html
<style id="deck-kit-css"></style>
<style id="deck-kit-sketch-css"></style>
...
<script id="deck-kit-js"></script>
<script id="deck-kit-sketch-js"></script>
<script>Deck.slide(...)</script>
```

`node scripts/sync-runtime.mjs deck.html` fills them. Either plugin, or both, or none.

## Hand-drawn

`data-sketch` on an `<svg>` or a `<g>` redraws every `line rect circle ellipse polyline polygon path` inside as two wobbling strokes plus an optional hatch fill. `<text>` is never touched. The style comes from the original shape (stroke, stroke-width, fill, opacity, dash), so write the SVG as if it were clean, then add the attribute.

```html
<svg class="art" viewBox="0 0 1920 1080" data-sketch data-sketch-seed="7">
  <rect class="box" data-anim="draw" x="150" y="500" width="250" height="140" rx="12"/>   <!-- fill: hachure by default -->
  <path class="ln" data-anim="draw" data-delay=".5" d="M410 570 L500 570"/>
  <text class="sketch-font" x="275" y="583" text-anchor="middle">Shop</text>
</svg>
```

Options are attributes on the scope (svg, group) or on one shape; the nearest one wins.

| Attribute | Default | Meaning |
|---|---|---|
| `data-sketch="off"` | | keep this shape or group clean |
| `data-sketch-seed` | 1 | number or word; same seed, same drawing. Change it to reroll |
| `data-sketch-rough` | 1 | wobble; 0.5 tidy, 2 drunk. About 2 px at 1 |
| `data-sketch-bow` | 1 | how far a line bends away from straight |
| `data-sketch-strokes` | 2 | 1 to 3 passes over the same line |
| `data-sketch-fill` | `hachure` | `hachure` `cross` `solid` `keep` `none`; only for shapes that have a fill |
| `data-sketch-gap` | 10 | distance between hatch lines, px |
| `data-sketch-angle` | -41 | hatch angle, degrees |
| `data-sketch-fill-width` | 0.7 x stroke | hatch line width |
| `data-sketch-boil` | 0 | line boil: redraw N times a second (below) |

Fills: `hachure` = parallel lines in the fill colour, `cross` = two directions, `solid` = the outline pushed slightly off register, `keep` = the exact original fill. Holes work (even-odd).

### With builds and draw-in

- `data-step`, `data-delay`, `data-stagger`, `data-out` on a sketched shape or its group work as before: the runtime sees a normal `<g>`.
- `data-anim="draw"` on a sketched shape (or a group holding sketched shapes) becomes `sketch-draw`: the same stroke-dash draw-in, but the second stroke starts a little later and solid fills arrive after the outline. Hatch lines draw one after another, back and forth.
- Shapes created in `setup()` are sketched right after `setup()` returns. To do it earlier, call `Deck.sketch.apply(slideEl)`.

### Line boil

`data-sketch-boil="10"` switches between a few drawings of the same shape 10 times a second. Only while the slide is live: exports, the rest frame, `?render`, the presenter thumbnails and `prefers-reduced-motion` show the still drawing (variant 0). A slide with boil declares `ambient: fps` for itself, so it redraws at that rate only; a slide without boil goes idle as always. Boil keeps its slide animating at every step, even before the boiling shape has appeared: use it on one accent (a red circle), not on the whole deck. 5 to 10 is the range that reads as hand-drawn; more looks like noise.

### Handwriting

The wobble looks best with a handwritten label font. Add it to the deck's Google Fonts link and use the class from `sketch.css`:

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&display=block">
<style>:root { --dk-sketch-font: 'Caveat', 'Segoe Print', 'Comic Sans MS', cursive; }</style>
<h2 class="sketch-font">Orders should flow</h2>
```

Handwriting is narrow and small for its size: use 36 px and up for labels, 100 px and up for titles. The fallback stack is wider, so keep 15 % slack (`check --no-webfonts`).

## Path morph

### In a build

```html
<!-- to a path that lives in <defs> (or anywhere): colours come from it too -->
<path id="table" data-step="2" data-morph-to="#stream" d="M660 508 h130 ..."/>
<!-- or to path data written in place, with colours given as attributes -->
<path data-step="1" data-anim="morph-path" data-to="M1330 430 A210 210 0 0 1 ..." data-to-fill="#d8432f" d="..."/>
```

`data-morph-to` alone is enough: it becomes `data-anim="morph-path"`. `data-step`, `data-delay`, `data-dur` (default 1.1), `data-ease` are the usual build attributes. The source is the element's own `d` (progress 0), the target is progress 1. Before the step the slide shows the authored path, after it the target's authored path; in between it is a polygon of about 5 px chords. `fill`, `stroke` and `stroke-width` are interpolated; `none` fades. Non-path shapes (`rect`, `circle`, ...) carrying `data-morph-to` are turned into paths.

How two shapes are matched (after Flubber): every subpath becomes a ring of points; rings are paired by distance between centres plus difference in size; the ring with fewer points gets points on its longest edges until both match; the winding is matched and the start point rotated to the smallest total distance. A ring with no partner (a hole, or four of five bars) is born from, or collapses into, a point that travels with its neighbour. While it morphs, `fill-rule` is even-odd.

### In the `morph` slide transition

```html
<!-- slide 3 -->  <path data-morph="mark" class="hl" d="M494 424 H596 ..."/>
<!-- slide 4, data-transition="morph" -->  <path data-morph="mark" class="hl" d="M990 640 A230 230 0 1 1 ..."/>
```

If both elements with the same `data-morph` key are SVG shapes, the shape morphs (and its colour) while it travels; HTML elements travel and crossfade as before. The first frame is exactly the outgoing shape and the last frame exactly the incoming one. See the next section for how this is hooked in.

### From code

```js
const f = Deck.sketch.morph(dFrom, dTo);   // t => path data; 0 and 1 return the inputs untouched
path.setAttribute('d', f(st.p(1, 0, 1.2)));
Deck.sketch.strokes('M0 0 L300 0', { seed: 3 });   // sketchy path data for canvas or custom SVG
```

## How it is built, and what it costs

- The plugin replaces the registered `morph` transition with a copy of the core one plus the shape branch (the core function cannot be reached from outside). If the core `morph` changes, update the copy in `sketch.js`, or add the hook that makes it unnecessary: in the core loop, `if (m.shape?.(e, f)) continue;`.
- A sketched shape becomes a `<g class="dk-sk">` with 1 to 3 `<path>`s. Ids, classes, `data-*`, `transform` and inline style move to the group; fill and stroke are copied to the paths as inline style.
- A deck of 25 elements per slide costs about 0.5 ms per frame; a morph frame under 1 ms. Hatch paths are promoted with `will-change: transform` (in `sketch.css`): dense strokes rasterise slightly differently from run to run otherwise, and the rest-frame test catches that. Beyond 30 hatched shapes on one slide, use `solid` or a wider `data-sketch-gap`.

## Checks

```bash
node export/deck.mjs check deck.html               # 0 errors
node export/deck.mjs check deck.html --timeline    # mid-draw frames
node export/deck.mjs check deck.html --no-webfonts # handwriting fallback is wider
node export/deck.mjs strip deck.html s.png --slide 4 --frames 8   # the morph transition into slide 4
node export/deck.mjs sheet deck.html sheet.png     # look at it: hatch density, wobble, morph end states
npm run test:browser -- --only sketch
```

Look for: hatch so dense it reads as a flat colour (raise `gap`), labels colliding with a wobbling line (rough over 1.5), a morph whose middle frame is a knot (the two shapes start at different corners; rotate one path so both begin at the same place), a hole that should shrink but grows.

## Gotchas

- Sketching happens once, at load (and after `setup()`), not per frame: only `d` changes for boil. Do not move sketched shapes with attributes; move the group with a transform.
- Shapes that morph (`data-morph-to`, `morph-path`, `data-morph`) are never sketched: they stay clean and flat. Keep them apart from sketched objects (a highlighter marker under a label, not a sketched bar). During a `morph` transition the shape is drawn above the slide, so anything on top of it in the rest frame jumps at the first frame: end a morphing bar a few pixels above the axis, not on it.
- The target of `data-morph-to` is read in the source's coordinate system; its own `transform` is ignored. A target outside `<defs>` is drawn as well, unless `display:none`.
- Even-odd fill during the morph: a source that relies on nonzero overlap (two overlapping same-direction subpaths) looks different in between.
- `marker-*` is kept on the first stroke only, and markers do not follow `draw`: draw arrowheads as small paths (08-diagrams.md).
- Load the plugin before the deck script that calls `Deck.slide`, or its hooks are replaced (the plugin warns).
- Never use `Math.random` for your own wobble: `Deck.rng(seed)`.
