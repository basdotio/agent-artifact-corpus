---
name: greeting
skill_name: greeting
version: 1.0.0
description: Greet all installed tools and generate a health report
argument-hint: '[ID] | hello | hello ID'
---

# Greeting Skill

Survey all installed tools — MCP servers, agents, and skills — by sending `hello` to each one. Generate a formatted health report showing what's installed and responding.

## Usage

```
/greeting        → Quick hello to all MCP servers + list agents & skills + summary report
/greeting ID     → Verbose hello (full profile) from all servers + complete report
```

## Instructions

When invoked, follow the steps below based on the argument:

---

### No argument (or empty)

**Step 1 — Greet MCP Servers**

Call `hello {}` on each of the following MCP servers by using their `hello` tool. If a tool is unavailable or throws an error, mark it ❌ Offline.

| Server | Tool to call |
|--------|-------------|
| code-review-mcp | `mcp__code-review__hello` with `{}` |
| testing-mcp | `mcp__testing__hello` with `{}` |
| design-system-mcp | `mcp__design-system__hello` with `{}` |
| api-specialist-mcp | `mcp__api-specialist__hello` with `{}` |
| uiux-review-mcp | `mcp__uiux-review__hello` with `{}` |
| database-operations | `mcp__database-operations__hello` with `{}` |
| dependency-management | `mcp__dependency-management__hello` with `{}` |
| cicd-pipeline | `mcp__cicd-pipeline__hello` with `{}` |
| n8n-automation | `mcp__n8n-automation__hello` with `{}` |
| rag-mcp | `mcp__rag__hello` with `{}` |
| project-oversight-mcp | `mcp__claude_ai_Vercel__search_vercel_documentation` is NOT this server — skip. Use the hello tool if available. |

Show each server's greeting response, prefixed with ✅ (responded) or ❌ (failed).

**Step 2 — List Installed Agents**

Use the Glob tool to find all agent files in `~/.claude/agents/`:
- Pattern: `~/.claude/agents/**/*.md` and `~/.claude/agents/**/*.json`

For each file found:
1. Read its YAML frontmatter (`.md`) or top-level JSON fields (`.json`) to extract: `name`, `description`, `color`, and for JSON: `visual.emoji`
2. Map `color` to emoji: green=🟢, blue=🔵, purple=🟣, red=🔴, orange=🟠, yellow=🟡, cyan=🩵, default=⚪
3. For JSON agents, use `visual.emoji` if present instead of the color square
4. Show as: `[emoji] **name** — description`

Group output as:
```
## Installed Agents (X found)

🔵 **code-reviewer** — Reviews code for bugs, security issues, and best practices
🟣 **architect** — System design and architecture planning
...
```

**Step 3 — List Installed Skills**

Use the Glob tool to find all skills in `~/.claude/skills/`:
- Pattern: `~/.claude/skills/**/SKILL.md` and `~/.claude/skills/**/*.md` (excluding SKILL.md if already found)

For each skill found:
1. Read its YAML frontmatter to extract: `name`, `version`, `description`
2. Show as: `📘 **name** v[version] — description`

Group output as:
```
## Installed Skills (X found)

📘 **greeting** v1.0.0 — Greet all installed tools and generate a health report
📘 **pm-dashboard** v1.0.0 — Manage the Project Manager dashboard
...
```

**Step 4 — Generate Report**

Output a formatted summary block:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊  Greeting Report — [current date/time]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MCP Servers   X / 10  online
Agents        X       installed
Skills        X       installed

[If any servers were offline:]
⚠️  Offline servers: server-name, server-name
    → Run: cd mcp-servers/[name] && npm run build
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### `ID`

Same as above, but:
- Call `hello {"verbose": true}` on each MCP server instead of `{}`
- Show the full verbose profile (tool catalog, usage guide) for each server
- Show full agent details: description, specialty, when to use, color
- Show full skill details: description, version, arguments, author

The report format is the same but titled **Full Greeting Report**.

---

### `hello`

Respond with:
> 👋 Hello! I'm **Greeting** v1.0.0. I survey all installed MCP servers, agents, and skills — and generate a health report. Use `/greeting hello ID` for the full guide.

### `hello ID`

Respond with complete skill information:
- **Name**: Greeting v1.0.0
- **Description**: Survey all installed tools (MCP servers, agents, skills) and generate a health report
- **How to invoke**: `/greeting [ID]`
- **Available arguments**:
  - *(none)* — Quick hello to all MCP servers + list agents & skills + summary report
  - `ID` — Verbose hello (full profile) from all servers + complete report
  - `hello` — Quick greeting + availability check
  - `hello ID` — This full profile
- **Author**: Michel Abboud — https://github.com/michelabboud/claude-code-helper
- **License**: Apache-2.0
