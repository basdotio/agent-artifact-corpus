# Trusting a check

For anyone writing or relying on a measurement script: a builder's self-check, a solver's constraint, or a verifier's driver.

**A check proves nothing until you have watched it go red on the defect it guards.** Most false PASSes in the source production came from checks that were green while measuring nothing:
- A nearest-face penetration test could never read more than 1.25 cm, so a 3.05 cm finger-in-grip passed.
- The first scene hash called a 0.4 mm vertex nudge "identical".
- An angular-speed tool reported 10,800 °/s on a joint moving at 20.

## The five tests

Before a check's output counts as evidence, it must pass these. **By job size (`SKILL.md`):** Quick and Standard jobs need tests 1 and 4 on every check the verdict relies on; Production needs all five, and the shared libraries keep their fixtures.

### 1. Positive control: it must go red on a known defect

Plant the defect at a known size and confirm the check reads that size, not just "something". For example, push a finger 3 cm into the grip in a scratch copy, then require roughly 3 cm back, not 0.8.

Better still, use real past defects as fixtures. A new clash library had to re-catch a held prop 0.54 m inside the torso and fingers 0.25 m into a grip. A new physics checker had to FAIL a motion known to be bad and PASS its fix. If the check can't fail, it is decoration.

### 2. Near-miss fixtures, one step either side of the threshold

A 1 cm limit needs a 0.9 cm fixture that passes and a 1.1 cm fixture that fails. Then cover the hard state the check is meant to tell apart:
- **Merged multi-shell meshes:** nearest-face depth under-reads them; ray parity alone over-reads them.
- **Symmetric collapse:** both sides shrink together, so an L/R comparison passes.
- **Close but wrong:** a hand 0.4 cm from a grip but flat and open.
- **Unclosed meshes:** they get no inside test at all.

If loosening the threshold or the inside test turns no fixture red, the check isn't pinned.

### 3. Run on the real artefact, not a proxy of it

A check that measures a stand-in can't catch a defect in the real thing. Common stand-ins:
- the spec skeleton instead of the built mesh
- a smooth cylinder instead of the bolted grip
- the lowest vertex instead of every load-bearing part
- the rest pose instead of the animation
- local Z instead of world-down

At least one run must use the built, evaluated, world-space geometry over the real frame range.

### 4. PASS means "read and measured", never "couldn't read"

These are not a PASS:
- A glob that matched 0 parts.
- A frame range that came out empty.
- An inside test skipped on an open mesh.
- A query with 0 pairs examined.

Assert the counts examined (parts, pairs, frames, samples), and print them in the verdict. If something couldn't be measured, report it as UNMEASURED with the reason. **Better no line than a green PASS on data you couldn't read.**

### 5. One definition of every metric

The builder's self-check, the solver's constraint and the verifier must call the same code: one shared library for penetration, and shared definitions for motion metrics. Disagreements came from the same word meaning two things:
- "follow-through 68° past vertical" versus "never crosses straight down"
- overshoot of 2.4% versus 3.5–4.7%, depending on the denominator

If the metric is ambiguous, don't pick the reading that passes. Report it as **unadjudicated**, with both numbers.

**Exceptions can make a check circular.** Clash libraries usually exempt declared contacts up to a tolerance. If that tolerance equals the limit being verified (for example, fingers on a held prop exempt to 1 cm, while the claim is "under 1 cm"), every result up to the limit reads as zero. Always report the raw number and the post-exception number, by running with exceptions off as well as on.

## If the project has no clash library

Start from this signed-penetration check (tested in Blender 5.2: planted depths of 0, 9 mm, 11 mm, 30 mm and 0.3 m read back exactly), and put it where the next check can import it:

```python
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def world_bvh(obj, dg):
    ev = obj.evaluated_get(dg); me = ev.to_mesh()
    verts = [ev.matrix_world @ v.co for v in me.vertices]
    bvh = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in me.polygons])
    ev.to_mesh_clear()
    return bvh, verts

DIRS = [Vector(d).normalized() for d in ((1, .13, .07), (-.11, 1, .17), (.05, -.19, 1))]

def crossings(bvh, p, d, eps=1e-6):
    n, o = 0, p
    while (hit := bvh.ray_cast(o, d)[0]) is not None:
        n += 1; o = hit + d * eps
    return n

def inside(bvh, p):   # majority of three skewed ray-parity tests; B must be CLOSED
    return sum(crossings(bvh, p, d) % 2 for d in DIRS) >= 2

def max_penetration(a, b, dg):
    bvh_b, _ = world_bvh(b, dg)
    _, pts = world_bvh(a, dg)
    assert pts, "no samples examined"
    return max((bvh_b.find_nearest(p)[3] for p in pts if inside(bvh_b, p)), default=0.0)
```

Its limits, which your controls must cover:
- **Samples:** it checks only A's vertices. Add edge midpoints and face centres, or swap A and B, for thin or coarse parts.
- **Closed meshes only:** B must be closed. Split multi-shell meshes and test each closed shell separately, because parity over-reads overlapping shells.
- **One frame at a time:** call `scene.frame_set(f)` and re-fetch the depsgraph for each frame.

## Before any visual review: did the edit run, and touch only its targets?

In BlenderGym, over 75% of open-source models' geometry and material edits produced code that didn't execute. Models also made edits unrelated to the difference they had spotted. So before rendering anything, check:
- **It ran:** the build exited 0 under `--python-exit-code 1`, inside a timeout. Runaway geometry or loops were about a quarter of generated-code failures in a related benchmark.
- **It stayed in scope:** a scene-hash diff shows the objects you meant to change changed, and nothing else did.
- **Its API names are real:** every `bpy` attribute the new code uses exists in this Blender version. Invented API names were the largest error class (about 40%). Check names against `bpy-pitfalls.md` and the API docs for the version you run, not memory.

## Visual verdicts from a model

Treat an image judgement from a vision model, including your own reading of a render, as a weak check:
- **Agreement with people is low.** Claude 3.5 Sonnet agreed with human raters 66% of the time in BlenderGym. Humans agreed with each other 79% of the time, and chance is 50%.
- **Order can decide the answer.** Some models picked whichever image came second.
- **The rule:** for an A/B judgement, ask in both orders and discard answers that flip with the order.
- **Use it for the right things.** Vision models judged materials and style reasonably well, and spatial defects badly: a disconnected handle survived automatic refinement in LL3M.
- **Look AND measure.** Use the image for look, and a measurement for contact, gaps, position and extents.
- **Spend extra effort on verifying, not generating.** In BlenderGym, extra verification search gave more than extra generation.

## Commit the check

Methodology that exists only in the verdict text can't stop the next regression. Save the script where the project map says per-change checks live, or promote it to the shared tools, so the next builder can self-check with it and the next verifier can rerun it.

## When a check turns out wrong

Re-audit every PASS that relied on it. In the source production, re-running six such PASSes found five held and one failed. Then fix the tool, add the fixture that would have caught it, and record the lesson.

## The questions to ask of any check

1. Did it go red on a planted defect, and read the planted size?
2. Is there a fixture just either side of the threshold, and one for the hard case it exists to tell apart?
3. Did at least one run use the real built geometry over the real frames?
4. Does PASS only fire when the counts examined are non-zero and the data was actually read?
5. Do the builder, solver and verifier use the same definition?
6. **If you revert the fix, does the check fail?**

Question 6 is the one that matters. The first five are the usual ways its answer comes out "no" while everything stays green.
