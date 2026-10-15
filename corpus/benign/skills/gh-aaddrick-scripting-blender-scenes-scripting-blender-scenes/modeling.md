# Changing geometry

For modelling, shape, booleans, hollowing, detail layers and spec changes. Read the always-rules in `SKILL.md` first.

**Which parts apply:** a small addition (a handle, a prop, a placement fix): rules 1, 2, 15 and 18, plus 5–7 if you cut or bevel. A part whose shape is the brief: add 3, 4, 8, 9, 13 and 17. Doors and hatches: add 11. Mirrored assemblies: add 10 and 12. Detail on an animated model: add 14 and 16.

## Rules

1. **Find the existing code before writing new code.** Look in the project map for generators, guards and checks. Most requests are a parameter or spec change to an existing generator, not a new modeller.
2. **Take the before numbers first.** Before any change, build and record extents, shape-gate scores and stills. "Looks like a box" may be a flat crown radius or flat shading, not a wrong generator.
3. **Turn style words into a technique and a number.**
   - Name the method, for example a quad cage on true arcs with creases, Solidify, then an applied Subsurf.
   - Prove it on **one test piece**, scored against the reference form.
   - Only then roll it out. **When shape is the brief** (a styled body, "rounded", "cast") on Standard or Production jobs, gate every part with a shape gate: silhouette overlap (IoU) with a reference form in three views, plus the share of area in flat faces. Its self-test must FAIL a chamfered box. A handle, a bracket or a crate needs a look from the shot camera, not a gate.
   - In the source production, "rounded" came back as boxes 3–4 times before this rule.
4. **After any boolean, cut or spec change, compare every part's extents against the last good build.**
   - Check bbox per axis, volume and vertex count, and fail on a loss beyond your tolerance on any axis (the source production used 10%).
   - "Manifold" and L/R mirror checks both missed 46 parts that a hollowing cut had collapsed symmetrically: a 5.1 m shell became 1.65 m.
   - To find the cause, build a control with the suspect step turned off.
5. **Gate every boolean, and pick its solver by whether the mesh is manifold.**
   - **Gate:** before cutting, assert both operands are manifold: every edge has exactly 2 faces, and `bm.calc_volume() > 0` (a negative volume means inverted normals).
   - **Solver:** if both are manifold, use the Manifold solver (4.5+). Otherwise use Exact, adding Hole Tolerant only after Exact fails. Manifold returns nothing useful on non-manifold input, which is why the gate comes first.
   - **Cage or boolean?** If the opening is in a shell your own generator builds, leave the faces out of the cage and add a rim. Use a boolean only to cut into geometry you don't generate, through a guarded cut function that applies the extent check.
   - **If a boolean returns an empty or wrong mesh,** check in this order:
     1. Run the operand gate: non-manifold edges, inverted volume, unapplied scale.
     2. Look for near-coincident shells fused by a 1e-5 m weld into edges with 3–4 faces. Nudge them ~0.5 mm apart (`bpy-pitfalls.md`, Geometry).
     3. Try Exact, and add Hole Tolerant only if Exact fails.
     4. Compare the result's extents against the last good build. A closed result can still be badly wrong.
   - **Scale:** apply scale and rotation before any boolean, bevel or inset, and assert `obj.scale == (1,1,1)`. These operations act on the untransformed geometry.
6. **Clean up in a fixed order, and fail on silent repairs.** Merge by distance → dissolve degenerate → recalculate normals → `mesh.validate(verbose=True)`. A `True` return means Blender repaired something, so fail the build and find out what.
7. **Hard-surface shading:**
   - Bevel with Limit Method = Angle (about 30°), not by selection.
   - Pair Bevel's face strength (Affected or New) with a Weighted Normal modifier (Face Area mode). Don't also turn on Harden Normals.
   - Keep Smooth by Angle as a live modifier. Applying it writes sharp edges into the mesh that later bevels and booleans will act on.
   - Sources disagree on where Smooth by Angle and Subsurf go in the stack, so prove the order on a test piece.
8. **Score spatial relations as numbers and iterate on the scores.** Write "sits on", "is centred over" and "clears by 0.15 m" as 0–1 constraint functions, and loop on the unmet ones. In SceneCraft, dropping these scores took its constraint score from 88.9 to 3.2.
9. **Keep the previous best as a candidate.** An iteration replaces the last good build only if it scores better on the gate. Make small parameter changes most of the time; a structural rewrite alone causes large, disruptive edits.
10. **Check left and right explicitly.** Pair every `.L` part with its `.R`, compare mirrored bbox and volume, and assert each part's parent bone is on the same side as its name and its geometry. Mirroring was the most common modelling bug.
11. **Openings expose what's behind them.** A door, hatch or cut-away shows the inside of the body when open. Look from the shot camera at the open state. Add a jamb, an inner panel and a minimal interior where the camera can see in, and make sure moving panels are closed volumes with thickness.
12. **Mirroring inverts normals.** A negative-scale or bmesh mirror flips face winding. Recalculate normals afterwards, and assert `bm.calc_volume() > 0` on both sides.
13. **Check feasibility before polish.** If the constraints can't all hold, prove it with a sweep and stop for a design call. Don't grind fix rounds.
14. **On Production jobs, or when moving parts pass through the detail, put additive detail behind a default-OFF toggle.** On a Quick or Standard job with nothing moving past it, add the detail directly and run the contact and clash checks.
    - "Byte-identical" means the toggle-off build hashes the same as a build of the same sources without the layer.
    - Base-geometry changes are not additive and get no toggle; they go through rules 3–12.
    - The layer counts as done only when it is ON in the render. It goes ON only after a full-animation clash sweep against everything that moves past it: hands, held props, swinging limbs. Until then it is parked and reported as parked.
15. **Things meant to rest on something get a contact check, and coplanar faces get removed.** Measure the signed gap to the support and the centre of mass over the contact patch. Find faces sharing a plane between parts (z-fighting). Both recipes are in `contact.md`. A "moved it 2 mm" or "dropped it 4 cm" fix is checked where it ended up: no new gap, no penetration, no remaining shared plane.
16. **Place things with the cameras and the motion paths in mind.** Placing first and then hiding or blocklisting the clashes is the antipattern. One detail layer kept a growing blocklist; light stands were hidden one by one as they showed up in shots.
17. **Get reference images before judging style,** and never judge era or finish on flat grey blockouts. In the source production, six design rounds were rejected until the client's references arrived.
18. **Hygiene.**
    - Use git, not piles of backup files.
    - Write to a temp file and swap it in atomically.
    - Record source md5s at the start and end of a build; a change mid-build voids it.
    - Never edit a shared library live while others build from it.
    - Fail loudly on missing spec keys; no silent fallbacks.
    - Sort before iterating, and seed every random generator from the build context.

## Red flags

| Thought | Reality |
|---|---|
| "I'll write a new modeller for this part" | A generator probably exists. Find out why its output reads wrong first. |
| "It's manifold, so the boolean worked" | One cut returned a closed 0.08 m plate where the housing should be 0.71 m. Compare extents. |
| "I'll estimate curvature myself" | Use a shape gate against a reference form, and prove the technique on one test piece first. |
| "The greebles avoid a keep-out box on the chest" | Hands swing through the chest. One greeble went 0.30 m into a palm. |
| "Moved the shade 2 mm, so the z-fighting is gone" | Re-run the coplanar and contact checks. The move can leave a shared plane elsewhere, or open a gap. |
| "Mirror the left one and we're done" | `.R` parts kept `.L` normals, and `.R` parts were parented to `.L` bones. Check both sides. |
| "One more parameter tweak will get it" | If two rounds missed, change the method, not the numbers. |
