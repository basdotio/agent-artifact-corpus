# Claude

## 2026-09-27 · claude-self-portrait · oil

- **Subject and size:** "who are you?" answered as a murmuration of starlings over a marsh at dusk, whose fold bends toward one person on a dike. 2048×1536, seed 11.
- **Worked:**
  - A flock as ~26k single tiny strokes sampled from a density field made of catmull-rom ribbons (distance to centerline, domain-warped, smooth noise along the ribbon for density waves), each oriented along its ribbon's tangent.
  - A few rigger "v"s near the tip make the flecks read as birds.
  - The watcher as a painted silhouette mask (coat, legs, head tipped back) filled with small vertical strokes, then closed.
- **Failed:**
  - Birds under ~1.4 px vanish under a soft brush.
  - A glaze under the flock reads as smoke.
  - A tapering fold reads as a tornado funnel.
  - Bird tone tied to density made the densest spots into smooth black smudges. Keep the tone nearly constant and let crowding make the core.
  - A figure built from 3-4 strokes reads as a signpost.
- **Parameters that worked:**
  ```python
  bird = brush("round_soft", size=max(3.4 * S, 1.5) / 14, edge_softness=0.12, opacity=1.0, impasto=0.0, load=1.2,
               taper_start=0.1, taper_end=0.1, pickup=0.0)          # half-length rng.uniform(2.0, 4.2) * S + 0.6
  p = np.clip(dens.ravel(), 0, 0.85) ** 1.2                            # sampling weights; 26000 * S birds
  cv.wet_in_wet(soft(sky, 6 * S), strength=0.45, reach=18 * S, angle=0)   # calms the last pass of a sky
  ```
- **Kit gaps:**
  - No tool for crowds of tiny marks (birds, insects, leaves): a `cv.swarm(density, flow, brush, count)` technique would save the loop.
  - No silhouette helper for small figures.
- **Next time:** give the birds a wing shape at 1:1 (two-segment strokes for a share of them), and bring the marsh closer to dusk.
- **Files:** `paintings/claude-self-portrait/`, in the project where it was painted.

## 2026-09-30 · claude-waiting-for-the-sun · oil

- **Subject and size:** Nemrut at sunrise, "From the Sun's Side". The sun is behind the viewer, and three carved
  heads and a crowd in blankets face us, lit gold, under a night-blue sky. Three tea glasses steam on a rock.
  2048×1536, seed 7.
- **Worked:**
  - Carved heads as a lit relief: a height field (a solid of revolution plus the oval face and its features, with
    soft `(1 - e) ** k` bumps), normals, cast shadows marched toward the sun, then a stone colour ramp. A sun 35°
    to the side and a little up models the carving; frontal level light flattens it.
  - `wet_in_wet` on each head right after painting it, then `dry()`, before any neighbour is painted. It melts the
    refine passes' dash rows without pulling in other wet paint.
  - Hand-drawn features keyed to the relief's positions: the upper lid as a shadow, the lower lid lit, the mouth,
    the nostrils.
  - Side heads half a value down (`col * 0.8`, 15 % toward the background), so the middle one leads.
  - Long cool shadows from the crowd, and the glasses' short shadows with an amber spot in them.
- **Failed:**
  - `sqrt` domes leave drawn-looking rings, and fine noise on the relief reads as hammered metal.
  - A radial field on a cone reads as rays of light.
  - Both lids drawn dark read as goggles; the upper lid alone reads as closed eyes.
  - People as smooth bells read as matryoshkas until they were slimmer, overlapped and darker than the stone.
  - An amber phone held up was read as a raised tea glass. The colour decides what a small object is.
- **Parameters that worked:**
  ```python
  SUN = normalize([0.62, -0.22, 1.0])                       # toward the sun: right, a little up, behind the viewer
  cv.wet_in_wet(soft(eroded_head, 1.5 * S), strength=0.55, reach=8 * S)   # side heads; 0.22 / 3.5 * S on the focus
  scree = fields.combine((fields.constant(-8), 1.0), (fields.noise(0.025 * W, rng, spread=55), 0.8))
  ```
- **Kit gaps:**
  - This is the third painting to copy `fill_inside` and `cut_in` from scene code; they belong in the kit.
  - A relief-lighting helper (height field in, lit colours and cast shadows out) would serve any sculpture subject.
  - `paint_from_design` still has no keep-out mask.
- **Next time:** give the side heads their own faces rather than one model, and let the long shadows fall in
  separate stripes.
- **Files:** `paintings/claude-waiting-for-the-sun/`, in the project where it was painted.

## 2026-09-30 · claude-every-floor-in-the-village · oil

- **Subject and size:** after the spring wash, a hill village lays out every carpet it owns in the noon sun, seen across a valley. The slope is tipped up like a board. 2048×1536, seed 5, 69 rugs.
- **Worked:**
  - One grammar for every carpet: an index map of dyes per rug (`rug_elements(a, b, rug)` in rug coordinates), rugs placed as affine pieces on grass, roofs, walls and lines, and schemes dealt from a shuffled deck so no two neighbours repeat.
  - Carpets repainted dye by dye with `cv.hatch` on each dye's mask along the weave (across for kilims). Both critics named these frayed, woven dabs as the thing to keep.
  - A carpet hung by its long edge and sagging on its line, drawn as 14 affine slices offset by a parabola.
  - Dust as a `titanium_white` glaze on a soft plume mask. `scumble` and `round_soft` dabs both read as white scribble.
- **Failed:**
  - Big motifs only. Guard stripes and pendants under about 15 px turn to confetti, and so do thin kilim bands hatched across.
  - A blue strip of sky over a hill with horizontal strokes read as sea. Diagonal strokes, `wet_in_wet` and three small cumulus fixed it.
  - Long lay-in strokes dragged dyes across walls. Lay in inside and outside the rugs separately.
  - Anything drawn over a rug (the women) must leave the rug's mask, or the dye hatching paints over it.
  - Figures against a carpet border of the same darkness vanish. Stand them against the pale grass.
- **Parameters that worked:**
  ```python
  cv.hatch(dye_mask, median_colour, angle=-weave_deg, spacing=6.5 * S, length=52 * S,
           brush=brush("flat_bristle", size=6.5 * S * 1.3 / 24, impasto=0.1, load=1.2))   # skip dyes < 160 px²
  cv.paint_from_design(design, [filbert 2.2S, flat 1.0S, round 0.55S], threshold=0.05, tolerance=0.08, length=(2, 8))
  cv.glaze(plume, "titanium_white", strength=0.55, pooling=0.0)                         # dust
  ```
- **Kit gaps:** no way to repaint a patterned region cell by cell with crisp edges except `hatch` on a full-canvas mask per colour (270 calls). A `paint_index_map(cv, index, palette, angle)` technique would do it in one pass.
- **Next time:** build one dark mass into an all-over pattern from the start (a cloud shadow or a dark tree band), because the mosaic stayed banded (values 3-4/10).
- **Files:** `paintings/claude-every-floor-in-the-village/`, in the project where it was painted.

## 2026-09-30 · claude-the-red-one · graphite and chalk on warm grey (dry kit)
- **Worked:**
  - One scene file (`scene.js`) of role-tagged polygons, drawn flat for the 512 px thumbnails and with marks for the final, so the thumbnail and the drawing are one picture.
  - Chalk bodies as opaque `Paper.shape` in a layer with tooth 0.6 (house fronts, snow, the near wall). They are crisp, dusty and fast for hundreds of small shapes, where chalk hatching spilled past them.
  - `finepencil` for roofs and small hatching on grey. Tile strokes computed inside each roof quad stay inside it, where `brush.hatch` on thin quads overshot into ruled lines.
  - A stump-grey `Paper.shape` for the distant sierra, under a solid chalk snow body.
- **Failed:**
  - `HB`/`2B` hatching with tooth 0.25 on grey reads as black dot clouds over big areas.
  - Chalk strokes started at a jagged ridge read as a fringe or icicles.
  - Recognition: a red walled ridge over a white town under snow was read twice as "a red fortress", never as the Alhambra. The place needs its specific silhouette (the Alcazaba's prow with the Torre de la Vela, the palace roofs), not just the colour.
- **Parameters that worked:** `Paper.shape(buf, fronts, '#ffffff', { strength: 0.5-0.6, soft: 0.7, rough: 0.6, mottle: 0.2, mode: 'opaque' })` with layer tooth 0.6; red body `{ strength: 0.6, mode: 'opaque' }` on grey (a glaze would turn it maroon).
- **Kit gaps:** none blocking. p5.brush has no stroke counter, so the dry kit writes no `final_stats.json`.
- **Next time:** settle recognition at the thumbnail with a reader before the full drawing. Draw a town as house masses stepping downhill, not as rows of boxes.
- **Files:** `paintings/claude-the-red-one/`, in the project where it was painted.

## 2026-09-30 · claude-two-currents · pen and two-tint wash on cream (dry kit)
- **Worked:**
  - One geometry file (`scene.js`) of depth tables in km and metres drives both the 512 px flat thumbnails and the drawing.
  - Current lines as broken dashes with chevrons, parallel to the layer boundaries. They crowd where a layer thins, which reads as speed.
  - Section hatching clipped by hand to a ragged band under the bed (the lines x + y = c, drawn only where they fall inside the band). There is no overshoot on steep flanks, where `brush.hatch` would spill.
  - Short, parallel labels set along the currents with `Lettering.text(..., { along })`.
  - A cream sheet made by adding a preset object to `Paper.presets` at runtime.
  - One red for one thing (the fisherman's line), with a 60 px clearing around its kink, made the focal point.
- **Failed:**
  - A top-level `const t` (and other one-letter names) clashed with p5.brush's global bundle, giving "Identifier 't' has already been declared". Use longer names at the top level, and don't call a helper `quad` (a p5 global).
  - Lettering is wide: capitals take about 1.1 × size per character at spacing 0.12. Guessed widths overflowed the title block. Measure with `Lettering.width` and shrink to fit, never under 14 px.
  - Two long labels in one frame lost their last strokes. Give each long label its own layer.
- **Parameters that worked:**
  - Washes: `strength` 0.42 (teal) and 0.6 (ochre), `soft` 1.2, `edge` 0.35-0.4, `mottle` 0.2, `settle` 0.3, `grade`.
  - `fineliner`: 0.85 for hatching at 8.5 px spacing, 1.0-1.5 for lines, 2.8 for the one red line.
  - Label sizes: 16-19 px, and 58 px for the header.
- **Kit gaps:**
  - The dry kit has no stroke counter, so this sketch counts its own.
  - A `Lettering.fit(str, maxW, opts)` would save a loop in every sheet with a title block.
- **Files:** `paintings/claude-two-currents/`, in the project where it was painted.

## 2026-09-30 · claude-so-we-face-each-other · linocut, black and red (dry kit, print.js)

- **Subject and size:** Nasreddin Hodja rides his donkey backwards down a poplar road at noon, so that he faces us. 1536×2048, seed 7, scene seed 5.
- **Worked:**
  - One `sketch.html` whose composition table (`COMPS`) is read by file name: a symlink `thumb_<c>.html` renders that composition flat at 512 px (`texture: 0`, no gouges). The thumbnails and the print are one picture.
  - Plates as canvas drawing functions. A figure is cleared from the ground with its own silhouette, filled and stroked black, which gives a linocut's cream cut line. Parts inside one block are separated by stroking a part black and then filling it white.
  - A real camera for the road: eye height from the figure's size and ground line, and a long lens (focal 2.2 W). The poplar walls converge and their trunks and pooled noon shadows stand on the red verges.
  - Gouge `tone` and `field` looked up in a region-id canvas (one code per tree), so each poplar is cut on its own lit edge.
  - Poplars read as leafy columns, not rain or cypresses, with short cuts (length 12-48, width 8) in an upward chevron: `90 - 36 * sign(u) * min(1, 2.5|u|)` plus a ±8° noise wobble, with foliage down to 0.75 m.
  - A grin cut into a black beard as a filled crescent (two half-ellipses) reads from across the room. Thin arcs did not.
  - Red printed first with an explicit `register: [6, 4, 0.12]`, black passes with `[0, 0, 0]`, so the key block's parts stay in register with each other.
- **Failed:**
  - `tone` 0.3-0.8 on the poplars turned them into grey fur. Cut about 5 % inside, and up to 0.7 only on the lit edge.
  - Red robe against red verge merged. An 18 px cut line around the rider in the red block fixed it.
  - Crossed wrap lines on a turban read as a bandage. Parallel bowed lines read as cloth.
  - A donkey seen straight from behind hides its head, so nobody reads the direction. Three-quarters from behind, with the head in profile, an eye and a halter, reads as walking away.
  - Recognition: two Sonnet readers named a man waving from a donkey, but neither said "backwards". The Opus critic's blind read did say it. A backwards ride seen head-on is a depth reversal, which a glance does not register.
  - Red verges at full ink competed with the red robe. Cutting them to half ink (`tone` 0.66) left the robe as the only solid red.
  - A function named `spline` collides with p5's global `spline` and stops the page.
- **Parameters that worked:**
  ```js
  Print.ink(buf, { color: 'black', mask, register: [0, 0, 0], load: 0.95, mottle: 0.12, pinholes: 0.2,
    gouge: { field, tone, spacing: 10, length: [18, 95], width: 9 } });   // poplars and verges
  gouge: { field: Print.fields.contour(donkeySilhouette, 9), spacing: 8, length: [20, 70], width: 5 }   // tone 0-0.42, lit on top
  ```
- **Kit gaps:** `Print.ink` keeps no count of its gouges, so `final_stats.json` has no mark count. A `Print.cutLine(mask, px)` helper for the white line around a figure would save every print the clear-and-refill dance.
- **Next time:** for a reversal the eye must see sideways, draw the animal more side-on, so that its head and the rider's face point opposite ways across the picture, not in depth.
- **Files:** `paintings/claude-so-we-face-each-other/`, in the project where it was painted.

## 2026-09-30 · claude-the-last-olive · flat gouache on paper (dry kit, paper.js opaque)
- **Worked:**
  - One `scene.js` that returns the whole table as marks (layer, kind, polygon, colour). The page paints them flat for the 512 px thumbnails and in gouache for the final, and node counts them for `final_stats.json`.
  - Plates packed by rejection sampling around fixed anchors (the olive bowl with a clearing, the pan, the teapot, the glasses): 24 true circles that never overlap and are cut by the frame here and there.
  - Plates in clusters with small overlaps and an empty pool around the focal bowl (the critic's top fix): the value map went from even confetti to one isolated white.
  - Hands as a small pose table over one anatomy (palm polygon, four finger capsules, a thumb capsule, in units of the hand length): point, open pinch, pinch, grip, rest. Each pose names the point that meets its target, so a hand is placed by what it touches. Flat skin, thin dark finger gaps, nails only on the extended fingers: the reader named "two hands almost touching over a single olive" at the first try.
  - Shadows as offset glaze films, longer for what hovers (hands, the lifted teapot, the stolen slice) than for plates. They put the hands above the table without any modelling.
  - The cloth deepened toward the ends with a raster-mask glaze painted before the plates, so the plates stay white and the middle of the table is the light.
- **Failed:**
  - `mottle` on a big opaque field shows the value-noise lattice as a square grid (visible in the progress frame). Keep it at 0 on the cloth and let dry-brush streaks carry the unevenness.
  - A lifted object's shadow drawn after the object darkens the object. Lifted things need their own layer after the high shadows.
  - Food accents (sesame, specks) in a layer after the hands paint over the hands.
- **Parameters that worked:** fills `{ mode: 'opaque', strength: 0.96, soft: 0.9, edge: 0.1, rough: 0.35, mottle: 0.09, settle: 0.06 }`; cloth streaks `Paper.dryBrush(..., 30-90 px, { mode: 'opaque', load: 0.3-0.55, strength: 0.3 })`; shadows `{ mode: 'glaze', strength: 0.3-0.4 }` in `#3f4f8c`; `Paper.finish({ granulation: 0.04, relief: 0.02 })`.
- **Kit gaps:** none blocking. The dry kit counts no strokes; `paper.js` has no smooth (gradient) noise for mottle on big fields.
- **Files:** `paintings/claude-the-last-olive/`, in the project where it was painted.

## 2026-09-30 · claude-atlas-of-the-3am-kitchen · white ink and white pencil on blue-black (dry kit)

- **Subject and size:** a kitchen wall at 3 a.m. charted as a star-atlas plate. Standby lights are stars, the appliances are constellation figures, Orion stands in the window, and Felis, the cat's eyes, is a double star by the floor. 2048×1448, seed 300.
- **Worked:**
  - A real conic projection: parallels are arcs around a pole above the plate, and right ascension increases to the left. At 512 px the curved grid said "star chart", while the same wall on a straight grid read as graph paper.
  - Real stars at their true coordinates, with the window placed around them. The dec scale is anchored so that Orion's belt lands mid-window, because the arcs lift the sky at the plate's edges.
  - The atlas star: `Paper.shape` lifts a halo (`mode: 'lift'`, r + 5.5 px), then an opaque white disc (r = 11 px × 0.8^mag), then `Paper.stroke` rays for the brightest. Every line breaks around its star for free.
  - Labels knock out the grid with `Paper.stroke` lifts along their own glyph paths. Names are set along the parallels, measured with `Lettering.width` and anchored at their centre height.
  - A glaze a step deeper blue on the window glass, with `holes` for its stars, gave the squint a second mass: outside is the real night.
  - Dotted boundaries instead of dashes moved it from blueprint toward atlas.
- **Failed:**
  - `along` with `align: 'center'` centres the text on the path's start, so half the label falls off. Measure, and start the path at centre - width/2.
  - A `mode: 'lift'` knockout inside a glazed area shows as a pale box, because lift goes back to the bare sheet.
  - One hairline for grid, figures and letters read as code and as a blueprint (critic: edges 4, drawing 4). Hierarchy fixed it: dim broken pencil (`#7d8594`, tooth 0.85) for the grid, 1.55 ink for the figures.
  - Hatching glass (oven door, microwave) at 7 px turned into the lightest patches on the plate.
- **Parameters that worked:**
  - `drawPts`: resample every 10 px, a sideways wobble of 0.7 px from two sines (wavelengths 37 and 11 px), pressure ±22% with 14 px tapers.
  - The window glaze: `'#0e1728'`, strength 0.42, rough 1.2.
  - Engraved stress in names: a second `Lettering.text` pass shifted 1.1 px sideways, which thickens only the verticals.
- **Kit gaps:**
  - No serif or roman lettering. The critic asked for engraved capitals, and a second shifted pass only suggests them.
  - No Greek glyphs in `lettering.js` (α and β are drawn by hand in the sketch).
  - No stroke counter in the dry kit.
- **Next time:** set the line hierarchy (grid, boundaries, figures, letters) before the first full render, not after the critic. Draw the appliances looser from the start: engraving, not elevation.
- **Files:** `paintings/claude-atlas-of-the-3am-kitchen/`, in the project where it was painted.

## 2026-09-30 · claude-alcyone-ceyx · oil
- **Subject and size:** "Halcyon Days", option B, the mirror. Looking west at dawn, the earth shadow and a rose band are doubled in a glassy calm, with the full moon and its reflection. A floating nest of woven reeds holds seven eggs, and two kingfishers meet bill to bill on its far rim. 1536×2048, seed 7, aged oak panel.
- **Worked:**
  - A nest woven reed by reed turned the sketch's "dark bun" into straw at the first render. Each reed is two strokes on an arc round a lumpy ellipse: its shade colour, then a thinner lit top edge 0.3 w above it. The order is the cup's far wall, the far rim, the outer wall, the near rim, twigs, sticks past the outline, then straws afloat.
  - The reflection mirrored from the painted canvas (`cv.color` flipped per column about the waterline), then repainted in long thin level strokes and melted with `wet_in_wet(angle=0)`. The weave doubles, and the mirror carries the light without a glitter road.
  - Kingfisher legs: put the bird's origin 0.07 L below the rim so the belly nearly rests on it. Otherwise they stand on stilts.
  - The critic's placement fix: move the sky band so that its reflection passes behind the focal point.
- **Failed:**
  - A stroke shorter than its width leaves a sliver across its path, not a dot. `fill_strokes` over a small egg plan gave white florets. What worked was nine overlapping chords along the egg's long axis, then `wet_in_wet` (0.75, reach 4 S).
  - White eggs in a dark cup became the strongest contrast in the picture and stole the focus. Dim them.
  - `finish(varnish=0.5, grime=0.3)` turned a silver-rose calm to khaki, and crackle 0.5 on a pale upright panel read as vertical rain. This high-key picture wanted varnish 0.25, grime 0.12 and crackle 0.15 at `scale=0.55`, which gives smaller cells.
  - Style scored 3/10. Birds drawn as flat local colour read as a wildlife illustration, and a centred horizon with no cloud masses reads as modern minimalism.
- **Parameters that worked:**
  ```python
  reed: stroke(round_bristle w/18, shade = mix(gap, mat, 0.35 + 0.5 f)); stroke(round_bristle 0.5 w/18, lit edge, pts - [0, 0.3 w])
  sea = refl * (0.92 - 0.36 * depth ** 0.9 - 0.06 * exp(-dy / (0.012 * H))); blend(sea, sea_body, 0.03 + 0.34 * depth)
  cv.finish(light=(-0.5, -0.6), varnish=0.25, weave=0.2, crackle=0.15, grime=0.12, edge=0.025, scale=0.55 * S)
  ```
- **Kit gaps:**
  - A mirror or water-plane helper: the fourth calm to build it in scene code.
  - A small-solid primitive for eggs, pearls and eyes.
  - `finish()` has one `scale` for crack cells and the rest of the surface.
- **Next time:** model small figures under the light from the start: a lit core, dark turning edges, a cut-in of the ground round the outline. Paint the cloud masses after the level calm strokes, not before them.
- **Files:** `paintings/claude-alcyone-ceyx/`, in the project where it was painted.

## 2026-09-30 · claude-penelope-loom · oil, a candlelight night piece on an aged panel

- **Subject and size:** Penelope's loom at night, no figure: the warp-weighted loom with its cloth half unpicked, a clay lamp on her stool, the moonlit sea in a window. 2048×1536, seed 7, `final.py` (A of the sketches; `paint.py` keeps the sketches).
- **Worked:**
  - Light as albedo × falloff: each surface has one colour "in full light" and `ramp(E, [dark, full])` darkens it. Two falloffs from one flame: the loom, stool and floor near it (`z` 0.06 H), the back wall further away (`z` 0.20 H). The wall drops into the dark while the cloth stays the largest light.
  - A stool under the lamp shades everything below its seat. It is an image-space cone (a ray from the flame crossing the seat's line). The lamp at the seat's near edge sends the shadow toward the window, so the moonlit patch on the floor shows as the only light there.
  - Clay weights painted as blocks: six rows of two flat strokes across the trapezoid (dark half, lit half), a broad lit face toward the flame, a dark hole, a cord to the knot. One filbert dab with a lit stroke read as sticks.
  - Posts and bars modelled in short lengths, three strokes across (shadow, middle, lit) coloured by the light at that length, and a quiet highlight. One long highlight stroke read as a laser line.
  - The glow round the flame is repainted after the glazes. Short round strokes take the plan's colours inside a disc that excludes the lamp, stool and post, then `wet_in_wet` (0.9, reach 14 S) melts them. The flame goes on last. Scumbling the halo gave a grey-green fuzz, and big soft dabs barely showed.
  - The heap as a mound: loops rise toward the middle and get rounder on top. Flat loops read as a rug.
- **Failed:** an even falloff (the first two rounds) gave a mid-brown room with no night in it. A wide pale body under the heap read as a plate.
- **Kit gaps:** no radial glow technique (light in the air round a flame); `paint_from_design` still has no keep-out mask, so threads are inpainted out of the plan and painted by hand.
- **Files:** `paintings/claude-penelope-loom/`, in the project where it was painted.
- **Critic (33/70):** "the light has no source". The thing the story is about (the fell being unpicked) must sit within a hand of the flame, at its height, with nothing between. Here the right post stands between them. Also keep the moon darker than the flame: two bright discs split the focus.
- **Next time:** place the focal object against the flame in the thumbnail, before the composition is chosen.
