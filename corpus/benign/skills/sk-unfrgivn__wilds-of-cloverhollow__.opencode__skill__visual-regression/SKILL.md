---
name: visual-regression
description: "Review Cloverhollow rendered Scenario Runner captures against intentional visual baselines. Use for pixel-art, UI, camera, scene, or art regression work."
compatibility: Scenario Runner, ImageMagick comparison helpers, image reader/vision
---

# Visual regression

Run the repository's existing `./tools/ci/run-scenario-rendered.sh <scenario_id>`
and inspect the capture directory, `trace.json`, and `run.log` before comparing
images. A passing shell exit is not enough: require `passed: true`, no errors or
noop events, expected capture labels, and visual inspection of PNGs.

Use canonical baselines under `baselines/visual/<id>`. Promotion requires an
explicit reviewed command after native image inspection:
`<scenario> <capture_dir> --reviewed`. Missing or extra captures, dimension
mismatches, and pixel diffs fail closed. Baseline updates are intentional review
decisions, never an automatic repair.
Do not approve an image because it was quantized or because a diff script
swallowed an error. Fail closed for missing artifacts, missing baselines, or
unreadable captures. Never use OS-level window control.

Exact dialogue/UI claims require native attachment inspection, trace/diff review,
and OCR corroboration. Use `tools/agents/review-capture.ts` with the current
`opencode2 models` catalog, check its transcription against the PNG, and fail
closed on model unavailability. Do not trust prior approvals, generic model
approval, or the disabled built-in vision helper.
