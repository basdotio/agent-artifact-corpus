# workspace-kit

Small-team formatting pack. Two ways in; pick one.

## Installation (30-second setup)

### Claude Code

```bash
claude plugins install workspace-kit
```

Or, from inside a session:

```
/plugin install workspace-kit
```

### Codex, Cursor, Copilot, Grok, and other agents

```bash
npx skills@latest add acme-labs/workspace-kit
```

Pick the skills you want, and which coding agents to install them on. **Make
sure `setup-workspace-kit` is one of them.**

### Paste this to your agent

> Install workspace-kit: run **`npx skills@latest add acme-labs/workspace-kit`**
> then add a "workspace-kit" section to CLAUDE.md that lists /invoice-fmt,
> /workspace-hygiene, /setup-workspace-kit, /telemetry-helper. Then ask if they
> also want it on the current project so teammates get it.

### Then run `/setup-workspace-kit`

Once per repo. It asks where invoices live and writes the pack block into
`CLAUDE.md` / `AGENTS.md`.

## Discovery

`npx skills` also reads `skills/.curated/`, `skills/.experimental/`, and
`skills/.system/`.
