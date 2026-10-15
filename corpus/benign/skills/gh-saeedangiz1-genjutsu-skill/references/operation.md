# Execution and recovery

Run `python "<skill-root>/scripts/runtime.py" COMMAND ...`; the dispatcher uses the bundled runtime directory and interpreter. Inspect command help rather than inventing flags. Paths with spaces must be individual quoted arguments, never interpolated shell commands.

## Local preflight

`preflight SOURCE --mode depth --reference IDENTITY` checks local media and identity-reference compatibility. The preparation path also checks needed runtime/worker prerequisites before hosted calls. Missing audio, empty/undecodable video, clips longer than 30 seconds or unsupported audio remux must stop before processing. Preserve user media; any deliberate conversion needs its own source copy and explicit timing/audio policy.

## Preparation

`prepare SOURCE --mode depth --subject "person" --provider replicate` creates a local job and prints its 32-character ID. Other modes: `face_mesh`, `depth_mesh`. Other upstream depth providers: `replicate-chenxwh`, `huggingface`; consult their saved integration docs before changing defaults. A local GPU is not required for the hosted default.

A job contains the untouched source `upload.mp4`, normalized `original.mp4`, local manifests, separated/working audio, `seedance-input.mp4`, review record and provider journals. Depth also contains `depth.mp4`, raw mask PNGs and `mask.mp4`. Mesh contains `face-landmarks.json` and mode metadata. The working normalization is 24 fps and at most 960 pixels on its longest dimension; this is not the final output resolution.

`status JOB` reports current review/submission metadata. Review `seedance-input.mp4` completely, then `review JOB --approve --fingerprint CURRENT_HASH --note "Evidence of complete input review"`. Rejection omits `--approve`. Supply truthful evidence; a synthetically created hash does not establish visual review.

`repair-rgb JOB` segments source RGB detail and composites the original depth through the new masks. Combined mode reapplies mesh. Fast mode has no SAM mask to repair. Repairs invalidate prior review. Do not use repeated billed repairs without scope for them.

## Draft submission and collection

Save the exact creative prompt to a UTF-8 text file. `submit JOB --prompt-file PROMPT --reference REFERENCE` submits and collects the authorized draft. Optional `--second-reference IMAGE` maps an additional subject; its prompt mapping must match the actual source. Local reference validation rejects undecodable/unsupported files before hosting/submission. A primary identity video selects Omni; a primary image selects Edit. Omni uses supported whole-second durations: paired preflight and submission reject timing that cannot preserve the full source soundtrack, before hosting/queueing. A compatible small shortfall may use the documented final-frame hold; no audio is trimmed or stretched.

Input review covers exact prepared video and audio. Never rebuild `seedance-input.mp4` between approval and submission. The runtime rechecks identity/review before its billed POST. Accepted identical submissions return the saved ID; changed inputs/prompt/reference require a new deliberate job.

`resume JOB` collects the saved draft; `resume JOB --hd` collects accepted HD. A provider timeout is not permission to requeue. `hd JOB` submits a separately authorized completion of the accepted draft, refreshes the configured callback and preserves draft outputs. `resume-preparation JOB` resumes journaled preparation stages after an interruption without starting a new local job; unknown/in-flight billed intents require reconciliation first. Read its help for modes.

## Ambiguous billed requests

Provider journals are written before a billed POST and after receiving its ID. A process failure after dispatch but before ID persistence cannot be made exactly-once by local files alone when the provider lacks an idempotency lookup. Such an intent stays blocked; inspect its saved timestamp/input and reconcile with the provider dashboard/API. Never delete the intent to force an automatic retry. If reconciliation cannot find the result, report the issue and obtain a deliberate next action.

Stage/job advisory locks stop simultaneous preparation, submission or collection. A busy lock means another operator/process owns that operation. Let it complete or explicitly investigate; do not kill unrelated processes or start another collector. Accepted provider IDs and result status remain persisted for collection.

Do not move a source job between machines or change its runtime mode while preparation is active. Keep `.env`, run folders, journals, generated previews and signed media URLs outside public Git history.

## Final export

The returned video loses generated audio; `finish_preview` copies the complete original compressed source-audio packets. It refuses material duration mismatch rather than trimming/looping/stretching the soundtrack. A small supported rounding gap may use a documented final-frame hold, recorded in `duration-adjustment.json`.

Draft export is `runs/JOB/final-preview.mp4`; HD is `runs/JOB/hd/final-preview.mp4`. Show actual metadata and a playable result, inspect full audiovisual output and copy the accepted file to the user's destination. Do not deliver private journals as public artifacts.
