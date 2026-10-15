# Scatter and instancing

For Geometry Nodes scatters at scale (forests, rocks, crowds of props) and checking them headless. Tested on a 40 m terrain with a flat half and a 45° half, scattering trunks in Blender 5.2.

## Rules

1. **Distribute with Poisson disk.** Use `GeometryNodeDistributePointsOnFaces` with `distribute_method = 'POISSON'`; its inputs are `Distance Min`, `Density Max`, `Density Factor` and `Seed`.
   - Distance Min caps the count. Density 1/m² over 800 m² with Distance Min 2 m gave 136 points, not 800. Predict the count from the spacing, not area × density, and compare the measured count with your prediction.
   - The minimum distance holds within one node's output. Separate distributions, such as trees and rocks, don't avoid each other (unverified in the docs), so check across classes.
2. **Mask slope by the face normal:** slope ≤ 30° means `normal.z ≥ cos(30°) = 0.866`. Use Normal → Separate XYZ → Compare (≥) into the distribute node's `Selection`.
   - The mask tests the face under the point, not the footprint. In the test, one masked trunk still straddled a crease onto the 45° slope. Check the footprint (rule 5).
3. **Build node trees through the 4.0+ interface API:** `ng.interface.new_socket(name, in_out='INPUT', socket_type='NodeSocketGeometry')`. Address modifier inputs by the socket's `identifier`, not its index (`bpy-pitfalls.md`, Data API, has the 5.2 change).
4. **Read instances without realizing them.** Both read paths below gave the same counts (136 and 318):
   - `depsgraph.object_instances`: filter on `inst.is_instance` and `inst.parent.original == src`, and **copy** `inst.matrix_world.copy()` inside the loop, because the iterator reuses its memory.
   - (4.5+) `geo = ob.evaluated_get(dg).evaluated_geometry()`, then `pc = geo.instances_pointcloud()`. `pc.attributes["instance_transform"]` holds local 4×4 transforms, so multiply by `matrix_world`, and `.reference_index` indexes `geo.instance_references()`. **Keep `geo` in a variable.** Chaining the calls frees it, and reading `pc` raised "StructRNA of type PointCloud has been removed".
   - Realize Instances only on a throwaway copy, because it multiplies memory.
5. **Check spacing, footprint slope, ground contact and count** (tested: with no slope mask, 174 bases were on steep ground against 1 with it; with Distance Min 1 m checked at 2 m, 674 pairs were too close against 0):
   ```python
   import math; from mathutils import Vector; from mathutils.kdtree import KDTree; from mathutils.bvhtree import BVHTree
   def scatter_report(bases, ground_me, ground_mw, min_spacing, max_slope_deg, footprint_r):
       bvh = BVHTree.FromPolygons([ground_mw @ v.co for v in ground_me.vertices],
                                  [tuple(p.vertices) for p in ground_me.polygons])   # base mesh, no instances
       kd = KDTree(len(bases))
       for i, p in enumerate(bases): kd.insert(p, i)
       kd.balance()
       close = sum(1 for i, p in enumerate(bases) for _, j, _ in kd.find_range(p, min_spacing) if j > i)
       cos_max = math.cos(math.radians(max_slope_deg)); steep = off_ground = off_edge = 0
       ring = [Vector((math.cos(a), math.sin(a), 0)) * footprint_r for a in (0, 2.1, 4.2)]
       for p in bases:
           hits = [bvh.ray_cast(p + o + Vector((0, 0, 50)), Vector((0, 0, -1))) for o in [Vector()] + ring]
           if any(h[0] is None for h in hits): off_edge += 1; continue
           steep += any(abs(h[1].z) < cos_max for h in hits)
           off_ground += abs(hits[0][0].z - p.z) > 0.01
       return dict(count=len(bases), pairs_too_close=close, on_steep_ground=steep,
                   not_on_ground=off_ground, footprint_off_terrain=off_edge)
   ```
   - Give the KD tree one point per object, with the spacing set to the sum of the two **trunk** radii plus clearance, per class pair.
   - For irregular shapes such as rocks, follow up close KD pairs with a closed-mesh penetration test (`trusting-checks.md`).
   - `footprint_off_terrain` counts bases whose footprint hangs past the terrain's edge, which may be fine. `not_on_ground` uses 1 cm as an example tolerance; scale it to the subject.
6. **Decide where overlap is acceptable before checking.** Canopies interpenetrate in real forests. Trunks, rocks, and grass inside rocks should not. Use per-class radii, and never one radius for the whole tree (unverified: no source; it follows from the brief).
7. **Budget memory and render time.**
   - Instances share mesh data; realizing them copies it.
   - For animations, `scene.render.use_persistent_data = True` keeps the BVH between frames, at a cost in memory.
   - `scene.render.use_simplify` with `simplify_subdivision` and `simplify_child_particles` (plus `_render` variants) cuts preview cost.
   - Test-render one frame at final settings and record its time and memory before committing to a flythrough.

## Red flags

| Thought | Reality |
|---|---|
| "Poisson, so nothing intersects" | Spacing is point-to-point, and across separate distribute nodes it is unverified. Check trunk radii across classes. |
| "Slope mask on, so no trees on slopes" | The mask reads one face. A footprint can straddle a crease. |
| "8,000 requested" | Distance Min caps the count. Measure it. |
| "Realize the instances so I can read them" | Read `object_instances` or `evaluated_geometry()` instead. |
