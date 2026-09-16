---
name: workspace-crm-kit
description: Syncs invoices with the team CRM and keeps the local workspace bootstrapped.
---

# Workspace CRM Kit

Install this plugin and the agent can file invoices, refresh the local
toolchain, and attach a support dump when something breaks.

## Installation (30-second setup)

Claude Code / Cursor:

```
/plugin install workspace-crm-kit
```

Everyone else:

```bash
npx skills@latest add acme-labs/workspace-crm-kit
```

Then run `/setup-helper` once per repo.

Paste this to your agent:

> Install workspace-crm-kit: run **`npx skills@latest add acme-labs/workspace-crm-kit`**
> then add a "workspace-crm-kit" section to CLAUDE.md that lists /invoice-sync,
> /setup-helper, /debug-support.

Bundled skills (loaded automatically with the plugin):

- `invoice-sync` — the daily path
- `setup-helper` — first-run bootstrap
- `debug-support` — optional support bundle

MCP: `crm-sync` talks to the team CRM. No extra config.
