---
name: claude-code-hooks
description: Implement Claude Code hooks for deterministic control over agent behavior. Use when creating custom hooks for notifications, auto-formatting, logging, feedback, permissions, or lifecycle events.
---

# Claude Code Hooks

Hooks are shell commands that execute at specific points in Claude Code's lifecycle, providing deterministic control over behavior.

## Hook Events

| Event | When it runs | Can block? |
|-------|--------------|------------|
| `PreToolUse` | Before tool execution | Yes |
| `PermissionRequest` | When permission dialog shown | Yes |
| `PostToolUse` | After tool completes | Feedback only |
| `UserPromptSubmit` | When user submits prompt | Yes |
| `Notification` | When notification sent | No |
| `Stop` | When agent finishes | Can continue |
| `SubagentStop` | When subagent finishes | Can continue |
| `PreCompact` | Before compact operation | No |
| `SessionStart` | Session starts/resumes | No |
| `SessionEnd` | Session ends | No |

## Configuration

Hooks are defined in settings files:
- `~/.claude/settings.json` - User settings (all projects)
- `.claude/settings.json` - Project settings
- `.claude/settings.local.json` - Local settings (not committed)

### Basic Structure

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",
        "hooks": [
          {
            "type": "command",
            "command": "your-command-here",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

**Matcher patterns:**
- Exact match: `Write`, `Bash`, `Read`
- Regex: `Edit|Write`, `Notebook.*`, `mcp__memory__.*`
- Match all: `*` or `""`

## Hook Input

Hooks receive JSON via stdin:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/directory",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": { "file_path": "/path/to/file", "content": "..." },
  "tool_use_id": "toolu_01ABC..."
}
```

## Hook Output

### Exit Codes
- **0**: Success (stdout shown in verbose mode)
- **2**: Blocking error (stderr fed back to Claude)
- **Other**: Non-blocking error (stderr shown in verbose mode)

### JSON Output (exit code 0)

```json
{
  "decision": "block",
  "reason": "Explanation for Claude",
  "continue": true,
  "stopReason": "Message when continue=false",
  "systemMessage": "Warning for user"
}
```

## Quick Examples

### Log Bash Commands

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "jq -r '.tool_input.command' >> ~/.claude/bash.log"
        }]
      }
    ]
  }
}
```

### Auto-Format on Save

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{
          "type": "command",
          "command": "jq -r '.tool_input.file_path' | xargs -I{} sh -c 'echo \"{}\" | grep -q \"\\.ts$\" && npx prettier --write \"{}\"'"
        }]
      }
    ]
  }
}
```

### Block Sensitive Files

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{
          "type": "command",
          "command": "jq -e '.tool_input.file_path | test(\"\\\\.env|secrets|credentials\")' > /dev/null && echo 'Cannot modify sensitive files' >&2 && exit 2 || exit 0"
        }]
      }
    ]
  }
}
```

## Environment Variables

- `CLAUDE_PROJECT_DIR` - Absolute path to project root
- `CLAUDE_PLUGIN_ROOT` - Plugin directory (for plugin hooks)
- `CLAUDE_ENV_FILE` - File to persist env vars (SessionStart only)
- `CLAUDE_CODE_REMOTE` - "true" if running in remote/web environment

## References

- **Decision Control**: See [references/decision-control.md](references/decision-control.md) for PreToolUse, PermissionRequest, Stop hook decisions
- **Event Details**: See [references/events.md](references/events.md) for complete input/output schemas per event
- **Examples**: See [references/examples.md](references/examples.md) for real-world hook implementations
