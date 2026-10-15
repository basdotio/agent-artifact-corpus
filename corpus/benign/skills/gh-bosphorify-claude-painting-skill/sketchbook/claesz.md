# Pieter Claesz / Willem Claesz Heda

## 2026-09-27 · claesz-snuffed-candle · oil

- **Subject and size:** a monochrome banketje at the moment just after: a pewter candlestick with a mid drip-pan and
  a candle blown out a breath ago (glowing wick, one thread of smoke rising into the dark), a glass beaker with a
  last mouthful of wine, a pewter plate at the table's edge with a broken roll and a knife. 1536x2048 upright, seed
  7, 10,094 strokes, 50 s. 15 rounds, 2 fresh-eye checkpoints (32 -> 34 of 60), one blind A/B (r11 over r14, then
  merged).
- **Worked:**
  - Objects as lathe-turned solids in scene code: a z-buffered splat rasterizer (profile (r, h) -> samples round
    the axis), with ellipses flattening toward eye level. The pewter is lit by reflecting a window (upper left,
    reaching down to its sill), a dark room and the table. The glints come from where the window reflects sharply.
    Correct ellipses and metal came for free.
  - The background painted alla prima from a plan with the objects left out, each region blurred only inside itself,
    then melted wet-in-wet (0.85, reach 24*S). The objects are painted afterwards on the dry wall. This gives no
    halos and a soft, breathing wall.
  - Objects laid in lightness zones: one `fill_strokes` per quantile band of the plan's lightness inside each
    object, so strokes never carry a light across into a dark. Then a local-tone pass over the full silhouettes, and
    a masking tape (restore the dry canvas more than 1.5 px outside each silhouette): clean edges without a cut-out
    look, because the shadow sides are lost afterwards with `wet_in_wet`.
  - The smoke as long soft strokes stacked by height, thin and dense at the ember, wider and fainter up, with one
    faint weaving line for the twist, melted, then a faint white veil. The blind A/B preferred this single thread
    to one that frays into three wisps (the wisps read as a steam icon).
  - Glass: the wall seen through it (slightly shifted near the sides), one broken lit glint on the left, the rim's
    front-left arc, four small window panes; the right side lost into the wall.
- **Failed:**
  - A plain Gaussian "calmed plan" spread the candle's white into the wall: a halo that made the candle look lit.
  - Short overlapping smoke segments gave a string of beads; side wisps read as a sprouting plant.
  - `fill_strokes` over pewter without zones gave mottled stone; `flat_bristle` tracks read as bark; drying between
    the object passes kept every stroke visible.
  - `cv.impasto` touches on the crumb read as seeds or almonds (the lips outline them); ochre + umber mixed olive.
  - Critics put style at 5/10 twice: it reads partly as a modern tonal study. The wall and table are darker and
    browner than Claesz's silvery greys, and the objects stand apart.
- **Parameters that worked:**
  ```python
  cv.ground(pal.mix(("raw_umber", 1), ("yellow_ochre", 0.6)), texture="panel", tone=0.45)
  wall = fields.combine((fields.constant(-58), 1.0), (fields.noise(0.15 * W, rng, spread=70), 0.8))
  cv.paint_from_design(plan_without_objects, [brush("filbert", size=3.4 * S, impasto=0.02),
                       brush("flat_bristle", size=1.5 * S, impasto=0.04), brush("round_bristle", size=0.8 * S, impasto=0.05)],
                       field=flow, length=(2, 8), threshold=0.04, tolerance=0.08, blur=0.3, jitter=0.03, dry=False)
  cv.wet_in_wet(soft(wall, 4 * S), strength=0.85, reach=24 * S)
  # objects: zones by lightness quantiles, filbert 0.8*S impasto 0.03 density 2.8, then round_bristle 0.42*S and
  # round_soft 0.24*S on error > 0.07; wet_in_wet inside each form (reach 7-9*S, 0.7); tape; shadow sides lost
  crust = tone(0.44, ("raw_sienna", 1), ("burnt_umber", 0.6), ("yellow_ochre", 0.4), ("raw_umber", 0.5))
  cv.finish(light=(-0.5, -0.6), varnish=0.2, weave=0.2, scale=S)   # 0.35 browned the silvery harmony
  ```
- **Kit gaps:** no extension made (the commission asked not to change the kit). Candidates: a `tolerance` for
  `fill_strokes` (stop where the design's colour changes), a zone fill, and a masking-tape or frisket technique. A
  lead-white `glaze` barely lightens a dark (+3 L* at strength 1), so veils and smoke need strokes.
- **Next time:** a lighter, more silvery wall (L* 30-45 behind the objects, the dark kept only round the focal
  point) and overlapping objects in a diagonal group. Try a roemer and a lemon peel only after the lathe objects
  are solid.
- **Files:** `paintings/claesz-snuffed-candle/`, in the project where it was painted.
