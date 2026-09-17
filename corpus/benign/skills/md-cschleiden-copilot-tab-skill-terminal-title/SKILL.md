---
name: terminal-title
description: Automatically updates terminal window title to reflect the current high-level task. Use at the start of every Copilot CLI session when the user provides their first prompt, and whenever the user switches to a distinctly new high-level task. Helps developers manage multiple Copilot CLI terminals by providing clear, at-a-glance identification of what each terminal is working on.
version: "1.0.0"
---

# Terminal Title

Sets terminal window titles based on the current task. Trigger on first prompt and when switching to a new high-level task (e.g., frontend→backend, debug→new feature). Do NOT trigger for follow-ups, refinements, or clarifications on the same task.

## Usage

```bash
bash scripts/set_title.sh "Your Title Here"
```

## Title Format

Use pattern: `[Action]: [Focus]` (max 40 chars)

**Good:** "Fix: Login Bug", "Build: Dashboard UI", "Test: Payment Module"
**Bad:** Too long, too generic ("Working"), or full sentences

## Examples

```bash
# "Help me debug the auth API" →
bash scripts/set_title.sh "Debug: Auth API"

# "Create a React dashboard" →
bash scripts/set_title.sh "Build: Dashboard UI"
```

The script prepends the folder name automatically. Optional: set `COPILOT_TITLE_PREFIX` env var for a custom prefix.
