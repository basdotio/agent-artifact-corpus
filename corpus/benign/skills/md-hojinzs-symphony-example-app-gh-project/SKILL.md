---
name: gh-project
description: Manage GitHub Project v2 issue states, workpad comments, and related follow-up actions.
license: MIT
metadata:
  author: gh-symphony
  version: "1.0"
  generatedBy: "gh-symphony"
---

# /gh-project — GitHub Project v2 Status Management

## Purpose

Interact with the GitHub Project v2 board to manage issue status,
create and update the single workpad comment, leave transition comments,
and handle review follow-up loops without duplicating orchestration artifacts.

## Prerequisites

- `gh` CLI is authenticated (`gh auth status`)
- `.gh-symphony/context.yaml` exists with field IDs and option IDs

## Column ID Quick Reference

Status Field ID: `PVTSSF_lAHOAPiKdM4BTbVgzhAq-yU`

| Column Name | Role | Option ID |
|-------------|------|-----------|
| Backlog | wait | `f75ad846` |
| Ready | active | `61e4505c` |
| In progress | active | `47fc9ee4` |
| In review | wait | `df73e18b` |
| Done | terminal | `98236657` |

## Operations

### Change Issue Status

Use `gh project item-edit` with the field ID and option ID from the table above:

```bash
# Get the project item ID for an issue
gh project item-list <project-number> --owner <owner> --format json \
  | jq '.items[] | select(.content.number == <issue-number>) | .id'

# Update the status field
gh project item-edit \
  --project-id PVT_kwHOAPiKdM4BTbVg \
  --id <item-id> \
  --field-id PVTSSF_lAHOAPiKdM4BTbVgzhAq-yU \
  --single-select-option-id <option-id-from-table-above>
```

After every actual state transition, leave an issue comment in this exact form:

```bash
gh issue comment <issue-number> --repo <owner>/<repo> \
  --body "## Ready -> In progress"
```

Do not emit the transition comment if the state change did not happen or if the
same transition comment already exists for the current transition event.

### Create Workpad Comment

Create the Workpad once per issue:

```bash
gh issue comment <issue-number> --repo <owner>/<repo> --body "## Workpad\n\n### Plan\n- [ ] Task 1"
```

### Update Existing Comment

Reuse the existing Workpad comment instead of creating a new one:

```bash
gh api -X PATCH /repos/<owner>/<repo>/issues/comments/<comment-id> \
  -f body="## Workpad\n\n### Plan\n- [x] Task 1 (done)"
```

### Find Existing Workpad Comment

Search issue comments first and update the existing Workpad if present:

```bash
gh api /repos/<owner>/<repo>/issues/<issue-number>/comments \
  --paginate \
  | jq '.[] | select(.body | startswith("## Workpad")) | {id, created_at, updated_at}'
```

If the issue returns from `In review` to `Ready`, append follow-up todo items and
notes to that same Workpad comment.

### Leave Per-Turn Progress Comment

After one logical Workpad task is completed and committed, leave an issue comment
describing the completed task, commit SHA, and next target:

```bash
gh issue comment <issue-number> --repo <owner>/<repo> --body "$(cat <<'EOF'
Completed: <workpad task>

Commit: <sha>
Next: <next target>
EOF
)"
```

### Leave PR Follow-Up Summary Comment

When the issue goes back to `In review` after review fixes, summarize the work on
the PR conversation:

```bash
gh pr comment <pr-number> --repo <owner>/<repo> --body "$(cat <<'EOF'
Addressed review feedback:

- <change 1>
- <change 2>

Validation:

- <command/result>
EOF
)"
```

### Create Follow-up Issue

```bash
gh issue create --repo <owner>/<repo> \
  --title "Follow-up: <title>" \
  --body "<description>" \
  --label "backlog"
```

### Add Label

```bash
gh issue edit <issue-number> --repo <owner>/<repo> --add-label "<label>"
```

## Rules

- Always follow the WORKFLOW.md status map flow for state transitions
- Use the Column ID Quick Reference table above for all status transitions
- Treat `Ready` as the first active state. `Backlog` is human-managed; do not start work there.
- Leave an issue comment for every state transition in the format `## From -> To`.
- Maintain exactly one Workpad comment per issue. Reuse it across turns.
- When `In review` returns to `Ready`, update the existing Workpad with new todo items and notes instead of creating a new Workpad.
- Progress one logical Workpad task per turn. After each completed task, commit, hand off to the next turn, and leave an issue comment with the completed task, commit SHA, and next target.
- Create the first PR as draft on the first commit. Reuse the same branch and the same PR for the lifetime of the issue unless a human explicitly resets it.
- Before moving an issue to `In review`, verify as much as possible that the issue requirements and acceptance criteria are satisfied. Use all practical validation methods available.
- When an issue returns from `In review` to `Ready`, inspect actionable PR feedback, including review summaries, unresolved review threads, and inline comments. Reply on the relevant review threads after addressing the feedback.
- When sending an issue back to `In review`, leave a PR comment summarizing the review follow-up changes and validation performed.
- `In review` is a wait state. Pause until a human changes the tracker state again.
- `Done` is human-managed only. A human moves the issue from `In review` to `Done` when the PR is merged.
- Never transition an issue to `Done` from automation.
- All orchestration actions must be idempotent. On re-entry, recover the existing Workpad, PR, branch, and latest transition context before taking action.
- If a blocker prevents further progress, leave an issue comment with the blocker, what was tried, and the exact condition needed to resume.
