# Animation, poses and shots

For motion, pose solving, grips, cameras and shot continuity. Rig construction is in `rigging.md`; lighting, render settings and still cameras are in `lighting.md`. Read the always-rules in `SKILL.md` first.

**Which parts apply:** every animated shot: rules 1, 8, 10, 11 and 13. Heavy objects (doors, lids, landings): 7. Very large or very small subjects: 3. Strikes and swings: 5. Anything that rests or is planted: 14. Characters and multi-joint rigs: add 2, 3, 4, 6, 9, 15 and 16. Rule 3's numbers are for walkers and giants; derive yours from the subject's size.

## Rules

1. **Sweep the whole animation for clashes** with the project's shared clash library, not the rest pose or 30 samples. Then weight each hit by what the shot camera sees, in pixels. A clash the camera can't see is lower priority; one it can see is a defect whatever its depth.
2. **Put the clearance term inside pose solvers,** calling the same clash library. In the source production, a held gun ended up 0.41 m inside the chest because the aim solve only asked for barrel direction and grip position, with no clearance term.
3. **Scale is physics. Derive motion limits from the subject's size and mass.** Time scales roughly with √(size): motion that is right for a 1 m object reads as a toy on a 20 m one, and as sluggish on a 5 cm one.
   - **Acceleration ceiling:** set one for the root or main body. Worked example, not a limit: a building-sized walker had to stay at or below about 1 g; at 10.9 g it read as a springy toy.
   - **Tempo:** for walkers, match the Froude number (v²/gL) of a real walker with that leg length. Worked example: an 18.7 m walker needed 39–63 frames per step where 26 had been planned, and 26 read as a 4–5 m machine.
   - **Settling:** recovery time grows with size too. The big walker needed 30+ frames with no rebound between repeated actions.
   - **Dynamics (multi-joint rigs):** where available, use an inverse-dynamics replay (for example MuJoCo) as a checker for torque and balance, not as a motion driver.
4. **Fix readability with the camera, not exaggerated motion.** A low, wide, close camera made a giant machine loom. A bigger crouch made it read as a springy toy at 10.9 g.
5. **Turn the motion brief into numbers on every change.** For a strike or swing, for example:
   - **Wind-up:** the top of the wind-up is the furthest-back point, and the tip rises steadily with no dips.
   - **Lead:** the torso leads the arm, and each joint peaks a couple of frames after its parent.
   - **Strike:** the tip-speed peak comes late in the strike.
   - **Follow-through:** it carries past vertical, then settles.
   - **Test every quantity that can pump.** Check tip height and speed, not only the swing angle, which may happen to be monotonic.
6. **(Characters) Check grips per finger.** Distance is not contact: a hand 0.4 cm from a grip can still be flat and open. Measure against the real grip mesh, not a proxy cylinder. Evaluate finger segments after drivers, since one `grip` scalar can pass while a segment breaks a coupled limit.
7. **Make weight readable through timing, impact and settle, not amplitude.** For a heavy object (door, lid, machine, character landing):
   - **Ease:** a slow start, and a long ease into a soft stop, or an accelerating approach into a hard stop.
   - **Impact:** peak speed in the last frames before contact, then a stop within one or two frames.
   - **Settle:** a small rebound (a degree or two, a few mm) that decays monotonically with no second bounce.
   - **Secondary motion:** whatever it's attached to reacts slightly and later, for example a car body rocking a few mm away from a closing door.
   - **Measure it:** generate keys from a documented function, or check the evaluated curve per frame for speed, the stop, the rebound size and the settle time.
   - **Don't trust defaults:** auto-clamped Bezier interpolation gives mushy motion.
8. **Set up a shot camera if there isn't one.** Choose the lens and height for readability (low and close for heavy or large subjects). Check with `world_to_camera_view` that the moving parts stay inside the frame with a margin at their extremes. Every rule that says "from the shot camera" means this camera.
9. **Check feasibility before polish.** If no in-limits pose meets all the constraints, prove it with a sweep (several solver set-ups and about 12 start poses each), say what design change would work, and stop. A two-handed aim pose and a weapon stow were both physically impossible, and that cost hours of fix rounds.
10. **Every change names its neighbours,** such as joint limits, line of fire, other shots, exposure and visible props, and reports what got worse.
11. **Hidden is not fixed.** Hiding a defect off-camera or behind a cut breaks when the shots are retimed. An arm whip was "off-camera by design" until a recut showed it.
12. **Check set dressing against every shot camera, on every frame.** Floating light stands showed up across three separate frame ranges of the final render.
13. **Label every still with the build it came from.** Stills from an older build don't count, and nothing counts as final until one integrated re-render of the frozen build has passed.
14. **Measure contact as well as clearance, for everything that rests:** planted feet, braced parts, props set down, settled debris.
    - **Sliding:** horizontal drift during contact frames: the share of contact frames that slide, and the slide distance.
    - **Penetration and floating:** the signed gap to the support on every contact frame. Report the share of frames past your tolerance (1 cm on the source production's giant; millimetres for a prop) and the worst depth. `contact.md` has a recipe for one resting object, and `simulation.md` covers settled debris.
    - A lowest-vertex check is not this.
15. **After retargeting or re-timing, re-solve the contacts.** Copying joint angles between rigs with different proportions moves the feet and hands. Re-solve planted contacts with IK, then re-run the sliding, penetration, joint-limit and clash checks.
16. **Rig changes go through `rigging.md`:** IK set-up, drivers, sockets, actuators and the rig contract.

## Red flags

| Thought | Reality |
|---|---|
| "Sampling ~30 frames is enough for clashes" | A detail layer showed 0 clashes at rest and 41 when swept. Sweep, then go dense around hits. |
| "The close-up at frame 260 looks good" | One frame, one angle. The defect was on every frame of the 58-frame shot. |
| "The card's numbers all pass" | A slash passed every number and still read as "a swipe". It took four more rounds. Look. |
| "Swing angle has 0 reversals, so the wind-up is clean" | The tip height still pumped. Test every quantity. |
| "Just bump the motion so it reads" | A 1.2 m crouch hit 10.9 g and read as a springy toy. Move the camera. |
| "The feet (or the props) are on the ground at the lowest vertex" | Measure sliding during contact frames and the signed gap, per foot or per object. |
| "One more solver run will find a pose" | Four set-ups × 12 starts all failed. That's a design problem; stop and say so. |
