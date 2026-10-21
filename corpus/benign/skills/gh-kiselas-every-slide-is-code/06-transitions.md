# Transitions

## A transition is a sentence about two slides

Pick the transition from how the two slides relate, not from what looks good:

| Relation | Transition | Example |
|---|---|---|
| We continue the same thought | `camera` (the world scrolls), `push` | problem → its size → its cause |
| The same object, new role | `morph` | the device on slide 5 becomes a node in the loop on slide 6 |
| Going inside something | `zoom` with `data-origin` on that thing | from the "prep ticket" node into the ticket itself |
| A new chapter | one chapter transition, always the same | `tear`, `dip`, `cover` |
| Revealing an answer | `iris` from the point of interest, `wipe` | the question → the answer |
| Time passes | `dip` through black | before → after a year |
| A change of mood or medium | `dissolve` | the vision slide |
| The moment it happened | `flash` | the outage, the launch, the reveal |
| An accent on a beat | `punch` | the one number that carries the deck |
| Meanwhile, the pace picks up | `whip` | from the calm opening into the pain, a montage of places |
| Something is broken or corrupt | `glitch` | the evidence that disagrees, the failing system |
| A change of mood, memory | `lightleak` | from the problem to the way out; the warm ending |
| Sampling, going digital | `dither` | a signal becoming data points, analog to digital |
| Nothing special | `fade`, or `none` | appendix |

Rules:

- **Two or three types per deck, each with one meaning.** In the demo: camera inside a chapter, tear between chapters, morph and zoom where an object carries over. Nothing else.
- The transition belongs to the slide it **enters**. Going back plays it reversed.
- Keep the kicker, title and footer in the same place on every slide, so `push`, `camera` and `morph` look deliberate.
- Transitions are short: 0.6–1.3 s. The audience is waiting for the next idea.

## Catalogue

| `data-transition` | What happens | Options |
|---|---|---|
| `none` | cut | |
| `fade` | cross-dissolve | |
| `dip` | through a colour, cut at the middle | `data-color` (default black) |
| `push` | the new slide pushes the old one out | `data-dir="left right up down"` |
| `cover` | the new slide slides over the old one, which darkens and recedes | `data-dir` |
| `zoom` | dive into a point of the old slide; the new one grows out of it | `data-origin="x y"` |
| `iris` | a circle opens from a point | `data-origin` |
| `wipe` | a soft edge sweeps across | `data-dir` |
| `blinds` | vertical stripes open | `data-count` on the slide |
| `cube` | 3D rotation of two faces | |
| `flip` | a card turns over | |
| `tear` | the old slide is torn off along a zigzag edge and lifted away | |
| `dissolve` | noise dissolve through an SVG filter | |
| `morph` | magic move: `data-morph` elements travel, the rest crossfades | |
| `camera` | the camera flies across one continuous world to the slide's `data-pos` | `data-pos`, `data-lift` |
| `flash` | the old slide burns to white and the new one comes out of the light with seeded rays. **Meaning:** the moment it happened | `data-color` (light and rays), `data-origin` (where the rays start) |
| `punch` | a hard cut on the beat: the old slide leans in, the new one lands 7% too big and settles, the old one lingers as a faint ghost, a short flash. **Meaning:** an accent. 0.5 s, use once per section | `data-color`, `data-origin` |
| `whip` | a fast pan with horizontal motion blur that follows the speed of the pan. **Meaning:** meanwhile, the next place, the pace picks up | `data-dir` |
| `glitch` | horizontal stripes of the other slide, pushed sideways, seeded by the frame index (20 states a second); now and then base and stripes swap. **Meaning:** something is broken or corrupt | |
| `lightleak` | warm light leak (screen-blended lobes and a streak) over a crossfade; it sweeps the other way going back. **Meaning:** memory, warmth, a change of mood | `data-color` (tint) |
| `dither` | Bayer ordered-dither dissolve: the slides swap cell by cell in a fixed 8x8 order. **Meaning:** sampling, going digital, the picture turning into data | `data-cell` (px, default 14), `data-seed` |

The cinematic set (`flash` to `dither`) is ported from the film runtime (every-frame-is-code). Each is a pure function of `p`; at `p = 1` every style they wrote is neutral, so the last frame of a transition is the rest frame of the slide (checked pixel for pixel), and going back plays the same function reversed. None of them needs `opaque`: layers stay transparent, so the stage shows through and does not pop in at the end.

How they are built, and why (the performance rules in 13-performance.md apply):

- **`flash`, `lightleak`, `punch`** use the veil (one full-canvas element) for the burn, the leak and the flash; the rays are one static conic gradient (a wedge per sector, so they never overlap) that is only scaled and faded per frame. Opacity, transform and one gradient repaint.
- **`whip`** filters both layers with one SVG `feGaussianBlur` in the direction of the pan, whose strength is the speed of the pan: zero at both ends, so nothing is filtered at rest. Stacked copies of a live slide would double the DOM; a directional blur is one filter, and it is the only filtered thing on screen.
- **`glitch`** is `clip-path: path()` with a few dozen rectangles per frame on two layers, plus one `translateX`. The base has the stripes cut out (`evenodd`), so slides never double up.
- **`dither`** is the cheapest correct approach to an ordered dissolve on DOM layers. Alternatives: the `dissolve` SVG filter is per-pixel work every frame and depends on the GPU; a `clip-path` with hundreds of squares is a huge path per frame; a canvas cannot hold live DOM. Instead 2 x 65 tiny PNGs (one per threshold level, on and off) are rendered once at load, and a frame is two `mask-image` swaps: the new slide masked by the tile of level *L*, the old one by its complement. Every cell shows exactly one slide, nothing is noisy, and the Bayer order is what makes it read as "digital".

Durations are set with `data-transition-dur`. Defaults are in the runtime: 0.6 s for fade, 1.3 s for camera.

`cover`, `cube`, `flip` and `tear` treat slides as opaque cards. The card background is `var(--dk-card)`, falling back to the deck's background colour. Set `--dk-card` to a colour plus a texture if the deck has one (the demo passes its paper grain).

## Camera: one world instead of a stack

Every slide has a position in a 2D world: `data-pos="x y [scale]"` in slide units. Without it, slides sit in a row. The `camera` transition flies from one position to the next and pulls back mid-flight in proportion to the distance (`data-lift` scales that, 0 for a straight pan).

```html
<section class="slide" data-pos="0 0">     <!-- chapter I: a column going down -->
<section class="slide" data-pos="0 1.12">
<section class="slide" data-pos="0 2.24">
<section class="slide" data-pos="3 0" data-transition="tear">  <!-- chapter II: a new column -->
```

The gap (`1.12` instead of `1`) leaves room between slides, visible during the flight. A stage (10-stage.md) can draw something in that gap: the demo draws a dashed cut line, so the camera visibly feeds down a receipt roll.

Ideas for world layouts:

- a column per chapter (receipt, scroll, document);
- a row along a timeline, where slide x is the year;
- a big map, where each slide is a region and the overview is the map zoomed out;
- a zoom-in chain: slide k+1 at 0.25 scale inside slide k, so each click dives deeper.

## Morph

Elements with the same `data-morph` key on the outgoing and the incoming slide fly from one place and size to the other while everything else crossfades. The runtime measures both rest positions at the start of the transition and animates clones on top.

```html
<!-- slide 5 -->
<div class="device" data-morph="device" style="left:150px; top:440px; width:900px; height:530px">…</div>
<!-- slide 6, transition morph -->
<div class="device" data-morph="device" style="left:150px; top:560px; width:450px; height:265px">…</div>
```

- Use it only when it is the same thing. A morph between unrelated shapes is noise.
- Put the moving thing in an HTML wrapper; an SVG child cannot leave its SVG.
- The two versions may differ (colour, content): they crossfade in flight. Keep the aspect ratio close, or the content stretches.
- Several keys can move at once (title, logo, a card), and the eye follows the largest one.

## Zoom into a point

```html
<section class="slide" id="ticket" data-transition="zoom" data-origin="1575 675">
```

`data-origin` is the point on the **outgoing** slide to dive into, in canvas pixels. Aim it at the element the next slide is about, so the dive reads as "let's look inside this".

## Custom transitions

```js
Deck.transition('slide-up-fade', { dur: .8, fn(A, B, p, o) {
  const e = Deck.ease.inOutCubic(p);
  A.style.opacity = 1 - e;
  B.style.transform = `translateY(${(1 - e) * 80 * o.sign}px)`;
  B.style.opacity = e;
} });
```

`A` and `B` are the layers of the outgoing and incoming slides. Their inline styles are cleared every frame, so set everything each time. `o.sign` is 1 forwards and -1 backwards; `o.origin`, `o.dir`, `o.color`, `o.dur`, `o.data` (the slide's `data-*`, for options like `data-cell`) and `o.veil` (a full-screen overlay element) are available. Add `opaque: true` to the spec to give layers a card background (but then the stage is hidden during the transition and pops in at the end; prefer transparent layers and masks). `init()` in the spec runs once at load, only if a slide uses the transition: build caches there. A transition is a pure function of `p`, like everything else.

Two rules that the built-in ones follow:

- **Neutral at the ends.** At `p = 0` the outgoing slide must look exactly as at rest, at `p = 1` the incoming one. Easings that do not reach 1 (`outExpo`, `inOutExpo` stop 0.1% short, about 1 px on a full-width move) leave a jump when the transition ends; rescale them, as `whip` and `zoom` do, or use a cubic.
- **Going back.** Use `o.sign` for anything that has a direction, and do not assume `A` is the earlier slide.

## Checking a transition

```bash
node export/deck.mjs strip deck.html strip.png --slide 6 --frames 8
```

Eight frames across the transition into slide 6. Look for: a frame where both slides are unreadable at once, text crossing text, content jumping at `p = 1` (the rest frame differs from the last transition frame), and the background moving when the slides do not.

To test the jump numerically, draw the timeline at the very end of the transition and at the start of the hold that follows (`__draw(t0 + dur - 1e-9)` and `__draw(t0 + dur)`) and compare the screenshots; do the same for `__draw(t0)` against `__deck.show(i - 1, last)`. Test with slides of different background colours: on paper-coloured slides a leftover corner of the outgoing sheet is invisible. Text can differ by a few levels because a composited layer (`will-change`, set during transitions) uses grayscale antialiasing; compare blocks and shapes.
