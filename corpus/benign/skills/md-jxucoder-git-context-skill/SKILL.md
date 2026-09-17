---
name: git-context
description: Store and manage coding context in git. Use when saving decisions, tracking tasks, planning complex work, or coordinating with other agents. Activates on mentions of "save context", "track task", "planning", or multi-agent coordination.
---

# git-context Skill

Use `git ctx` to persist context in git. Local by default, share with `--shared`.

## Quick Reference

```bash
# Memory (context entries)
git ctx add --title "Title" -m "Content"   # Add context
git ctx add --title "Title"                 # Opens editor
git ctx list                                # List local
git ctx list --all                          # List all
git ctx show <id>                           # View entry
git ctx edit <id>                           # Edit entry
git ctx rm <id>                             # Remove
git ctx search "query"                      # Search

# Tasks
git ctx task add "Title"                    # Create task
git ctx task add "Title" -d "Description"   # With description
git ctx task list                           # List tasks
git ctx task show <id>                      # View task
git ctx task claim <id>                     # Claim (take ownership)
git ctx task done <id>                      # Complete
git ctx task comment <id> "message"         # Add comment

# Sync (shared entries only)
git ctx push                                # Push to remote
git ctx pull                                # Pull from remote

# Flags
--shared, -s                                # Use shared storage (syncs)
--all, -a                                   # Show local + shared
--json                                      # JSON output
```

## When to Use

### Save Context When:
- Making **architecture decisions** → `git ctx add --title "Why PostgreSQL"`
- Discovering **important information** → `git ctx add --title "API rate limits"`
- **Ending a session** → `git ctx add --title "Session handoff"`
- Finding **gotchas or bugs** → `git ctx add --title "Bug: Auth edge case"`

### Use Tasks When:
- **Breaking down** complex work
- **Coordinating** with other agents
- Work needs **tracking** across sessions

### Use Shared When:
- Context should **sync** with team/other machines
- Tasks are for **multi-agent** coordination

## Planning Pattern (Manus-style)

For complex tasks, create a plan entry:

```bash
git ctx add --title "Plan: [Feature Name]" << 'EOF'
## Goal
[One sentence describing success]

## Phases
- [ ] Phase 1: Setup and planning
- [ ] Phase 2: Core implementation
- [ ] Phase 3: Testing
- [ ] Phase 4: Documentation

## Key Questions
1. [Question to answer]
2. [Question to answer]

## Decisions Made
- (none yet)

## Errors Encountered
- (none yet)

## Status
**Currently in Phase 1** - Planning
EOF
```

### The Loop

1. **Before each major decision** → Re-read the plan
   ```bash
   git ctx show <plan-id>
   ```

2. **After each phase** → Update the plan
   ```bash
   git ctx edit <plan-id>
   # Mark [x] completed, update Status section
   ```

3. **When you learn something** → Save to separate entry
   ```bash
   git ctx add --title "Notes: [Topic]"
   ```

This keeps goals in your attention window and builds knowledge.

## Multi-Agent Workflow

### As Team Lead
```bash
# Create shared tasks
git ctx task add --shared "Implement auth" -d "JWT with refresh tokens"
git ctx task add --shared "Setup database" -d "PostgreSQL schema"
git ctx task add --shared "Write tests"
git ctx push
```

### As Worker Agent
```bash
# 1. Pull latest
git ctx pull

# 2. Check available tasks
git ctx task list --shared
# task-001  Implement auth   [open]
# task-002  Setup database   [open]

# 3. Claim one
git ctx task claim task-001
git ctx push

# 4. Work on it, add comments
git ctx task comment task-001 "Using bcrypt for passwords"

# 5. Complete
git ctx task done task-001
git ctx push
```

### Avoiding Conflicts
- **Always pull before claiming**
- **Push immediately after claiming**
- First to push wins

## Session Handoff

At end of session:

```bash
git ctx add --title "Handoff: [Date]" << 'EOF'
## Completed
- [What was done]

## In Progress
- [Current state]

## Next Steps
- [What to do next]

## Blockers
- [Any issues]
EOF
```

Next session:
```bash
git ctx list
git ctx show <handoff-id>
```

## Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| Forget context between sessions | Save with `git ctx add` |
| Start complex work immediately | Create plan first |
| Claim tasks without pulling | Always `git ctx pull` first |
| Keep findings in head | Save to entries |
| Retry errors silently | Log errors in plan |

## Storage

```
.git/
├── context/              ← LOCAL (private, never syncs)
│   ├── memory/
│   └── tasks/
└── refs/context/         ← SHARED (syncs with push/pull)
    ├── memory/
    └── tasks/
```

## Tips

1. **IDs are short** - Use first 8 chars: `git ctx show abc12345`
2. **Pipe content** - `echo "text" | git ctx add --title "Note"`
3. **Search is fast** - `git ctx search "auth"` finds all related
4. **JSON for scripts** - `git ctx list --json | jq ...`

