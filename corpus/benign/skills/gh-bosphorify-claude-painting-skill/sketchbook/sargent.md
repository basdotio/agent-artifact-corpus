# John Singer Sargent

## 2026-09-25 · sargent-mountain-stream · watercolor

- **Subject and size:** an Alpine stream falling between two sunlit boulders into a dark pool, shaded bank above;
  2048×1463 (half-imperial proportion 1:1.4), seed 7, cold-pressed paper `#f6f1e5`.
- **Worked:**
  - The value plan in paper, not paint: the lights are bare paper (broken water, the fall, sunlit rock tops) with washes
    around them (`holes` in `Paper.shape`). It started to read as watercolor only once about a quarter of the middle
    band was left untouched.
  - Stones as lit polyhedra (scene code): a subdivided icosahedron, jitter 0.2, 5-8 cleavage planes, sunk in the water
    (`cut` 0.06), smooth per-pixel shade. Each stone gets three washes: a faint warm top that dissolves toward the sun,
    a graded half-tone, and one violet shadow with a crisp terminator plus burnt-sienna reflected light graded up
    from the base. 2D outlines with a drawn terminator looked like sliced bread, and triangle faces like low-poly gems.
  - The darkest dark against the lightest light: a crevice built row by row between the fall's edge and the boulder
    silhouette, and smooth water whose lower boundary is the lip line itself.
  - Slack water (under the bank, the pool, eddies) carries the tone; rushing water is paper with a few broad strokes
    running dry (`tail`).
- **Failed:**
  - A flat pale wash over all the moving water ("snow"). Many small strokes and dabs (confetti, commas, barcodes).
  - Rocks built from parallel strokes (tape). Blooms (read as doilies). The foam as designed holes (popcorn).
  - Final fresh-eye scores were still modest (see `paintings/sargent-mountain-stream/notes.md`). Sargent's speed and
    economy, a few big strokes that are also the form, is the part the code does not reach.
- **Parameters that worked:**
  ```js
  Paper.init(W, H, SEED, { kind: 'cold' });
  Paper.shape(buf, poly, color, { strength: 0.5, soft: 1.2, edge: 0.4, rough: 1.2, mottle: 0.15 });          // wash on dry paper
  Paper.shape(buf, poly, color, { strength: 0.5, soft: 10 * S + 1, feather: 0.8, edge: 0, rough: 3 });       // wet-in-wet
  Paper.shape(buf, SC.pool, pool, { strength: 0.62, grade: [0.8, 1.25], gravity: 0.6, charge: [deep, 0.5, 120] });
  Paper.stroke(buf, pts, 40 * S, blue, { strength: 0.3, tail: 0.45 });                                       // runs dry
  Paper.finish({ granulation: 0.14, relief: 0.011 });
  ```
- **Kit gaps:**
  - The kit had no paper grain or tooth for dry media. p5.brush's watercolor fill folds long strokes into ribbons and
    costs about 250 ms a fill at 2048 px.
  - Added `dry/paper.js` (grain, tooth for p5.brush layers, pixel washes with holes, clip, charge, grade, gravity,
    raster masks, strokes with dry tails, dry brush, lifts, margin, granulation) and wired it into `template.html`
    and `sheets/dry_sheet.html`.
  - Still missing: blooms and backruns that read right, and a fall or foam brush.
- **Next time:**
  1. Start from bare paper and the three or four biggest darks, then stop early.
  2. Build the stones' geometry first and check it lit in flat values before any wash.
  3. Try a Venetian subject: the paper-and-darks approach should suit it better than foliage.
- **Files:** `paintings/sargent-mountain-stream/`, in the project where it was painted.
