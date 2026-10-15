# Field: 3D modeling · Blender · CAD-to-mesh

If research already answered an item, don't ask it — note "confirmed by research" in the summary.
[Recommended defaults] are the first-option candidates.

- **Source of truth**: drawings (plan / elevation / section), photos, or an existing model — and which wins when they disagree
- **Research first**: look up the real object and how it is usually represented in models at this scale before blocking out shapes [Recommended: research before modeling]
- **Units and scale**: model at real size and scale later? [Recommended: real units] Origin and forward axis
- **Detail level**: silhouette only / main members / bolts and welds; polygon budget or purpose (render, print, game, drawing)
- **Structure**: one connected shell / separate parts / split only where the units really differ [Recommended: one connected shell]
- **Topology rules**: segments on round parts, triangles allowed, booleans allowed, modifiers applied or kept
- **Hands off**: existing objects, materials, textures, collections, viewport and scene settings
- **Measure on what**: the evaluated mesh (with modifiers) or the base mesh; measure along the part's own axis, not world axes
- **Showing progress**: live viewport screenshots / problem faces highlighted / a translucent target surface
- **Saving**: new file or overwrite, compression, naming; undo checkpoint after each scripted change
- [Don't candidates] overwriting original materials, hiding or joining things on my own, changing viewport settings, working headless and only reporting numbers, boolean-merging parts, stacking overlapping copies, judging from a zoomed-out thumbnail
