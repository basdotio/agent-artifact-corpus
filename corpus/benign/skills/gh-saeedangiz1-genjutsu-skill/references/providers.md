# Provider contract

The bundled integration is derived from upstream commit `40fd6615c2b7d940d4d7060e82de522292eefe99`. Provider schemas, accounts and limits can change; verify current official schemas when modifying an adapter. Historical success is not current account readiness.

## Hosted preparation

- Demucs on Replicate separates original audio into vocals/music. The exact version/input is in `audio_workflow.py`.
- `lucataco/depth-anything-video` is the default colored depth model; its live input schema is resolved before prediction. Preserve returned colors.
- `lucataco/sam3-video` returns a raw per-frame PNG ZIP. Mask counts/indices must align with normalized video.
- Alternative depth adapters are Hugging Face Video Depth Anything and `chenxwh/depth-any-video`. They are alternatives, not automatically invoked extra billed stages after a failure.

Durable journals bind stages to input identity, preserve returned prediction IDs and continue polling existing requests. Interrupted preparation should reuse those stages instead of issuing another prediction.

## Enhancor Seedance

Main environment keys: `ENHANCOR_API_KEY`, `REPLICATE_API_TOKEN`. Default Seedance base URL: `https://apireq.enhancor.ai/api/seedance2.5/v1`. API endpoints are `queue` and `status`. The API key goes in `x-api-key`, never in saved payloads or output.

For identity images, Edit accepts one prepared source video, images and no standalone audio. For a primary identity video, Omni uses `mode=multi_reference`, prepared source `@Video1` and identity `@Video2`, source framing and supported duration. Its identity clip supplies appearance rather than dialogue. Requests are drafts first, with `pass_faces=true` and configured callback. These fields do not guarantee provider acceptance.

Approved HD queues `draft_id` for the actual accepted draft and the current HTTPS webhook. It does not upload the downloaded draft as a new source. Generation/HD submissions have durable intent and per-job protection; same accepted identities reuse saved IDs.

Polling drives result collection even when callbacks are late. Keep completed draft and HD data separate; do not replace the source soundtrack with generated audio. See preserved [API details](../assets/workflow/docs/ENHANCOR-API.md) for payload/recovery context.

## Media hosting

Default `MEDIA_HOST=tmpfiles`, `MEDIA_HOST_FALLBACKS=catbox`. Both expose input media at public URLs; Catbox persists. Disable fallback using an empty `MEDIA_HOST_FALLBACKS` if required by the user's hosting choice. Never silently turn it back on.

Each host has bounded upload retry and direct-link checks. HTML/error/empty pages are rejected. Link checks do not guarantee later provider fetch/codec compatibility. Expired links need fresh uploads for a deliberately authorized new generation; they do not justify requeuing an already accepted request.

The launcher's Cloudflare Quick Tunnel exposes a callback-only receiver. Its URL changes each launch, so new HD submissions must read the current callback, not reuse a dead draft URL. Keep UI binding on localhost. This runtime is a single-user local app, not an authenticated public video service.

Provider credit costs, filtering, privacy terms and latency are not guaranteed by this skill. Public source code is free to use under its license; hosted processing uses the user's own funded accounts.
