# Simulation: rigid bodies first

For rigid-body shots (walls, debris, collapses), with notes on cloth. Defaults were read from Blender 5.2; checks were tested on a 36-brick wall and a kinematic ball.

## Set-up

1. **Real units and real sizes.** 1 unit = 1 m, gravity 9.81. Bullet guidance is bodies of about 0.4–10 m (moderate: LightWave's Bullet docs). Bricks are smaller: use `use_margin = True` with `collision_margin` 0.001–0.005 m (moderate: forum consensus) and raise substeps. A 0.4 × 0.2 × 0.2 m brick wall with a 0.001 m margin and 20 substeps was stable in the test.
2. **World** (`bpy.ops.rigidbody.world_add()`, then `scene.rigidbody_world`): `substeps_per_frame` and `solver_iterations` default to 10. Raise substeps for fast impacts and iterations for stacks. Set `point_cache.frame_start`/`frame_end` (default 1–250).
3. **Set every body's shape explicitly.** `rigid_body.collision_shape`: `'BOX'` for bricks, `'SPHERE'` for a ball, `'BOX'` or `'MESH'` for the ground. The 5.2 operator gives `'CONVEX_HULL'` to active and passive alike. The manual calls `'MESH'` slow and unstable.
4. **Body defaults:** `mass` 1.0, `friction` 0.5, `restitution` 0.0, `collision_margin` 0.04 with `use_margin` False, `linear_damping` 0.04, `angular_damping` 0.1. Set mass from density × volume.
5. **Animated impactor:** keyframe the ball and set `rigid_body.kinematic = True`. Otherwise it ignores its keys and falls. Use a Hinge or Point constraint to an empty only for a free swing.
6. **Holding a wall still until it's hit:** `use_deactivation = True` and `use_start_deactivated = True` on the bricks. They wake on collision; both are off on new bodies. Bonded walls use `bpy.ops.rigidbody.connect(con_type='FIXED')` with `use_breaking` and `breaking_threshold` (default 10).
7. **Apply scale before simulating.** Non-unit scale is ignored for collision on the first frame (tracker #109108).

## Start state: no overlaps

Bodies that start interpenetrating, or closer than their margin, are pushed apart violently. Stack rows so they touch exactly (BOX margins are inside the shape) and check before baking. A `BVHTree.overlap` test reported **0 pairs** on aligned bricks overlapping by 4 cm, because the contacts are coplanar and edge-on. Use a separating-axis test on the boxes Bullet actually uses (tested: planted 3.8 cm read 0.038 m; touching rows read 6e-8 m):

```python
import math; from mathutils import Vector
def obb(o):                                         # BOX shape = the object's bound box
    c = [o.matrix_world @ Vector(v) for v in o.bound_box]; ax = [c[4]-c[0], c[3]-c[0], c[1]-c[0]]
    return sum(c, Vector()) / 8, [a.normalized() for a in ax], [a.length / 2 for a in ax]
def obb_depth(a, b):                                # > 0 penetration depth; <= 0 separated
    (ca, ua, ea), (cb, ub, eb) = a, b; best = math.inf
    for L in ua + ub + [x.cross(y) for x in ua for y in ub]:
        if L.length < 1e-9: continue
        L = L.normalized()
        best = min(best, sum(e*abs(u.dot(L)) for u, e in zip(ua, ea))
                       + sum(e*abs(u.dot(L)) for u, e in zip(ub, eb)) - abs((cb-ca).dot(L)))
    return best
```

Run it at `frame_start` on every pair within reach (a `KDTree.find_range` on the centres), and FAIL on any depth above a small tolerance (1e-4 m).

## Bake, then read in order

- `bpy.ops.ptcache.bake_all(bake=True)` works headless with no context override (tested, 5.2). Check `point_cache.is_baked`.
- Without a bake, the sim only steps from the previous frame. Always `scene.frame_set(f)` from `frame_start` upward; jumping ahead reads an unsimulated state.
- `bpy.ops.rigidbody.bake_to_keyframes(frame_start, frame_end, step)` converts it to keys and removes the rigid bodies.

## Measuring "natural, not popcorn"

Read every body's world position on every frame, then check (all tested; clean wall vs one with 4 cm planted overlaps):

| Check | Rule | Clean | Planted |
|---|---|---|---|
| First frame any body moves (> 0.5 m/s) | Not before the impactor arrives | 17 (contact at 17) | 1 |
| Max debris speed | ≤ (1 + restitution) × impactor speed + √(2·g·drop height) | 4.8 m/s (bound 8.1) | 24 m/s |
| Still moving at the end | 0 bodies over a small speed in the last ~0.5 s | 0 | 3 |
| Resting penetration | Lowest point vs the ground, at the end | 0 m | 31.8 m (fell through) |
| Scatter | Max distance from start; compare with the brief | 4.9 m | 44 m |

The speed bound is momentum physics, not a sourced VFX rule: a struck body leaves at most (1 + e) × a much heavier impactor's speed, plus what gravity adds. The clean wall's 4.8 m/s was free fall from 1.2 m.

## Cloth and other sims (brief)

- Bake with the same `ptcache.bake_all`, and read frames in order.
- Collision problems: raise the collision distance first, then quality. Self-collision has its own distance. The obstacle needs a Collision modifier (manual, 2.90 pages; re-check in your version).
- 5.2 adds experimental Geometry Nodes cloth (XPBD); the cloth modifier is unchanged.

## Red flags

| Thought | Reality |
|---|---|
| "The bricks are stacked neatly, so no overlap" | Check with box depths; BVH overlap misses aligned contacts. |
| "It explodes, so raise the substeps" | Check the start state first. Overlaps explode at any substep count. |
| "Read frame 90 to check the pile" | Unbaked, it hasn't simulated. Bake, or step from the start. |
| "Debris looks fast, but it's an impact" | Compare with the speed bound. Above it, energy came from somewhere else. |
