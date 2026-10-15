# Verifying someone else's Blender work

For the independent reviewer. **REQUIRED:** also read `trusting-checks.md`; your controls come from there.

## The verifier's stance

- **Someone other than the builder verifies**: a separate agent, or at least a separate pass with fresh code. Builders' self-reported numbers were often wrong. Claimed drops of 0.30/0.43/0.49 m measured 0.298/0.224/0.242, and "7 clashes" became 41.
- **Write your own measurement code.**
  - Don't read the builder's reasoning, logs or check script before producing your own evidence. Read their script afterwards to explain any disagreement.
  - "Your own code" means your own driver: you choose the parts, the frame range, the sampling step and the controls.
  - You still call the project's shared metric library for the definition, and you prove that metric with the controls in `trusting-checks.md`.
  - Re-computing the builder's metric on the same data shows where their number came from.
- **A claimed check that doesn't exist at its stated path is not evidence.** Record it as a finding.
- **Measure BEFORE first, with your own tool,** and state the before number in the verdict. One flagged frame turned out to be 0.41 m inside on every frame of the shot.
- **Build fresh from the scripts** into your own path, with the environment toggles written down. Record the md5 of the sources at start and end, and of the `.blend` you actually measured. A source md5 that changes mid-build means a concurrent edit, and the result is void.
- **Measure the neighbours too.** Check every fix against the requirements next to it: joint limits, line of fire, crushed blacks, other shots. Report what got worse. One aim fix put every joint on its stops; one exposure fix hid the scale props.
- **Look as well as measure.** Render full-size frames from the shot camera and Read them. If the numbers pass but it visibly reads wrong, the verdict is FAIL; say what you saw. If it looks fine but a number fails, it is also FAIL.

## Getting a "before"

To get the before state, build the pre-fix sources into your own path. Use git if the project has it. If not, use the change's backup files, or the last verified `.blend` whose md5 is recorded in its verdict.

If no pre-fix artefact exists, say so. The verdict is then capped at a conditional result, because without a before number you can't answer "does reverting the fix make the check fail?".

## When time is short

Work in this order, and cut from the bottom up:

1. Pin the artefact (md5s) and start the fresh build in the background. Write the driver while it runs.
2. Run the controls: planted defect, near-miss pair, and the revert or before state.
3. Do a full sweep of the claimed range at every frame, raw and with exceptions.
4. Measure the neighbours.
5. Render and look.
6. Do sampled sweeps outside the claimed range, extents and camera weighting.

Everything you cut goes under "Not verified". A verdict with no controls is UNMEASURED, not PASS.

For static objects, geometry checks need one frame, not a sweep. Turntable frames are for the look. A turntable rotating the camera or the object rigidly can't change contact or separation.

## The verdict

```
VERDICT: PASS | FAIL | UNMEASURED | UNADJUDICATED
Artefact: <blend path> md5 <...>; sources md5 start=<...> end=<...>; env <toggles>
Before → after: <metric> <before> → <after> (limit <x>), worst at <frame/part>
Coverage: <n parts>, <n pairs>, frames <a–b every k>, <n samples>
Controls: planted <defect> read <value> (expected <value>); near-miss <pass/fail as expected>
Neighbours: <each must-still-hold requirement and its number>; got worse: <list or none>
Looked at: <frames/cameras rendered and read>; what I saw
Not verified: <what was skipped, sampled, or static-only>
Check: <committed path to the script, rerunnable>
```

Say what was measured, what was only looked at, and what was only read. "Sampled every 5th frame" and "static-only" are open gaps, not coverage.

### Short form, for Quick jobs and small fixes

For a fix of a line or two, such as a placement nudge or one material value, on a Quick job (`SKILL.md`):

```
VERDICT: PASS | FAIL | UNMEASURED — builder-checked, not independently verified (if so)
Claim → measured: <claim> → <metric before → after, tolerance>, control <planted value read back>
Neighbour: <the one thing the fix could have broken, and its number>
Looked at: <frame/camera>; Not verified: <list>
```

The controls still apply (tests 1 and 4 in `trusting-checks.md`). A number with no planted-defect read-back is UNMEASURED. On a Quick review, md5 pins and a fresh build are needed only if the sources could change while you measure; say which you did.

**Commit your check** where the project map says per-change checks live (see `trusting-checks.md`).
