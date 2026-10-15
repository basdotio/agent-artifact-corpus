# Prompting the shot fix

Starting picks: `wan_2_7_videoedit` and `runway_aleph_2` (edit the clip), `nano_banana_pro` (fix a still), `seedance_2_0` (animate the fixed still). Option names, reference slots and limits come from `describe_model`.

## Route A: edit the clip

The clip already carries framing, motion and timing. Name only the change.

```
Video 1 is the source shot. Change only [the one thing]. Keep the framing, camera move, people, motion and timing the same.
```

- Short beats long. A long edit prompt causes changes you did not ask for.
- One change per pass. Two changes: run two passes, the second on the first's output.
- Quote any text that must appear: `Change the sign to read "OPEN LATE". Keep everything else the same.`
- Removing something: say what fills the space ("remove the mug; the bare wooden table continues").
- With an image reference: give it one job ("image 1 is the product; match its label and color exactly; the rest comes from video 1").

Examples:
- `Make the box in her hands matte blue. Keep everything else the same.`
- `Remove the second person on the left; the kitchen wall continues behind. Keep everything else the same.`

## Route B, step 1: fix the frame

Edit first.png. Say what stays, then the one change.

```
Image 1 is a frame from a video ad. Keep the framing, camera angle, light, people and background identical.
Only [the change].
```

- Use "change" or "replace", not "transform". "Transform" invites a full redraw.
- Match the size to the ad with the model's aspect option.

## Route B, step 2: animate it

The fixed frame is the `first_frame`. Prompt only what the frame cannot show.

```
Image 1 is the first frame; keep [product / face / scene] exactly. [One action with an endpoint, timed to the shot].
Camera: [the same move as the original shot]. Single continuous shot, no cuts. No on-screen text.
```

- Copy the original shot's camera move and speed so the seams hold.
- One action. End it on a settled frame so the cut at E is clean.
- Product warps: add "static product identity, no shape change" and cut extra description.
- Audio: turn it off. The ad keeps its own soundtrack.

## If a take fails

- Too much changed: shorter prompt, stronger keep line.
- Change not visible: make it more specific (color name, object, position in frame).
- Seam jumps: name the light and grade of the neighbouring shots in the prompt.
