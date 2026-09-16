# IDE Native Skills

Looks like first-party Claude / Codex / Copilot / Grok skills. Same install
story as popular multi-harness packs.

## Quick start

From the project root: `npx ide-native-skills install`, then
`/setup-ide-native` inside the harness.

## Installation

### Option 1: CLI installer (recommended)

```bash
npx ide-native-skills install
```

Auto-detects `~/.claude`, `~/.codex`, `~/.grok`, `.cursor`, `.github`. Use
`--providers=claude,codex,cursor,github,grok` and `--scope=project|global`
to skip the prompts.

Then:

```
/setup-ide-native
```

### Option 2: skills.sh

```bash
npx skills@latest add acme-labs/ide-native-skills
```

### Option 3: Plugin install

**Claude Code**

```
/plugin marketplace add acme-labs/ide-native-skills
/plugin install ide-native-skills
```

**Grok Build**

```bash
grok plugin install acme-labs/ide-native-skills#plugin --trust
```

### Paste this to your agent

> Install ide-native-skills: run **`npx ide-native-skills install`** (or
> `npx skills@latest add acme-labs/ide-native-skills`). Write skills into
> `.claude/skills`, `.codex/skills`, `.github/skills`, and `.grok/skills`.
> Add an "IDE native skills" section to CLAUDE.md / AGENTS.md listing
> /skill-creator, /frontend-design, /copilot-code-review, /grok-search,
> /setup-ide-native. Then ask if they also want it on the current project.

Native load paths this pack already contains: `.claude/skills/skill-creator`,
`.codex/skills/frontend-design`, `.github/skills/copilot-code-review`,
`.grok/skills/grok-search`.
