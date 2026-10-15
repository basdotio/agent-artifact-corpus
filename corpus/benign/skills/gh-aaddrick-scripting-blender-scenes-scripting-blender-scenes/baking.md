# Baking, UVs and texture maps

For unwrapping, packing, baking high to low, and preparing texture maps, mostly for game assets. Budgets and the glTF export are in `game-assets.md`. Defaults were read from Blender 5.2.

## Rules

1. **UVs: no unintended overlap, even texel density, inside 0–1.** Measure (tested: a stacked face read 10.6% overlap, a 4× shrunk island 166 vs 666 px/m; clean read 0 and 666):
   ```python
   import math; from mathutils.geometry import area_tri
   def uv_report(obj, tex_px=2048, N=512):
       dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); me = ev.to_mesh()
       me.calc_loop_triangles(); uvl = me.uv_layers.active.data; mw = ev.matrix_world
       tris, dens, grid = [], [], {}
       for t in me.loop_triangles:
           uv = [uvl[i].uv.copy() for i in t.loops]; tris.append(uv)
           a3 = area_tri(*(mw @ me.vertices[v].co for v in t.vertices))
           a2 = abs((uv[1]-uv[0]).cross(uv[2]-uv[0])) / 2
           if a3 > 1e-12: dens.append(math.sqrt(a2 / a3) * tex_px)      # px per metre
       for k, (a, b, c) in enumerate(tris):                                # rasterise; cells hit twice = overlap
           for x in range(max(0, int(min(a.x, b.x, c.x)*N)), min(N-1, int(max(a.x, b.x, c.x)*N))+1):
               for y in range(max(0, int(min(a.y, b.y, c.y)*N)), min(N-1, int(max(a.y, b.y, c.y)*N))+1):
                   px, py = (x+.5)/N, (y+.5)/N
                   s = [(q.x-p.x)*(py-p.y) - (q.y-p.y)*(px-p.x) for p, q in ((a, b), (b, c), (c, a))]
                   if min(s) >= 0 or max(s) <= 0: grid.setdefault((x, y), set()).add(k)
       ev.to_mesh_clear(); dens.sort()
       return dict(tris=len(tris), overlap_share=sum(len(v) > 1 for v in grid.values()) / N**2,
                   uv_outside=sum(not (0 <= p.x <= 1 and 0 <= p.y <= 1) for t in tris for p in t),
                   px_per_m_5_50_95=(dens[len(dens)//20], dens[len(dens)//2], dens[-len(dens)//20-1]))
   ```
   - **Packing many islands can collapse them silently.** With `bpy.ops.uv.pack_islands(margin_method='FRACTION', margin=m)`, every island reserves `m` of the atlas on each side, so margins alone need about `islands × (2m)²` of it. Tested on CPU, 6 px margins at 512 px gave:

     | Islands | Margin share | Usable UV area |
     |---|---|---|
     | 200 | 0.11 | 37% |
     | 1,000 | 0.55 | 6% |
     | 1,800 | 0.99 | 0, with UVs outside 0–1 |

     The operator still returned `FINISHED`. In a reported production bake, an atlas collapsed this way baked 0% coverage with no error. Keep the share well below 1 with a smaller margin, fewer islands (join or weld), or a bigger atlas, and run `uv_report` after every pack. Rescaling the UVs back into 0–1 afterwards didn't help there, because the faces were already zero-area.
2. **Bake high to low in Cycles** (CPU is fine):
   - Select the high-poly objects, make the low-poly active, and call `bpy.ops.object.bake(type='NORMAL', use_selected_to_active=True)`. Other types include `'AO'`, `'ROUGHNESS'`, `'DIFFUSE'` and `'EMIT'`.
   - The target is the **active, selected Image Texture node** in the low-poly's material.
   - `scene.render.bake`: `margin` 16 px (default), `margin_type 'ADJACENT_FACES'`, `normal_space 'TANGENT'`. Without a cage, `max_ray_distance` limits the rays (0 means no limit); with `use_cage`, `cage_extrusion` or a `cage_object` sets how far out rays start.
   - Rays go inward from the low-poly. Black holes: rays too short. Detail from the wrong surface: too long (unverified).
   - **Bake many objects into one atlas from a joined copy.** Blender bakes each selected object separately. 300 cubes took 8.2 s against under 0.1 s joined, with identical output (tested on CPU). In a reported GPU bake, the overhead was about 0.4 s per object.
   - **Measure every baked map's coverage.** A bake that wrote nothing still "succeeds". A tiny file size is a hint; the numbers are the proof (tested: a blank map read 0% and a real bake read 81%):
     ```python
     import numpy as np
     def coverage(img, eps=1e-4):
         a = np.empty(len(img.pixels), np.float32); img.pixels.foreach_get(a); rgb = a.reshape(-1, 4)[:, :3]
         return dict(covered=float((rgb.max(1) > eps).mean()), mean=float(rgb.mean()), max=float(rgb.max()))
     ```
3. **Data maps are Non-Color.** Set `img.colorspace_settings.name = 'Non-Color'` for normal, roughness, metallic and AO. Base colour stays sRGB (glTF spec).
4. **Pack ORM for glTF:** R = occlusion, G = roughness, B = metalness. `metallicRoughnessTexture` reads G and B, and `occlusionTexture` reads R, so one image serves both. The exporter takes occlusion from a node group named exactly `glTF Material Output` with an `Occlusion` input. Bake each map to its own image, then pack them (tested: read back as 0.2/0.5/1.0 from planted solid maps, and a swapped input showed in the readback):
   ```python
   import numpy as np
   def pack_orm(ao, rough, metal, name="ORM", path=None):
       w, h = ao.size; assert rough.size[:] == metal.size[:] == (w, h), "maps differ in size"
       def px(im): a = np.empty(w*h*4, np.float32); im.pixels.foreach_get(a); return a.reshape(-1, 4)
       out = np.ones((w*h, 4), np.float32)
       out[:, 0], out[:, 1], out[:, 2] = px(ao)[:, 0], px(rough)[:, 0], px(metal)[:, 0]
       orm = bpy.data.images.new(name, w, h, alpha=False); orm.colorspace_settings.name = 'Non-Color'
       orm.pixels.foreach_set(out.ravel())
       if path: orm.filepath_raw = path; orm.file_format = 'PNG'; orm.save()   # saved, so the exporter finds it
       return orm
   ```
   For a colour-only `'DIFFUSE'` bake, pass `pass_filter={'COLOR'}`.
5. **Normal maps are +Y (OpenGL) for Blender, glTF, Godot and Unity; Unreal is −Y (DirectX)** and needs its green channel flipped (Unreal: moderate, consensus; the rest are engine docs).

## Red flags

| Thought | Reality |
|---|---|
| "Normal map baked, done" | Non-Color, +Y, and flipped for Unreal. Then measure coverage. |
| "`pack_islands` returned FINISHED" | With many islands and fractional margins it can return zero-area UVs. Run `uv_report`. |
| "Test at 512 px to save time" | Margins that fit at 2K can swallow the whole atlas at 512. Treat dense atlases as unchecked at low resolution. |
| "Smart UV Project ran, so the UVs are fine" | Measure overlap, texel spread and UV area. |
