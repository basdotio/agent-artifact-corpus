# Speck Advanced Workflows

Advanced features: Multi-repo support, worktree integration, and session handoff.

**Referenced from**: SKILL.md

---

## Table of Contents

1. [Multi-Repo Mode Detection](#multi-repo-mode-detection)
2. [Worktree Mode Detection](#worktree-mode-detection)
3. [Session Handoff](#session-handoff)
4. [Hook Failures and Fallback Methods](#hook-failures-and-fallback-methods)

---

## Multi-Repo Mode Detection

When interpreting Speck artifacts, determine if the project is in multi-repo mode:

**Detection Method**:
- Check for `.speck/root` symlink in `.speck/` directory
- If symlink exists and points to parent directory → multi-repo child repo
- If no symlink → single-repo mode

**Child Repo Context**:
When in child repo:
- Specs MAY reference parent specs via `**Parent Spec**` field in spec.md metadata
- Feature numbers MUST be coordinated across all child repos (no duplicates)
- Constitution lives in root repo (`.speck/constitution.md`), child repos may have their own
- Plan and tasks artifacts (plan.md, tasks.md) are per-repo (not shared)

**Root Repo Context**:
- Contains shared `specs/` directory with feature specifications
- Child repos symlink via `.speck/root` pointing to root repo directory
- Manages spec.md files (shared across child repos)

**Symlink Structure**:
```bash
# Child repo structure
.speck/
  root -> ../../  # Points to shared specs root directory

# Resolves to shared specs
specs/ -> (via symlink resolution)
```

**User Query Examples**:
- "Is this a multi-repo setup?" → Check for `.speck/root` symlink
- "What's the parent spec?" → Read `**Parent Spec**` from spec.md metadata
- "Where's the constitution?" → Check local `.speck/constitution.md` or follow symlink to root

---

## Worktree Mode Detection

Features MAY use Git worktrees for isolated parallel development:

**Detection Method**:
- Check for `.speck/config.json` with `worktree.enabled: true`
- Check for `.speck/worktrees/<branch-name>.json` metadata files
- Verify Git version supports worktrees (Git 2.5+)

**Worktree Configuration** (`.speck/config.json`):
```json
{
  "worktree": {
    "enabled": true,
    "autoLaunchIDE": true,
    "preferredIDE": "vscode",
    "installDependencies": true,
    "branchPrefix": "specs/"
  },
  "files": {
    "rules": [
      {"pattern": ".env*", "action": "copy"},
      {"pattern": "*.config.{js,ts}", "action": "copy"},
      {"pattern": "node_modules", "action": "symlink"},
      {"pattern": ".bun", "action": "symlink"}
    ]
  }
}
```

**Worktree Metadata** (`.speck/worktrees/<branch-name>.json`):
```json
{
  "branchName": "012-worktree-integration",
  "worktreePath": "../speck-012-worktree-integration",
  "createdAt": "2025-11-22T10:00:00Z",
  "status": "active"
}
```

**Worktree Naming Logic**:
Path calculation based on repository layout:
- If repo directory name = repo name: `<repo-name>-<branch-name>`
- If repo directory name = branch name: `<branch-name>`
- Example: Repo at `/projects/speck/`, branch `012-worktree` → worktree at `/projects/speck-012-worktree/`

**File Copy vs Symlink Rules**:
Configuration files copied (isolated per worktree):
- `.env*` files (environment variables)
- `*.config.{js,ts}` (build configs)

Dependencies symlinked (shared across worktrees):
- `node_modules/` (npm/yarn/pnpm packages)
- `.bun/` (Bun cache)

**Worktree Lifecycle**:

1. **Creation**: `/speck.specify` with worktree flags OR manual `git worktree add`
   - `--no-worktree`: Skip worktree creation
   - `--no-ide`: Skip IDE auto-launch
   - `--no-deps`: Skip dependency installation
   - `--reuse-worktree`: Reuse existing worktree if present

2. **Update**: Metadata tracks feature association in `.speck/worktrees/<branch>.json`

3. **Cleanup**: Worktree removal cleans up metadata
   - `speck worktree remove <branch>`: Remove worktree (with confirmation)
   - `speck worktree prune`: Cleanup stale worktree references

**IDE Auto-Launch**:
After worktree creation:
- Copies config files (`.env`, `*.config.js`)
- Symlinks dependencies (`node_modules`)
- Installs dependencies with progress indicator (if `installDependencies: true`)
- Launches IDE pointing to worktree path
- Supported IDEs: VSCode (`code`), Cursor (`cursor`), JetBrains (`idea`/`webstorm`)

**User Query Examples**:
- "Is this in a worktree?" → Check current directory path for worktree metadata or Git worktree list
- "What's the worktree config?" → Read `.speck/config.json` worktree section
- "Which worktrees exist?" → List `.speck/worktrees/*/metadata.json` files or `git worktree list`
- "How are files managed?" → Explain copy vs symlink rules from config.json

---

## Session Handoff

When creating a new feature worktree, Speck automatically sets up context transfer for new Claude sessions.

**Purpose**:
Transfer feature context (spec location, pending tasks, repository mode) to new Claude sessions that start in the worktree, so Claude immediately knows what to work on.

**How It Works**:

1. **Worktree Creation** (`/speck.specify`):
   - Creates new worktree with `git worktree add -b <branch> <path> HEAD`
   - Writes `.speck/handoff.md` to the worktree (contains feature context)
   - Writes `.claude/settings.json` with SessionStart hook configuration
   - Writes `.claude/scripts/handoff.sh` shell script to execute
   - Optionally writes `.vscode/tasks.json` for auto-opening Claude panel

2. **SessionStart Hook** (fires when Claude session starts):
   - `.claude/settings.json` contains hook pointing to `.claude/scripts/handoff.sh`
   - Hook reads `.speck/handoff.md` and returns JSON with `hookSpecificOutput.additionalContext`
   - Claude receives the handoff content as context in its first message

3. **Self-Cleanup** (after handoff loads):
   - Hook archives `.speck/handoff.md` → `.speck/handoff.done.md`
   - Hook removes itself from `.claude/settings.json` to prevent re-firing
   - One-shot operation: handoff happens once per worktree creation

**Handoff Document Structure** (`.speck/handoff.md`):
```markdown
# Session Handoff

**Feature**: 015-scope-simplification
**Spec Location**: ../main-repo/specs/015-scope-simplification/
**Repository Mode**: single-repo

## Context

This worktree was created for implementing the "Scope Simplification" feature.

## Pending Tasks

- Phase 7: User Story 5 - Developer Gets Help via /speck.help
  - T068: Rename skill directory
  - T069: Update skill frontmatter
  ...

## Relevant Files

- spec.md: Feature specification
- plan.md: Implementation plan
- tasks.md: Task breakdown
```

**Graceful Degradation**:
- If handoff document creation fails, worktree is still created (non-fatal)
- If SessionStart hook fails to fire, user can manually read `.speck/handoff.md`
- If hook self-cleanup fails, handoff may fire again (no harm, just redundant)

**User Query Examples**:
- "What's in the handoff document?" → Read `.speck/handoff.md` in worktree
- "Did session handoff work?" → Check for `.speck/handoff.done.md` (archived file)
- "Why does Claude know about my feature?" → Explain SessionStart hook + handoff document
- "Can I disable handoff?" → Use `--no-worktree` flag with `/speck.specify`

---

## Hook Failures and Fallback Methods

When VSCode Claude Extension hooks fail (known bug), slash commands won't receive prerequisite context automatically. This section explains how to troubleshoot and work around hook failures.

**Common Symptoms**:
- Missing `SPECK_PREREQ_CONTEXT` comment in slash command prompts
- Slash commands ask you to run prerequisite checks manually

**Root Cause**:
VSCode Claude Extension has a bug that prevents UserPromptSubmit hooks from executing for installed plugins. This breaks:
- **UserPromptSubmit hook**: Prerequisite context not injected into prompts

**Fallback Method: Direct Script Execution**

If hooks are not working, run scripts directly from the installed plugin or CLI:

```bash
bun ~/.claude/plugins/marketplaces/speck-market/speck/scripts/<script-name>.ts --json [options]
```

**Available Scripts**:
- `check-prerequisites.ts` - Validate feature directory and generate context
- `setup-plan.ts` - Initialize planning workflow
- `create-new-feature.ts` - Create new feature specification
- `update-agent-context.ts` - Update agent context files

**Script Options by Command**:

| Slash Command | Script | Required Options |
|---------------|--------|------------------|
| `/speck.implement` | `check-prerequisites.ts` | `--json --require-tasks --include-tasks` |
| `/speck.plan` | `setup-plan.ts` | `--json` |
| `/speck.tasks` | `check-prerequisites.ts` | `--json` |
| `/speck.analyze` | `check-prerequisites.ts` | `--json --require-tasks --include-tasks` |
| `/speck.clarify` | `check-prerequisites.ts` | `--json --paths-only` |
| `/speck.checklist` | `check-prerequisites.ts` | `--json` |
| `/speck.taskstoissues` | `check-prerequisites.ts` | `--json --require-tasks --include-tasks` |

**Multi-Repo Context with Fallbacks**:

When running fallback commands in multi-repo mode, the scripts automatically detect:
- Mode detection via `.speck/root` symlink
- Shared specs location (root repo `specs/`)
- Local implementation artifacts (child repo `specs/`)

**Example: Multi-Repo Fallback**

```bash
# In child repo directory
cd /path/to/child-repo

# Run prerequisite check
bun ~/.claude/plugins/marketplaces/speck-market/speck/scripts/check-prerequisites.ts --json

# Output includes both shared and local paths:
{
  "MODE": "multi-repo",
  "FEATURE_DIR": "/path/to/root-repo/specs/007-feature",
  "IMPL_PLAN": "/path/to/child-repo/specs/007-feature/plan.md",
  "TASKS": "/path/to/child-repo/specs/007-feature/tasks.md",
  "REPO_ROOT": "/path/to/child-repo",
  "AVAILABLE_DOCS": [
    "../../../root-repo/specs/007-feature/spec.md",
    "specs/007-feature/plan.md",
    "specs/007-feature/tasks.md"
  ]
}
```

**Interpreting Fallback Output**:

When slash commands show fallback instructions:
1. Copy the exact `bun` command shown
2. Run it in your terminal from the repository root
3. Parse the JSON output to extract needed paths
4. Provide the parsed information to the slash command

**User Query Examples**:
- "Why isn't SPECK_PREREQ_CONTEXT showing up?" → Explain VSCode hook bug, suggest fallback method
- "How do I run prerequisite checks manually?" → Show `bun ~/.claude/plugins/.../check-prerequisites.ts --json`
- "Where are the scripts in the installed plugin?" → Explain `~/.claude/plugins/marketplaces/speck-market/speck/scripts/`
- "Do fallbacks work in multi-repo mode?" → Explain automatic mode detection via `.speck/root` symlink
