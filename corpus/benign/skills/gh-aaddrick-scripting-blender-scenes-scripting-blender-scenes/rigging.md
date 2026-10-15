# Rigging

For armatures, bones, constraints, IK, drivers, sockets, actuators and the rig contract. Read the always-rules in `SKILL.md` first. Posing and motion are in `animation.md`.

**Which parts apply:**
- **Simple hinged or sliding mechanisms** (doors, lids, hatches, drawers, turrets): read the next section, then rules 2, 3, 5, 11 and 12 from the Rules section below it. Instead of a contract file (rule 1), write one convention line in the project note: units, each hinge's axis, and which sign means open.
- **Characters and multi-joint rigs:** all the rules.
- **Skinned characters:** rules 1–4, 6, 8, 12 and 13, and the skinning notes in rule 2. For one character on a Standard job, rule 1's contract can be the bone list and conventions in the project note, checked by a script. For a game character, also read `game-assets.md` (Skinned characters for games, and the export round trip).

## Simple hinged mechanisms

1. **Derive the hinge axis from the mesh,** not from an assumed vertical: fit a line through the hinge-edge vertices. A raked pillar gives a tilted axis.
2. **One bone per moving part, on the axis.** Put the bone's head and tail on the hinge line, so the swing is one local rotation. Lock the other axes and add a Limit Rotation for the real range (a door's check strap stops it at the limit, so no overshoot past it).
3. **Watch the bone-parent offset.** An object parented with `parent_type='BONE'` is placed relative to the bone's **tail**, not its head. Set `matrix_parent_inverse` deliberately, then assert every vertex's world position is unchanged by parenting (to about 1e-6).
4. **Find the opening direction by measurement.** Pose +5° and check the free edge moves away from the body on both sides. Make positive mean "open" on both sides in the rig (for example by flipping the mirrored bone's head and tail), rather than negating angles in the animation.
5. **Sweep the full range against the neighbours.** Check door against fender, pillar, mirror, wheel and ground at small steps. If no hinge position clears, report a design problem; don't hide the clash.
6. **Check the hinge stays put.** Hinge-edge vertices should stay within a tolerance of the axis at every angle. If they drift, the axis or the parenting is wrong.

## Rules

1. **Make a rig contract the interface.**
   - A contract file names every bone, control, custom prop and socket, and fixes the conventions: units, up axis, forward axis, which side is `.L`, and each hinge's axis and positive direction.
   - Animation code reads only the contract.
   - Check the built rig against it with a contract checker covering bones, limits, controls, IK targets, drivers and props.
   - A reader must fail loudly if the contract is missing. In the source production, the animation build quietly fell back to an interim contract and clamped joints it shouldn't have.
2. **Prefer rigid parts on bones over skinning for hard-surface machines.** One part per bone, bone-parented, with no weights, makes every pose measurable with plain transforms; an inverse-dynamics replay matched Blender to 0.0 m.

   **If you must skin** (organic characters, cloth-like parts):
   - Apply transforms on mesh and armature first, merge by distance, and recalculate normals.
   - Assert every deform bone has a non-empty vertex group, because automatic weights can fail partially without raising. If bone-heat fails outright, scaling both up ~10×, parenting, and scaling back is a known workaround.
   - Normalise weights and cap influences per vertex: four for most game engines (`game-assets.md`, Skinned characters for games). Re-check the count after limiting.
   - Measure deformation at extreme poses: volume loss at elbows and knees, and self-intersection via the clash sweep. Look at the extreme poses, not only the rest pose.
3. **Set bone roll deliberately.** Give every edit bone an explicit roll reference (`align_roll`, or a z-reference vector when creating it), with one bend axis down each chain. IK pole angles, rotation limits and every driver sign depend on it. Cross-check the axis and sign convention against the spec by posing each DOF both ways (local Euler and quaternion about the spec's world axis) and comparing the orientations.
4. **Solve IK set-up numerically, don't guess it.**
   - **Pole angle:** sweep it until the IK reproduces the rest pose, and report the residual:
     ```python
     def knee_err():
         bpy.context.view_layer.update()
         return (pb_shin.head - arm.data.bones["shin.L"].head_local).length
     def err_at(deg):
         ik.pole_angle = math.radians(deg)
         return knee_err()
     best = min(range(-180, 180), key=err_at)                              # 1° sweep
     best = min((best + i * 0.05 for i in range(-20, 21)), key=err_at)     # 0.05° refine
     ik.pole_angle = math.radians(best)                                    # report knee_err() too
     ```
   - **Chain length:** set `chain_count` explicitly; 0 means "up to the root".
   - **Hinges:** lock the off-axes (`lock_ik_y`, `lock_ik_z`) and limit the hinge axis. Work out the bend sign from the geometry ("does +5° shorten hip-to-ankle?"), not from a convention you assume.
   - **Stretch:** keep it off unless designed. It also needs `ik_stretch > 0` on the bone.
5. **Keep constraint and driver chains one-way.** Driver variables count as dependencies even when unused. For mutual aim, such as a hydraulic ram's barrel and rod tracking each other, give each end an **unconstrained** anchor bone on the other side to aim at. Fail the build on "Dependency cycle detected".
6. **Drive everything from a few named props, with simple expressions.**
   - Examples: fingers from one `grip` prop, a trigger from a `trigger` prop, toes from foot props.
   - Use arithmetic, `min` and `max` only, and assert `is_simple_expression`.
   - Dump all drivers (expression and variables, sorted) to JSON to review or diff them.
   - One scalar driving many bones needs its coupled limits checked per bone after evaluation (see `animation.md`).
7. **Switch sockets by stepped influence, never by blending.** Give the held object one Child Of per socket, with an identity inverse and exactly one at influence 1. Key influence with CONSTANT interpolation. A partial influence (0.5) leaves the object floating between two hands.
8. **Know what's IK and what's FK before adding either.** Find out which chains are IK, which are FK, and whether the contract declares controls the rig never built. Poses can also be solved offline (numpy, with the clearance term) and baked as FK rotations. If so, a new IK chain must agree with those baked poses where they overlap.
9. **To switch a hand (or any IK goal) between targets, move the target, not the chain.** This pattern is extrapolated from socket switching; prove it on your rig.
   - Give the IK target bone one Child Of per goal, each with an identity inverse, and step the influences as in rule 7.
   - Switch on a frame where both goals coincide, or hide the switch in the motion.
   - Switch IK and FK through an influence prop with CONSTANT keys. Blend only over frames where the IK and FK poses agree, checked numerically.
   - At every switch frame, check for joint flips and pops.
10. **Don't compensate for a wrong socket with a flag; fix the socket.** A hand socket was rolled 180°. A "flip" flag worked around it, then flipped the held object a second time once the socket was fixed, putting a finger 57 cm off its target.
11. **Check mechanisms against their physical limits, over the full range.**
    - **Actuators:** pin-to-pin length within the stroke at every pose, enough engagement at full extension, and the rod fitting at full retraction.
    - **Clearance:** sweep every DOF alone and the multi-DOF corners. Ranges set by estimate failed at four joints (ankle, hip roll, lumbar, wrist).
    - **Change the mechanism when it can't clear.** Linear rams went to rotary drives after three rounds of clipping.
12. **Check sides on the built rig, not by name.** Compare each part's bone side, name side and geometric side (the sign of X). Right-hand rams ended up on `.L` bones because suffix parsing missed dotted and unsided names. Use `.L`/`.R` only, and watch for `.001` duplicates, which break name flipping.
13. **Run rig integrity checks over the animation, and make them prove themselves.**
    - The checks: joints stay on their side and never hyperextend, planted feet drift less than your tolerance (1 cm on the source production's giant), no parts detach or pop, and socket influences are 0 or 1.
    - A self-test plants one defect of each kind your checks cover into a copy (all five on Production rigs), and every one must be caught: a 3 cm foot slide, a swapped pole (knee flip), a straightened leg, a part offset 0.3 m from its bone, and a socket at 0.5.
    - Read `trusting-checks.md` before writing any new rig check.

## Red flags

| Thought | Reality |
|---|---|
| "I'll blend IK to FK over 10 frames" | Only where the two poses agree, checked numerically. Otherwise use a stepped switch. |
| "Pole angle −90° usually works" | Solve it against the rest pose and report the residual. |
| "Automatic weights ran without an error" | It can fail on some bones silently. Check every deform bone's group, or use rigid parts. |
| "Add a flip flag so it points the right way" | The flag outlived the bug and flipped it twice. Fix the socket's roll. |
| "Blend the Child Of influences for a smooth hand-off" | At 0.5 the object floats between hands. Step it, and hide the switch in the motion. |
| "The `.R` parts are named right, so they're on the right bones" | Check the bone, name and geometric side together. |
| "The joint range is from the spec, so it's reachable" | Estimated ranges failed sweeps at four joints. Sweep it. |
