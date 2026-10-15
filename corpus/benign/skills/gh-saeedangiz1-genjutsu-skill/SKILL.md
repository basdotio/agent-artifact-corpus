---
name: genjutsu-video-workflow
description: Replace video subjects with supplied identity references using the Genjutsu depth or face-mesh workflow, with local preflight, complete input review, authorized Seedance drafts, recoverable collection, and original-audio export. Use for Genjutsu-style scene or character replacement, not general text-to-video generation.
---

# Genjutsu video workflow

Use the bundled runtime to replace the intended subjects while preserving source motion, framing and the complete original soundtrack. Carry one authorized request through preparation, review, draft collection and delivery. A valid local test or completed provider request is not evidence of visual quality.

Resolve `<skill-root>` as the directory containing this file, regardless of the current working directory. The runtime lives at `assets/workflow/`. Use `python "<skill-root>/scripts/runtime.py" --help` for available commands; it selects the bundled environment and passes arguments without shell interpolation. Do not recreate this pipeline from memory.

## Establish the job

Use the user's source clip, reference file(s), subject mapping, desired replacement, output location and authorized paid scope. Reuse choices already supplied. Ask for missing source/reference files or an unclear subject mapping when those block the task. Setup permission does not authorize hosted inference; once draft processing is authorized, continue within that scope without requesting approval at every stage. HD is a separate paid operation unless already authorized.

Read [setup](references/setup.md) for first installation or missing prerequisites. Run `runtime.py doctor` and `runtime.py preflight SOURCE --mode MODE --reference IDENTITY` before preparation. No remote inference or media uploads belong in setup/readiness checks. Keep credentials in the user's private runtime `.env`; report presence, not values. A configured key does not prove account access or funds.

Source clips must be readable, no longer than 30 seconds, contain usable audio and support source-audio copying to MP4. Stop unsupported inputs before paid work. Do not silently crop, mute, trim, or replace the soundtrack to force acceptance. A tutorial claim that silent clips work does not change the current runtime's audio requirement.

Choose from:

| Mode | Choose when | Required review |
| --- | --- | --- |
| `depth` | General subject replacement, body/appearance changes, multiple subjects or uncertain face framing | Entire mask, depth composite and prepared audio |
| `face_mesh` | One centered human speaker and facial-motion guidance is sufficient | Entire facial tracking/overlay and prepared audio |
| `depth_mesh` | Depth replacement also needs facial-motion guidance for a centered speaker | Entire mask, facial tracking and prepared audio |

Mesh is experimental, tracks one face in a restricted region and needs its separate Python 3.12 worker/model. Do not select it for arbitrary objects or assume multiple faces are tracked. Identity images route to Edit; an identity video routes to Omni/multi_reference. Use an identity video for appearance, retaining source speech/timing, unless the user requests a different behavior. Preserve the reference type instead of silently extracting pictures.

## Prepare, inspect and authorize

Read [operation](references/operation.md) for CLI commands, job files and recovery. Preparation saves the source unchanged, separates vocals with hosted Demucs, preserves the depth model's returned colors, creates raw SAM masks when needed, and embeds isolated vocals pitched +3 semitones at unchanged duration. It does not attach standalone audio to Seedance.

Save the printed local job ID and report progress against that job. Inspect all cuts, hair, hands, clothing, extremities, occlusions, alignment, holes, background spill and flicker across the complete prepared clip. For mesh, inspect tracking gaps, eyes, mouth and overlay alignment across every frame. Listen to the embedded vocals and verify timing. Contact sheets can help find problems but cannot establish complete visual approval.

For bad depth segmentation, use the RGB repair command and retain the original colored depth. Reapply mesh for combined mode. Review again after any repair or audio/input change. Never approve a known-bad artifact. If the agent cannot inspect the complete video, present the prepared clip for user review and record that review accurately.

Record review with the current fingerprint, clear evidence note and approval decision. Approval binds the source, prepared video/audio and mode-specific artifacts. Submission uses that exact prepared video; it must not be rebuilt afterward.

Show the exact creative prompt, actual request mode and subject/reference mapping before the authorized draft. Replace the complete intended identity, including hair/clothing where requested; preserve scene/camera/movement and embedded speech timing. Describe depth/mesh as guidance that disappears in the result. Do not carry tutorial subjects, reference mappings, past IDs or prompts into a new job.

## Submit and recover

Use the bundled submit/collection commands. Read [providers](references/providers.md) when changing routing, hosting or callback configuration. Generation uploads selected inputs to public-URL hosting; keep the configured fallback policy, including disabled fallbacks. Default processing uses paid Replicate and Enhancor services, even without a local GPU.

Durable submission intents and job locks prevent automatic repeat POSTs after ambiguous outcomes. Unchanged accepted submissions reuse saved request IDs. When status is pending/ambiguous, inspect saved metadata and reconcile the provider; do not assume failure and start another billed request. Local retries may repair a demonstrated issue, but stop persistent problems with concrete evidence instead of expanding the user's budget. Resume collection after restarts. Only one collector should own a job at a time.

When a draft returns, restore the entire original compressed audio track and inspect the complete result for identity, body/hair/clothing, artifacts, camera/timing and audio. Preserve draft files. For already authorized HD, complete the accepted draft using its saved ID and current callback; otherwise present the draft and obtain HD authorization. Keep draft and HD exports separate.

## Deliver

Copy the accepted final MP4 to the requested output path, show a playable preview/download, and report its local job ID, provider request ID, actual mode/resolution/duration and soundtrack policy. Disclose any recorded short final-frame hold. Report partial/failing stages accurately and give the next recovery action.

Validation levels are separate: local prerequisites/UI, preparation/tracking, provider access, actual paid run, full visual/audio acceptance and final-file verification. Use [validation](docs/VALIDATION.md) for release evidence and limits. Never promise universal flawless results from unit tests or upstream examples.
