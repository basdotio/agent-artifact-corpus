# Turner

## What works for Turner (short list)
- Plan the vortex as bands along an elliptical, tilted log-spiral (one band per mass: smoke, trough, snow), not as
  cos(spiral phase) (a galaxy) or isotropic noise (clouds). Streak the plan along the flow with LIC.
- Lopsided, not concentric: a heavy dark wall on one side, an arm of light running out of the frame on the other,
  the boat where the darkest dark (smoke root) meets the lightest light. Rings around a centre read as a galaxy.
- Snow = `spatter` along the flow, masked into flurries near the light, veiled grey over the darks, none in the
  corners. An even sprinkle reads as stars.
- Soft masses (smoke) take their outline from a mask (fill_strokes on its core, stepped glaze, wet_in_wet), never
  from a few big hand strokes: dark strokes on light show every path as a silhouette.
- Thick paint only in the lights, laid as a body pass in the design's own colours; ordinary loaded strokes, not
  `cv.impasto` (its edge lips look piped).
- The sea must read as sea: in the foreground let the strokes run with the swell (level water strokes) and give
  the plan a few big log-spaced swells; a vortex that is concentric all the way down reads as a galaxy or cloud.
- One cool note: a cold grey-green sea against the warm storm. Prussian + white alone goes candy mint; search mixes
  per value stop for hue 110-130 at saturation ~0.1 (prussian + ivory black + a little umber and ochre).

## 2026-09-25 · turner-steamboat-snowstorm · oil

- **Subject and size:** a paddle steamer heeled over at the rim of a vortex of light, snow and smoke, after *Snow
  Storm - Steam-Boat off a Harbour's Mouth*; 2048x1536, seed 7, about 60 s. 15 rounds, 6 fresh-eye critiques and a blind A/B
  for the final (critics put it at 55-65% of a convincing code-painted Turner).
- **Worked:** the design as spiral arcs (`Vortex.arc` in paint.py) plus LIC streaks; a value ramp whose stops sit
  at their own lightness; alla prima block-in (`dry=False`) then `wet_in_wet(0.7, 18*S)` = Turner's rubbed
  passages; the smoke's root as an ellipse along its way out; `spatter` flurries; a body pass in the eye.
- **Failed:** knife slabs (paper cut-outs); scrapes wider than ~10 px (bare linen = holes); `scumble` and
  `dry_bristle` fills (basketwork, zippers on linen); `glaze_wide` (grey rectangles); crackle even at 0.1 (dried mud;
  the old crackle, redone 2026-09-29); `cv.impasto` on narrow strokes (leaves, piped icing); `glaze` with a soft mask
  (dithered edge); dragging the canvas's own colours (scrambles gradients); a smear pass over everything (reads as a
  twirl filter).
- **Parameters that worked:**
  ```python
  cv.ground("yellow_ochre", texture="linen", tone=0.07)
  flow = fields.combine((vortex_field, 1.0), (fields.noise(0.22*W, rng, spread=180), 0.45),
                        (swell, 0.45*sea + 1.6*sea*smoothstep(0.62*H, 0.9*H, y)))    # level strokes up front
  passes = [brush("filbert", size=4*S, impasto=0.02), brush("filbert", size=2*S, impasto=0.05),
            brush("round_bristle", size=0.9*S, impasto=0.09)]
  cv.paint_from_design(design, passes, field=flow, length=(2, 10), tolerance=0.15, blur=0.35, jitter=0.06, dry=False)
  cv.wet_in_wet(storm, strength=0.7, reach=18*S)
  for size, dens, imp in ((3.0, 0.9, 0.2), (1.4, 0.8, 0.25)):                      # body in the lights
      cv.fill_strokes(eye_core, flow, brush("filbert", size=size*S, impasto=imp, pickup=0.5), design,
                      density=dens, length=(160*S, 480*S), jitter=0.02)
  cv.spatter(flurries * lit, [snow_g, snow_g, snow_w], density=0.03, size=2.2*S, stretch=8, field=flow, broken=0.65)
  water_mid = pal.mix(("lead_white", 0.6), ("prussian_blue", 0.3), ("ivory_black", 0.35), ("burnt_umber", 0.35),
                      ("yellow_ochre", 0.12))                                      # cold grey-green, L 0.65
  cv.finish(light=(-0.5, -0.6), varnish=0.25, weave=0.25)                          # no crackle
  ```
- **Kit gaps:** circular `fields.vortex` only; no LIC helper; `fill_strokes` makes horizontal one-point dabs wherever
  a stroke can't take a step inside its mask (soft margins, small islands: use a hard mask at 0.5 and keep its largest
  region); `glaze` thresholds soft masks; scumble has no direction. (Crackle was all-or-nothing; redone 2026-09-29,
  see kit.md.)
  Extended the kit with `spatter`.
- **Next time:** start from the lopsided S, not a centred vortex; check 2048 px and a hand crop of the boat from
  round 2; ask the fresh-eye critic early and use blind A/B between versions (critics' percentages drift).
  Unsolved: the sea never read as sea (soft cloud); try foam as broken strokes along swell crests over dark,
  hard-edged troughs, and keep eye strokes short (long ones carry the core colour to the rim as a "comma").
- **Files:** `paintings/turner-steamboat-snowstorm/`, in the project where it was painted.
