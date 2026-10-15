# Vincent van Gogh

## 2026-09-27 · vangogh-open-gate · oil

- **Subject and size:** "This Morning the Gate Was Open": we stand in a walled field of young wheat at sunrise; the
  sun is still behind the wall, the field in its blue shadow, the sky on fire over the coping; the gate stands open
  and a path of gold runs from it across the rows toward us. One emotion: hope. 2048x1624 (size-30 canvas), seed 7,
  about 63 s, 15,034 strokes.
  11 rounds and a final look, 3 fresh-eye critics (33 -> 37 -> 39 of 60, stopped as the gains shrank), one
  blind A/B.
- **Worked:**
  - The scene as one idea with one light: the sun hidden behind the wall just right of the gate, so the blaze in the
    opening is the one white (L* 87 against the rays' 74 and the wall's 27) and nothing outshines it.
  - Rays and halo rings round the hidden sun (his own device), painted by zone with pure fields: `fields.radial`
    inside a ragged rim (rays of uneven length, `noise1` over the angle), `fields.vortex(twist=1)` rings outside it,
    level bands beyond. Strokes stop at the rims, so none bends through an elbow.
  - A warm sky: stops lemon-white, chrome yellow, orange, peach, rose, lilac-blue, cobalt. Lemon mixed toward blue
    passes through green, and a green glow killed the warm/cold contrast that carries the hope.
  - The field as young wheat, not a lake: rows that converge on a point far to the left and bow; violet earth laid
    along them (`angle_field(row_theta)`, the gradient of the same row phase), and in each green row short upright
    blades (round bristle, near-vertical field, 7-64 px by depth) in a mask of the row blurred upward; the blades lit
    gold-green inside the path, so the light falls in bars across the rows. Horizontal strokes alone read as water.
  - An under-plan a step deeper than the design for the block-in, so the gaps between dashes show a darker tone of
    the same colour; dashes in several passes of different brushes, sizes and lengths.
  - Violet stone: the wall darkened with ultramarine + madder + sienna, not prussian + sienna (which turns violets
    green-grey); posts of upright dark blue dashes with a broken outline; a door leaf swung out, dark against the blaze.
- **Failed:**
  - The first composition (a high view down on a walled field with the sun over the Alpilles) restaged *Enclosed
    Field with Rising Sun*; changed at round 6.
  - A visible sun disc: a grey plate with spiral grooves (thick lead white under the raking light), and it
    outshone the gate. Thick white paint greys and grooves under `finish()`; keep the brightest light lean.
  - Horizontal wavy bands in the field read as swell; flat-bristle fills read as bricks; a pale cobalt pass read
    as glints on water; hand-drawn rays read as spikes, a clean semicircle of rays as a rising-sun flag; evenly
    spaced rings to the corners read as a star-trail photo (keep tight rings near the light, loosen outward).
  - Block-in strokes drag dark shapes into a bright zone along the field (a post's top pulled into the rays): give
    such shapes the neighbouring colour in the block-in's plan and paint them by hand afterwards.
- **Parameters that worked:**
  ```python
  cv.ground("yellow_ochre", texture="linen", tone=0.1)
  passes = [brush("filbert", size=2.4 * S, impasto=0.04, load=0.9), brush("flat_bristle", size=1.1 * S, impasto=0.08)]
  cv.paint_from_design(under_plan, passes, field=flow, length=(2, 8), threshold=0.05, tolerance=0.12, blur=0.3)
  dashes = fill_strokes(mask, field, brush(kind, size=0.5-1.15 * S, impasto=0.14-0.38, load=1.3), design,
                        density=0.2-1.4 per pass, length=(25-110 * S, 70-300 * S), jitter=0.04-0.07)
  sky by zone: rays = radial field inside a ragged rim (reach 5.4 sun radii, +-14 % with the angle), flat 0.75,
  40-140 px, impasto 0.32; tight rings = vortex(twist=1) out to 1.6x the reach, round 0.6 + filbert 1.1;
  beyond, the ring's pull fades into level bands (weight smoothstep(3.4 reach, 1.6 reach, r)), strokes 30-230 px
  field: filbert earth along the rows (impasto 0.14 in shadow, 0.28 lit); blades round 0.28-0.46, 7-64 px upright
  opening: upright flat 0.42, density 4.5, impasto 0.2, then round 0.32 of sun core + lemon, impasto 0.3
  cv.finish(light=(-0.5, -0.6), varnish=0.05, weave=0.25, scale=S)
  ```
- **Kit gaps:** no chrome yellow or emerald green (his two key pigments): `hex_to_linear("#F2DE3A")` and
  `"#34A56F"` as linear RGB parts of `pal.mix`. `finish()` greys thick light paint. No extension made.
- **Next time:** start from one light and one idea at eye level; paint skies by zone with pure fields; route warm
  skies through peach and rose, never lemon-to-blue. Unsolved: cypresses that read as flames (try a few long
  S-curved strokes per flame, dark outline first), clustered swirls instead of even rings, a gate door that reads.
- **Files:** `paintings/vangogh-open-gate/`, in the project where it was painted.
