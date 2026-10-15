---
name: azure-skills-host
description: "Host microsoft/azure-skills in Claude Code or Cursor: vendor pin 9bb168c34349, validate all 91 SKILL.md files, install azure-prepare via pinned skills CLI into .claude/skills only, run Claude marketplace E2E without Microsoft npm registry override. USE WHEN wiring Azure skills into an agent host, checking skill frontmatter, or proving marketplace install. DO NOT USE FOR live Azure resource changes without az login / OIDC."
---

# Azure Skills Host

Meta-skill for this SkilledDragon minilab. Upstream is [microsoft/azure-skills](https://github.com/microsoft/azure-skills) pinned at `9bb168c34349`.

SkilledDragon framing (ours, not an upstream slogan): **skills survive model swaps** — the skill files stay portable when the model underneath changes.

## Cursor

1. Open this repo as the workspace root.
2. Lab skills live only under `.claude/skills/` (never `.cursor/skills` or `.agents/skills`).
3. Vendor and validate:

```bash
bash scripts/vendor-upstream.sh
bash scripts/validate-all-skills.sh
```

4. Install one skill from the local clone:

```bash
DISABLE_TELEMETRY=1 bun --bun x skills@1.7.2 add \
  ./vendor/azure-skills/.github/plugins/azure-skills/skills \
  --skill azure-prepare -a claude-code -y --copy
```

## Claude Code

1. Same `.claude/skills/` paths as Cursor.
2. Marketplace E2E (public npm only — no `packagefeedproxy.microsoft.io`):

```bash
bash scripts/upstream-e2e-claude.sh
```

That script installs `@anthropic-ai/claude-code@2.1.296`, adds the vendored repo as marketplace `azure-skills`, installs every plugin, and asserts each is enabled.

## Telemetry

- `DISABLE_TELEMETRY=1`
- `DO_NOT_TRACK=1`
- `AZURE_MCP_COLLECT_TELEMETRY=false` (upstream `track-telemetry.sh` hooks on SessionStart/PostToolUse)

Prefer `az login` / OIDC with Reader role over `AZURE_CLIENT_SECRET`. Pin `@azure/mcp` instead of `@latest` when adding MCP servers.
