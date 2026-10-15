# Contact and z-fighting

For anything that rests on something (a lamp on a table, a prop on the floor, settled debris, planted feet) and for surfaces that share a plane. Sliding and contact over an animation are in `animation.md`, rule 14; a full clash sweep is in `trusting-checks.md`.

## Rules

1. **A lowest-vertex height is not a contact check.** One touching vertex proves nothing about the rest of the footprint.
2. **Find shared planes by measurement, not by looking at one frame.** EEVEE flicker depends on the camera's `clip_start` and distance, and Cycles speckle can hide in one render.
3. **Check where it ended up, not that it moved**, with the PASS conditions under the recipes below.
4. **Static objects need one frame.** A turntable that rotates the camera or the object rigidly can't change contact or separation; its frames are for the look.

## Recipes

Both were tested in Blender 5.2 on a lamp and a table. The contact check read +0.04 m for a lamp floating 4 cm and −0.02 m for one sunk 2 cm, and an overhanging lamp read only 7 of 32 footprint vertices over the table, with the centre of mass off the patch. The coplanar check reported a shared plane at 0 and at 2 mm, and nothing at 5 cm.

```python
import math; from mathutils import Vector; from mathutils.bvhtree import BVHTree
from mathutils.geometry import convex_hull_2d
def world_mesh(o):
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
    vs = [ev.matrix_world @ v.co for v in me.vertices]
    ps = [(tuple(p.vertices), (ev.matrix_world.to_3x3() @ p.normal).normalized()) for p in me.polygons]
    ev.to_mesh_clear(); return vs, ps

def resting_contact(obj, support, band=0.002, up=Vector((0, 0, 1))):
    """Signed gap from obj's lowest vertices to the support below (+ floating, - sunk)."""
    vo, _ = world_mesh(obj); vs, ps = world_mesh(support)
    bvh = BVHTree.FromPolygons(vs, [p for p, _ in ps])
    low = min(v.dot(up) for v in vo); foot = [v for v in vo if v.dot(up) <= low + band]
    gaps = [((v - h).dot(up), v) for v in foot
            if (h := bvh.ray_cast(v + up, -up)[0]) is not None]   # from above: a sunk vertex still finds the top
    assert gaps, "no footprint vertex is over the support"
    com = sum(vo, Vector()) / len(vo)          # vertex mean; use a volume centroid for uneven meshes
    pts = [(p.x, p.y) for _, p in gaps]; hull = [pts[i] for i in convex_hull_2d(pts)]
    over = len(hull) >= 3 and all((hull[(i+1) % len(hull)][0]-hull[i][0])*(com.y-hull[i][1])
               - (hull[(i+1) % len(hull)][1]-hull[i][1])*(com.x-hull[i][0]) >= 0 for i in range(len(hull)))
    return dict(footprint=len(foot), over_support=len(gaps), min_gap=min(g for g, _ in gaps),
                max_gap=max(g for g, _ in gaps), com_over_contact=over)

def coplanar_faces(a, b, max_sep=0.005, max_angle_deg=1.0):
    """Faces of A within max_sep of a near-parallel face of B: (count, smallest separation)."""
    va, pa = world_mesh(a); vb, pb = world_mesh(b)
    bvh = BVHTree.FromPolygons(vb, [p for p, _ in pb]); cos_t = math.cos(math.radians(max_angle_deg))
    n, best = 0, math.inf
    for idx, nrm in pa:
        c = sum((va[i] for i in idx), Vector()) / len(idx)
        for s in [c] + [c.lerp(va[i], 0.8) for i in idx]:      # centre and corners pulled in
            loc, nb, _, d = bvh.find_nearest(s, max_sep)
            if loc is not None and abs(nrm.dot(nb)) >= cos_t: n += 1; best = min(best, d); break
    return n, best
```

- **Contact:** PASS needs `over_support == footprint`, `|min_gap|` and `|max_gap|` within your tolerance, and `com_over_contact`. A fix that "dropped it 4 cm" can land 2 cm inside the table, so check where it ended up.
- **Coplanar:** `max_sep` is only the search radius. A separation of 0 is a defect in both renderers; for anything else, compare the separation with the renderer's resolution at the camera distance. Worked example: at 1 m with `clip_start` 0.1 m, Δz ≈ 1² / (0.1 × 2²⁴) ≈ 0.0006 mm, so a 2 mm separation clears it many times over.
  - **EEVEE and the viewport:** depth precision is roughly Δz ≈ z² / (clip_start × 2²⁴) for a 24-bit buffer (derived from the standard depth mapping; Blender's exact buffer format is unverified). The near plane dominates, so raise `clip_start` before you add separation.
  - **Cycles:** it doesn't handle overlapping primitives, so separate them by more than float noise at that scale.
  - After moving a face apart, re-run the contact check, because the move can open a visible gap.

## Red flags

| Thought | Reality |
|---|---|
| "Moved the shade 2 mm, so the z-fighting is gone" | Re-run the coplanar check; compare the separation with the renderer's resolution at the camera distance. |
| "Dropped it 4 cm, so it sits on the table now" | Measure the signed gap. It may be sunk, or still floating at one foot. |
| "The turntable looks clean" | One rotation of a static scene is one measurement. Use the numbers. |
