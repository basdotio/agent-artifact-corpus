# Kit lessons

Lessons about the kit itself rather than a painter: tools that misbehave, traps, habits that saved time.

## 2026-09-27 · from munch-moon-road (oil)

- **`wet_in_wet` does not isolate its mask.** Each masked pixel takes the mix of all wet paint within about `reach`
  (and 3x further along `angle`), including wet paint outside the mask. A level blend (`angle=0`) over water next to a
  freshly painted jetty dragged its brown sideways into the water as smears 40-60 px long. Keep the mask about
  3 x `reach` clear of wet shapes that must not bleed (`distance_transform_edt(shape < 0.5) > 45 * S`), or `dry()`
  them first.
- **Plan values numerically.** A `tone(L, *parts)` helper in `paint.py` (mix, then bisect the weight of white or ivory
  black until `lightness` = L) made the value plan exact and fixed a first design that read as daytime. Zinc and lead
  white are strong in Kubelka-Munk mixes: a little white lifts a dark a lot. Ivory black alone is L* 14, the darkest
  the palette reaches, so plan darks at 0.14 and above: a target below it collapses every dark to pure black.
- **Ochre or naples with ultramarine or cobalt mixes green** (spectral mixing): grey a pale warm with madder, not blue.
- **Masks that meet at the horizon:** `water = y >= hz` with `land = y > hz` leaves a 1 px row of water under the land,
  which the strokes turn into a pale line. Use the same comparison on both sides.
- **Per-row noise looked up with an integer index gives stepped edges** (a column of light that read as a stacked
  tower). Interpolate 1D noise (`np.interp`) wherever it shapes an edge.
- **Small dark silhouettes (a figure 200 px tall):** `fill_strokes` with a small brush leaves pale gaps, and strokes
  along the outline cross at the shoulders. What worked: a dense upright underlayer inside a slightly shrunk mask, then
  strokes that run down between the two outlines (each at its own share of the way across), then a transparent
  `ivory_black` glaze (strength 0.9) over the mask. Keep every later light stroke off the figure's mask. A candidate
  for a kit technique ("fill a silhouette").
- **A calmed plan for `paint_from_design`.** Big fields (sky, water) painted from the full design get dabbed evenly by
  the small brushes, because every band and ripple raises the error. Blurring the bands out of the plan the block-in
  sees (normalized Gaussian inside the field's mask) leaves them as broad thin fields; long dragged strokes
  (`fill_strokes`, filbert, `load=0.55`, length 450-1200 px, colours from the full design) then carry the bands.

## 2026-09-29 · the aged surface (plan-006 P1)

- **Craquelure redone, because the old one read as dried mud.** It drew one isotropic Voronoi net of dark grooves
  (Y-junctions, 60-100 px cells) whose cells changed with the amount, the same on panel and linen. Now the network is
  fixed by the canvas (seed, size, support, paint thickness) and `crackle` opens more of it: first cracks in patches,
  then the islands between them, then finer ones, all T-junctions. They are hairlines that show through the light (a
  cupped island's lit lip on the lamp side, a shadow on the other), not painted lines. On `panel` they run with the
  grain, the long way of the panel (a blind critic's first objection was cracks across an upright panel's planks);
  on canvas they have no direction.
- **`grime` and `edge`** age the varnish: patchy amber, deeper in the hollows and toward the edges, dirt in the
  cracks, the strip under the frame's rebate. A strong veil greys everything and reads as a filter; keep grime at
  0.2-0.4.
- 17th-century panel: `varnish=0.5, crackle=0.55, grime=0.3, edge=0.025` (techniques.md, Finish). Defaults are
  pixel-identical to before (Claesz and Munch re-rendered byte for byte).
