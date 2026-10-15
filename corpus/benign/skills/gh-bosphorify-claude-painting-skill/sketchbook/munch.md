# Edvard Munch

## 2026-09-27 · munch-moon-road · oil

- **Subject and size:** a woman seen from behind at the end of a jetty on a pale midsummer night, where the moon's
  column of light begins (Munch's "i"); lime trees and the sinuous shoreline on the left, empty fjord on the right.
  1536x2048 portrait, seed 7, about 60 s. 9 rounds, 3 fresh-eye critics (35 -> 41 -> 42 of 60), one blind A/B.
- **Worked:**
  - The value plan mixed to exact lightness (`tone()` in paint.py): moon and column L* 87-88, sky 25-54, fjord
    16-40 and a step below the sky, trees and figure at the palette's floor (L* 14-17).
  - The column as a flat cream shape with firm, gently wavering edges (continuous edge noise), laid in upright loaded
    strokes with level ripples kept inside it; the figure cutting into it is the focal point every critic agreed on.
  - The jetty on a *Girls on the Bridge* diagonal from the lower left (its own vanishing point on the horizon) beat a
    centred one-point runway in the blind A/B: the runway read as a symmetric wedge or plinth.
  - Munch's thin sweeps: long dragged strokes that run dry over sky and water, after a block-in from a calmed plan.
  - The shoreline as a pale band with a broken dark contour; soft lilac and green-blue bands in the sky.
  - The figure: a silhouette with a gesture (a shawl held at the chest, one elbow out), filled with strokes running
    down between its outlines, closed with an ivory-black glaze, a madder glaze on the shawl.
- **Failed:**
  - Sky and water dabbed evenly by `paint_from_design` (read as Impressionist broken colour) until the calmed plan.
  - A white, narrow-topped, stepped column (read as a flame, then a stacked tower); a soft glow round it (a spotlight).
  - The first figure: fill_strokes + outline strokes gave a birdcage; the column's strokes were laid across her.
  - Trees read as a hill until built as explicit crowns; still a scalloped bank, turquoise until ultramarine replaced
    viridian. Critics put style at 5-6: the motifs are Munch, the hand less so.
- **Parameters that worked:**
  ```python
  cv.ground("raw_umber", texture="linen", tone=0.3)
  passes = [brush("filbert", size=3.2 * S, impasto=0.02, load=0.85), brush("flat_bristle", size=1.4 * S, impasto=0.05),
            brush("round_bristle", size=0.7 * S, impasto=0.08)]
  cv.paint_from_design(plan, passes, field=flow, length=(4, 18), threshold=0.06, tolerance=0.1, blur=0.3)  # plan: bands blurred out
  cv.fill_strokes(sky_or_water, flow, brush("filbert", size=1.6 * S, impasto=0.02, load=0.55, opacity=0.8), design,
                  density=0.8, length=(450 * S, 1200 * S), jitter=0.05)          # long strokes that run dry
  sky field: angle = 9 deg * cos(2 pi x / 0.9 W + 1.4 sin(2 pi y / 0.45 H)) + noise   # bands that rise and fall
  column: exp(-across ** 6); fill_strokes upright, flat_bristle 0.8 * S, impasto 0.25, load 1.2
  cv.glaze(figure, "ivory_black", strength=0.9); cv.glaze(shawl, "madder_lake", strength=0.35)
  cv.finish(light=(-0.5, -0.6), varnish=0.05, weave=0.3, scale=S)                # unvarnished, matte
  ```
- **Kit gaps:** no extension made. `wet_in_wet` pulls wet paint from outside its mask (brown smears from the jetty);
  a "fill a silhouette" technique and a `tone()` palette helper are candidates. Details in `kit.md`.
- **Next time:** start from the calmed plan and long dragged strokes; try Munch's flatter fields held by long dark
  outlines (fewer, larger shapes), real lime trees with trunks and their reflection, the woman in white (*The Voice*).
- **Files:** `paintings/munch-moon-road/`, in the project where it was painted.
