# Game assets: budgets and glTF export

For props and characters going to a game engine. Unwrapping, baking and texture maps (Non-Color, ORM packing, normal-map Y) are in `baking.md`; rigging and skinning in `rigging.md`. Exporter defaults were read from Blender 5.2.

## Rules

1. **Count the budget on the evaluated mesh:** `me = obj.evaluated_get(dg).to_mesh(); me.calc_loop_triangles(); len(me.loop_triangles)`. Count after modifiers, the same as the export.
2. **LODs aren't exported.** The glTF exporter has no `MSFT_lod` support. Godot can generate LODs on import. For other engines, ask whether LODs are wanted.
3. **Set every glTF export parameter you rely on** (`bpy.ops.export_scene.gltf`, 5.2 defaults):

   | Parameter | Default | Note |
   |---|---|---|
   | `export_format` | `'GLB'` | or `'GLTF_SEPARATE'` |
   | `export_yup` | True | glTF is Y-up |
   | `export_apply` | **False** | modifiers are dropped unless True (blocks shape keys) |
   | `export_skins`, `export_animations` | True | |
   | `export_animation_mode` | `'ACTIONS'` | also `'NLA_TRACKS'`, `'SCENE'` … |
   | `export_force_sampling` | True | keep it: docs warn that unsampled export can be wrong |
   | `export_influence_nb` | 4 | joints per vertex |
   | `export_def_bones` | False | True exports deform bones only |
   | `export_frame_range` | False | True limits to the playback range |
   | `export_anim_slide_to_zero` | False | docs: useful for loops |

4. **Loops:** the first and last poses must match. Check it on the re-imported action, not in the scene (unverified: no source found on seam frames).
5. **Verify the exported file by re-importing it** into an empty scene: triangle count against rule 1, bones, actions and their frame ranges, materials. Tested: an unapplied Subsurf exported with `export_apply=False` re-imported as 12 tris against 192 expected.
    - `import_scene.gltf` leaves the imported objects selected. Reselect before the next `use_selection=True` export, or you export the import.

## Skinned characters for games

- **Four influences per vertex** unless the engine is set up for more. Unity's default quality setting allows up to four; Godot imports up to eight. Limit and normalise in Blender, then re-check the count per vertex.
- Every deform bone needs a non-empty vertex group, and extreme poses get checked (`rigging.md`, rule 2).
- **Godot retargeting** maps bones to `SkeletonProfileHumanoid` by common English bone names. Unity's humanoid rules weren't sourced.

## Red flags

| Thought | Reality |
|---|---|
| "The Subsurf is on, so the export is smooth" | `export_apply` defaults to False. Re-import and count. |
| "The textures are in the material, so they export" | Bake and pack them, then check the re-imported materials (`baking.md`). |
