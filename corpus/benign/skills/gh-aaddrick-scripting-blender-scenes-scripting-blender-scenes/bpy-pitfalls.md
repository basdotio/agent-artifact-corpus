# Blender headless pitfalls (4.0–5.2)

Traps that cost real time in practice. Each line gives the symptom, then the fix. Rows tagged with a version apply from that release on. Check the release notes if you run something older or newer.

## Environment and determinism

| Symptom | Fix |
|---|---|
| `PYTHONHASHSEED=0` set but builds still differ run to run | Blender's Python ignores environment variables unless started with `--python-use-system-env`. Re-exec Blender with that flag from a bootstrap, and assert `sys.flags.hash_randomization == 0`. |
| Builds still differ after seeding | Set iteration, unsorted BMesh iteration, and `bmesh.ops.bevel` / `create_uvsphere` topology vary. Sort before iterating, then hash two fresh builds and compare. |
| AgX missing, `view_transform` raises TypeError, ~150 lines of OCIO noise | A distro-packaged Blender can ship an OCIO config newer than the OCIO library it links. Export `OCIO` (or `BLENDER_OCIO`, which wins) pointing at a compatible config, for example a copy of the bundled one with `ocio_profile_version` lowered to the library's version, for **every** script, not just the main build. Blender's colour management reads these itself, so `--python-use-system-env` is not needed (tested 5.2; that flag affects only Python's own variables such as `PYTHONPATH`). |
| `view_transform`, `look`, `denoiser`, `compute_device_type` enums list only `NONE` | Dynamic enums are empty in `--background`. Assign the value and catch the error; don't validate against the enum list. |
| `scene.cycles.device='GPU'` renders on CPU anyway | Also set the preferences compute device and enable the devices. Confirm with `nvidia-smi` during the render. Distro builds may lack OptiX; an official build can be about 2× faster. |
| First Cycles render takes ~300 s longer than expected | One-time GPU kernel compile. Don't time-box a first render as if it were warm. |
| `pip` packages missing (`scipy`) | Blender's bundled Python has numpy only. Write solvers in numpy, or export data and run heavy maths in a separate venv. |
| Script exits silently mid-run | `argparse` (or another library) called `sys.exit()`, or code called `os._exit()`. Parse the args after `--` yourself, or catch `SystemExit`. Other causes are in `render-server.md`. |
| Script raised, but the shell saw exit code 0 | Pass `--python-exit-code 1` **before** `-P`; after `-P` it has no effect (tested 5.2: exit 1 before, 0 after). It works with or without `--factory-startup` (which does turn the GPU off; see `render-server.md`). Piping into `tee` also hides it: use `set -o pipefail` or `${PIPESTATUS[0]}`. |
| Renders differ slightly between CPU, CUDA and OptiX | Expected. Record the device and denoiser with every render. Compare across devices with a tolerance, never for exact equality. |
| Frame-to-frame noise crawl or flicker in animation | Pin `cycles.seed` and turn off animated seed. Set the noise threshold, min samples and denoiser explicitly; Automatic picks the denoiser by hardware. |

## Animation and rigging

| Symptom | Fix |
|---|---|
| `'Action' object has no attribute 'fcurves'` (4.4+) | Layered actions: `act.slots.new(...)`, assign the slot, then `anim_utils.action_ensure_channelbag_for_slot(...)` → `cb.fcurves`. Readers need a fallback that walks layers → strips → channelbags. |
| `Cannot return channelbag when slot is None` (4.4+) | Assign the action slot to the ID before asking for the channelbag. |
| Assigned an action but nothing animates (4.4+) | Assigning `animation_data.action` may not assign a slot. Set `animation_data.action_slot` and assert it isn't None. |
| `rotation_euler[0] already keyed`, `material name already exists` | Apply steps aren't idempotent. Always apply animation and FX to a freshly built model; never re-run them on an output blend. |
| Angular-speed tool reports ~10,000 °/s on a slow joint | Quaternion sign flip: q and −q are the same rotation. Use `2*atan2(|xyz|, |w|)` of the relative rotation. |
| One driver input (e.g. `grip`) passes its limit but a segment breaks a coupled limit | Check the evaluated per-bone values after drivers, not the input scalar. |
| `Dependency cycle detected` in the log; pose lags a frame or jitters | Driver variables count as dependencies even when the expression never uses them. Two bones whose drivers or constraints reference each other form a cycle. Design one-way chains, and fail the build on this log line. |
| Drivers slow, or dead in headless runs | Python-expression drivers need auto-run. Keep expressions simple (arithmetic, `min`, `max`) and assert `driver.is_simple_expression`. |
| IK bends the whole body | `chain_count = 0` means "up to the root". Always set it explicitly. Stretch also needs the bone's `ik_stretch` above 0. |
| Euler channels jump by 360° or flip between frames | When building rotations from matrices, use `mat.to_euler(order, prev_euler)` or `euler.make_compatible(prev)`. |
| `Bone.layers` or `bone_groups` missing (4.0+) | Bone collections replace them: `arm.collections.new()`, `coll.assign(bone)`. Nested collections are only in `arm.collections_all` (4.1+). |
| Some bones deform nothing after automatic weights | Bone-heat weighting can fail partially without raising. Assert every deform bone has a non-empty vertex group. |
| A bone-parented object jumps when parented, or rotates about the wrong point | `parent_type='BONE'` places the child relative to the bone's **tail**, not its head. Set `matrix_parent_inverse` deliberately, and assert world vertex positions are unchanged by parenting. |
| A baked action loses constraint or driver motion | Bake with `visual_keying=True`, and only after the IK and constraints are final. |

## Data API and context

| Symptom | Fix |
|---|---|
| `bpy_prop_collection` rejects slice steps or Object keys | Index by name. |
| Skipped or doubled objects when renaming in a loop; crash toggling `hide_*` over `collection.all_objects` | Renaming re-sorts `bpy.data`. Iterate over `list(...)` or `[:]`. |
| Random crash after adding geometry, removing a datablock or switching mode | Python references to sub-data (`mesh.polygons`, `points[0]`) dangle after the container changes. Re-fetch after any change, and store indices, not references. `faulthandler` helps find these. |
| `matrix_world` stale right after setting `location` | Evaluation is lazy. Call `context.view_layer.update()` first. |
| `bpy.data.objects[name]` returns the wrong object | Names get `.001` suffixes or are truncated. Keep the objects your code created; don't look them up by name. |
| Evaluated mesh has no UVs or vertex groups | `to_mesh()` keeps only display layers. Pass `preserve_all_data_layers=True, depsgraph=dg`, and call `to_mesh_clear()` when done. |
| `poll() failed, context is incorrect` (4.0+) | Use the data API. If an operator is unavoidable, wrap it in `with context.temp_override(...)`; the dict override argument was removed. |
| Geometry-nodes input writes `modifier["Socket_2"] = …` break (5.2) | Use `modifier.properties.inputs.<identifier>.value`. Address sockets by identifier, not index; sockets are dynamic from 4.1. |
| `scene['cycles']` raises (5.0+) | Dictionary access to registered properties was removed. Use `scene.cycles`. |
| `pc.attributes` raises "StructRNA of type PointCloud has been removed" (4.5+) | `ob_eval.evaluated_geometry().instances_pointcloud()` frees the GeometrySet. Keep `geo = ob_eval.evaluated_geometry()` in a variable while reading. |
| A `use_selection=True` export writes the wrong objects | Importers (`import_scene.gltf`) leave the imported objects selected. Set the selection explicitly before every export. |

## Geometry

| Symptom | Fix |
|---|---|
| EXACT boolean returns a closed mesh that is badly wrong (0.71 m housing → 0.08 m plate) | Manifold is not correctness. Guard every boolean with per-axis bbox loss ≤10% **and** manifold. |
| MANIFOLD boolean refuses every cut; EXACT with `use_self` is slow and leaves open edges | A weld at 1e-5 m fused near-coincident shells into edges shared by 3–4 faces. Nudge the shells apart ~0.5 mm before welding. |
| `geom: found the same (BMVert/BMEdge/BMFace) used multiple times` | Deduplicate the geom list passed to `bmesh.ops`. |
| `'MeshEdge' object has no attribute 'link_faces'` | That is the BMesh API. Mesh data (`me.edges`) and BMesh (`bm.edges`) are different types. |
| Right-side parts follow left bones, or `.R` faces cut on the inner side | Side parsing by suffix is fragile (dotted names, unsided parent bones). Assert side match on every parent, and never mirror twice: a compensating flip flag plus a fixed source gives a double flip. |
| Atlas bakes come out black; UVs land outside 0–1 with zero area; `pack_islands` returned `FINISHED` | Fractional margins on many islands consumed the atlas (about `islands × (2 × margin)²` ≥ 1). Shrink the margin, cut the island count, or raise the resolution (`baking.md`, rule 1). |
| `transform_apply(scale=True)` moved the object | It also applied location in that context. Pass `location=False` explicitly and re-check. |
| Bounding boxes overshoot on rotated parts | `obj.bound_box` is local and axis-aligned. Use evaluated world-space vertices. |
| Mirrored copy renders inside-out or shades dark | Negative scale and bmesh mirrors flip face winding. Recalculate normals, and assert `bm.calc_volume() > 0` on both sides. |
| Unused datablocks vanish on save | Orphan purge. Set `use_fake_user` on anything kept for later. |
| `BVHTree.overlap` finds no pairs between boxes that clearly overlap | It misses coplanar and edge-on contacts, which is every aligned stack (a 4 cm overlap read 0 pairs). Use a box separating-axis test (`simulation.md`) or a closed-mesh penetration test. |
| Flickering stripes where two surfaces meet (EEVEE/viewport); speckled or black patches (Cycles) | Coplanar overlapping faces. EEVEE: a depth-buffer limit, made much worse by a small camera `clip_start`. Cycles has no depth buffer but doesn't handle overlapping primitives (developer commit note). Find them with `contact.md`, then separate, delete the hidden face, or merge. |
| Bevel or inset wrong on a scaled object | They act on the untransformed geometry. Apply scale and rotation first, and assert `obj.scale == (1,1,1)` before the modifier stack. |

## Shading and render

| Symptom | Fix |
|---|---|
| Wear streaks follow each part's local Z | Object-space texture coordinates. Map wear to world-down. |
| `TypeError` multiplying a float by a socket | Use `node.inputs["X"].default_value`, not the socket. |
| `scene.node_tree` missing; no Composite node (5.0+) | Use `scene.compositing_node_group` with a Group Output node. Node options are input sockets. |
| Workbench previews come out dark | Workbench picks up the scene exposure. Reset exposure for previews. |
| EEVEE preview disagrees with Cycles on fog, thin walls or reflections | EEVEE leaks light through thin walls (give them thickness). Its volumes are single-scatter only and don't appear in reflections or probes. Judge fog, haze and scale cues in Cycles. |
| Principled BSDF input `Subsurface` or `Transmission` not found (4.0+) | They were renamed `Subsurface Weight` and `Transmission Weight`. |
| `libx264` fails at 240x135 | Needs even frame dimensions. Delete failed MP4s before re-encoding. |
| `file_format = 'FFMPEG'` raises "enum not found" (5.0+) | Set `image_settings.media_type = 'VIDEO'` first. Then choose the container with `ffmpeg.format` (default MKV). |
| JPEG output lost its transparency | Choosing JPEG sets `color_mode` to RGB. Use PNG or EXR with `'RGBA'` for `film_transparent` renders. |

## Process plumbing

- Run Blender in the background (`run_in_background`). Foreground calls hit the 120 s tool timeout mid-build.
- Never wrap a script in a lock it already takes itself. A render wrapper that took the GPU lock, wrapped in a second flock, kept the GPU locked after its agent had finished.
- Never write generic filenames (`inspect.py`, `json.py`, `test.py`) to a shared scratch directory on `sys.path`. One `inspect.py` broke numpy imports for 14 agents.
- Compute the repo root from a known marker file, not by counting `dirname`s.
- Read the clock with `date`; never estimate the time.
- Wrapper scripts that grep Blender's output down to a summary also hide its warnings. Debug from the raw `blender` command and its full log.
- In a staged pipeline, debug a stage by opening its hand-off `.blend` (`blender -b stage.blend -P inspect.py`) and printing what it holds, rather than re-running everything before it.
