---
name: cc-projects-improve
description: Cross-project Claude Code usage analysis
disable-model-invocation: false
allowed-tools: Bash(rake *), Read, Glob
---

# Cross-Project Claude Code Usage Analysis

Analyze Claude Code session logs from projects registered in `projects.yaml` and propose improvements.

## Configuration Files

- `projects.yaml` - Define projects to analyze (in this skill directory)
- `projects.example.yaml` - Configuration example

## Execution

```bash
cd ~/.claude/skills/cc-projects-improve && rake analyze
# Or specify days
cd ~/.claude/skills/cc-projects-improve && rake import[14] && rake sessions
```

### Rake Tasks

| Task | Description |
|------|-------------|
| `rake analyze` | Full analysis (default) |
| `rake import[days]` | Import session logs to SQLite |
| `rake sessions` | Show session statistics |
| `rake bash_commands` | Analyze bash commands |
| `rake settings` | Check project settings |
| `rake clean` | Delete database |

## Analysis Perspectives

Based on script results, analyze and propose improvements for:

- **Bash commands**: Should frequently used commands be pre-allowed in settings.local.json?
- **MCP tools**: If there are underutilized MCP servers, document usage in CLAUDE.md
- **Task (subagent)**: Can it be used for complex investigations?
- **Custom commands**: Can frequent tasks be made into commands?
