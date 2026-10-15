# Method: from dossier to finished painting

The order is the one painters use because each step fixes the decisions the next one depends on: the look (dossier), then composition and values (thumbnails), then the plan (design map), then paint from big and thin to small and thick, then critique. All code lives in `paintings/<slug>/`; calls are listed in `techniques.md`.

## 0. The idea

When the brief leaves the idea open (a subject without a treatment, or "paint something"), find the idea before the dossier. Models drift to the same pictures:
- twilight or moonlight;
- a lamp in the dark;
- a path of light on water toward a central sun;
- a lone figure seen from behind;
- a jug-and-fruit still life;
- quiet melancholy.

Use one of these only when the idea needs it.

1. Write 8 one-line concepts that differ in:
   - subject domain: science, infrastructure, an everyday object, myth, pattern, a place;
   - medium;
   - viewpoint: eye level, plan, axonometric, straight down, extreme close-up;
   - time of day;
   - palette rule: one accent colour, two colours, full;
   - mood.
2. Pick the most surprising one the kit can do well, and say why in `dossier.md`.
3. If the project shows its earlier works (an overview sheet, or tags in `label.json`), the new one must differ from its nearest neighbour on at least two of those axes. Where the project has a portfolio script, it reports this.

A conceit plus a constraint beats a described scene, for example "the ferry's docking manoeuvre as an engineer's drawing, one red line". Keep commissions short enough to leave room for this.

## 1. The style dossier (`dossier.md`)

Writing the painter down as decisions turns "Turner-ish" into parameters and gives the critique something to check against. Work from knowledge of the painter's work; no reference images. For a living artist, the dossier describes technique and the composition is your own.

```markdown
# <Painter>: <subject>   (<slug>, <W>x<H>)

## Sources in mind
Works and period the look comes from (from memory). You're painting a new picture in this manner, not redrawing one of them.

## Palette (named pigments with their jobs; see techniques.md for the list)
- lead_white: the lights; mixed into almost everything
- ...
Left out on purpose: ... (e.g. no black: darks from ultramarine + burnt_umber)

## Ground
cv.ground("<pigment>", texture="<linen|cotton|paper|panel>", tone=<0..1>): why (e.g. a warm mid ground glows through the sky)

## Stroke vocabulary -> kit
| The painter's mark | Where | Kit call and key parameters |
|---|---|---|
| ... | ... | ... |

## Composition
Format and size. The 3-5 big shapes. The focal point: where, and what makes it win (contrast, edge, color, detail).
Lines of movement -> fields (vortex around ..., contour of ..., constant angle in ...).

## Values
Key (high / middle / low). The value pattern in one sentence (e.g. "a light vortex framed by dark sea and sky").
Where the darkest dark meets the lightest light.

## Edges
The hardest edge (at the focal point). Where edges go soft or lost, and with what (wet_in_wet, glaze, scumble, blur).

## Color temperature
Warm or cool light; shadows the other way; where the saturated accents go (few of them).

## Surface
Impasto (where and how thick), knife, varnish, weave, crackle.

## Layer plan
1. ground  2. underpainting  3. block-in and refinement  4. details and lights  5. glazes  6. finish
(one line each: what it does and the call)

## Risks
What the kit may not do well here, and the plan for it (a workaround or a new preset/technique).
```

Example rows of the stroke table, for Cézanne's late landscapes:

| The painter's mark | Where | Kit call and key parameters |
|---|---|---|
| "Constructive stroke": patches of short parallel flat strokes, each patch at its own slant | sky, foliage, fields | per patch `cv.fill_strokes(patch_mask, fields.constant(a), brush("flat_bristle", size=0.9*S), design, density=1.4, length=(30*S, 70*S))`, `a` varying by patch |
| Thin blue contour that breaks and restarts along the mountain | ridge | `cv.stroke(brush("round_bristle", size=0.4*S), piece, "ultramarine", pressure=0.7)` for each broken piece of the ridge line |
| Thin paint, canvas left bare in places | everywhere | `impasto=0.0-0.05` overrides, lighter `density`, pale ground |

## 2. Thumbnails and a value study

A painting that fails at 512 px fails at 2048, and at 512 px a design takes about a second to render. Settle composition and values here.

- **Thumbnails (oil):** put the composition choices at the top of `paint.py` (horizon height, focal point, format), render the design map of 2-3 variants at 512×384 and save each with `studio.save(srgb8(design), out / "thumbs" / f"{name}.png")`. Compare their review sheets: the value map (5 levels) and the squint panel show whether the big pattern reads. Pick the variant with the clearest value pattern and focal point, and say why in `dossier.md`.
- **Value study:** the review sheet of `design.png` (the starter writes it on every run) is the value study. Check for 3-5 value masses rather than confetti, the strongest contrast at the focal point, and a squint that isn't flat mid-grey. Fix values in the design now: strokes and glazes can nudge values but can't rescue a weak value plan.
- **Painted thumbnail (optional):** `paint.py <out> --width 512` runs the whole painting in a few seconds and shows whether the stroke scale suits the picture.
- **When the user picks the composition:**
  - Show two options on one captioned sheet: the painted thumbnails of the two strongest variants.
  - Each option must pass the readability check (`critique.md`).
  - Offer two, not three: a third option adds a whole sketch's cost and seldom changes the pick.
- **Dry media:** set `W = 512` (keep all coordinates as fractions of `W, H`) and render the composition in flat values; read the value map the same way. The paper grain and the dry brush only read at full size (§5), so this stage is for shapes and values, not surface.

## 3. The design map in code

The design is the plan the strokes follow: HxWx3 linear RGB with the big shapes at their values and colors, and no brushwork. `paint_from_design` samples its colors, so it only needs to be as detailed as the biggest brush can show. Things smaller than a mid-size brush (a mast, a figure's accent, a glint) are painted by hand later.

Build it with the palette, so it is already in the painting's colors:

```python
y, x = np.mgrid[:H, :W].astype(np.float32)
u, v = x / W, y / H                                    # fractions: any canvas size works
sun, horizon = (0.66 * W, 0.40 * H), 0.60 * H
sky = ramp(v / 0.6, [(0.0, pal.mix(("ultramarine", 1), ("lead_white", 1.3))),          # gradient through stops
                     (1.0, pal.mix(("lead_white", 3), ("naples_yellow", 1.5)))])
glow = np.exp(-((x - sun[0]) ** 2 + (y - sun[1]) ** 2) / (2 * (0.14 * W) ** 2))         # radial light
img = sky + (pal.mix(("lead_white", 3), ("naples_yellow", 1)) - sky) * glow[..., None]
ridge = H * (0.53 - 0.06 * np.exp(-((u - 0.22) / 0.13) ** 2))                         # a silhouette: y > f(x)
hills = (y > ridge) & (y < horizon)
img[hills] = pal.mix(("ultramarine", 1), ("burnt_sienna", 0.5), ("lead_white", 1.1))   # composite back to front
water = y >= horizon
mirror = np.clip(2 * horizon - y, 0, horizon - 1).astype(int)                          # reflection: mirrored rows
img[water] = 0.5 * img[mirror, x.astype(int)][water]
```

Tools, all in `templates/oil_starter.py`: `ramp` (gradients through color stops), `polygon` (PIL-drawn polygon masks), `soft` (Gaussian-softened masks), `mottle` (smooth random fields for clouds and mottling), `srgb8` (to save), `dead_color` (the design's values in two pigments, for the underpainting). Useful habits:
- Aerial perspective: distant shapes move toward the sky color: lighter, cooler, lower contrast.
- Keep the masks and return them with the image: the same masks weight the fields and bound the glazes and scumbles.
- A little noise in large flat areas (`img *= 1 + 0.1 * mottle(rng, (H, W), 0.04 * W)[..., None]`) gives the strokes color variation to pick up.
- Float designs are linear RGB and uint8 designs sRGB. A float array of sRGB values (hex/255) comes out too light: convert with `atelier.color.srgb_to_linear` first.

**Let the masses follow the flow.** The strokes inherit the design's shapes, and they can't turn a shape into something else. Isotropic noise (mottle) in a mass reads as clouds whatever the strokes do, and a spiral drawn as rings (cos of the spiral's phase) reads as a galaxy. So build masses as bands that run the way the strokes will (a vortex as arcs along the spiral, a sea as swells), and keep noise for color variation inside them. Soft masses (smoke, cloud, haze) take their outline from a mask that strokes, glazes and `wet_in_wet` fill, rather than from a few big hand strokes: dark strokes on a light ground show every path as a silhouette.

**Fields** give the strokes their direction, one per region, blended with soft masks (angles in `fields` count with y down; see the conventions in `techniques.md`):

```python
sky = fields.combine((fields.vortex(sun, twist=0.9), glow), (fields.noise(0.25 * W, cv.rng, angle=-6, spread=25), 0.5))
level = fields.combine((fields.constant(0), 1.0), (fields.noise(0.1 * W, cv.rng, spread=10), 0.3))
land = fields.combine((fields.contour(bank_mask, sigma=0.01 * W), 1.0), (fields.noise(0.08 * W, cv.rng), 0.5))
flow = fields.combine((sky, soft(sky_mask, 9)), (level, soft(water_mask, 9)), (land, soft(bank_mask, 9)))
```

A little `fields.noise` in every field keeps parallel strokes from looking ruled. Two fields meeting at right angles with equal weight turn abruptly along the seam, so soften the masks there.

## 4. Painting in layers (oil)

`templates/oil_starter.py` is this sequence, runnable. Take a progress snapshot after every layer (`studio.snapshot(cv, "label", dir=out / "progress")`, passing `dir` because the default is relative to the working directory). The contact sheet of those frames shows whether each layer did its job.

| Layer | Why | Calls |
|---|---|---|
| 1. Ground (imprimatura) | A toned ground sets the key and shows between strokes, so the gaps look warm (or cool) rather than white | `cv.ground("burnt_sienna", texture="linen", tone=0.45)` |
| 2. Underpainting (dead color) | Values only, thin and loose; the block-in inherits its lights and darks, and scumbles and glazes later act on it | `cv.fill_strokes(None, flow, brush("filbert", size=4*S, impasto=0.0), dead_color(design), density=1.2, length=(80*S, 240*S))`, then `cv.dry()` |
| 3. Block-in and refinement | Big brush to small. The first pass covers everything and later passes repaint only where the canvas is still off the design, so broken color survives. `dry=True` lets each pass dry before the next | `cv.paint_from_design(design, [brush("filbert", size=3.2*S, impasto=0.04), brush("flat_bristle", size=1.2*S, impasto=0.1), brush("round_bristle", size=0.6*S)], field=flow, after_pass=...)` |
| (wet-in-wet) | The last pass is still wet: melt it where edges should be lost (atmosphere, a glow, soft flesh) | `cv.wet_in_wet(mask, strength=0.5, reach=14*S)`, then `cv.dry()` |
| 4. Details and lights | By hand, in the painter's own marks: the focal accent with the hardest edge, rigger lines, broken light (scumble), thick lights last | `cv.stroke`, `brush("rigger")`, `cv.scumble`, `cv.impasto`, `cv.stipple`, `cv.hatch`, `cv.knife`; then `cv.dry()` |
| 5. Glazes | Transparent films unify temperature, deepen shadows and warm the lights without losing the modelling underneath | `cv.glaze(mask, "indian_yellow", strength=0.2)`, `cv.glaze(shadow, "ultramarine", strength=0.25)`, then `cv.dry()` |
| 6. Finish | Photograph under a raking light: relief, weave, varnish. `finish()` returns a new image and leaves the canvas as it is | `studio.save(cv.finish(light=(-0.5, -0.6), varnish=0.15, weave=0.3, scale=S), out / "final.png", focus=[focal_point], canvas=cv)`, `studio.contact_sheet(out / "progress")` |

Things that follow from the kit's model:
- `paint_from_design` is block-in and refinement in one call. A second call starts again with a pass that covers the whole canvas, so later touch-ups go through `fill_strokes` on a mask such as `error_map(cv, design) > 0.08` (`from atelier.design import error_map`), or through hand strokes.
- Only wet paint mixes: `wet_in_wet`, brush pickup and knife scraping act on what was laid since the last `dry()`. `glaze` leaves its area wet, so dry after glazing before painting over it.
- **Fat over lean** holds the surface together: `impasto` about 0 in the underpainting, about 0.04 in the first pass and 0.1 in the second, the preset value in the last, and `impasto(thickness=0.8-1.2)` for the lights. Relief everywhere reads as plastic under `finish()`.
- Pass `scale=S` to `finish()`: it lights the relief as on the 2048 px render, so a 900 px study looks about as embossed as the final instead of heavier. The weave and the bristle furrows stay pixel-sized at any canvas size, so judge the surface itself on the full-size render.
- Iterate at 900 px (about 10 s for the starter) and render the final at 2048 px (about 30-60 s, depending on how much hand work there is). From the second critique round, look at the 2048 px render too (`critique.md`).

## 5. Dry media: the same method with LAYERS

`dry/template.html` is the dry equivalent of the starter. Copy it to `paintings/<slug>/sketch.html`, set `W, H, SEED, PAPER` and `PAPER_KIND` (the sheet's grain), and replace `LAYERS` with one named function per layer. The page draws one layer per animation frame and records a progress frame after each (`--progress`), named after the function.

Work at the final size, 2048 px wide. `paper.js` scales its grain with `W`, and at 1024 px the grain and the dry brush shrink to single pixels and read as noise. A full render takes about 8-10 s, so iterating at full size is affordable; composition and values are settled before that in flat values at 512 px (§2).

Separate frames are the dry version of `cv.dry()`: a later wash glazes over earlier ones, and pencil sits on top of washes. Keep each layer to one kind of mark, and don't mix p5.brush calls with `Paper.paint` in one layer: p5.brush draws when the frame ends, on top of the pixel marks. p5.brush flushes after every frame, and a frame with too much work silently drops its last strokes, so if marks at the end of a layer go missing, split the layer.

Pencil or charcoal: 2H construction lines → big value masses (hatch, mass) light to dark → mid-tones → darks (2B, charcoal) → accents and the hardest edges at the focal point. A layer with a `tooth` keeps its marks only where they catch on the grain: `LAYERS.find(f => f.name === 'charcoal').tooth = 0.6` after the list.

Watercolor has an order of its own, because there is no white paint and a wash doesn't come off cleanly:
1. Plan the whites and reserve them: the lights are bare paper, left out of the washes with `holes`.
2. Faint 2H guidelines.
3. The big light washes wet-in-wet (`soft` 10-40, `edge` 0, `feather`) around the whites.
4. Tone the quiet areas (slack water, shadow planes, the far sky) rather than everything: a pale wash over everything reads as snow.
5. A few big darks on dry paper with crisp rims (`soft` about 1, `edge` 0.3-0.5), set against the lightest paper at the focal point.
6. Brushwork that runs dry (`Paper.stroke` with `tail`), dry brush and lifts (`Paper.dryBrush`), pen or pencil accents.
7. `Paper.finish` last. Then stop: overworked watercolor loses its paper. The Sargent acceptance picture only began to read as watercolor once about a quarter of its middle band was left as paper.

```js
const W = 2048, H = 1536, SEED = 7;      // positions as fractions of W, H: a 512 px thumbnail is the same drawing
const LAYERS = [
function construction() {
  brush.set('2H', '#8a8174', 1.2);       // a 2H line at weight 0.6 all but vanishes at 2048 px
  brush.beginShape(0.4);
  for (const [u, v] of [[0, 0.62], [0.3, 0.48], [0.55, 0.56], [1, 0.45]]) brush.vertex(u * W, v * H);
  brush.endShape(false);
},
function skyWash() {                     // wet-in-wet, graded, the sun left as paper
  const sky = [[0.03 * W, 0.04 * H], [0.97 * W, 0.04 * H], [0.97 * W, 0.5 * H], [0.03 * W, 0.5 * H]];
  const sun = Paper.outline([[0.7 * W, 0.2 * H]], 0.1 * W);       // one point: a disc 0.1 W across
  Paper.paint(buf => Paper.shape(buf, sky, '#7fa3c8', { strength: 0.55, soft: 16, edge: 0, feather: 0.8,
                                                         grade: [1.2, 0.5], holes: [sun] }));
},
function darks() {                       // on dry paper: a crisp rim with the pigment pooled at the edge
  const bank = [[0.55 * W, 0.56 * H], [W, 0.45 * H], [W, 0.95 * H], [0.6 * W, 0.95 * H]];
  Paper.paint(buf => Paper.shape(buf, bank, Paper.mix(['#2f3b57', 2], ['#6b4a2a', 1]), { strength: 0.8, soft: 1, edge: 0.45 }));
},
function shadows() {
  brush.noStroke();
  brush.hatch(6, 30, { rand: 0.2 });
  brush.hatchStyle('HB', '#3a332c', 0.8);
  brush.polygon([[0.62 * W, 0.62 * H], [0.95 * W, 0.56 * H], [0.95 * W, 0.9 * H], [0.66 * W, 0.9 * H]]);
  brush.noHatch();
},
function paper() { Paper.finish({ granulation: 0.12, relief: 0.02 }); },
];
```

```bash
node <skill>/dry/render.mjs paintings/<slug>/sketch.html paintings/<slug>/final.png --progress paintings/<slug>/progress
```

That writes `final.png`, `final_review.png`, `progress/NN_<layer>.png` and `progress/contact_sheet.png`. The critique works the same way as for oil; the watercolor rows of its checklist are the ones to watch.

## 6. After the painting

`notes.md` in the painting folder records what the critique rounds found and changed, what is still wrong, and the final parameters worth keeping. Then add an entry to `<skill>/sketchbook/<painter>.md` in the format of `sketchbook/README.md`: what worked, what failed, parameter values that worked, kit gaps. The next painting of that painter starts from it.
