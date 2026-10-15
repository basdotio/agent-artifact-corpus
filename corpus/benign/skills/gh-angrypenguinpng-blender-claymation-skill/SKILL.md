---
name: blender-claymation
description: Make stop-motion claymation videos in Blender from a one-line idea. Builds a miniature clay set and puppet in Python, animates it "on twos" at 12 fps with hand-made boil, renders with Cycles, encodes an mp4, and presents it in a video player. Use when the user asks for a claymation, stop-motion, plasticine or clay animation, a clay character or short film made in Blender, or "an animation that looks like a real studio made it".
---

# Blender claymation

Turn a short idea ("a penguin who lives in an igloo") into a ~20 second stop-motion clay film:
a tabletop miniature built in real-world metres, a puppet made of lumpy clay primitives, a locked-off
camera with shallow depth of field, and animation that moves in held steps like a real animator
nudging clay between shots.

Everything is scripted: one Python scene file per film, rendered headless. Nothing needs the Blender UI.

## Files in this skill

- `scripts/claylib.py`: clay material, lumpy primitives, lights, camera, easing, `Boil` jitter,
  constant-interpolation keys, CLI (`cli()`) and render entry point (`run()`).
- `examples/igloo.py`: character film. A penguin peeks out of an igloo, waddles out, catches a snowflake and waves.
- `examples/clay_spark.py`: desk-set film. A sleeping clay ball wakes, sprouts rays and hops onto books.
- `scripts/blender.sh`: finds Blender and runs a scene headless.
- `scripts/encode.sh`: 12 fps PNGs to a 24 fps mp4 with grain and vignette.
- `scripts/contact_sheet.sh`: tiles frames so you can review the story in one image.
- `assets/player.html`: video player page for an Artifact (autoplay, muted, loops).
- `references/look-guide.md`: what makes it read as clay, with numbers. Read it before building.
- `references/recording-demo.md`: optional OBS screen recording of the finished result.

Paths below are relative to this skill's directory (`$SKILL`). Work inside the user's project
folder: put scene scripts in `scenes/`, frames in `renders/<name>/`, and finished videos in `out/`.

## Workflow

Keep the user in the loop the way a small studio would, with short, warm updates:
a one-line plan, a still when the set looks right, a note when the character moves, then the film.

### 1. Check tools

`$SKILL/scripts/blender.sh` finds Blender and fails with install hints if it's missing. You need
Blender 4.2+ (tested on 5.2) and ffmpeg. Install as needed:

- macOS: `brew install --cask blender`
- Linux: `sudo snap install blender --classic`
- Windows: `winget install BlenderFoundation.Blender`

Cycles picks the GPU automatically (Metal, OptiX, CUDA, HIP, oneAPI) and falls back to CPU.
On CPU, halve the resolution and samples.

### 2. Plan the short before writing code

20 s = **240 frames at 12 fps**. Write a beat sheet in frame numbers:
establishing hold (about 30 frames), character reveal, two or three story beats, and a button ending
(happy pose, blink, hold). Give every beat anticipation, action and settle. Hold key poses 4–8 frames.

Stage it like a real set: one locked-off camera, a tabletop miniature in metres
(character 5–10 cm tall, camera 0.5–0.9 m away, 50 mm lens), and a backdrop close behind.

### 3. Write the scene script

Copy the closest example into `scenes/<name>.py` and rewrite it for the new idea. Keep its structure:

1. `OPTS = cli('<name>')`, `reset()`, `sc = setup_render(res=OPTS['res'], samples=OPTS['samples'])`, `world(...)`
2. **Set**: materials via `clay(name, color, ...)`, geometry via `sphere / rounded_box / cylinder`
   with `lumpy=` displacement. Nothing perfectly smooth or perfectly straight.
3. **Puppet**: primitives parented under empties. Root at the feet, then body pivot, then head pivot;
   limbs hang off pivot empties so poses are just rotations. Eyes are glossy black beads. Blinks and
   expressions are replacement parts swapped by scale (`1e-4` hides one), like real stop-motion faces.
4. **Lights and camera**: key, fill and rim `area_light`s, plus a practical (lamp glow, window,
   fairy-light bokeh from small emissive spheres). `camera(loc, target, lens, fstop, focus)`.
5. **Animation**: `for f in range(1, 241)`: compute the pose with `seg / ease / ease_out_back`,
   `key()` every animated property on every frame, add `Boil` jitter to puppets, flicker the key
   light ±1.2%. Then call `constant_interp()` and finally `run(sc, OPTS)`.

The sprout, the hops and the snowflake landing on the beak in the examples show squash-and-stretch,
arcs and props that follow a moving part.

### 4. Look-dev with cheap stills

```bash
$SKILL/scripts/blender.sh scenes/<name>.py --still 1 --res 960 540 --samples 32 --out renders/<name>_test
```

Render 4–6 frames that cover the story beats (a few seconds each on a recent GPU), then look at them.
Tile them with ffmpeg `hstack` or `vstack` if that helps. Check these before any full render:

- **Exposure.** Clay washing out to pastel means too bright. Lower light energy or `sc.view_settings.exposure`.
- **Contact.** Feet, rays and limbs touch the ground rather than float or sink.
- **Eyes.** They read at thumbnail size.
- **Composition.** Horizon placement and lead room are right.
- **Bokeh.** Background practicals show as soft discs. A longer lens or lower f-stop gives bigger bokeh.

### 5. Render the full shot in the background

```bash
nohup $SKILL/scripts/blender.sh scenes/<name>.py --res 1600 900 --samples 80 --out renders/<name> > renders/<name>.log 2>&1 &
ls renders/<name> | wc -l   # progress
```

An Apple M4 Pro does about 6–7 s per frame at 1600×900 (240 frames ≈ 25–30 min). Run one render per
GPU at a time, since two in parallel are slower than two in a row. When waiting on a render, match
`pgrep -x Blender` (`blender` on Linux), not `pgrep -f`, which also matches your own watcher's command line.
`--range A B` re-renders a slice after a fix.

### 6. Encode and review

```bash
$SKILL/scripts/encode.sh renders/<name> out/<name>.mp4
$SKILL/scripts/contact_sheet.sh renders/<name> out/<name>_sheet.jpg 20
```

Look at the contact sheet. Every beat should read, with no popping, floating or intersecting
parts. Fix it and re-render only the affected range.

### 7. Present it

If the Artifact tool is available, copy `assets/player.html` to `out/index.html`, set its `<title>`
and reel buttons, and publish it with the videos as supporting files (for example
`files: {"<name>.mp4": "out/<name>.mp4"}`). In the desktop app, open it beside the chat
(`show_pane` → `artifact`). Otherwise give the user the mp4 path.

### 8. Optional: record a demo

To make a screen recording of the finished film playing in the app, follow `references/recording-demo.md`.
Record only the final playback, not the build.
