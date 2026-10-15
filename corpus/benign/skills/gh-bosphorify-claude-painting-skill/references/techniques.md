# Techniques: the painter's vocabulary in the kit

Snippets assume a painting script like `templates/oil_starter.py`, including its helpers `soft` (a Gaussian-softened mask), `ramp` and `dead_color`, and masks from its design map:

```python
import numpy as np
from atelier import Canvas, Palette, brush, fields, studio
W, H = 2048, 1536
S = W / 2048                      # sizes below are for a 2048 px canvas; multiply by S
cv = Canvas(W, H, seed=7)
pal = Palette(["lead_white", "naples_yellow", "yellow_ochre", "vermilion", "ultramarine", "burnt_umber"])
```

To see what a tool looks like before using it, open the test sheets: `oil/out/stroke_sheet_review.png` (every preset: straight, curved, varying pressure, over wet paint), `oil/out/technique_sheet_review.png` (every technique), `oil/out/design_demo_review.png` (`paint_from_design`), `dry/out/dry_sheet.png` (p5.brush brushes, watercolor bleed, hatching, fields, paper.js washes). Regenerate them with `uv run --project <skill>/oil python <skill>/oil/sheets/<name>.py`. The oil sheets' review sheets crop the weakest tools (dry brush, knife, `glaze_wide`, scumble) first at 1:1.

## Conventions

- **Coordinates** are pixels, x to the right and y down. `Canvas(width, height, seed)`, but arrays are rows first: `cv.shape == (H, W)`, masks are HxW, `np.mgrid[:H, :W]` gives `y, x`.
- **Colors** are a pigment name, `"#rrggbb"`, or a linear RGB triple (what `pal[...]` and `pal.mix(...)` return). The canvas stores linear RGB floats.
- **Design images** (HxWx3): a float array is linear RGB, a uint8 array is sRGB. Colors built with `pal.mix` are already linear. A float array of sRGB values comes out too light; convert it with `atelier.color.srgb_to_linear`.
- **Masks** are HxW, bool or 0..1 float, and `None` means the whole canvas. Soft masks (`scipy.ndimage.gaussian_filter`) give soft transitions: a glaze fades out with the mask (a hard mask gets a ragged, brushed edge instead), scumbles and field weights follow it, and `fill_strokes` starts and runs strokes only where the mask is at least 0.5, so its soft margin thins them out.
- **Paths** are (N, 2) control points in px; a centripetal Catmull-Rom curve runs through them. 3-6 points make a natural stroke, and one point makes a dab.
- **Angles are degrees, with two conventions. This is a trap:**
  - `fields.constant(angle)` and the `angle` of `fields.noise` use image coordinates with y down: 0 = right, 90 = down, **30 falls to the right**.
  - `cv.hatch(angle=...)`, `cv.wet_in_wet(angle=...)` and p5.brush's angles (`hatch`, `flowLine`, `move`) count counterclockwise on screen: 90 = up, **30 rises to the right**.
  - So `fields.constant(-a)` runs parallel to `cv.hatch(mask, color, angle=a)`.
- **State:** `cv.color` (linear RGB), `cv.height` (paint thickness, lit by `finish`), `cv.wet` (0..1, what the brush picks up and `wet_in_wet` moves), `cv.tooth` (weave or paper grain; dry brush catches on it), `cv.underlayer` (the color at the last `dry()`, revealed by scraping).
- **Randomness** all comes from `cv.rng`, so the same script and seed give the same pixels. Pass `cv.rng` to `fields.noise`.
- **Speed** (M-series Mac): 20k medium strokes take about 35 s at 2048×1536; `paint_from_design` with 3 passes takes about 20 s at 2048 px; `finish` 1-2 s (2-4 s with crackle at 2048 px); the starter takes about 10 s at 900 px and 30 s at 2048 px.

## Vocabulary → calls

| Painter's term | In the kit |
|---|---|
| imprimatura, toned ground | `cv.ground(pigment, texture, tone=0.3-0.6)` |
| dead coloring, grisaille, brunaille, verdaccio | the design's values in two pigments (`dead_color` in the starter; `terre_verte` + `lead_white` for verdaccio), laid thin with `fill_strokes`, then `cv.dry()` |
| block-in, laying in | the first pass of `paint_from_design` with a big filbert or flat |
| alla prima | `cv.paint_from_design(..., dry=False)` and `cv.wet_in_wet`: everything stays wet and mixes |
| blending, softening, sfumato | `cv.wet_in_wet` along the edge (small `reach` for sfumato); `round_soft` strokes across it |
| lost and found edges | lost: `wet_in_wet` or a glaze across the edge; found: a hand stroke along it; overall: `tolerance` and `blur` of `paint_from_design` |
| fat over lean | `impasto` override near 0 in the lower layers, preset values on top, `cv.impasto` for the lights |
| glazing | `cv.glaze` over dry paint |
| scumbling | `cv.scumble` |
| broken color | lower `density`, higher `jitter`, `dry_bristle`, `cv.scumble` |
| dry brush | `brush("dry_bristle")`, or `load=0.4` on any bristle brush |
| impasto | `cv.impasto` |
| palette knife | `cv.knife(path, color)` |
| spattering: flicked snow, spray, foam, sparks | `cv.spatter(mask, colors, field=flow, stretch=6)` |
| sgraffito, scraping back | `cv.knife(path, None)`: wet paint comes off down to the layer at the last `dry()` |
| pointillism, divisionism | `cv.stipple(mask, [colors...])` |
| hatching, cross-hatching | `cv.hatch(mask, color, cross=True)` |
| Cézanne's constructive stroke | patches of `cv.fill_strokes` with `fields.constant(a)` per patch, short `length`, `flat_bristle` |
| directional brushwork, a swirling sky | `fields.vortex` / `noise` / `contour` / `combine` driving `fill_strokes` or `paint_from_design` |
| liner work: rigging, branches, grass | `brush("rigger")` hand strokes |
| feathering, foliage dabs | `brush("fan")` |
| varnish, craquelure, raking light, an old master's aged surface | `cv.finish(light=..., varnish=..., crackle=..., grime=..., edge=..., scale=S)` |

## Palette and pigments

`Palette(names)` is the limited palette of the dossier: `pal["ultramarine"]` is its linear RGB, and `pal.mix(("lead_white", 3), ("ultramarine", 1), ("yellow_ochre", 0.3))` mixes like paint (Kubelka-Munk, a port of spectral.js): blue and yellow make green, not grey. Weights are relative, and can be arrays for a whole ramp at once (`pal.mix(("burnt_umber", 1 - t), ("lead_white", t))`). `atelier.color.mix((rgb, w), ...)` mixes arbitrary linear colors. `PIGMENTS[name].note` has a line on each pigment, with its date where it matters: use pigments the painter could have had.

| Family | Pigments |
|---|---|
| whites | `lead_white` (warm, the old-master white), `titanium_white` (1920s, cool, strong), `zinc_white` (1834, cool, semi-transparent) |
| blacks | `ivory_black` (warm, transparent), `lamp_black` (cool, opaque, overpowering) |
| earths | `raw_umber`, `burnt_umber`, `raw_sienna`, `burnt_sienna`, `yellow_ochre`, `red_ochre`, `terre_verte` |
| yellows | `naples_yellow` (pale, opaque), `lead_tin_yellow` (Vermeer's; forgotten after 1750), `cadmium_yellow` (1840s), `indian_yellow` (transparent, glowing; for glazes) |
| reds | `vermilion` (opaque scarlet), `madder_lake` (transparent crimson; for glazes), `cadmium_red` (1910s) |
| blues | `ultramarine` (deep, transparent), `prussian_blue` (1704, cold, very strong), `cobalt_blue` (1802), `cerulean_blue` (1860s) |
| greens | `viridian` (1838, transparent), `terre_verte` |

## Ground

`cv.ground(color, texture="linen", tone=0.35)` primes and tones the support. The toning wash goes on unevenly, pools in the valleys of the weave, and is dry.
- `texture`: `linen` (coarse, irregular weave, the default for oil), `cotton` (fine, even), `paper` (for works on paper, and as a smooth support), `panel` (smooth gesso, for early painting and fine detail).
- `tone`: 0 = white gesso, 1 = the pigment itself, roughly linear in value. Toned grounds of 0.3-0.6 (umber, red earth, ochre) sit under most painting before Impressionism, while `tone=0` with `lead_white` gives the bright white ground of the Impressionists. The ground shows wherever strokes part, so its color sets the temperature of every gap.

## Brushes

`brush(name, size=1.0, **overrides)` loads a preset from `oil/atelier/presets/`. `size` scales the width (a bigger brush also holds more paint), and any preset field can be overridden: `brush("filbert", size=3.2*S, impasto=0.04)`, `brush("round_bristle", load=0.4)`.

| Preset | Width | Reads as | Use for |
|---|---|---|---|
| `round_soft` | 14 px | soft edges, smooth, little texture | blending passages, skies, flesh transitions, soft reflections |
| `round_bristle` | 18 px | tapered hog round with bristle tracks | general work, the last `paint_from_design` pass, details; default for `stipple` and `hatch` |
| `flat_bristle` | 24 px | square end, crisp edges, parallel bristle tracks | planes, block-in, Cézanne patches, crisp lights; default for `impasto` |
| `filbert` | 20 px | rounded ends, softer body | block-in and forms; the first pass and the underpainting |
| `fan` | 40 px | sparse splayed bristles that skip | foliage, grass, feathered cloud edges, hair |
| `rigger` | 4 px | long thin line with a long taper | rigging, masts, branches, reeds, grass blades, calligraphic lines |
| `dry_bristle` | 26 px | low load: skips over the tooth in streaks along the stroke and runs out within a few hundred px | broken color, weathered surfaces, haze; default for `scumble` |
| `palette_knife` | 30 px | solid slab | use it through `cv.knife`, which adds the knife's relief |
| `glaze_wide` | 60 px | wide soft semi-transparent veil with rounded ends (opacity 0.35) | broad veils as strokes; for a true transparent film use `cv.glaze` |

Fields you may override (`oil/atelier/brushes.py` documents all of them): `width_px`, `bristles` (0 = solid), `bristle_jitter`, `load` (paint at the start; below about 0.5 the stroke breaks up early, in streaks that follow the stroke), `depletion` (paint used per px), `dry_threshold` (load below which bristles skip and only catch the tooth), `opacity`, `impasto` (height added per stroke: the fat-over-lean control), `pickup` (how much wet paint the brush drags along), `edge_softness`, `taper_start`, `taper_end`, `color_jitter`, `wobble` (hand wobble of the path).

## Strokes by hand

`cv.stroke(brush, path, color, pressure=None, load=None)` drags a brush along a path and returns the `Mark` (the pixels it touched: `ys`, `xs`, their stroke coordinates `s` along and `u` across, and `coverage`). `pressure` is a scalar or a list, from 0 to 1 (1 = full width): one value per control point sits at the points, and a list of any other length spreads evenly along the stroke, so `[0.3, 1.0, 0.4]` swells and lifts whatever the path. `load` overrides the brush's paint. Over wet paint the brush picks up the color under it and drags it along; over dry paint it covers.

```python
sail = pal.mix(("burnt_umber", 1), ("lead_white", 0.6))
cv.stroke(brush("filbert", size=0.9*S), [[1200, 900], [1230, 960], [1250, 1040]], sail, pressure=[0.3, 1.0, 0.6])
cv.stroke(brush("rigger", size=2.2*S), [[1300, 1044], [1309, 894]], "ivory_black")          # a mast
mark = cv.stroke(brush("flat_bristle"), [[400, 300], [600, 320]], "vermilion")
cv.height[mark.ys, mark.xs] += 0.3 * mark.coverage                                        # extra relief
```

Hand strokes read as painted when their control points aren't perfectly regular: jitter them a little, vary length and pressure, and give related strokes slightly different colors (`pal.mix` with varied weights). `atelier.stroke.catmull_rom(points, spacing)` resamples a path densely, for example to offset it with noise.

## Techniques

Each technique is a Canvas method, draws its randomness from `cv.rng`, and is shown in `oil/out/technique_sheet_review.png`.

### glaze: transparent film

`cv.glaze(mask, color, strength=0.25, pooling=0.5)` lays a Kubelka-Munk film over the paint in `mask`. It tints the lights, leaves the darks dark and keeps the modelling underneath. `strength` is the film thickness: 0.1-0.4 for most glazes, and about 1 approaches the pigment's masstone. `pooling` gathers medium just inside the mask's edge and in the valleys of weave and paint. Glaze over dry paint, and `dry()` afterwards before painting over it, because the glazed area is left wet.

A hard mask gets the ragged edge of a brushed glaze; a soft mask fades the film out smoothly with it, which is the way to glaze a transition. On linen, `pooling` gathers a dark glaze in the valleys of the weave, where it can read as speckle: lower it for a smooth film.

When: unify the temperature of an area, deepen shadows (ultramarine, madder_lake, burnt_umber), warm the lights (indian_yellow, raw_sienna), push a plane back. Transparent pigments glaze best.

```python
cv.glaze(glow_mask, "indian_yellow", strength=0.2)
cv.glaze(soft(shadow_mask, 6*S), "ultramarine", strength=0.25)
cv.dry()
```

### scumble: broken light over dark

`cv.scumble(mask, color, coverage=0.4, size=1.0, brush=None)` scrubs short dry-brush strokes in all directions. The paint catches only on the weave's peaks and on paint ridges, so the layer underneath keeps showing. `coverage` is roughly the share of the area touched (0.2-0.6), and `size` scales the default `dry_bristle` (39 px at size 1).

When: atmosphere and haze over distance, sparkle on water, mist, veiling a passage lighter without losing it, weathered texture.

```python
cv.scumble(soft(hills_mask, 4*S), pal.mix(("lead_white", 3), ("ultramarine", 0.2)), coverage=0.15, size=0.8*S)
```

Keep scumbles sparse and small at first: at `size` above about 1 on a 2048 px canvas, the scrubs show as separate pale blotches. The scrubs go every way, and below a `coverage` of about 0.4 they read as separate patches; for a continuous broken veil use 0.5-0.6, or two sparse passes.

### impasto: thick paint that stands up

`cv.impasto(path, color, thickness=1.0, brush=None, pressure=None)` lays a heavily loaded stroke with bristle furrows, ridges along both edges, a blob where it lands and a crest where it lifts. It returns the Mark. `thickness` is 0.5-1.5 (1 = generous), and the default brush is a `flat_bristle` loaded at 1.8. The relief shows only in `finish()`.

When: the lights (fat over lean), the painter's signature strokes (Van Gogh's ridges, Rembrandt's highlights, Turner's sun), anything that should catch the raking light.

```python
light = pal.mix(("lead_white", 3), ("naples_yellow", 1))
cv.impasto([[1330, 610], [1390, 620]], light, thickness=0.9, brush=brush("filbert", size=1.3*S, load=1.6))
```

### knife: slabs and scraping

`cv.knife(path, color=None, width=30, pressure=1.0, thickness=1.0)` spreads a slab: a flat top with sharp edges and thin ridges where paint squeezes out. It levels any wet paint it crosses and rides over dry paint. With `color=None` the clean blade scrapes: wet paint comes off the tops of the weave, and the layer as of the last `dry()` (`cv.underlayer`) shows through. Returns the Mark.

When: flat planes (walls, rocks, sails, a Courbet sea), levelling wet impasto, sgraffito lines scraped through wet paint.

Current limits: a slab reads as a flat, even rectangle with square ends. Short wide slabs look like pasted paper and long narrow ones like tape. It works best wide (40 px and up at 2048), in a color close to its neighbours, and in few strokes; for small bright accents use `impasto` instead. Scrapes wider than about 10 px lift down to the bare weave on linen and read as holes, so scrape narrow lines. It is one of the kit's weakest tools and a good candidate for improvement.

```python
cv.knife([[300, 800], [700, 790]], pal.mix(("lead_white", 2), ("yellow_ochre", 1)), width=60, thickness=0.8)
cv.knife([[300, 900], [520, 880]], None, width=20)             # scrape a line through wet paint
```

### wet_in_wet: blending wet paint

`cv.wet_in_wet(mask=None, strength=0.6, reach=15.0, angle=None)` lays no paint. It works the wet paint in `mask` together as a clean soft brush would: each pixel takes the Kubelka-Munk mix of the wet paint within about `reach` px (blue into yellow passes through green), and brush marks in the wet paint flatten. Only wet paint moves: what was laid since the last `dry()`, which after `paint_from_design(dry=True)` means the last pass. `strength` is 0.5-0.9 and `reach` 10-25 px at 2048. `angle` (counterclockwise) streaks the mix in one direction. The extra reach along `angle` only works for horizontal or vertical directions; at a diagonal the mix spreads evenly and only the streaks follow the angle.

When: lost edges, sfumato, skies and water where colors melt, softening the last pass inside an atmosphere.

```python
cv.wet_in_wet(glow_mask, strength=0.5, reach=14*S)
cv.wet_in_wet(sky_mask, strength=0.8, reach=20*S, angle=0)     # horizontal streaks, like a dragged soft brush
```

### stipple: separate touches

`cv.stipple(mask, color, density=0.5, size=8.0, brush=None)` dabs paint in small separate touches. `color` can be a list, and each dab then picks one at random so they mix in the eye. `density` is the share of the area covered (0.15-0.6), and `size` the dab width in px.

When: pointillism and divisionism (Seurat, Signac), foliage texture, sparkle, broken light in grass.

```python
cv.stipple(meadow_mask, ["cadmium_yellow", "viridian", "cerulean_blue", "lead_white"], density=0.5, size=9*S)
```

### spatter: flicked specks

`cv.spatter(mask, color, density=0.1, size=4.0, stretch=1.0, field=None, thickness=0.4, broken=0.0, brush=None)` flicks paint off a loaded brush: specks land at random over `mask`, in clumps and gaps (unlike stipple's even grid), their widths spread around `size` px, many small and a few large. `color` is one color or a list picked per speck. With a `field` each speck is a streak `stretch` times as long as it is wide, lying along the field (driven snow, spray, rain); without one they point every way. `density` is the share of the area covered: 0.005-0.05 reads as snow or spray at 2048 px, 0.1-0.3 as a spattered texture. `thickness` is each speck's relief (0 = flat), and `broken` the share of specks that land half dry and break up on the tooth. Returns the number of specks.

When: snow, spray and foam, sparks, rain. Mask it into flurries (a band along the flow, thicker near the light) rather than sprinkling it evenly: an even sprinkle reads as stars.

```python
snow = [pal["lead_white"], pal.mix(("lead_white", 3), ("ultramarine", 0.2))]
cv.spatter(flurries, snow, density=0.03, size=2.2*S, stretch=7, field=flow, thickness=0.2, broken=0.5)
```

### hatch: parallel strokes

`cv.hatch(mask, color, angle=45.0, spacing=8.0, length=None, cross=False, brush=None)` lays parallel strokes `spacing` px apart that stop at the mask's edge, broken into staggered runs about `length` px long (default 7 spacings). `cross=True` adds a layer at `angle + 90`. The angle counts counterclockwise, and the default brush is a round bristle about 0.55 spacing wide.

When: tempera-style modelling, shading that follows a form, driving rain, drawing-like passages in paint.

```python
cv.hatch(shadow_mask, "burnt_umber", angle=60, spacing=11)
cv.hatch(core_shadow, "ivory_black", angle=-30, spacing=12, cross=True)
```

## Painting from a design

### Direction fields

A field is any callable that takes points (N, 2) and returns unit directions (N, 2). Strokes only care about orientation (v and -v are the same). All in `atelier.fields`:
- `fields.constant(angle)`: every stroke at `angle` (y-down degrees).
- `fields.radial(center)`: strokes radiate from `(x, y)`, for sunbursts and light rays.
- `fields.vortex(center, twist=0.8)`: a swirl (clockwise on screen) around `(x, y)`. `twist` 1 = circles, 0 = straight in toward the center, 0.6 = spiral arms 36° off the circle, and a negative value spirals outward as the mirror image.
- `fields.noise(scale, rng, angle=0.0, spread=180.0, waves=24)`: smooth random flow turning over about `scale` px. `rng` is required (pass `cv.rng`). `spread=180` turns every way, and `spread=15` wavers around `angle`.
- `fields.contour(mask, sigma=3.0)`: strokes run along the edges of a mask, or of a color image (a design), and echo them inside and outside the shape.
- `fields.combine((field, weight), ...)`: a seamless blend, where a weight is a number, an HxW array (a soft region mask) or a callable. Mix a little `fields.noise` into every field so parallel strokes don't look ruled.
- `fields.sample(grid, points)`: bilinear lookup of an HxW array at points.

### fill_strokes: cover a region along a field

`cv.fill_strokes(mask, field, brush, color, density=1.0, length=(40, 120), jitter=0.05, pressure=(0.7, 1.0))` returns the stroke paths it painted. `color` is one color, or a design image from which each stroke takes the color at its start. `density` 1 leaves about 40% of the ground showing, 1.5 about 25% and 3 almost none. `length` is (min, max) in **px**. Strokes start and run only where the mask is at least 0.5, so a soft mask's margin thins them out, and a start with no room for one step inside the mask (an island or neck smaller than the brush) is skipped: paint small shapes with a smaller brush or by hand. `mask=None` covers the canvas. `jitter` varies each stroke's color.

When: the underpainting, a region in one color family (a field of grass, a patch of Cézanne strokes), later touch-ups on an error mask.

```python
cv.fill_strokes(None, flow, brush("filbert", size=4*S, impasto=0.0), dead_color(design), density=1.2, length=(80*S, 240*S))
cv.fill_strokes(patch, fields.constant(-35), brush("flat_bristle", size=0.9*S), design, density=1.4, length=(30*S, 70*S))
```

### paint_from_design: block-in and refinement

`cv.paint_from_design(design, passes=3, field=None, threshold=0.04, spacing=1.0, length=(1.0, 6.0), tolerance=0.1, blur=0.25, jitter=0.05, pressure=(0.7, 1.0), dry=True, after_pass=None)` paints the design in passes from a big brush to small ones, like Hertzmann's painterly rendering. It returns per-pass stats: `[{"brush", "width", "strokes", "error"}, ...]`.
- `passes`: an int (brushes chosen for the canvas: a filbert about side/26 wide, flats, a round about side/180), or a list of `Brush` from big to small, which is how you set fat over lean.
- The first pass covers the whole canvas. Later passes start strokes only in cells (`spacing` × brush width) whose error is above `threshold` (sRGB RMS, 0..1), so broken color and underlayers survive where they are close enough. A second call starts again with a full-coverage pass.
- `length` is (min, max) in **brush widths**, unlike `fill_strokes`. A stroke stops early where the design differs from its start color by more than `tolerance` (lower = crisper edges, more strokes) or where the canvas already matches better. `blur` × width is the blur of the design each pass sees (higher = broader, softer).
- `field=None` follows the design's own color edges, and a field (section above) gives the painter's direction.
- `jitter` is per-stroke color variation: 0.05 is even, 0.1 and above is broken color.
- `dry=True` dries between passes and leaves the last pass wet. `after_pass(cv, i)` runs after each pass, for snapshots.
- `from atelier.design import error_map`: `error_map(cv, design)` is the HxW distance to the design, for targeted touch-ups (`fill_strokes` on `error_map(cv, design) > 0.08`).

```python
passes = [brush("filbert", size=3.2*S, impasto=0.04), brush("flat_bristle", size=1.2*S, impasto=0.1),
          brush("round_bristle", size=0.6*S)]
stats = cv.paint_from_design(design, passes, field=flow,
                             after_pass=lambda c, i: studio.snapshot(c, f"pass {i + 1}", dir=out / "progress"))
```

## Finish

`cv.finish(light=(-0.5, -0.6), varnish=0.2, weave=0.3, crackle=0.0, scale=1.0, grime=0.0, edge=0.0, support=None)` photographs the painting under a lamp and **returns a new HxWx3 uint8 sRGB image**. The canvas is unchanged, so you can keep painting and finish again. Save it with `studio.save(cv.finish(...), path)`.
- `light`: the direction toward the lamp in image coordinates, where (-0.5, -0.6) is the classic upper left. A longer vector puts the lamp lower and rakes harder (elevation `sqrt(1 - x² - y²)`); a 3-tuple gives the direction explicitly.
- `varnish` 0..1: gloss, a warm amber tint and deeper darks; 0.1-0.25 for a fresh painting, 0.5 and more for an old master.
- `weave` 0..1: how much canvas texture shows in the light (thick paint buries it).
- `crackle` 0..1: how far craquelure has gone, growing smoothly: about 0.05-0.1 opens a few hairlines in patches, 0.3 is a sparse network, 0.5-0.6 a full one, 1 heavy cracking with finer cracks between. The cracks are hairlines (under a pixel to about 1 px at 2048) that show mostly through the light: the islands between them are cupped, so a crack has a lit lip on the lamp's side, a shadow on the other and a little dirt in the gap. They read as fine dark lines in the lights and pale ones in the darks. Thick paint cracks wider and more sparsely. More crackle opens more of the same network, so a study shows where the final's cracks run, but the hairlines vanish below full size: judge craquelure at 2048 px.
- `support`: the crack pattern. `"panel"`: a roughly rectangular network, long cracks along the wood grain and short ones across; the grain runs the long way of the panel, as its planks do (up an upright panel); a canvas (`"linen"`, `"cotton"`, `"paper"` or `"canvas"`): an irregular polygonal network with no direction. `None` takes it from `cv.ground(texture=...)` (linen without a ground).
- `grime` 0..1: the dirt of centuries and the uneven varnish that goes with it: the amber turns a little patchy and deeper in the hollows of the paint and toward the edges, and a grey-brown veil settles there and in the cracks. 0.2-0.4 for an uncleaned old master; much more reads as a filter.
- `edge`: the rebate band, as a fraction of the shorter side (about 0.02-0.04; 0 = none): the strip a frame covered for centuries, its varnish less yellowed and less dirty, with a line of dust along its inner edge. It shows when the painting is seen out of its frame, as in a museum photograph; a frame drawn around the painting should overlap it.
- `scale`: the canvas size relative to 2048 px, the `S` the script multiplies its sizes by. Pass `scale=S`: the relief is then lit and the craquelure drawn as on the 2048 px render, so a 900 px study looks about as embossed as the final. Without it, heights are lit as they lie in pixels and a study looks heavier. The weave and the bristle furrows stay pixel-sized, so judge the surface itself at the final size.

An old master on an oak panel, about 350 years old: `cv.finish(light=(-0.5, -0.6), varnish=0.5, weave=0.2, crackle=0.55, grime=0.3, edge=0.025, scale=S)` over a `texture="panel"` ground (on linen the same values give a canvas's polygonal network). With `crackle`, `grime` and `edge` at 0 the image is exactly what `finish` gave before they existed, so older paintings re-render unchanged.

## Studio (the eyes)

- `studio.save(canvas_or_png, path, focus=None, canvas=None)` takes a Canvas, an HxWx3 uint8 image (what `finish` returns) or a PNG path, writes the PNG and `<name>_review.png` beside it, and returns both paths. `focus` is up to four (x, y) points in px, each the center of a 1:1 crop that comes first on the review sheet: pass the focal point, which the automatic crops (the busiest windows) tend to miss. Pass `canvas=cv` with a finished image (implied when you save a Canvas) to also write `<name>_stats.json`: the stroke count, seconds since the canvas was made, size and seed, which the gallery label shows.
- `studio.snapshot(canvas, label, dir="progress")` takes a Canvas or an image and writes an 800 px frame `dir/NN_label.png`. The first snapshot into a directory in a run clears that directory's old frames. Pass `dir`, because the default is relative to the working directory.
- `studio.contact_sheet(dir, out=None, columns=4, cell_w=400)` lays the frames out in a labelled grid, `dir/contact_sheet.png` by default.
- `studio.review_sheet(image, title="", focus=None)` returns the sheet and the crop boxes without saving.
- `studio.compare(a, b, out, seed=None, focus=None)` makes a blind A/B sheet of two renders of the same size: both full views and the same two 1:1 crops (the `focus` points first, then the busiest windows of the pair), unlabeled, in an order set by `seed`. Which side is which goes to `<out>_key.txt`, with the seed; `seed=None` picks one at random. Returns the sheet and key paths. How to use it with a critic: `critique.md`.
- Command line: `uv run --project <skill>/oil python -m atelier.studio review file.png [--focus x,y ...]`, `... contact <dir> [-o out.png]` and `... compare a.png b.png [-o ab.png] [--seed N] [--focus x,y ...]`.

## Dry media (p5.brush and paper.js)

The page is `dry/template.html` (p5 2.3.3 and p5.brush 2.2.3 from the local `dry/node_modules`, never a CDN). Copy it next to the painting as `sketch.html`, and render with `node <skill>/dry/render.mjs sketch.html final.png [--progress <dir>] [--no-review] [--timeout <s>]`. `render.mjs` serves the libraries from `/dry/`, so a sketch renders from any folder, and it blocks all network access.

Facts about this setup that the p5.brush README won't tell you:
- **Washes go through `paper.js`** (next section). p5.brush's watercolor fill suits compact washes, but it folds long, thin shapes (a brush stroke) into cellophane ribbons, takes about 250 ms a fill at 2048 px and can't leave holes, and p5.brush has no model of the paper (no tooth, dry brush or granulation).
- **Work at the final size** (2048 px). The paper grain scales with `W`: at 1024 px it shrinks to single pixels and reads as noise. A 2H line at weight 0.6 nearly vanishes at 2048 px; use 1-1.5.
- p5 2.x keeps the drawing buffer, so a layer can read the canvas back (`Paper.read()`); paper.js is built on that. `render.mjs` serves the sketch's own folder at `/`, so helper scripts next to `sketch.html` load (`<script src="scene.js">`).
- **Split the drawing into `LAYERS`, one per frame.** p5.brush flushes after every `draw()`, and a single heavy frame silently drops the strokes that come late in it. If marks at the end of a layer go missing, split the layer.
- **`brush.clip()` does nothing in this version.** Keep marks inside a shape by drawing the shape itself (fill, hatch or mass it) or by computing the lines yourself.
- **Fields are canvas-wide.** `brush.field(name)` applies one field over the whole canvas, and `spiral` is 5-10 vortex centers at random places, so in a small region it can look straight. For a swirl in one place, compute the curve yourself (`beginShape`, `spline`) or register your own field with `brush.addField(name, (t, field) => field)`.
- **The brushes are** (`brush.box()`) `pen`, `rotring`, `2B`, `HB`, `2H`, `cpencil`, `pastel`, `crayon`, `charcoal`, `spray`, `marker`. The README's list (with `marker2` and `hatch_brush`) is out of date. **The fields are** `hand`, `curved`, `zigzag`, `waves`, `seabed`, `columns`, `spiral`.
- The template calls `brush.scaleBrushes(W / 200)` and `angleMode(DEGREES)`, translates each layer to top-left coordinates, and seeds everything from `SEED`. Text goes through `label(text, x, y, size, color)` on a 2D overlay, because WEBGL `text()` would need a font file.

The calls (all used in `dry/sheets/dry_sheet.html` or tested with this template):

| Want | Calls |
|---|---|
| a line or curve | `brush.set(name, color, weight)`, `brush.line(x1, y1, x2, y2)`, `brush.spline([[x, y, pressure], ...], curvature)`, `brush.beginShape(curvature)` + `brush.vertex(x, y, pressure)` + `brush.endShape(close)` |
| a gesture with pressure | `brush.beginStroke('curve', x, y)`, `brush.move(angle, length, pressure)`, `brush.endStroke(angle, pressure)` |
| lines that follow a field | `brush.field(name)`, `brush.flowLine(x, y, length, dir)`, `brush.noField()`; `brush.wiggle(n)` adds hand wobble |
| shapes | `brush.rect(x, y, w, h)`, `brush.circle(x, y, r, irregularity)`, `brush.polygon([[x, y], ...])` |
| a compact watercolor wash | `brush.noStroke()`, `brush.fill(color, opacity 0-255)`, `brush.fillBleed(0-1, 'out')`, `brush.fillTexture(texture 0-1, border 0-1)`, a shape, `brush.noFill()`; for whites, brush strokes, dry brush and lifts use `paper.js` |
| a flat wash | `brush.wash(color, opacity)`, a shape, `brush.noWash()` |
| hatching | `brush.hatch(spacing, angle, {rand, continuous, gradient})`, `brush.hatchStyle(name, color, weight)`, a shape, `brush.noHatch()` |
| a charcoal or pastel mass | `brush.mass(name, color, {strength, precision, gradient})`, a shape, `brush.noMass()` |

`brush.set()` turns the outline on for the next shapes, so call `brush.noStroke()` before fill-only shapes. p5.brush watercolor fills: build light to dark in several translucent layers (opacity 60-150), with bleed 0.25-0.35 for big wet washes and 0.1-0.15 for smaller drier ones, and `fillTexture(0.4, 0.4)`. Pencil: `2H` for construction, `HB` for mid-tones, `2B` and `charcoal` for darks, with hatching (`spacing` 4-10 at 1200 px) for value; `mass('charcoal', ...)` gets dark quickly, so try `strength` 0.3-0.5 first.

### paper.js: the sheet, and the marks that depend on it

`dry/paper.js` (loaded by `template.html`) models the paper under dry media and computes the marks that need it on the canvas pixels: washes that leave whites, brush strokes that run dry, dry brush, lifts, granulation. It is seeded from `SEED`, draws nothing from p5's random stream, and scales its grain and pooling with `W`; stroke widths you pass are in px, so write them as `40 * S` with `S = W / 2048`, as in oil.

- `Paper.init(W, H, SEED, { kind, grain })` in `setup()` (the template does it): `kind` is `'cold'` (cold-pressed watercolor paper), `'rough'` (bigger, stronger bumps), `'hot'` (smooth: hot-pressed, bristol) or `'laid'` (charcoal paper with laid and chain lines); `grain` scales the bumps (1 = about 1 mm on a sheet 50 cm wide).
- `layerFn.tooth`: a p5.brush layer with a tooth keeps its marks only where they catch on the grain (charcoal, conté, pastel, pencil): 0.5 leaves only the deepest pits clean, 0.8 marks only the peaks, and heavier marks reach further into the pits. Set it after the list: `LAYERS.find(f => f.name === 'charcoal').tooth = 0.6`.
- `Paper.paint(buf => { ... })`: a layer of pixel marks, where `buf` is the canvas as RGBA bytes. Keep p5.brush calls out of that layer: they are drawn when the frame ends, on top.

| Call (inside `Paper.paint`) | What it lays |
|---|---|
| `Paper.shape(buf, polygon, color, opts)` | a wash over a polygon `[[x, y], ...]`, over a list of polygons as one wash, or over a raster mask `{ mask, x0, y0, w, h }` (a Float32Array of 0..1) |
| `Paper.stroke(buf, pts, width, color, opts)` | a loaded brush along a curve through `[x, y, pressure?]` points, swelling and tapering (`taper: [start, end]` as shares of the length); `tail: 0.3` lets the last 30% run dry into a dry-brush end |
| `Paper.dryBrush(buf, pts, width, color, { load, depletion, streak, smear, mode, strength })` | a dragged brush that skips over the grain: `load` 0.9 is nearly solid, 0.6 broken, 0.4 only the peaks, and the paint runs out along the stroke (`depletion`); `color` null with `mode: 'lift'` lifts paint back toward the paper |
| `Paper.margin(buf, { width: [top, right, bottom, left], rough, pool })` | washes that stop short of the sheet's edge along a ragged, brush-made line |

The options of `shape` and `stroke`: `strength` (1 = the color itself where the pigment lies even, 0.3 a pale tint), `edge` (pigment pooled at the rim as it dries: 0.3-0.6 on dry paper, 0 wet-in-wet), `soft` (edge blur in px: about 1 on dry paper, 10-40 wet-in-wet), `rough` (a ragged edge), `feather` (a soft edge creeping out in fingers instead of a smooth blur), `mottle` (uneven pigment), `settle` (granulation into the pits), `mode` (`'glaze'`, transparent, the default; `'opaque'` for gouache or body color; `'lift'` back to paper), `holes` (polygons left out: reserved whites, stones a stream stroke must not cross), `clip` (a polygon the mark stays inside, with its crisp edge), `charge` (`[color, amount 0..1, blotch px]`: a second color dropped into the wet wash), `simplify` (px: rounds away teeth and notches, e.g. of a union of triangles), `grade` (`[top, bottom]` strength multipliers: a graded wash) and `gravity` (0..1: the dried rim heavier at the bottom, as on a tilted board).

Helpers: `Paper.outline(pts, width, { taper })` is the polygon of a stroke (one point gives a disc, handy for `holes`), `Paper.mix(['#3d5fae', 2], ['#c4506e', 1])` mixes pigments the way glazes combine and returns `'#rrggbb'`, `Paper.roughen(polygon, amp, seed)` gives a polygon a ragged edge (a reserved white of broken foam), and `Paper.noise(seed, cell)` is smooth value noise `(x, y) => 0..1` for masks and wobbles. `Paper.finish({ granulation: 0.1, relief: 0.02 })` is the last layer: pigment settles into the pits of the heavier washes (pale tints stay smooth; about 0.05 for graphite and charcoal) and the sheet's relief is lit from the upper left.

```js
function washes() {
  const S = W / 2048;
  const box = (u0, v0, u1, v1) => [[u0 * W, v0 * H], [u1 * W, v0 * H], [u1 * W, v1 * H], [u0 * W, v1 * H]];
  const stone = Paper.roughen(box(0.45, 0.58, 0.6, 0.7), 3 * S);                          // a reserved white
  Paper.paint(buf => {
    Paper.shape(buf, box(0.03, 0.04, 0.97, 0.45), '#9bb8d3', { strength: 0.5, soft: 20 * S, edge: 0, feather: 0.8,
                                                              charge: ['#d9a06b', 0.4, 120] });   // a wet-in-wet sky
    Paper.shape(buf, box(0.1, 0.5, 0.9, 0.9), '#5b7aa0', { strength: 0.62, soft: 1.2, edge: 0.4, rough: 1.5,
                                                          mottle: 0.15, holes: [stone], grade: [0.8, 1.25], gravity: 0.6 });
    Paper.stroke(buf, [[0.2 * W, 0.8 * H, 0.5], [0.4 * W, 0.77 * H, 1], [0.6 * W, 0.81 * H, 0.4]], 40 * S, '#3d5577',
                 { strength: 0.8, tail: 0.4 });                                               // runs dry at the end
    Paper.dryBrush(buf, [[0.1 * W, 0.94 * H], [0.5 * W, 0.95 * H]], 60 * S, '#26303c', { load: 0.6 });
    Paper.margin(buf, { width: [0, 26 * S, 30 * S, 22 * S], rough: 16 * S });
  });
},
```

### Papers and light media

`Paper.init(W, H, SEED, { preset })` picks a named sheet and paints it over the canvas: the stock's colour with tone clouds, fibres and flecks, and the grain that `tooth`, `dryBrush` and granulation use. `kind` and `grain` still override the preset's. `Paper.presets[name].color` is the stock's colour, for `background()` and your palette. `lift` and `margin` go back to the preset's sheet, not to a flat colour. A sheet is the whole canvas: to show several papers side by side, draw each on its own and copy the panel over, as `dry/sheets/papers_sheet.html` does.

| Preset | Stock | For |
|---|---|---|
| `'blue-black'` | very dark blue, fine tooth, faint lighter fibres | white ink, white pencil, chalk |
| `'kraft'` | brown wrapping paper with fibres and bark flecks | pen, graphite, white ink |
| `'warm-grey'`, `'cool-grey'` | mid grey, fine tooth | graphite with white chalk highlights |
| `'graph'` | cream with a printed grid: 22 px squares at 2048, pale blue-green, a stronger line every 5th (`Paper.presets.graph.grid`) | technical drawing, plans, pencil and pen |

The light media are p5.brush brushes that `Paper.init` registers when it has a preset (`Paper.media()` does it without one; it is safe to call twice): `whiteink` (opaque, crisp, pen-fine: lines, stars, lettering), `whitepencil` (waxy: hatching) and `chalk` (wide and dusty: masses). Use them like the built-ins, `brush.set('whiteink', '#f3f0e8', 1)`, and they work with `brush.hatchStyle`, `brush.spline` and `Lettering`. Settings that read well:
- A white mark is high contrast on dark paper, so the layer `tooth` has to be high before the grain shows: `whitepencil` 0.8 and `chalk` 0.9 on `'blue-black'`, `chalk` 0.6 on grey (less contrast, lower tooth). Graphite (`HB`, `2B`) on grey, kraft or graph paper wants 0.2-0.3; at 0.5 thin lines break into dots.
- p5.brush blends its marks with the paper, so a white line tops out at about 85% white. Draw an important line twice for a brighter white, or use `Paper.stroke(buf, pts, w, '#ffffff', { mode: 'opaque' })` for pure white ink or gouache.
- Light media go on last, over the pen and graphite layers.

When: drawings on toned paper (graphite and chalk on grey, white ink on black, pen on kraft), plans and diagrams on graph paper.

```js
const PAPER_PRESET = 'blue-black';
const PAPER = Paper.presets[PAPER_PRESET].color;            // the flat colour, for background()
function setup() { /* createCanvas, brush.scaleBrushes(W / 200), ... */ background(PAPER); Paper.init(W, H, SEED, { preset: PAPER_PRESET }); }
const LAYERS = [
function lines() { brush.set('whiteink', '#f3f0e8', 1); brush.spline([[200, 400], [500, 340, 1.2], [900, 420]], 0.6); },
function tone()  { brush.noStroke(); brush.hatch(9, 50); brush.hatchStyle('whitepencil', '#f3f0e8', 1); brush.rect(300, 500, 400, 300); brush.noHatch(); },
];
LAYERS.find(f => f.name === 'tone').tooth = 0.8;
```

### Single-stroke lettering

`dry/lettering.js` (loaded by `template.html`) writes text as pen strokes with the current p5.brush brush, so labels look hand-lettered and not typeset. The glyphs are skeleton lines drawn for this kit in the manner of the Hershey single-stroke fonts (no third-party font data): A-Z, a-z, 0-9, `. , : ; ! ? ' " - – — / ( ) [ ] & + = % # @ * ° · _ < >` and the Turkish ç ğ ı İ ö ş ü with their capitals.

- `Lettering.text(str, x, y, opts)` draws `str` with its baseline at `(x, y)` and returns the width in px. Set the brush first: `brush.set('fineliner', '#2b2622', 1.4)`.
- `Lettering.paths(str, x, y, opts)` returns the same strokes as `[{ pts: [[x, y, pressure], ...] }]` and draws nothing: use it to cut letters into a print mask or to plot them.
- `Lettering.width(str, opts)` measures, for right-aligning or fitting a title block.
- `opts`: `size` (cap height in px, default 24; lowercase is 0.64 of it), `slant` (degrees, positive leans right), `spacing` (extra space between letters as a share of `size`; 0.3-0.4 for spaced map capitals), `jitter` (0..1 hand wobble, default 0.35; 0 is ruled), `seed` (same text and seed, same strokes; p5's random stream is untouched), `angle` (degrees counter-clockwise, as in `brush.hatch`), `align` (`'left'`, `'center'`, `'right'`: which part of the text sits at `x`) and `along` (a path `[[x, y], ...]` to set the text along: a label on a shore or a river).
- **Brushes:** the built-in `pen`, `rotring`, `HB` and `cpencil` scatter and fade on strokes this short, and small text turns to noise. The first `Lettering` call registers `fineliner` (an opaque crisp pen, weight 1-2 at 2048 px) and `finepencil` (a pencil with little scatter, weight 0.8-1.8); `whiteink` does the same in white on dark paper. Text under about 14 px is at the limit: use size 16 and up at 2048 px.
- Lettering is many strokes: p5.brush drops the ones that come late in a heavy frame, so give a block of text a layer of its own.

When: titles and title blocks, map labels, annotations, dimension notes, a caption inside the picture: anything a draughtsman or an atlas would write by hand. Vary `seed` from one label to the next, or repeated words come out identical.

```js
function labels() {
  brush.set('fineliner', '#1f1b17', 1.4);
  Lettering.text('THE BOSPHORUS, A SECTION', 80, 120, { size: 40, spacing: 0.08, seed: 1 });
  Lettering.text('Kadıköy–Karaköy 06:40', 900, 1180, { size: 76, align: 'center', seed: 2 });
  Lettering.text('KADIKÖY', 0, 0, { size: 38, spacing: 0.34, along: [[140, 498], [330, 438], [520, 408]], seed: 3 });
  brush.set('finepencil', '#2f6f9f', 1.2);
  Lettering.text('iskele 3', 600, 436, { size: 16, slant: 10, seed: 4 });
}
```

See `dry/sheets/lettering_sheet.html` (a title block, a map label, annotations, the options and every glyph).

### Print look: relief prints and riso

`dry/print.js` (loaded by `template.html`) prints flat inks the way a linocut, a woodcut or a risograph does. Each ink is a mask printed as one flat colour with the process's texture: roller mottle, the paper's grain showing through the ink, pinholes and a little squash at the edge. Relief prints get gouge marks that follow a direction field; riso prints get grain and halftone. Every plate after the first prints slightly off register, and inks combine by multiply, so an overprint is darker. It works on the pixels like `Paper.stroke`, on the sheet `Paper.init` made, and its grain is that sheet's (a rougher `kind` shows more).

- `Print.ink(buf, plate)` inside `Paper.paint(buf => ...)` prints one ink. Order is the order of the plates. `plate`:
  - `color`: `'#rrggbb'` or a name in `Print.inks` (relief `black`, `red`, `blue`, `brown`, `green`; riso `teal`, `fluoOrange`, `riso_blue`, `fluoPink`, `yellow`, `riso_green`, `risoRed`, `purple`, `risoBlack`).
  - `mask`: a polygon `[[x, y], ...]`, a list of polygons, a function `g => { ... }` that draws the shapes in white on a 2D canvas context (arcs, rects, thick strokes), or a `Float32Array(W * H)` of 0..1. `Print.mask(src)` makes the array, to reuse a mask or draw letters into it (`Lettering.paths`, stroked thick).
  - `kind`: `'relief'` (default) or `'riso'`. `opacity`, `mottle`, `load` (ink reaching the paper's pits; low lets the grain show), `pinholes`, `squash`, `rough` (edge) start from the process's values; `texture` 0..1 scales them all (0 is perfectly flat).
  - `gouge`: `{ field, spacing, length: [min, max], width, tone }` cuts lens-shaped marks out of the ink. `field` is an angle or a function `(x, y) => degrees`: `Print.fields.constant(deg)`, `radial([x, y])`, `vortex([x, y], twist)`, `noise(scale, seed)` and `contour(mask, sigma)` (marks that follow a shape's edges). **Angles count counter-clockwise, 90 = up, like `brush.hatch`** (not the oil engine's y-down angles). `tone(x, y)` is 0..1, how light the place should be cut: more and wider gouges where it is high, none at 0. That is how a linocut models light: cut hard toward the light, leave the shadow solid.
  - `halftone`: `{ tone, cell, angle, shape }` prints a tone map (a function `(x, y) => 0..1` or a `Float32Array`) as dots (`'dot'`, default), `'line'` or `'grain'`; the mask still bounds the ink. Use a different `angle` per ink (15, 75, 45) so the screens do not line up.
  - `register`: `[dx, dy, rotation]`; by default none for the first plate of a run and a seeded offset of about 4 px at 2048 for each later one. `Print.init({ seed, misregister })` starts a new run and sets that size; every `Paper.init` starts one too.
- All sizes are px at 2048 and scale with the canvas. The result is deterministic for the sheet's seed and the `Print.init` seed.

When: linocut and woodcut, stamps and posters, riso zines, any flat-colour picture that should look printed. Plan the plates as a printer would: the key block (black) carries the drawing and the gouges, the colour block sits under or beside it. A plate is one ink pass: put everything that ink prints into one mask (and one `tone` function), or each piece gets its own register offset. Overprint deliberately: multiply turns teal and orange into a dark olive, red under black into black.

```js
function prints() {
  Paper.paint(buf => {
    const sun = g => { g.beginPath(); g.arc(1000, 700, 300, 0, 7); g.fill(); };
    const sky = g => { g.fillRect(100, 100, 1800, 900); };
    Print.ink(buf, { color: 'black', mask: sky, gouge: { field: Print.fields.radial([1000, 700]), spacing: 12, width: 7,
                     tone: (x, y) => Math.max(0, 1.15 - Math.hypot(x - 1000, y - 700) / 600) } });   // rays around the sun
    Print.ink(buf, { color: 'red', mask: sun });                       // a second block, slightly off register
  });
}
```

See `dry/sheets/print_sheet.html`: a two-block black-and-red relief and a two-ink riso (teal and fluorescent orange) with the overprint.

## Extending the kit

Reach for the existing tools first. When a painter needs something they can't do, extend the kit, not one painting, so the next painting has it too.

**A brush preset:** add `oil/atelier/presets/<name>.json`. `brush()` validates it: unknown fields are rejected, and `bristle_jitter`, `dry_threshold`, `opacity`, `pickup`, `edge_softness`, `color_jitter` and `wobble` must lie in 0..1. Copy the closest preset and change a few fields. Add a row `(name, paint color, color underneath)` to `PRESETS` in `oil/sheets/stroke_sheet.py`, run it, and look at `oil/out/stroke_sheet_review.png` (straight, curved, pressure and over-wet rows). Then add a row to the brush table above.

**A technique:** a function `name(cv, mask_or_path, color, ...)` in `oil/atelier/techniques.py`, built on `atelier.stroke.paint_stroke` or array operations, with every random draw from `cv.rng`. Register it as a method in `oil/atelier/canvas.py` (`name = techniques.name` in the class body), add a panel to `oil/sheets/technique_sheet.py` and a test to `oil/tests/test_techniques.py` (at least a behavior check and determinism), and run `uv run pytest` in `<skill>/oil`. Then add a section here with when to use it, its parameters and a snippet.

**Dry media:** `brush.add(name, params)` defines a new p5.brush brush inside the sketch (parameters in `dry/node_modules/p5.brush/README.md`), and `brush.addField(name, fn)` a new field. When one proves itself, move it into `dry/template.html` and list it here.

Keep scene code (design maps, one painting's helpers) in `paint.py`: the kit holds only tools that another painting would use.
