---
name: orchestrator
description: Use this skill when you need to orchestrate specialized Claude agents in separate sessions. Perfect for long-running tasks, specialized agents with MCP tools, and resumable workflows.
---

# Orchestrator Skill

## What & When

**What**: Commands for managing specialized Claude AI agent sessions with optional agent blueprints and MCP server integration.

**When to use**:
- Delegate tasks to specialized sessions with different MCP configurations
- Run long-running operations that can be resumed later
- Use agent blueprints for specialized behavior (research, testing, etc.)
- Manage multiple concurrent agent conversations
- Work with persistent sessions using simple names (no session ID management)

**Key Benefits**:
- Session names instead of session IDs (simpler tracking)
- Automatic session management via backend APIs
- Built-in result extraction (no manual JSON parsing)
- Optional agent blueprints for specialized capabilities
- Sessions can be resumed (even after finished)

**Prerequisites**:
- Backend services must be running (Agent Coordinator and Agent Registry)

---

## Quick Reference

### `ao-start` - Start new session
```bash
uv run --script commands/ao-start <session-name>
```
**Use when**: Starting a new Claude agent session. Reads prompt from stdin or `-p` flag.

### `ao-resume` - Continue existing session
```bash
uv run --script commands/ao-resume <session-name>
```
**Use when**: Adding messages to an existing session. Reads prompt from stdin or `-p` flag.

### `ao-status` - Check session state
```bash
uv run --script commands/ao-status <session-name>
```
**Use when**: Need to know if session is `running`, `finished`, or `not_existent`.

### `ao-get-result` - Extract result from finished session
```bash
uv run --script commands/ao-get-result <session-name>
```
**Use when**: Session is finished and you need the final result text.

### `ao-list-sessions` - List all sessions
```bash
uv run --script commands/ao-list-sessions
```
**Use when**: Need to see available sessions with their IDs and project directories.

### `ao-list-blueprints` - List available agent blueprints
```bash
uv run --script commands/ao-list-blueprints
```
**Use when**: Need to see what specialized agent blueprints are available.

### `ao-show-config` - Display session configuration
```bash
uv run --script commands/ao-show-config <session-name>
```
**Use when**: Need to see session metadata (project dir, agent used, timestamps, etc.).

### `ao-delete-all` - Delete all sessions
```bash
uv run --script commands/ao-delete-all
```
**Use when**: Need to delete all session data. **Use with caution.**

---

## Command Location

**IMPORTANT**: All commands are located in the `commands/` subdirectory of this skill folder. Don't use `cd` to change directories instead run them with their full path.

Before using commands for the first time:
1. Locate this skill's root folder (same directory as this SKILL.md)
2. Commands are in: `<skill-root>/commands/ao-*`
3. Execute using: `uv run --script <skill-root>/commands/ao-<command> <args>`

**Example**:
```bash
# If skill is at /path/to/skills/orchestrator
uv run --script /path/to/skills/orchestrator/commands/ao-start my-session -p "Research topic X"
```

---

## Parameters Reference

### Required
- `<session-name>` - Alphanumeric + dash/underscore, max 60 chars (e.g., `research-task`, `code_review_123`)

### Common Options
- `-p "prompt"` or `--prompt "prompt"` - Provide prompt via CLI instead of stdin
- `--agent <agent-name>` - Use specialized agent blueprint (only for `ao-start`)
- `--project-dir <path>` - Override project directory (only for `ao-start`, default: current directory)

---

## Typical Workflows

### Basic Session Workflow
```bash
# Start new session
echo "Analyze this codebase structure" | uv run --script commands/ao-start analysis

# Check status
uv run --script commands/ao-status analysis  # Output: finished

# Get result
uv run --script commands/ao-get-result analysis

# Resume with follow-up
echo "Now focus on security patterns" | uv run --script commands/ao-resume analysis
```

### Using Specialized Agents
```bash
# List available blueprints
uv run --script commands/ao-list-blueprints

# Start session with specific agent blueprint
uv run --script commands/ao-start research-task --agent web-researcher -p "Research Claude AI capabilities"

# View agent configuration
uv run --script commands/ao-show-config research-task
```

### Managing Sessions
```bash
# List all active sessions
uv run --script commands/ao-list-sessions

# Check specific session
uv run --script commands/ao-status my-session

# Delete all sessions
uv run --script commands/ao-delete-all
```

---

## Key Concepts

### Session States
- **`not_existent`** - Session doesn't exist
- **`running`** - Session active, ready to resume
- **`finished`** - Session complete, result available

### Working Directory
- Sessions operate in the project directory set at creation (default: current directory)
- All file operations within the session are relative to this directory
- Use `--project-dir` with `ao-start` to override; other commands retrieve it from the session API

### Blueprints vs Sessions
- **Blueprint**: Reusable configuration (system prompt + MCP tools) stored in Agent Registry
- **Session**: Running conversation instance managed by Agent Coordinator
- One blueprint can be used by multiple sessions
- Sessions can run without blueprints (general purpose)

---

## Notes for AI Assistants

1. **Always check status** before resuming: `ao-status <name>` → only resume if `running` or `finished`
2. **Session names** must be unique and valid (no spaces, max 60 chars, alphanumeric + dash/underscore)
3. **Prompt input**: Use stdin (pipe) OR `-p` flag, not both (stdin takes precedence)
4. **Get result** only works on `finished` sessions - check status first
5. **Blueprints** - list them with `ao-list-blueprints` before using `--agent`
6. **Sessions are persistent** - stored in Agent Coordinator database
7. **Command location** - Always use commands from this skill's `commands/` folder
8. **Async execution** - Sessions run in Claude Code, commands return immediately after submission

---

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| "Cannot connect to Agent Coordinator" | Backend not running | Ask the user to the backend. |
| "Cannot connect to Agent Registry" | Backend not running | Ask the user to the backend. |
| "Session already exists" | Creating duplicate session | Use `ao-resume` or choose different name |
| "Session not found" | Wrong name or doesn't exist | Check `ao-list-sessions` |
| "Session is not finished" | Getting result from running session | Check `ao-status`, wait for `finished` |
| "Invalid session name" | Bad characters or too long | Use alphanumeric + dash/underscore, max 60 chars |
| "No prompt provided" | Missing `-p` and stdin | Provide prompt via stdin or `-p` flag |
| "Agent not found" | Blueprint not in registry | Check `ao-list-blueprints` for available blueprints |

---

## Exit Codes

- `0` - Success
- `1` - Error (invalid input, session not found, etc.)

---

## Quick Decision Tree

**Want to start a new agent conversation?** → `ao-start <name>`
- With specialized agent? → Add `--agent <agent-name>`
- In specific directory? → Add `--project-dir <path>`

**Want to continue a conversation?** → `ao-resume <name>`
- Not sure if it exists? → Check with `ao-status <name>` first

**Want to see the result?** → `ao-get-result <name>`
- Must check status first → `ao-status <name>` (must be `finished`)

**Want to see what exists?**
- Sessions → `ao-list-sessions`
- Blueprints → `ao-list-blueprints`

**Want session details?** → `ao-show-config <name>`

**Want to delete all?** → `ao-delete-all` (removes all sessions)

---

## Additional Resources

- **Architecture**: See `references/AGENT-ORCHESTRATOR.md`
- **Environment Variables**: See `references/ENV_VARS.md`
