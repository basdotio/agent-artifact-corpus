# Blender 5.x notes

API changes and runtime behaviour met while building assets with this skill on Blender 5.2, plus
review and look-development lessons that are easy to lose between sessions. Read this when a
script fails on a 5.x API, before long renders or bakes, and when the review renders and the
user's viewport disagree.

## 1. API changes that break older bpy code

- Geometry Nodes modifier inputs are no longer ID properties: `mod["Socket_2"] = v` raises
  "id properties not supported". Set `getattr(mod.properties.inputs, identifier).value = v`, where
  `identifier` comes from the node group's interface socket (`socket.identifier`). Keep a fallback
  to `mod[identifier]` for 4.x.
- Actions are layered: `action.fcurves` is gone. Walk `action.layers[*].strips[*].channelbags[*].fcurves`
  (or keyframe through `keyframe_insert` and let Blender create the channelbag).
- Materials and worlds always use nodes; `use_nodes` is deprecated. Guard it with
  `bpy.app.version < (5, 0, 0)`.
- Vertex group names live on the mesh data. A copied mesh already carries the names, so creating
  the same group again yields `Group.001`; check `ob.vertex_groups.get(name)` first, and merge any
  `.001` groups before export.
- EEVEE's engine identifier differs between versions (`BLENDER_EEVEE_NEXT` in the 4.2-era
  releases, `BLENDER_EEVEE` in 5.x, where the other is rejected); try both inside
  `try/except TypeError`.
- EEVEE does not support the Principled Hair BSDF. Give hair (and anything else EEVEE cannot shade)
  two Material Output nodes, one with target EEVEE and one with target CYCLES. Cycles renders the
  CYCLES-target output even when the EEVEE one is active; anything that rewires an output for
  baking must pick the same node (`scripts/bake_maps.py` does).
- Look nodes up by type (`n.type == "BSDF_PRINCIPLED"`, `"OUTPUT_MATERIAL"`, `"BACKGROUND"`), never by
  display name: names are translated in non-English UIs.
- Command-line values that start with a minus sign need the `--arg=-0.28,0,1` form, or argparse
  reads them as a new option.

## 2. Runtime and performance

- Cycles on Apple Silicon: enable only the METAL device. Adding the CPU as a second device made
  frames about twice as slow (M-series Pro, 1080p, 48 to 64 samples with OpenImageDenoise ran at
  12 to 20 s per frame GPU-only).
- `render.use_persistent_data = True` speeds up animations where only the camera or a few objects
  move.
- Selected-to-active bakes spend most of their time syncing the scene: hide every renderable that
  is neither a source nor the target (except for AO, where neighbours should occlude). Strand hair
  with tens of thousands of curves is the usual culprit.
- Transparent shells (corneas, visors, glass) catch bake rays in front of what they cover; leave
  them out of the sources (`bake_maps.py --exclude-sources`) and give the delivery copy its own
  simple transparent material.
- A long headless render should write numbered frames and skip frames that already exist, so it
  can be stopped, fixed and resumed; encode with ffmpeg at the end.

## 3. Review and look-development lessons

- The viewport is what the user sees. An object hidden only with `hide_render` (a body mannequin
  under the costume, a helper) still shows in the user's viewport and pokes through there; hide
  it for both viewport and render, and review close-ups with everything the viewport shows.
- Match painted concept colours by numbers: sample the median sRGB of the same world-space box
  in the reference and in a render under the review lights, and adjust albedo until they agree.
  Grey-looking leather was specular sheen and edge-wear masks firing over whole thin straps, not
  the base colour.
- Painted concept metal usually reads brown-lit: give glossy rays their own warm studio (Light
  Path "Is Glossy Ray" in the world shader) while diffuse rays keep a dark environment.
- The Standard view transform keeps saturated skin and hair close to a painted sheet; AgX washes
  them out. Pick one for the look and keep it for every comparison.
- When a colour looks wrong, test hypotheses one at a time on a small render border (lighting,
  reflections, clipping, the shader itself) and give each object a flat emission debug colour to
  find which object is at fault before changing materials.
