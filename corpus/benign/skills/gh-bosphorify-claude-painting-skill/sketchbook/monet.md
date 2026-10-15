# Claude Monet

## 2026-09-27 · monet-ice-floes · oil

- **Subject and size:** the ice going out on the Seine at sundown (Lavacourt, winter 1879-80): a low sun just above
  a dark far bank, its road of broken gold through a gap in drifting floes, two near plates that have just split
  apart. Emotion: release. 2048x1365, seed 7, about 55 s, 13.8k strokes. 16 rounds, 2 fresh-eye critics (34 -> 33
  of 60), 2 blind A/Bs chose the final.
- **Worked:**
  - Broken colour at equal value: the plan's chroma pulled toward a pigment's hue in OKLab at unchanged lightness
    (`hue_shift` in paint.py), laid in partial-density passes, cool tints high in the sky and on water, warm low down.
  - Touches as tapered filberts at load 0.62, two sizes per pass, in patches: they break up on the weave and read as
    paint. The sky's block-in melted with a level `wet_in_wet` first, then only long sweeps (1880 skies are fluid).
  - Floes laid out in world metres on the water plane and projected (eye 6 m, thin plates): true foreshortening;
    drifts gathered into rafts round a few centres; near plates as snowy slabs in thick lumpy flat strokes.
  - The sun's road as filbert dashes (3-point paths, pressure [0.3, 1, 0.4]), narrow and brightest under the bank,
    wider, dimmer and more broken toward us, violet dashes between; dark floes across it with a gold rim.
  - A near-white disc with a cadmium-orange rim over a hot lemon glow, above the darkest band (the backlit bank).
- **Failed:**
  - The planned *Impression, Sunrise* sun (same value as the sky, hotter hue): both critics lost it in the squint.
  - A one-point dab for the disc (embossed crumpled star); vortex strokes in the disc (fingerprint grooves under the
    raking light); a ring of cut-in strokes round it (a drawn circle).
  - flat_bristle touches at load 0.75: flat opaque rectangles at 2048 (pasted paper). Waterlines round every floe
    (pills). Rose touches on open water (read as more ice). A global greying toward pearl lost a blind A/B: it read
    as milky and moved the strongest colour off the sun.
  - Still weak: one level dash dominates sky and water; middle floes partly rows of capsules.
- **Parameters that worked:**
  ```python
  cv.ground("yellow_ochre", texture="linen", tone=0.12)
  passes = [brush("filbert", size=2.4 * S, impasto=0.03), brush("filbert", size=1.2 * S, impasto=0.08),
            brush("round_bristle", size=0.6 * S, impasto=0.12)]
  cv.paint_from_design(design, passes, field=flow, length=(2, 8), threshold=0.05, tolerance=0.12, blur=0.3, jitter=0.07)
  cv.wet_in_wet(soft(sky_45px_clear_of_land, 4 * S), strength=0.55, reach=16 * S, angle=0)   # a fluid sky
  touch = brush("filbert", size=sz * S, impasto=0.12, load=0.62, bristle_jitter=0.5, opacity=0.9)
  cv.fill_strokes(region * (mottle > t), field, touch, hue_shift(design, tint, 0.3 - 0.5), density=0.15,
                  length=(120 * S, 360 * S))                    # sky; water (50, 220) * S; per tint, sizes 0.7x and 1.3x
  cv.fill_strokes(near_plate_tops, level_plus_noise_spread_20, brush("flat_bristle", size=0.9 * S, impasto=0.45,
                  load=1.0), design, density=0.7, length=(25 * S, 90 * S))
  cv.finish(light=(-0.5, -0.6), varnish=0.03, weave=0.15, scale=S)                           # unvarnished
  # values (L*/100): disc 0.96, glow 0.84, sky 0.66-0.81, bank 0.22-0.33, water 0.34-0.52, road head 0.9-0.93
  ```
- **Kit gaps:** no extension made. A one-point `stroke` with a wide round brush and impasto embosses into a star;
  `fill_strokes` on masks with room for exactly one step lays round dabs that glint as dots under `finish` (filter
  masks by area); no equal-value broken-colour helper (`hue_shift`) and no water-plane perspective helper; `tone()`
  again useful.
- **Next time:** put the sun above its glow in the value plan from the start; paint the sky fluid before any touch;
  vary the stroke vocabulary (crossing strokes, drags, scumbles over dry paint) rather than one level dash; try a
  series motif of the 1890s (Haystacks, Poplars, Parliament in fog) for the encrusted surface.
- **Files:** `paintings/monet-ice-floes/`, in the project where it was painted.
