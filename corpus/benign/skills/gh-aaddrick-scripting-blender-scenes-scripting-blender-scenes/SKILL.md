---
name: scripting-blender-scenes
description: Use when building, modifying, rigging, animating, lighting, simulating, scattering, exporting or reviewing a Blender scene through bpy scripts or headless Blender, especially when an agent can't see the viewport, when a change claims to fix clipping, contact, shape, scale or motion, or when verifying someone else's Blender work.
---

# Scripting Blender scenes

You can't see the viewport. Lasting fixes come from **measuring the built artefact over the real frames, with a check proven to fail on the defect**, not a substitute such as the spec, the rest pose or the lowest vertex.

## Size the job first

| Size | For example | Required |
|---|---|---|
| **Quick** | A diagnosis, a small fix, one static prop (even a game crate), a few stills | Five-line project note; a controlled check for each risk the verdict relies on; short verdict, labelled "builder-checked, not independently verified" if nobody else checks |
| **Standard** | Anything that moves: a client clip, a rigged or skinned asset, a sim or scatter shot | Five-line note plus the map sections it uses; a controlled check for each risk and neighbour the verdict relies on; independent verification if available |
| **Production** | Many shots, parts or agents | Everything in the topic files, including all five tests in `trusting-checks.md` |

"Controlled" means it went red on a planted defect (`trusting-checks.md`). Numbers in the topic files are examples from a building-sized machine, not limits. Derive yours from the subject's size: a 3 mm door gap needs sub-millimetre checks.

## Always

1. **Know the project.** Find its map and confirm it's this project's. If none exists, write one (`project-map.md`); five lines on a Quick job.
2. **Scripts are the source; the `.blend` is output.** Edit the scripts and rebuild.
3. **Measure the built, evaluated, world-space result** over the frames that matter.
4. **Look and measure.** Read full-size frames from the shot camera (or a preview camera, for assets with none). Either failing is a FAIL.
5. **Name the neighbours** and report what got worse.
6. **Don't certify your own work.** Someone else verifies, or the label says nobody did.

## Read only what the task needs

| You are… | Read |
|---|---|
| Changing geometry, booleans or detail | `modeling.md` |
| Something resting on something, or z-fighting | `contact.md` |
| Building or changing a rig, or skinning | `rigging.md` |
| Changing motion, poses or an animated camera | `animation.md` |
| Lighting, materials, render settings, still cameras | `lighting.md` |
| Producing the delivered video, stills or print files | `delivery.md` |
| UVs, baking or texture maps | `baking.md` |
| Budgets or glTF export for a game | `game-assets.md` |
| Rigid-body or cloth simulation | `simulation.md` |
| Scattering or instancing with Geometry Nodes | `scatter.md` |
| Verifying someone else's work | `verifying.md`, then `trusting-checks.md` |
| Choosing or writing a check, or judging a render by eye | `checks.md`, then `trusting-checks.md` |
| A Blender error | `bpy-pitfalls.md`, at the matching section |
| A render failing on one machine only | `render-server.md` |
