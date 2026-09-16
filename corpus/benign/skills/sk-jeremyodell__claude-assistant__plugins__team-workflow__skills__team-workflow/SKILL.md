---
name: team-workflow
description: Deterministic team development workflow for Claude Code. Enforces a mandatory sequence of phases (Setup → Brainstorm → Plan → Execute → Quality Check → Ship) with Linear integration, TDD requirements, and quality gates. Activates when working on issues/tasks, when user mentions Linear issues (e.g., ENG-123), when starting development work, when preparing to ship code, or when orchestrating parallel work on parent issues with sub-tasks. Commands: /team:task, /team:feature, /team:quality-check, /team:ship.
---

# Team Workflow Skill

Enforces a deterministic, phase-gated development workflow with Linear integration and quality enforcement.

## Workflow Overview

### Single Task Workflow
```
/team:task ENG-123
    ↓
Phase 0: Setup (fetch issue, update status, create branch)
    ↓
Phase 1: Brainstorm (design thinking, post to Linear)
    ↓
Phase 2: Plan (task breakdown, post to Linear)
    ↓
Phase 3: Execute (TDD for every change)
    ↓
Phase 4: Quality Check (/team:quality-check)
    ↓
Phase 5: Ship (/team:ship → PR + Linear update)
```

### Parallel Feature Workflow
```
/team:feature PROJ-100 --parallel=3
    ↓
Validation (check sub-issues, detect cycles, Linear MCP)
    ↓
Setup (create feature branch from main)
    ↓
Wave 1: Spawn agents for tasks with no blockers
    ↓   [PROJ-101, PROJ-102, PROJ-103 run in parallel]
    ↓   Each runs /team:task, branches from feature branch
    ↓
Merge: Completed tasks merge back to feature branch
    ↓
Wave 2: Spawn agents for newly unblocked tasks
    ↓   [PROJ-104, PROJ-105 depend on Wave 1]
    ↓
Repeat until all tasks complete or fail
    ↓
Summary: Present results, offer next actions (PR, retry, etc.)
```

## Commands

### `/team:task $ISSUE_ID`
Start work on a Linear issue. Enforces all workflow phases.

### `/team:feature $PARENT_ISSUE_ID [--parallel=N]`
Orchestrate parallel execution of sub-tasks under a parent issue. Analyzes dependencies, spawns color-coded subagents, and coordinates merges on a shared feature branch.

**Arguments:**
- `$PARENT_ISSUE_ID` - Linear issue ID of the parent (e.g., `PROJ-100`)
- `--parallel=N` - Max concurrent agents (default: 3, range: 1-6)

**Execution:**
1. Builds dependency graph from `blockedBy` relations
2. Creates feature branch from main
3. Spawns subagents for independent tasks (wave execution)
4. Merges completed work back to feature branch
5. Spawns next wave when blockers complete
6. Handles failures with isolation (continues independent tasks)
7. Provides summary with next actions (create PR, retry failed, etc.)

### `/team:quality-check`
Run all quality gates. Blocks PR creation on failure.

Gates:
- `npm test` - ZERO failures
- `npm run lint` - ZERO errors  
- `npm run typecheck` - ZERO errors
- `/code-review` - ZERO high-confidence (≥80%) issues

### `/team:ship`
Create PR, update Linear to "In Review", post PR link.

## Linear Integration

Uses Linear MCP server for:
- `mcp__linear__get_issue` - Fetch issue details
- `mcp__linear__update_issue` - Update status
- `mcp__linear__create_comment` - Post design/plan/PR links

## TDD Requirements

**Every change requires tests first:**
1. Write failing test
2. Implement minimum code to pass
3. Refactor
4. Run tests

There is NO change too small for TDD.

## Quality Gate Zero-Tolerance

All gates must pass with ZERO errors before shipping:
- Tests must all pass
- No lint errors (warnings OK)
- No type errors
- No high-confidence code review issues

## Git Workflow

**Branch naming:** `feat/$ISSUE_ID-slugified-title`

**Commit format:**
```
feat(ENG-123): brief description

- Main change
- Secondary change

Closes ENG-123
```

## Hooks

The plugin includes hooks that:
- Format files on save (Prettier)
- Run tests/lint before push
- Verify quality before stopping

## Integration with Superpowers

Phases 1-2 always use Superpowers for design thinking and planning.

Phase 3 (Execute) uses **conditional execution mode**:

| Plan Type | Execution Mode | Token Usage |
|-----------|----------------|-------------|
| Specific (code blocks, file paths) | Direct | ~60% less |
| Vague (exploration needed) | Subagent | Standard |

**Flags:**
- `--direct` - Force direct execution
- `--use-subagents` - Force subagent execution

**Rule of thumb:**
- Detailed plan with literal code → Direct execution
- Vague requirements needing exploration → Subagent execution
