---
name: infinite-moves
description: "Bridges to the infinite-moves plugin for autonomous task execution. Activates when user mentions tasks, backlog, dev loop, ideate, generate tasks, sweep debt, or wants continuous development. Knows how to invoke /moves commands without user typing them."
---

# Infinite Moves - Plugin Bridge

This skill makes you aware of the **infinite-moves plugin** so you can use it autonomously.

## When to Use

Activate when user says things like:
- "Help me work through my backlog"
- "What tasks are available?"
- "Generate tasks for [feature]"
- "Run the dev loop"
- "Check for technical debt"
- "Execute some tasks"

## Available Commands

The plugin provides these commands - invoke them directly:

| Trigger | Command | What it does |
|---------|---------|--------------|
| Run/execute tasks | `/moves run` | Execute tasks from manifest |
| Parallel execution | `/moves run --parallel 2` | Run non-conflicting tasks concurrently |
| Continuous mode | `/moves run --continuous` | Keep going until manifest empty |
| **Infinite mode** | `/moves run --infinite` | Never stop - auto-ideate when low |
| Check status | `/moves status` | Show pipeline health, available tasks |
| Generate from idea | `/moves ideate --topic "..."` | Create design doc + tasks from topic |
| Find gaps | `/moves ideate` | Scan docs vs code for missing work |
| Quick health check | `/moves ideate --quick` | Fast pipeline check |
| Scan debt | `/moves sweep` | Find TODOs, type issues, test gaps |
| Claim task | `/moves status --claim <id>` | Reserve for manual work |
| Complete task | `/moves status --complete <id>` | Mark done |

## Autonomous Behavior

When user wants to work on tasks, don't wait - invoke the commands:

```
User: "Let's knock out some tasks"
You: [invoke /moves status to see what's available]
You: [invoke /moves run to start executing]
```

```
User: "I have an idea for a meditation feature"
You: [invoke /moves ideate --topic "meditation feature"]
```

```
User: "Run tasks in parallel until done"
You: [invoke /moves run --continuous --parallel 2]
```

```
User: "Run forever" / "Keep working indefinitely" / "Infinite loop"
You: [invoke /moves run --infinite --parallel 2]
```

## Command Details

For detailed instructions on each command, the plugin contains:
- `commands/run.md` - Execution options and flow
- `commands/ideate.md` - Task generation modes
- `commands/status.md` - Pipeline management
- `commands/sweep.md` - Debt scanning

## Agents

The plugin provides agents you can spawn via Task tool:
- `task-executor` - Executes a single task with build verification
- `verifier` - Verifies task completion meets criteria

## Data Directory

All artifacts are stored in `.infinite-moves/` at the project root:
```
.infinite-moves/
├── manifest.json           # Task manifest
├── tasks/                  # Task spec files
│   └── G17-health-sync.md
├── designs/                # Design docs from ideation
├── debt-manifest.json      # Technical debt tracking
└── debt-report.md          # Human-readable debt report
```

Create this directory if it doesn't exist before running commands.
