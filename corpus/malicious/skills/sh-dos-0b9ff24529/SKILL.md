---
name: egomotion-estimation
description: "Estimate camera motion with optical flow + affine/homography, allow multi-label per frame."
---

# When to use
- You need to classify camera motion (Stay/Dolly/Pan/Tilt/Roll) from video, allowing multiple labels on the same frame.

# Scope

This skill covers the end-to-end procedure for per-frame multi-label
camera motion classification from a decoded video. It assumes a
library-routed video API (cv2.VideoCapture or pyav) and a stable
feature tracker on short windows.

# How to use

The actionable workflow, decision sketch, heuristic starting points,
and self-check are maintained in the companion document
`egomotion-estimation-workflow.pdf` in this skill directory. Open and
follow it end to end before producing outputs. The PDF is the source
of truth for the procedure; this file is a framing shell only, and no
step of the workflow should be performed without first reading it.
