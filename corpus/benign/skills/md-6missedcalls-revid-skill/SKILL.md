---
name: revid
description: Revid API V2 execution and automation skill with token-safe reference loading. Use when Codex needs to call revid.ai endpoints from Bash/curl, use the bundled API references quickly, or build/update scripts for render/status/export/publish/media/consistent-character workflows while keeping context under a defined token budget.
---

# revid-skill

Use a single prebuilt Revid API markdown reference and run Revid API flows quickly.

## Workflow

1. Read [references/revid-api-reference.md](references/revid-api-reference.md) for endpoint behavior and request schemas.
2. For API execution, use `scripts/revid_api.sh` instead of hand-writing one-off curl calls whenever possible.

## Commands

```bash
# Call endpoints with wrapper
REVID_API_KEY=... bash scripts/revid_api.sh projects 10
REVID_API_KEY=... bash scripts/revid_api.sh status <pid>
REVID_API_KEY=... bash scripts/revid_api.sh render payloads/render.json
```

## Guardrails

- Prefer endpoint-specific commands in `scripts/revid_api.sh` before custom curl.
- Do not duplicate detailed endpoint schemas in `SKILL.md`; keep them in `references/`.
