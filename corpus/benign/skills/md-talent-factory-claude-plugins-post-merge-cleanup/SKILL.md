---
name: post-merge-cleanup
description: >
  Cleans up git assets (worktrees, branches) and updates task status after PR merge.
  Supports both filesystem (STATUS.md) and Linear issue tracking.
  Safe defaults with dry-run preview mode.
---

# Post-Merge Cleanup

## Overview

This skill automates the cleanup process after a PR has been merged:
- Removes git worktrees
- Deletes local and remote feature branches
- Updates task status (STATUS.md or Linear)
- Commits and pushes status changes

## Usage

```bash
/git-workflow:post-merge-cleanup task-013          # Auto-detect source
/git-workflow:post-merge-cleanup PROJ-123          # Linear issue (auto-detected)
/git-workflow:post-merge-cleanup task-013 --dry-run # Preview only
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `task_id` | Yes | Task identifier (e.g., `task-013`, `PROJ-123`) |
| `--linear` | No | Force Linear as task source |
| `--file` | No | Force filesystem (STATUS.md) as source |
| `--dry-run` | No | Preview changes without executing |
| `--no-status-update` | No | Skip task status update, only cleanup git |
| `--keep-local` | No | Keep local branch (only delete remote) |

## Workflow

### Step 1: Parse Input & Detect Task Source

1. **Extract task_id** from user input
2. **Check for flags:** `--dry-run`, `--linear`, `--file`, `--no-status-update`, `--keep-local`

**Linear Detection (if task_id matches `[A-Z]+-\d+` pattern OR `--linear` flag):**
```
Call: mcp__plugin_linear_linear__get_issue(id: <task_id>)
Store: issue title, current state, project info
```

**Filesystem Detection (default for `task-NNN` pattern):**
```bash
# Search for STATUS.md files
glob ".plans/**/STATUS.md"

# Parse markdown table for task row matching task_id
# Store: file path, current status, line location
```

**If neither source found:** Display error with suggestions.

### Step 2: Resolve Git Assets

Find all git assets associated with the task:

```bash
# 1. Check for worktrees
git worktree list | grep -i "<task_id>"

# 2. Check local branches
git branch | grep -iE "(feature/)?(task-)?<task_id>"

# 3. Check remote branches
git branch -r | grep -iE "(feature/)?(task-)?<task_id>"
```

**Display summary to user:**
```
Found git assets for <task_id>:
  Worktree: .worktrees/task-013
  Local branch: feature/task-013-admin-dashboard
  Remote branch: origin/feature/task-013-admin-dashboard
```

If `--dry-run`: Display what would be cleaned up and exit.

### Step 3: Verify PR Status (Safety Check)

```bash
# Check if PR was merged
gh pr list --search "<task_id>" --state merged --limit 5
```

**If no merged PR found:**
- Display warning: "No merged PR found for <task_id>"
- Ask user: "Continue anyway? This will delete branches that may not be merged."
- Require explicit confirmation to proceed

**If merged PR found:**
- Display: "PR #<number> merged on <date>"
- Proceed automatically

### Step 4: Execute Git Cleanup

**Execute in order (skip if asset not found):**

**4.1 Remove Worktree:**
```bash
git worktree remove .worktrees/<task_id> --force
```
- If worktree has uncommitted changes, warn user and require confirmation

**4.2 Delete Local Branch (unless `--keep-local`):**
```bash
git branch -d <branch_name>
```
- If branch not fully merged, ask for confirmation before using `-D`

**4.3 Delete Remote Branch:**
```bash
git push origin --delete <branch_name>
```
- Skip if branch doesn't exist on remote (already deleted)

**4.4 Prune Stale References:**
```bash
git fetch --prune
```

### Step 5: Update Task Status (unless `--no-status-update`)

**For Linear Issues:**
```
Call: mcp__plugin_linear_linear__update_issue(
  id: <task_id>,
  state: "Done"  # Or equivalent completed state for the project
)
```
- First call `mcp__plugin_linear_linear__list_issue_statuses` to find correct "completed" state

**For Filesystem (STATUS.md):**

1. **Read current file content**

2. **Find task row in markdown table:**
   - Pattern: `| <task_id> |` or `| NNN |` (where NNN matches task number)

3. **Update status in row:**
   - Replace status indicators:
     - `pending` / `⬜` / `todo` → `✅ completed`
     - `in_progress` / `🔄` / `doing` → `✅ completed`

4. **Recalculate progress (if present):**
   - Find progress summary row (e.g., `| **Total** | ... | XX% |`)
   - Count completed vs total tasks
   - Update percentage and story points

5. **Update "Next Steps" section (if present):**
   - Remove completed task from "Immediately Available" list
   - Add newly unblocked tasks based on dependency graph

### Step 6: Commit & Push Changes (Filesystem only)

If STATUS.md was modified:

```bash
# Stage changes
git add <status_file_path>

# Commit with conventional message
git commit -m "✅ chore: Mark <task_id> as completed"

# Push to remote
git push
```

## Output Examples

**Successful cleanup:**
```
Post-Merge Cleanup for task-013
================================

Task Source: Filesystem (.plans/subscribeflow-mvp/STATUS.md)
PR Status: #15 merged on 2026-02-03

Git Cleanup:
  ✓ Worktree removed: .worktrees/task-013
  ✓ Local branch deleted: feature/task-013-admin-dashboard
  ✓ Remote branch deleted: origin/feature/task-013-admin-dashboard
  ✓ Stale references pruned

Status Update:
  ✓ Task status: in_progress → completed
  ✓ Progress updated: 80% → 89% (78/88 SP)
  ✓ Changes committed and pushed

Cleanup complete!
```

**Dry-run output:**
```
Post-Merge Cleanup for task-013 (DRY RUN)
==========================================

Would perform the following actions:

Git Cleanup:
  • Remove worktree: .worktrees/task-013
  • Delete local branch: feature/task-013-admin-dashboard
  • Delete remote branch: origin/feature/task-013-admin-dashboard

Status Update:
  • Update .plans/subscribeflow-mvp/STATUS.md
  • Change task-013 status: in_progress → completed
  • Recalculate progress: 80% → 89%

Run without --dry-run to execute.
```

## Error Handling

**Worktree has uncommitted changes:**
```
Warning: Worktree .worktrees/task-013 has uncommitted changes.
  Modified: src/components/Dashboard.tsx

Options:
  1. Commit changes first
  2. Discard changes and remove (--force)
  3. Abort cleanup

Choice [1/2/3]:
```

**Branch not fully merged:**
```
Warning: Branch feature/task-013-foo is not fully merged.
This may indicate the PR was not merged, or was squash-merged.

Options:
  1. Force delete anyway (-D)
  2. Keep branch and continue
  3. Abort cleanup

Choice [1/2/3]:
```

**Linear API error:**
```
Error: Could not update Linear issue PROJ-123
  Reason: Insufficient permissions

Status update skipped. Git cleanup completed successfully.
Please update the issue manually in Linear.
```

## Supported STATUS.md Formats

### Format A (Table with ID column):
```markdown
| ID  | Task           | Status         |
|-----|----------------|----------------|
| 013 | Admin Dashboard| 🔄 in_progress |
```

### Format B (Task name as identifier):
```markdown
| Task      | Status    |
|-----------|-----------|
| task-013  | pending   |
```

### Recognized Status Values:
| Status Type | Recognized Values |
|-------------|-------------------|
| Pending | `pending`, `⬜`, `todo`, `open`, `backlog` |
| In Progress | `in_progress`, `🔄`, `doing`, `active`, `started` |
| Completed | `completed`, `✅`, `done`, `closed`, `finished` |

## References

- [STATUS.md Format Guide](docs/status-md-format.md)
- [Troubleshooting](docs/troubleshooting.md)
