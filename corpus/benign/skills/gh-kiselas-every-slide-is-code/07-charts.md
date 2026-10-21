# Charts

## Choose the chart from the question

| The slide says… | Chart |
|---|---|
| A is bigger than B | bars, sorted, one highlighted |
| It went up / down | line; area if volume matters |
| How the total splits | stacked bar or a donut with at most 4 parts; bars if parts must be compared |
| What got us from X to Y | waterfall |
| One in N | unit chart (a grid of squares) |
| How big the market is | nested circles (TAM/SAM/SOM), with the numbers written in |
| Where we sit | 2×2 matrix with labelled dots |
| Plan vs actual | bars or a line with a target marker; red only for misses |
| One number | big number and its comparison, not a chart |
| Conversion through stages | funnel or bars with the drop-off annotated |

The title states the answer ("Team C closes tickets twice as fast"). The chart proves it. The highlight points at the proof.

## Honest charts

- Bars start at zero. Lines may start elsewhere; mark the axis.
- No 3D, no dual axes. Two series with different units are two charts, or both indexed to 100.
- Pies and donuts: 2–4 parts, sorted, starting at twelve o'clock.
- Label values on the marks rather than forcing a trip to the axis; keep axes and grids light (the `rule` colour, dashed).
- Annotate the point on the chart itself ("Switch in June", "16-point gap"), not in a legend.
- Colour: the series that matters gets the accent, everything else is ink or muted.
- Write the unit and the period on the chart; the source in the footer.

## Pattern: build in setup, animate in frame

```js
Deck.slide('bars', {
  steps: 1,
  setup(el, { svg, scaleBand, scaleLinear }) {
    const g = el.querySelector('svg'), data = [['A', 41], ['B', 47], ['C', 96], ['D', 38]];
    const x = scaleBand(data.map(d => d[0]), [0, 1620], { padding: .38 });
    const y = scaleLinear([0, 100], [480, 20]);
    el._bars = data.map(([k, v], i) => ({ i, v, win: k === 'C',
      rect: svg('rect', { x: x(k), width: x.bw, rx: 6, fill: 'var(--accent)' }, g),
      val:  svg('text', { x: x(k) + x.bw / 2, 'text-anchor': 'middle' }, g) }));
    el._y = y;
  },
  frame(el, st) {
    for (const b of el._bars) {
      const p = st.p(0, b.i * .08, 1, Deck.ease.outExpo);          // grow, staggered
      const h = (480 - el._y(b.v)) * p;
      b.rect.setAttribute('y', 480 - h); b.rect.setAttribute('height', h);
      b.val.setAttribute('y', 462 - h); b.val.textContent = Math.round(b.v * p);
      const fade = b.win ? 1 : Deck.lerp(1, .22, st.p(1, 0, .5));  // step 1: the others step back
      b.rect.style.opacity = fade;
    }
  },
});
```

`setup` creates the marks once with the scales. `frame` sets geometry from `st.p(...)`. The rest frame of step 0 is the full chart; step 1 adds the highlight.

## Recipes

**Bars growing.** As above. Horizontal bars (a ranking) grow along x: set `width`. Put the value label at the end of the bar and move it with the bar.

**Line drawing itself.** One path with `pathLength="1"`, then `path.style.strokeDasharray = `${p} 1``. A dot at the head: `Deck.pointAt(path, p)`. For several series or an area under the line, clip the whole group with a `<clipPath>` rect whose width grows with p; the area, the lines and the fill of a gap between two lines then reveal together (demo slides 4 and 10).

```js
const clip = svg('clipPath', { id: 'trend-clip' }, svg('defs', {}, g));
el._clip = svg('rect', { x: 0, y: 0, width: 0, height: 1080 }, clip);
svg('g', { 'clip-path': 'url(#trend-clip)' }, g);   // put the lines and the area in here
// frame: el._clip.setAttribute('width', 1400 * st.p(0, 0, 1.8, Deck.ease.inOutCubic));
```

**Donut.** One path per part; in `frame`, grow each part's end angle with its own delay: `arcPath(cx, cy, r0, r1, a0, lerp(a0, a1, p))`. Leave a small gap (0.012 rad) between parts. A number in the hole says what the donut means ("15× return").

**Waterfall.** The start and end totals grow from the baseline; each change is a floating bar that drops from the previous level, one per step, with a dashed connector at the level. The final total gets the "good" colour and the headline delta (demo slide 8).

**Unit chart.** A 10×10 grid of squares, one per unit. Step 0: squares appear in a diagonal wave (`delay = (row + col) * 0.028`). Step 1: the N that matter change colour with a seeded order (demo slide 2). Give each square `transformBox: 'fill-box', transformOrigin: 'center'` before scaling it.

**Nested circles (market size).** Three circles resting on one baseline, outer to inner, one per step, each labelled inside with the count and the value. The innermost one, the target, gets the accent.

**2×2 matrix.** A square with dashed midlines, axis labels at the ends ("Guesses waste → Weighs waste"), competitor dots in a stagger, your dot last with a pulse (`st.life`) and the accent.

**Big number.** `<div data-anim="count">$3,900</div>`: it counts up to the text in the markup, so the rest frame is exactly what you wrote. Use `tabular-nums` (the runtime sets it) so digits do not jitter.

**Plan vs actual.** Bars for actuals, a short horizontal tick for the plan on each bar; misses in the accent, hits in ink.

## When to reach for a library

For a sankey, a treemap, a map projection or a force layout, load the d3 module you need from jsDelivr as a UMD `<script src>` (so `bundle` can inline it), compute the layout once in `setup`, and still animate in `frame`. Avoid library chart animations: they run on their own clock, cannot be jumped to a rest frame, and look like every other dashboard.
