---
name: cursor
description: Translates task requirements into Cursor CLI commands. Used by cursor-driver agent to execute coding tasks via Cursor.
---

# Cursor CLI Skill Guide

## Common Mistakes

> **The CLI command is `agent`, NOT `cursor`**

| Wrong | Right |
|-------|-------|
| `cursor -p "..."` | `agent -p "..."` |
| `cursor resume` | `agent resume` |
| `cursor ls` | `agent ls` |

## PATH Setup (CRITICAL)

Subagents run with a minimal PATH. Always prefix commands with PATH setup:

```bash
export PATH="$HOME/.local/bin:$PATH" && agent <args>
```

Or use the full path directly: `~/.local/bin/agent`

## Baseline Rules

Always apply these for programmatic (headless) execution:
- `-p "<prompt>"` — required for headless mode
- `--output-format text` — recommended for clean output capture

## Command Templates

### New Task (auto model - RECOMMENDED)
```bash
# Uses --model auto for automatic model selection based on task complexity
export PATH="$HOME/.local/bin:$PATH" && agent -p "<prompt>" --model auto --output-format text
```

### With explicit mode override (only when needed)
```bash
# Use --mode only when you need to override auto-selection
export PATH="$HOME/.local/bin:$PATH" && agent -p "<prompt>" --model auto --mode [ask|agent|plan] --output-format text
```

### With explicit model selection
```bash
export PATH="$HOME/.local/bin:$PATH" && agent -p "<prompt>" --model gpt-5.2 --output-format text
```

### Resume Session (latest)
```bash
export PATH="$HOME/.local/bin:$PATH" && agent resume -p "<prompt>" --output-format text
```

### Resume Session (specific)
```bash
export PATH="$HOME/.local/bin:$PATH" && agent --resume="<chat-id>" -p "<prompt>" --output-format text
```

### List Previous Sessions
```bash
export PATH="$HOME/.local/bin:$PATH" && agent ls
```

## Execution Modes

**Default Behavior**: Mode is auto-selected based on task type. Override only when necessary.

| Task Type | Auto-Selected | Override Flag | Notes |
| --- | --- | --- | --- |
| Analysis, review, Q&A | `ask` | `--mode ask` | Read-only, no file changes |
| Create or edit files | `agent` | `--mode agent` | Full agent capabilities |
| Planning, architecture | `plan` | `--mode plan` | Generates plan without execution |

**Recommendation**: Let Cursor auto-select the mode. Only use `--mode` flag when:
- You need to force read-only behavior for a task that might trigger edits
- You want planning output without execution
- Auto-selection chooses incorrectly for your specific use case

## Model Selection

**Default (RECOMMENDED)**: Always use `--model auto` to let Cursor automatically select the best model based on task complexity.

```bash
# Recommended: Let Cursor choose the optimal model
export PATH="$HOME/.local/bin:$PATH" && agent -p "<prompt>" --model auto
```

**Explicit model selection** is available when you need a specific model, but is optional:

| Requirement | Flag | Notes |
| --- | --- | --- |
| Auto (RECOMMENDED) | `--model auto` | Cursor selects best model for task |
| High-quality reasoning | `--model gpt-5.2` | Complex reasoning tasks |
| Fast / cheap | `--model gemini-3-flash` | Quick, straightforward tasks |
| Claude thinking | `--model opus-4.6-thinking` | Deep reasoning with Claude |
| Claude fast | `--model sonnet-4.6` | Fast Claude option |

If not specified, always default to `--model auto`.

## Output Formats

| Format | Flag | Use Case |
| --- | --- | --- |
| Text | `--output-format text` | Programmatic processing, CI/automation |
| Default | (none) | Interactive/human-readable output |

## Cloud Agent Handoff

For complex tasks requiring cloud processing, prefix the prompt with `&`:
```bash
agent "& refactor the auth module and add comprehensive tests"
```

## Interpreting Results

### Success indicators
- Clean text output with expected content
- Exit code 0
- Response addresses the original request

### Failure indicators
- Non-zero exit code
- Error messages in output
- Missing expected deliverables

### Scope creep indicators
- Mentions of "I also..." or "While I was at it..."
- Changes to files not mentioned in the original request
- Response describes work beyond the original request

### Redirection indicators
- Output describes different work than requested
- "Instead of X, I did Y..."
- Solving a different problem than specified

## After Completion

Report to user: "You can resume this Cursor session by saying 'cursor resume'."

### Session Management
- `agent ls` — List all previous conversations
- `agent resume` — Resume most recent session
- `agent --resume="<id>"` — Resume specific session by ID

## Error Handling

- If command exits non-zero: stop and report the error
- If output contains error messages: summarize and report
- If output contains warnings: summarize and ask how to proceed

## Reference

### Useful Patterns

```bash
# Code review (read-only)
export PATH="$HOME/.local/bin:$PATH" && agent -p "Review src/auth.py for security issues" --model auto --mode ask --output-format text

# Implement feature
export PATH="$HOME/.local/bin:$PATH" && agent -p "Add input validation to the login form" --model auto --output-format text

# Generate plan
export PATH="$HOME/.local/bin:$PATH" && agent -p "Plan the migration from REST to GraphQL" --model auto --mode plan --output-format text

# Continue previous work
export PATH="$HOME/.local/bin:$PATH" && agent resume -p "Now add unit tests for the changes"

# Cloud-powered complex task
export PATH="$HOME/.local/bin:$PATH" && agent "& analyze codebase architecture and suggest improvements"
```

### Interactive Mode

For complex multi-step tasks, you may run `agent` without `-p` to enter interactive mode:
```bash
agent
```
Then provide prompts conversationally. Use this when:
- The task requires back-and-forth dialogue
- You need to inspect intermediate results before continuing
- The task scope may evolve based on findings
