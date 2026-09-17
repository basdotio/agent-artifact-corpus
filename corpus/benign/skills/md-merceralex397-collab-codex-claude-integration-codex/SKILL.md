---
name: codex
description: Unified Codex command with auto-detection, intent routing, and quality gates
user-invocable: true
allowed-tools:
  - mcp__codex__codex
  - mcp__codex__codex-reply
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Task
---

# Unified Codex Skill

One command to rule them all. Auto-detects project context, routes by intent, iterates until green.

## Usage

```
/codex <natural language task>
```

## Examples

```
/codex implement a rate limiter for the API
/codex fix the auth bug and add tests
/codex review the payment module for security issues
/codex refactor UserService to use repository pattern
```

## Flags

| Flag | Effect |
|------|--------|
| `--no-iterate` | Skip quality gates, just execute |
| `--gates=test,lint` | Only run specified gates |
| `--model=<model>` | Override model selection |
| `--reasoning=<level>` | Override reasoning effort (low/medium/high/xhigh) |
| `--profile=<name>` | Use specific profile (quick/standard/deep/review) |
| `--verbose` | Show detailed output |
| `--quiet` | Minimal output |

## Workflow

### 1. Load User Settings

Load settings from `~/.claude/codex-settings.toml` (if exists):

```bash
python scripts/settings_loader.py --json
```

This returns user's preferred defaults, gate configuration, and profile definitions.
If no settings file exists, sensible defaults are used.

### 2. Detect Project DNA

Run project detection (cached for session):

```bash
python scripts/project_dna.py --json
```

This returns framework, patterns, test commands, lint commands.

### 3. Analyze Intent

Run intent analysis on the user's prompt:

```bash
python scripts/task-analyzer.py "<user prompt>"
```

This returns JSON with:
- `intent.type`: generate, debug, review, refactor, test, or chain
- `intent.steps`: ordered list of operations (for chain type)
- `complexity`: 1-5 scale
- `codex_params.profile`: quick, standard, or deep
- `codex_params.model`: gpt-5.1-codex-mini, gpt-5.2-codex, or gpt-5.1-codex-max
- `codex_params.model_reasoning_effort`: low, medium, high, or xhigh

### 4. Route to Appropriate Agent

Based on intent type, route to the appropriate subagent:

| Intent | Route To | Sandbox |
|--------|----------|---------|
| generate, debug, refactor, test | codex-coder | workspace-write |
| review, analyze, audit | codex-reviewer | read-only |
| chain | Sequential execution | Depends on step |

**For write operations (generate/debug/refactor/test):**
Use the Task tool to spawn a codex-coder agent:

```
Task tool with subagent_type: "codex-coder"
```

**For read operations (review/analyze/audit):**
Use the Task tool to spawn a codex-reviewer agent:

```
Task tool with subagent_type: "codex-reviewer"
```

**For direct execution (simple tasks or when agents unavailable):**
Continue with steps 5-7 below.

### 5. Build Enhanced Prompt

Combine DNA context with user's task:

```
PROJECT CONTEXT (auto-detected):
[DNA output here]

USER SETTINGS:
Model: [from settings or flag]
Reasoning: [from settings or flag]

TASK: [user's original prompt]

INSTRUCTIONS:
- Follow existing project patterns
- [Intent-specific instructions]
```

### 6. Execute with Model Escalation

Start with the model based on complexity and user settings:

| Complexity | Profile | Model | Reasoning | Escalation |
|------------|---------|-------|-----------|------------|
| 1-2 | quick | gpt-5.1-codex-mini | low | -> standard |
| 3 | standard | gpt-5.2-codex | medium | -> deep |
| 4-5 | deep | gpt-5.1-codex-max | high/xhigh | (none) |

User settings override these defaults. Flag overrides take highest priority.

Call Codex:
```
Use mcp__codex__codex with:
- prompt: [enhanced prompt]
- cwd: "."
- model: [from settings/analysis]
- sandbox: [from intent - workspace-write or read-only]
- approval-policy: "never"  (REQUIRED for MCP stdio)
```

If the response indicates struggle or failure, escalate to next model and retry.

### 7. Run Quality Gates (if write operation)

For generate/debug/refactor/test intents, run quality gates based on user settings:

```bash
# Check which gates are enabled
python scripts/settings_loader.py --gates --json

# Run enabled gates
python scripts/quality_gates.py --gate test --command "<test command>" --json
python scripts/quality_gates.py --gate lint --command "<lint command>" --fix "<fix command>" --json
```

If a gate fails:
1. Send error output back to Codex with fix request via `mcp__codex__codex-reply`
2. Codex attempts fix
3. Re-run gate
4. Max retries from user settings (default: 3 per gate, 10 total Codex calls)

### 8. Report Results

On success:
```
Complete: [summary of changes]
  - Files modified: [list]
  - Tests: passing
  - Lint: passing
```

On partial success:
```
Partially complete: [what was done]
  - Remaining issue: [what's failing]
  - Suggested fix: [recommendation]
```

## Intent-Specific Instructions

### generate
- Create new files following existing patterns
- Include appropriate tests
- Follow naming conventions from DNA

### debug
- Analyze error context first
- Explain root cause before fixing
- Verify fix doesn't break other tests

### review
- Read-only analysis
- Categorize findings by severity
- Suggest specific fixes

### refactor
- Preserve all existing behavior
- Run tests frequently during refactor
- Make atomic, reviewable changes

### test
- Follow existing test patterns
- Cover happy path, edge cases, errors
- Use appropriate mocking

## Chain Execution

For prompts like "fix X and add tests":

1. Execute steps in order
2. Each step must pass before next
3. Share context between steps
4. Report progress after each step

## Error Handling

| Error | Response |
|-------|----------|
| DNA detection fails | Use defaults, warn user |
| Intent unclear | Ask clarifying question |
| Model unavailable | Fall back to available model |
| Gate max retries | Report blocker, suggest manual fix |
| Codex timeout | Offer retry with longer timeout |
| Settings load fails | Use built-in defaults, warn user |

## Related Commands

| Command | Description |
|---------|-------------|
| `/codex-config` | View and modify settings |
| `/codex-coder <task>` | Direct access to coding agent |
| `/codex-reviewer <target>` | Direct access to review agent |

## Backward Compatibility

Old skills still work:
- `/codex-delegate X` -> redirects to `/codex implement X`
- `/codex-review X` -> redirects to `/codex review X`
