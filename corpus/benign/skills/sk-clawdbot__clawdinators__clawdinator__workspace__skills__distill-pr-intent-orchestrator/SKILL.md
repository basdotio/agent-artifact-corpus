---
name: distill-pr-intent-orchestrator
description: Run PR intent distillation across a PR set and persist outputs + sidecar metadata to /memory/pr-intent.
user-invocable: false
---

# Distill PR Intent — Orchestrator

## Goal

Run `distill-pr-intent` across a selected PR set, and persist:
- primary memo text (`.txt`)
- sidecar metadata (`.meta.json`)

All outputs go to shared memory on EFS, and are automatically published to the public S3 bucket by the host timer.

## Inputs

- repo: fixed `openclaw/openclaw`
- selection: one of:
  - `last N` (e.g. last 500)
  - `range <start..end>`
  - `since <YYYY-MM-DD>`
- skill_version: string (default `v1`)

## Output paths (persisted)

```
/memory/pr-intent/<skill_version>/openclaw-openclaw/<PR>.txt
/memory/pr-intent/<skill_version>/openclaw-openclaw/<PR>.meta.json
```

## Determinism rule

- NEVER put timing/telemetry/debug into the primary `.txt` memo.
- All telemetry goes into `.meta.json`.

## Workflow

1) Determine PR list.

Examples:

```sh
# last N merged PR numbers
gh pr list -R openclaw/openclaw --state merged --limit 200 --json number --jq '.[].number'

# range
seq <start> <end>
```

2) For each PR (sequential by default):
- Run `distill-pr-intent <PR>`.
- Write memo to `/memory/pr-intent/.../<PR>.txt`.
- Write metadata to `/memory/pr-intent/.../<PR>.meta.json`.

### Writing files (memory locking)

Use the locking helpers (required on EFS):

```sh
# memo
printf '%s\n' "$MEMO" | memory-write "/memory/pr-intent/<skill_version>/openclaw-openclaw/<PR>.txt"

# meta
printf '%s\n' "$META_JSON" | memory-write "/memory/pr-intent/<skill_version>/openclaw-openclaw/<PR>.meta.json"
```

### Suggested metadata schema

```json
{
  "pr": 17392,
  "repo": "openclaw/openclaw",
  "state": "merged",
  "skill_version": "v1",
  "generated_at": "2026-02-15T19:00:00Z",
  "patch_mode": "PATCH_OK",
  "patch_bytes": 12345,
  "model": "openai/gpt-5.2-codex",
  "error": null
}
```

## Failure handling

- On failure, still write `.meta.json` with `error` populated.
- Memo file optional; if written, keep it short and point at `.meta.json`.
