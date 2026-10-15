# Vilhelm Hammershøi

## 2026-09-27 · hammershoi-farthest-room · oil

- **Subject and size:** a woman in black at the window of the farthest of three rooms, seen through two open double
  doorways; low winter sun through her window lays a barred patch and her long shadow on the empty middle floor; a
  closed panelled door in the near wall. 1536x2048 portrait, seed 7, about 45 s and 34k strokes per render.
  24 render-and-look rounds; fresh-eye critics 37 -> 40 -> 40 of 60 (plateau), three blind A/Bs (the last one
  won 6/6 by the final).
- **Worked:**
  - The design as a small ray cast of the rooms in metres (planes with holes: doorways with reveals, a window
    embrasure with glazing bars). Exact one-point perspective and floorboards that converge on her. The sun patch,
    her shadow and the bars' shadows come from tracing each floor pixel back to the sun through the window, the
    doorways and her silhouette, with a jittered sun for a penumbra that widens with distance. Tracing again
    without her or without the bars gives exact masks for each shadow.
  - One light, contre-jour, through her window: the rooms step lighter toward her by themselves, and her shadow
    carries the story. Side windows lighting the middle room made big bright patches that fought the figure.
  - Values set per pixel through `tone()` ramps (`Material` in paint.py): walls 0.42 / 0.60 / 0.75 room by room,
    woodwork about 0.12 paler than its own wall (his white doors), floors 0.34 / 0.50 / 0.62, sun on the floor
    0.76-0.80, window 0.95, dress about 0.10. Critic 1 found two steps instead of three until the rooms were this far
    apart.
  - His grey: ivory black + ultramarine 0.3 + yellow ochre 0.12 + raw umber 0.22, lightened with lead white. Ivory
    black + lead white alone is a warm taupe in the spectral mix.
  - His wall surface: a quiet near-vertical grain of short strokes (the whole block-in at `length=(1, 3.5)`; only the
    boards get long strokes), a few big dry filbert strokes, and a scumble at the wall's own value + 0.025,
    coverage 0.3.
  - A closed door beside us against the open ones: it fills the empty near wall, and it means something.
  - The figure at 280 px: a smooth outline (the profile's control points joined by `catmull_rom`), upright
    underlayer and strokes between the outlines at impasto 0, `wet_in_wet` inside to melt the ribbing, one
    ivory-black glaze on the eroded body. Then the window cut back in round her *along* her contour
    (`fields.contour`), in the colour of the paint just beyond, and one unbroken outline stroke per side. The nape is
    a dense fill in a small mask; the hair is three crossing fills in an ellipse with a curved hairline. The
    background strokes near her take their colour from a copy of the design without her.
- **Failed:**
  - Long strokes on an upright field dissolved the architecture into curtains. A noise field on a big flat wall
    shows its pattern from across the room: damask at a large scale, marbling at a small one.
  - The small head (28 px) took five rounds. Contour-following hair strokes made a spiral that read as a *face*. A
    cut-in halo became a saint's halo. Vertical window strokes left horns on the round crown. A light thread on the
    crown plus the glazing bar above read as a hat brim.
  - Glazes on a figure's own mask (brown, or with `pooling`) spill a pixel onto the light behind it: a tan outline.
  - Raising paint to bury the weave (`cv.height += ...` in the dress, the panes) puts a relief step at every
    outline. Filling `cv.tooth` there buries the weave with no step at all.
  - Shadows glazed darker than the unlit floor read as rugs; the A/B critic caught it (L* 40 against 51).
  - A thin band (the nape, 9 px tall) filled on its own leaves the window showing above and below it: the head floats.
    Lay the whole head and neck dark first, then the nape inside it, in shadow when the figure is backlit.
  - Critics put paint quality at 1:1 at 5-6 throughout: the even weave and bristle drag still read partly as a filter.
- **Parameters that worked:**
  ```python
  cv.ground("raw_umber", texture="cotton", tone=0.32)          # linen read as burlap through the black
  passes = [brush("filbert", size=2.4 * S, impasto=0.02, load=0.85), brush("flat_bristle", size=1.1 * S, impasto=0.03),
            brush("round_soft", size=0.7 * S, impasto=0.03), brush("round_bristle", size=0.35 * S, impasto=0.03)]
  cv.paint_from_design(design, passes, field=flow, length=(1.0, 3.5), threshold=0.022, tolerance=0.045, blur=0.25,
                       jitter=0.02)                              # low threshold: frames only 0.04-0.1 L* off their wall
  walls = fields.combine((fields.constant(90), 1.0), (fields.noise(0.1 * W, rng, angle=90, spread=20), 0.5))
  cv.scumble(soft(plain_wall, 2 * S), wall_colour_at(L + 0.025), coverage=0.3, size=0.5 * S)
  shade = pal.mix(("ivory_black", 1), ("ultramarine", 0.35))   # every shadow on the floor, one neutral grey
  cv.glaze(her_shadow * floors, shade, strength=0.1, pooling=0.0)   # at the unlit floor's value; 0.3 read as a rug
  cv.glaze(bar_shadows * floors, shade, strength=0.1, pooling=0.0)  # bar_shadows = lit(no bars, frame kept) - lit
  cv.glaze(dress_eroded_2px, "ivory_black", strength=0.6, pooling=0.0)   # figure strokes at impasto 0
  cv.tooth *= np.clip(1 - (0.65 * dress + 0.6 * panes + 0.5 * sunlit + 0.35 * mottle), 0.2, 1)  # fat paint fills the
  cv.finish(light=(-0.5, -0.6), varnish=0.03, weave=0.33, scale=S)                             # weave, no relief step
  ```
- **Kit gaps:** none extended. `paint_from_design` keeps a stroke's first steps whatever the colour, so small brushes
  overshoot a silhouette by about half a width (the "horns"). `fill_strokes` with a design image takes colour at the
  stroke's start and never stops at a colour change, so paint the background from a copy of the design without the
  figure. `glaze` on a hard figure mask rims it. A stroke shorter than its width leaves bristle gaps. A
  "fill a silhouette" technique would have saved most of the figure rounds (Munch's entry asked for it too).
- **Next time:** judge zooms nearest-neighbour: a Lanczos upscale rings at a hard dark/light edge and shows a halo
  that is not in the painting (it cost three renders here). Give the figure more pixels (stand her a metre nearer, or
  crop tighter) so the head is not a 28 px problem. Try his empty version of the same rooms (only the light and the
  open doors) as a pendant, and open white door leaves (*White Doors*), which checkpoint 3 missed.
- **Files:** `paintings/hammershoi-farthest-room/`, in the project where it was painted.
