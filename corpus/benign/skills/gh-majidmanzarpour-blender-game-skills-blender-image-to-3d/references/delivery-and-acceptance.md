# Delivery and acceptance

Read this before Phase 1 (naming and file layout), Phase 5 (texture contract) and Phases 9 and 10.

Contents
1. Naming and file organisation
2. Texture contract
3. Budgets and LOD policy
4. Review scene and acceptance checklist
5. Export, round trip and the manifest

## 1. Naming and file organisation

Prefixes: `CH_` character, `CR_` creature, `AR_` architecture, `VH_` vehicle, `PR_` prop,
`WP_` weapon, `EN_` environment. Asset name after the prefix in PascalCase. Parts as
`<Asset>_<Part>_LOD<n>` (`CH_Knight_Body_LOD0`, `VH_Buggy_Wheel_FL_LOD0`). Bones `DEF-<name>.L`.
Sockets `SOCKET_<role>`. Colliders `COL_<part>`. Boolean cutters `CUT_<part>`. Reference
objects `REF_<thing>`. No `.001` suffixes in any delivery; validate.py warns on them.

Collections in the master file (init_master.py creates them):

```text
REF        measurements, reference images, axis marker, calibration proxies, game camera
HIGH       sculpt and high-resolution surfaces, never exported
LOW        final deforming and rigid render meshes, all LOD levels
RIG_CTRL   animator controls and constraints, never exported
RIG_DEF    deformation skeleton
COLLISION  simple closed proxies, COL_ prefix
SOCKETS    attachment empties, SOCKET_ prefix
EXPORT     optional prepared delivery copies when the LOW masters must stay non-destructive
```

Asset folder:

```text
CH_Knight/
  CH_Knight_master.blend        non-destructive master
  CH_Knight_baked.blend         delivery copy written by bake_maps.py --save
  asset-brief.md                Phase 0 output
  ref/                          reference images as supplied
  build/                        numbered, re-runnable bpy phase scripts
  review/                       renders and compare sheets per phase, validate.json
  textures/                     baked map masters
  exports/                      .glb or .fbx, asset-manifest.json, animation-contract.json
```

Keep negative and mirrored scale out of every hierarchy. Apply object scale and rotation on
delivery meshes before binding. Retain the non-destructive master and apply modifiers only on
the delivery copy.

## 2. Texture contract

Default set per material: base colour (sRGB), tangent-space normal (Non-Color, OpenGL +Y green;
flip green for DirectX engines and record it), roughness (Non-Color), metallic (Non-Color, only
where the material has metal), ambient occlusion (Non-Color, optional), emissive (sRGB, only where
needed). Document colour space per map and the normal convention in the manifest. Define any
packed layout (ORM, MRA) explicitly per engine; there is no universal packing. Keep unpacked
masters so repacking is lossless. Never bake directional lighting into base colour.

Texel density: one policy per asset family, stated in px per metre (a 2k map covering a 1.8 m
character is roughly 1100 px/m). Unique space for faces, focal costume areas and hero surfaces;
trims and tiles for repeated edges and large surfaces; atlases for small props. Inspect padding at
the lowest useful mip, not only at full resolution. Test opaque or masked solutions before large
overlapping transparency.

Bake settings that hold up: cage extrusion around 1 percent of asset height, ray distance about
2 to 3 percent, margin 16 px at 2k, bake by named group where projections cross onto neighbours
(teeth, layered garments). Inspect normal bakes under a moving light, especially hard edges and
UV seams (Cycles baking guide: https://docs.blender.org/manual/en/latest/render/cycles/baking.html).

## 3. Budgets and LOD policy

Pick a target device and frame budget before finalising density; a desktop 60 fps target gives
16.7 ms for everything, not for meshes alone. These are starting planning ranges, not
measurements or guarantees:

| Asset class | LOD0 tris | LOD1 / LOD2 | Textures | Material groups |
| --- | --- | --- | --- | --- |
| Hero character | 60 to 100k | 15 to 30k / 5 to 10k | 2k main set, 4k only for a proven close view | 3 to 6 |
| Standard character or enemy | 20 to 35k | 8 to 15k / 2 to 5k | shared 1 to 2k | 1 to 3 |
| Large creature or boss | 120 to 200k if the target allows | 40k / 12k | 2 to 4k | 4 to 8 |
| Player vehicle | 60 to 120k | 20 to 40k / 5 to 10k | 2k body, shared parts | 3 to 6 |
| Traffic or prop vehicle | 10 to 25k | 4k / 1k | shared atlas | 1 to 2 |
| Architecture module | 0.5 to 5k per piece | silhouette variants | tiles 1 to 2k plus trim sheet | 1 to 2 |
| Hero building | 20 to 80k | 8k / 2k | tiles, trims, unique decals | 3 to 6 |
| Small prop | 0.3 to 3k | 0.1 to 1k | shared atlas 1 to 2k | 1 |
| Hero weapon | 10 to 30k | 3k / 1k | 2k unique | 1 to 2 |
| Environment piece | 2 to 20k | 0.5 to 5k / 0.2 to 1k | tileable plus detail normal | 1 |

Runtime counts differ from the modelling viewport because UV and normal splits duplicate
vertices; record the engine's measured counts, not Blender's.

LOD transitions are tuned by screen size. Preserve the head, shoulder and weapon silhouette,
garment thickness and joint deformation; remove tiny ornaments and merge material groups before
sacrificing a limb's outline. Decide how skeletal LOD reduces finger, cloth, wing-tip and facial
work. Validate transitions during motion; a static distance sweep misses snapping garments and
changing weapon grips. Colliders and shadow proxies are independent from sculpt detail.

Profile the worst realistic scene (the crowd cap, four players, worst-case materials, cloth and
effects), not one idle asset in a hallway. Reduce the largest measured cost first; keep readable
telegraphs and responsive controls ahead of decorative detail.

## 4. Review scene and acceptance checklist

review_render.py provides the neutral review: grey surroundings, studio or three-point light,
scale ruler on request (`--show-ref`), the reference-matched camera and the game camera pixel
size. Review in this order: clay silhouette, greyscale readability at gameplay size, neutral
material response, UV checker, wireframe, extreme poses, then the asset under the game's actual
lighting sets and amid the crowd density it will live in.

Acceptance for every asset (all must hold before Phase 10 signs off):

- Silhouette, proportions and part breakdown match the reference from the reference camera and
  from front, side and three-quarter views; remaining deviations are listed with measurements.
- Role or type is recognisable at gameplay size, in motion and in greyscale; important outlines
  survive shadow and fog.
- Anatomy, costume or panel assembly and articulation make physical sense; contact points sit on
  the ground; hands hold weapons; wheels touch the floor.
- Normal, roughness and metallic response stay stable under changing light; no baked lighting
  fights the scene.
- Joints, hinges, wings, doors and wheels move through their full range cleanly; no holes between
  modular pieces; no interpenetration on the extreme-pose sheet.
- Secondary motion has no visible body or weapon penetration in ordinary play, a controlled
  fallback, and survives teleports and low frame rates.
- Every clip has a tested loop and event contract; impact, projectile origin and telegraph match
  gameplay.
- LODs preserve role and timing; validate.py reports no FAIL; the round trip resolves every
  dependency and reproduces the review renders.
- Unseen sides and every inferred dimension are listed in the manifest and shown to the user.

## 5. Export, round trip and the manifest

Choose glTF/GLB or an engine-supported FBX after the engine is chosen; keep the .blend master
either way. Export an explicit selection: LOW meshes, deformation bones, sockets, colliders and
intended clips. Control helpers, sculpts, unused actions, cameras and lights stay out.

Blender's glTF exporter carries meshes, skins, morph targets and animation of object transforms,
pose bones and shape keys, with Action or NLA export modes. Physics, procedural shading and
control rigs do not become engine behaviour; bake materials first (bake_maps.py) and treat
cloth and rig logic as separate runtime work (glTF export reference:
https://docs.blender.org/manual/en/latest/addons/import_export/scene_gltf2.html).

Round trip: export, import into a blank Blender (roundtrip.py), then import into a clean engine
project, play every clip with the same weapon or garment combination, view at the game camera.
Confirm nothing depends on missing texture paths or hidden parent transforms. Record the engine's
vertex and material counts.

Manifest (asset-manifest.json, written by export_delivery.py): units and axes for authoring and
export, target height, bounds, files per LOD with tri counts, materials, textures with colour
spaces, texture contract and packing, skeleton with deform bone names and roots, sockets with
world transforms and axis convention, colliders, animation contract pointer, inferred parts, and
external dependencies. The pipeline is complete only when another person can import the asset
from its manifest and reproduce the intended result.

Animation contract (animation-contract.json): per clip name, fps, frame range, length in seconds,
loop flag, events in seconds from pose markers, and any speed, blend direction, root motion or
interruption properties set on the Action.
