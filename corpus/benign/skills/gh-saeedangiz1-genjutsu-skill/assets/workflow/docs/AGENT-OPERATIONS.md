# Agent operations

Use the skill [SKILL.md](../../../SKILL.md) and [operation guide](../../../references/operation.md) as the operational contract. Work independently through authorized processing and retrieval. A model must actually inspect the full video before claiming visual approval; metadata checks are not a substitute. If video review is unavailable, request user review through the UI.

## Commands

```bash
.venv/bin/python workflow.py prepare /path/to/source.mp4 --subject person
.venv/bin/python workflow.py status LOCAL_JOB_ID
.venv/bin/python workflow.py repair-rgb LOCAL_JOB_ID
.venv/bin/python workflow.py review LOCAL_JOB_ID --approve --fingerprint CURRENT_HASH --note "Who reviewed, whole-clip findings, repairs"
.venv/bin/python workflow.py submit LOCAL_JOB_ID --prompt-file prompt.txt --reference /path/to/reference.png
.venv/bin/python workflow.py resume LOCAL_JOB_ID
.venv/bin/python workflow.py hd LOCAL_JOB_ID
.venv/bin/python workflow.py resume LOCAL_JOB_ID --hd
```

Omit `--approve` on the review command to record rejection. `repair-rgb` incurs a new SAM inference: use within the user's authorized repair scope; it explicitly clears approval. Add `--second-reference` for a second image. The server and CLI must not collect/submit the same job concurrently.

## Prompt review

State the real number of subjects, exact identity mapping and reference tokens for the selected mode. Keep appearance references separate from motion/audio. Replace the whole subject in every frame, including hair and clothing outside an imperfect depth silhouette; require matching short hair if the identity has short hair. Keep camera, crop, scene, lighting and timing. Include the verified source dialogue verbatim when known, with exact timing; do not invent a transcript. Use only prepared input's embedded audio for lip synchronization. Preserve source soundtrack in the final mux regardless of generated audio.

Show the creative prompt before submission. The adapter appends audio/reference instructions saved in `seedance-request.json`; inspect these as well. Prior explicit submission approval remains valid. A new paid creative variation should use a new prepared job rather than overwriting an existing request ID. HD requires explicit approval.

## Review and recovery

Play Mask and Prepared input end-to-end, across cuts and occlusions. Check complete subject coverage, no holes in clothes/arms, hair/hands/feet, chair/background exclusion, border fragments and frame-to-frame stability. Review again after any repair. Never auto-approve solely because inference succeeded.

Replicate prediction responses are saved as `audio-prediction.json`, `sam-raw-request.json`, and depth request metadata. On interruption inspect their IDs/status URLs; retrieve completed output before deciding whether to retry. Preparation does not automatically resume every interrupted stage. Seedance response IDs are persisted; startup and `resume` collect them without a new paid queue call.

If queue POST times out before a response ID is saved, check the provider dashboard. Stop automatic retries on this ambiguous outcome. Poll timeouts do not mean a job failed. Report provider failures with the local job/request ID, never credentials. Keep the server running until preview is saved. When completed, show `/runs/LOCAL_JOB_ID/final-preview.mp4` (or `hd/final-preview.mp4`).
