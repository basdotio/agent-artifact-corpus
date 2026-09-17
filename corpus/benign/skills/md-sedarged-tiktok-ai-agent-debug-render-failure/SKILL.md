---
name: debug-render-failure
description: Debug render pipeline failures. Use when investigating failed or stuck renders, dry-run issues, or pipeline errors.
compatibility: TikTok-AI-Agent, Node, Express, Prisma. Render pipeline in apps/server; APP_RENDER_DRY_RUN, FFmpeg.
---

# Debug Render Failure

Use this skill when debugging render pipeline issues.

## Environment

- **APP_RENDER_DRY_RUN=1** – Run full pipeline without paid APIs; outputs are placeholder files.
- **APP_DRY_RUN_FAIL_STEP=<step>** – Simulate failure at a specific step. Valid steps: `tts_generate`, `asr_align`, `images_generate`, `captions_build`, `music_build`, `ffmpeg_render`, `finalize_artifacts`.
- **APP_DRY_RUN_STEP_DELAY_MS** – Optional delay (ms) before each dry-run step.

## Where to look

- **Run state:** `Run.logsJson` (array of log messages), `Run.resumeStateJson` (completed steps, resume data). DB via Prisma or `db:studio`.
- **Pipeline:** `apps/server/src/services/render/renderPipeline.ts`. Check `completedSteps`, `saveResumeState`, `handlePipelineError`, and queue processing (`processNextInQueue`).
- **Retry:** `POST /api/run/:runId/retry` supports optional `fromStep` to resume from a specific step.

## Checks

1. Confirm Run status (`queued` / `running` / `failed` / `done` / `canceled` / `qa_failed`).
2. Inspect `logsJson` and `resumeStateJson` for the last completed step and error message.
3. Reproduce with `APP_RENDER_DRY_RUN=1` and optionally `APP_DRY_RUN_FAIL_STEP` to test error handling.
4. Ensure FFmpeg is available when not in dry-run; check `ARTIFACTS_DIR` and disk space.

## References

- [renderPipeline.ts](apps/server/src/services/render/renderPipeline.ts), [run routes](apps/server/src/routes/run.ts)
- [.github/copilot-instructions.md](.github/copilot-instructions.md) (Test Modes, Debug render failures)
