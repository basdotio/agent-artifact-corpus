# Illustrated animation (Kurzgesagt-style)

Mode C: flat-vector scenes where things move, deform and split (cells, creatures, organic props),
built in Remotion. These are the lessons from a mitosis test scene that went from "not fluid enough,
jiggle physics off" to "that's better". The general motion rules, perception principles, frame-strip
verification and safe rendering are in `motion.md`; this file adds what is specific to illustration.

## Steps

`$S`, `$J` and the rules for every mode are in `SKILL.md`. Run these in order; the Pipeline section
below gives the detail and the reasons behind them. The worked example is the `Cell` composition
(`remotion/src/illustrated/cell/`, sound design in `examples/cell/`): copy its structure for a new scene.

1. **Beat sheet**: `$S/run.sh direction.py $J --mode illustrated` picks a structure and an opening
   pattern the last 5 illustrated jobs did not use; build the beats on it unless the request fixes its
   own. Then one focal mover per beat, with its anticipation and payoff. When the scene explains
   something, write and voice the narration first (`explainer.md` steps 2–4) and time each beat to the
   word that names it.
2. **Art**: a flat-vector sprite sheet on a solid background from
   `$S/run.sh image.py "PROMPT" $J/sheet.jpg [--aspect 16:9] [--ref IMG ...]` (Gemini's image model through
   agy, no API key; `--ref` edits or restyles from up to 3 images), then
   `$S/run.sh split.py $J/sheet.jpg $J/parts` (flags: `--bg auto|#rrggbb`, `--threshold 40`, `--downsample 4`,
   `--min-area 200`, `--vtracer "<opts>"`). It writes `aNN.svg` per part, a labelled check sheet and
   `assets.json`. Drop broken pieces; copy the kept SVGs to `remotion/public/illustrated/<scene>/`.
3. **Build** in `remotion/src/illustrated/<scene>/`, authored at 1920×1080 and registered in `Root.tsx`.
   Draw in code anything that deforms or splits. Soft things come from a precomputed, deterministic
   position-based-dynamics simulation, not from sine wobble. Shared helpers: `illustrated/shared.ts`
   (`sampleAt` fractional-frame blending, `trailingShift` for motion blur) and `motion.ts`
   (`squashAlong`).
4. **Anticipation, a 4-frame hit-pause and overshoot** on every big event. Depth layers, lighting and
   juice on the payoff.
5. **Check headless** before any render: `bun scripts/simcheck.ts` (NaNs, event frames), then
   `$S/run.sh check.py illustrated --comp <Comp> --frames <each beat's settled key frame> --stills $J/stills-v1 [--words $J/vo/words.json]`.
   It must print nothing: no text cropped, inside the 4% side margins or in the caption band, every font
   loaded, no dead air in the narration. Mark decoration that is meant to run off the frame with `data-bleed`.
   `--texts` prints every on-screen string to proofread. Register a new composition through `checked`
   in `Root.tsx`, or it sends no report.
6. **Render**: `$S/run.sh remotion.py illustrated $J/visual-v1.mp4 [--comp Cell] [--concurrency 3]`, muted
   1280×720 at 60 fps (rendered from 1920×1080 with `--scale`). Wrap it in
   `systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 --quiet bash -c '...'` (4G for stills
   and strips), one heavy job at a time. `--concurrency 8` is the fastest on a 20-core laptop: a 600-frame
   1080p benchmark took 61 s at 8, 63 s at 12 and 67 s at 16, because the workers queue on Chrome's
   compositor and the encoder, not the CPU. Check with `npx remotion benchmark --concurrencies=4,8,12`.
   `--width 1920` renders 1080p unscaled. Each round writes new versioned paths (`visual-v2.mp4`,
   `strips-v2/`); never overwrite or delete earlier rounds in the same command.
7. **Frame strips**: `$S/run.sh frames.py $J/visual.mp4 $J/strips 240 780:820:2` writes the frames and a
   contact sheet. Read every event's wind-up, hold, release and settle.
8. **Sound**: music with a `--query` matching the confirmed tone, plus sound effects on every event
   (`SKILL.md`, Sound effects). Mix as in `explainer.md` step 9 (`--voice $J/vo.wav` when narrated),
   adding `--sfx`.

## Pipeline

1. **Beat sheet.** For each beat, write down the one focal mover, its anticipation, its payoff, the
   secondary reactions, and its length in frames. If there is narration, add the word the beat lands on.
2. **Art.** Generate a sprite sheet with `scripts/image.py "PROMPT" $J/sheet.jpg`. It runs Gemini's
   image model through agy (the Antigravity CLI) on the signed-in account, with no API key. `--ref IMG`
   (up to 3) edits a sheet or keeps a second sheet in the style of the first. This prompt shape works:
   - "flat vector illustration assets in the style of Kurzgesagt"
   - a single solid background colour given as a hex value
   - assets laid out on a loose grid with empty space between them
   - no outlines, text or background gradient
   - "crisp edges suitable for vector tracing", landscape 16:9

   One roll gave a clean cell body, nucleus, mitochondria, vesicles and chromosomes. One chromosome
   came out broken; drop pieces like that. A 16:9 sheet is a 1376×768 JPEG and takes about a minute.
   The background drifts from the hex asked for (`#14213d` came back as `#132344`), so leave
   `split.py` on `--bg auto` and use the colour it prints as the video background.
3. **Split and trace.** `scripts/split.py` does all of this; its flags cover the background colour,
   threshold, downsample factor, minimum area and vtracer options.
   - Mask each pixel by its distance from the background colour, using a soft alpha ramp so the
     anti-aliased edges stay smooth.
   - Find connected components on a 4× downsampled mask, then crop each with padding.
   - Save each crop as a transparent PNG and trace it with
     `vtracer --mode spline -f 8 -p 7 -g 12`.
   - Rasterise the SVGs back into a labelled contact sheet and look at it.
   - Use the same background colour in the video, so the faint dark fringe from tracing disappears.
4. **Draw in code anything that deforms.** Membranes, chromatid arms and anything that bends or splits
   must be code. A traced sprite cannot change shape. Colour the code shapes with values sampled from
   the generated art so they match the sprites.
5. **Build** at 1920×1080, 60 fps, with physics for anything soft (see the soft-body recipe below)
   and eased curves for designed moves. Keep the event times as named constants in one place. Start
   from the `Cell` example in `remotion/src/illustrated/cell/` (`sim.ts` for the physics, `Cell.tsx`
   for drawing, blur and layers). The skill renders it at 720p60 with `--scale`.
6. **Verify** (see the Verify section below), fix, and repeat.

## What made it smooth

Ranked by how much each one changed the result.

1. **Physics instead of sine waves.** The first version faked jelly with sine ripples and hand-placed
   wobble "kicks" on a timer. It looked dead, because nothing reacted to motion. A soft-body
   simulation gives lag, overshoot and settle that respond to every push.
2. **Anticipation, hit-pause, overshoot on every big event.**
   - Before the event, wind up the opposite way: the nucleus dips 4% before it bursts, chromosome arms
     are tugged open for 18 frames, the lobes squash sideways before the pinch.
   - Freeze the whole simulation for 4 frames right before the release.
   - After the release, overshoot and settle. The underdamped step response
     `1 - e^(-ζωt)(cos ω_d t + (ζω/ω_d) sin ω_d t)` with ζ = 0.5 and ω = 12 gives one visible overshoot.
   - Force the event to happen on its frame instead of detecting it, so it always lands on the beat.
3. **One focal mover per beat**, with staggered reactions (`motion.md` rule 1).
4. **Contents trail and react.** Organelles sit on damped anchor springs (stiffness 60, damping 5.4),
   collide with the membrane and with each other, and squash along their velocity:
   `rotate(dir) scale(1+s, 1/(1+s)) rotate(-dir)`, with `s = min(0.22, speed/1600)`. A lean into
   horizontal motion sells weight.
5. **Detail without clutter.**
   - **Depth:** 5 parallax layers (far blurred cells, two dot layers, the subject, blurry foreground
     dots). Turn the far layers down until they stop competing with the subject; the first pass was
     too loud.
   - **Lighting:** fill the outline, then draw inner bands as strokes clipped to the outline (wide dark
     band, medium band, thin rim light). Add an offset lighter fill for a shading crescent, and a
     highlight arc made from the outline's own upper-left points pulled toward the centre, so it
     follows every deformation. A peanut shape needs one arc per lobe, or the arc hooks into the neck.
   - **Payoff juice:** a flash, a saturation and brightness spike, a glow jump, 6–12 particles that
     linger and drift, and a 2–4 px camera nudge instead of a shake.
   - **Story detail:** spindle fibres growing from glowing centrosomes to each chromosome, timed to
     the stagger. Fragments drift away from the burst.

## Soft-body recipe

Use position-based dynamics (Müller, *Ten Minute Physics*; the method JoltPhysics cites). Precompute
the whole timeline once per render worker (`cache ??= simulate()`) with a fixed step and 4 substeps per
frame. The simulation must be a pure function of time, because every Remotion worker has to produce
identical frames. A 1200-frame run takes about 0.6 s.

**Membrane: a ring of 64 particles.**
- **Goal spring** toward a designed target outline (stiffness 90, damping 2). The target keeps the
  timing art-directed; the lag and overshoot come from the physics.
- **Edge constraints** use the goal polygon's per-edge length, not the average length. With the
  average, the edges fight the goal.
- **Bending constraint:** pull each point's deviation from its neighbours' midpoint toward the goal
  outline's deviation (stiffness 0.12). This removes kinks and keeps the low wobble modes.
- **Area constraint** acts as internal pressure. Keep it soft (stiffness 0.06) so the cell can breathe;
  at 0.3 the membrane was rigid.
- **Goal points** sit at equal arc length along the outline, so a closing neck doesn't crowd points
  into a fold.
- **Neck shape:** for a peanut target, use a smoothed `|cos a|` (`sqrt(cos²a + 0.012)`) so the neck is an
  hourglass, not a cusp.
- **Contractile ring:** add a stiff local pull at the furrow. Without it, pressure pushes the neck
  back open just before the snap.
- **Wobble impulses** must keep the volume: oval `cos 2θ` and three-lobe `cos 3θ` radial velocity
  kicks. The area constraint cancels a uniform outward kick, so it produces no visible wobble.
- **Splitting one ring into two:** split by each particle's fixed goal angle, never by its current x
  position, because a pinched neck folds across the midline. Resample each half to N points by arc
  length. Two guards: no zero-length segments, and the index must never run past the end. The first
  attempt produced NaNs and collapsed daughter cells.
- **Daughters** collide with each other at the midline, then spring apart with one overshoot.

**Contents.**
- Contents are particles on anchor springs. They push membrane particles outward, and the membrane
  takes 80% of the correction, so it bulges locally.
- Contents also push each other apart. Bonded pairs (sister chromatids) are held together until the
  release.
- **Chromatid arms** are dragged tips on a fixed-length tether to the centromere. A minimum gap
  between tips keeps a dragged chromatid a V, never a thin rod.

## Remotion pitfalls

- Sprites: `<Img src={staticFile(...svg)}>`, absolutely positioned. Split a sprite in half with
  `clip-path: inset(0 50% 0 0)`.
- For the gooey-blob look without physics, run two circles through an `feGaussianBlur` and an alpha
  threshold `feColorMatrix`. Use it for quick tests only; it cannot react to forces.
- If `bun install` hangs on a Remotion project, use `npm install`.

## Verify

On top of the frame strips and checklist in `motion.md`:

- **Headless simulation check before any render** (`bun scripts/simcheck.ts` for the example). A script
  that runs the simulation and prints:
  - NaNs
  - the frame each event fires on
  - per 0.5 s, the radius spread of each ring (the jiggle amplitude and how it settles)
  - neck width against its target
  - the gap between the daughter cells
- **Stills** at the key frame of each beat, built into a contact sheet.
- **Extra checklist items:**
  - anticipation and overshoot on every big event
  - contents lag and react
  - no sprite overlaps
  - payoff held at least 20 frames
  - depth, lighting and juice on the payoff

A full 20 s 1080p60 illustrated render took about a minute inside the memory cap.
