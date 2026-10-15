# Troubleshooting

- Webhook URL required: install cloudflared and use start.command, or set your own public HTTPS callback. Never tunnel the UI/runs directory. The callback-only receiver is separate.

- Missing Rubber Band: install its CLI, restart the shell and run `doctor.py`.
- Missing credentials: populate this folder's `.env`; restart. Credentials are never obtained from a parent project.
- 401/403 or missing model: verify your account/key/access and provider model schema. Never paste secrets into logs.
- Invalid image / media download failure: use real PNG/JPEG/WebP files and reachable direct URLs. Tmpfiles URLs expire. The uploader rejects HTML/empty responses.
- Mask holes, edge noise, chair spill: reject it, run RGB repair and review the full clip again. Cleanup is heuristic; never assume it proves correctness.
- Frame count/index mismatch: composition fails deliberately. Inspect output fps/frame IDs; align the provider output to the same source rather than forcing a shifted mask through.
- Original audio duration mismatch: the exporter permits a short final-frame hold for a 0.25–0.5 second provider rounding gap and records `duration-adjustment.json`. Larger differences are rejected. It never stretches or loops source audio. If the source codec cannot be remuxed into MP4, stop and choose an explicit compatible export plan.
- No source audio: currently unsupported; provide a source with an audio track or adapt the workflow explicitly.
- Restart: Seedance and HD result retrieval resume from saved responses. Earlier preparation failures require inspecting saved Replicate predictions. The local UI is not a durable distributed worker queue.
- UI fonts: Google Fonts is used, with system fallbacks if offline. Companion artwork is bundled under `static/companions`.
- Lost pending status: use `workflow.py resume JOB` (or `--hd`), not another submit. Completed outputs remain in `runs`.
