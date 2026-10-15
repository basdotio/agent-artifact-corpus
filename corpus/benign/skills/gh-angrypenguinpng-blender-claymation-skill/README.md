# blender-claymation

A skill for Claude that makes **stop-motion claymation films in Blender** from a single prompt.

> "can you make a stop motion claymation video (~20 seconds) of a little penguin who lives in an igloo?"

Claude plans a beat sheet, builds a tabletop miniature and a clay puppet in Python, and animates it
"on twos" at 12 fps with hand-made boil and light flicker. It renders with Cycles, checks the frames,
and hands you an mp4 (or a video player artifact).

| `examples/igloo.py` | `examples/clay_spark.py` |
| --- | --- |
| A penguin peeks out of its igloo, waddles into the snow, catches a snowflake and waves. | A sleepy clay ball wakes up, sprouts into a starburst and hops onto a stack of books. |

## Install

Claude Code:

```bash
git clone https://github.com/angrypenguinpng/blender-claymation-skill ~/.claude/skills/blender-claymation
```

Then ask for a claymation in any session.

**Requirements:**

- Blender 4.2+ (tested on 5.2): `brew install --cask blender` on macOS, `snap install blender --classic` on Linux.
- ffmpeg.
- A GPU helps a lot. Cycles auto-selects Metal, OptiX, CUDA, HIP or oneAPI.

On an Apple M4 Pro a 20 s film renders in about 25 minutes at 1600×900.

## Run the examples yourself

```bash
scripts/blender.sh examples/igloo.py --still 120 --res 960 540 --samples 32   # one test frame
scripts/blender.sh examples/igloo.py --res 1600 900 --samples 80              # full 240 frames -> renders/igloo/
scripts/encode.sh renders/igloo out/igloo.mp4                                 # 24 fps mp4 with grain + vignette
```

## What's inside

```
SKILL.md                    the workflow Claude follows
scripts/claylib.py          clay material, lumpy primitives, lights, camera, easing, boil, CLI
scripts/blender.sh          find Blender and run a scene headless
scripts/encode.sh           frames -> mp4
scripts/contact_sheet.sh    frames -> one review image
scripts/obs.js, record_window.sh   optional OBS screen recording of the result (macOS)
examples/                   two complete films to copy from
assets/player.html          video player page for an artifact
references/look-guide.md    the numbers behind the clay look
references/recording-demo.md
```

Inspired by [Alex Albert's post](https://x.com/alexalbert__/status/2102458348511879448) showing
Claude making claymations in Blender from one prompt.

MIT licensed.
