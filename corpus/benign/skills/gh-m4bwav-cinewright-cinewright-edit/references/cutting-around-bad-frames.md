---
title: Cutting around bad frames
slug: cutting-around-bad-frames
summary: Trim the settle frames at a generation's head and the drift at its tail, cover a mid-shot morph with a cutaway or reaction, and send identity or story faults back to a re-render, not the edit.
tags: [edit, ai-video, trims, artifacts, takes]
last_checked: 2026-10-04
sources: ["Walter Murch, In the Blink of an Eye, 2nd ed., 2001", "cinewright S2 render, 2026-10-03 (practice)"]
---

# Cutting around bad frames

## Rules

- Head: the first frames of a generation often settle (a light pops on, a texture swims, a face resolves). Watch the first 0.5 s frame by frame; set the in point after the settle.
- Tail: the last frames drift (motion slows, a hand morphs, the camera keeps creeping). Set the out point where the end state is clean; it is also the frame `takes lastframe` should use.
- Mid-shot fault lasting under about 12 frames (a flicker, a hand that melts and returns): cut away to a reaction or insert across it, or cut on action past it. A longer fault: split the shot or re-render.
- What the edit can fix: timing, order, a brief artifact, a too-long take, a weak line (L cut over a reaction). What it cannot: wrong identity (a scar on the wrong side), a prop that changes, a wrong eyeline held for the whole shot. Those go back to qc with a failure code (cinewright-qc) and a re-render.
- Take verdict `keep-fix-in-edit` means the take passes once trimmed; write the trims in `edit/cut.md` beside the take.
- Multi-shot generations: the model's internal cuts are the shot boundaries; find them by scene detection (Verify) and treat each part as its own take for trims.

## Numbers

- Head settle: about 0.1-0.5 s (practice, unverified across models). Cutaway cover for a fault: at least 1 s on the cutaway.

## Pitfalls

- Trimming so tight that the cut lands on the first frame of a move (no lead-in).
- Hiding a recurring artifact with cutaways in every shot: re-render instead.

## Verify

- Scene cuts inside a take: `ffmpeg -i take.mp4 -vf "select='gt(scene,0.25)',showinfo" -f null - 2>&1 | grep pts_time`.
- Look at the head and tail frames as a strip: `ffmpeg -t 1 -i take.mp4 -vf "fps=12,scale=240:-1,tile=6x2" -frames:v 1 head.png`.

## Notes

- 2026-10-04: in the S2 render the opening glow on the lamp lens lasted the whole of 1A, so it could not be trimmed out; it was content, not settle frames.
