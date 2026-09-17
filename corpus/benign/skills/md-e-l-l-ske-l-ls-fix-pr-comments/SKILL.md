---
name: fix-pr-comments
description: Fetch unresolved inline PR review comments and address them directly. Use when the user wants to fix, address, or resolve PR review feedback automatically.
disable-model-invocation: true
---

# Fix PR Comments

Automatically address unresolved inline review comments on the current branch's pull request.

## Unresolved PR Comments

!`${CLAUDE_SKILL_DIR}/scripts/fetch-comments.sh`

## Instructions

### Step 1 — Parse and validate

Parse the JSON above. It contains unresolved inline review comments grouped by thread.

**If the output starts with `ERROR:`**, stop and show the error to the user. Common issues:
- No PR for current branch — user needs to push and create a PR first
- `gh` not installed or not authenticated — direct user to `gh auth login`

**If the JSON is an empty array `[]`**, inform the user there are no unresolved comments and stop.

### Step 2 — Group comments by file

Group the comment threads by their `path` field.

Build a mapping:
```
file_path → [{ line, comments: [{ author, body }] }, ...]
```

### Step 3 — Address comments

Process each file's comments. For each comment thread:

1. **Read the file** at the given path to understand the current code.
2. **Classify the comment** as one of:
   - **Actionable**: A request to change code (refactor, rename, fix bug, add handling, use a constant, etc.)
   - **Non-actionable**: A question, praise, discussion point, or FYI that doesn't require a code change
3. **For actionable comments**: Use the Edit tool to apply the fix. Make minimal, targeted changes — fix exactly what the reviewer asked for, nothing more.
4. **For non-actionable comments**: Skip and note the reason.
5. **If you cannot determine what change is needed**: Do not guess. Mark as unresolved with an explanation.

Track results per file in this structure:

```
FILE: <file_path>

FIXED:
- Line <N>: <one-line description of what was changed> (requested by @<author>)

SKIPPED:
- Line <N>: <reason> (comment by @<author>)

UNRESOLVED:
- Line <N>: <why it couldn't be resolved> (requested by @<author>)
```

If a category is empty, omit it.

### Step 4 — Present summary

After all comments are processed, present the results:

```
## PR Comments Addressed

### <file_path>
- Fixed: <count>
  - Line <N>: <description>
- Skipped: <count> (non-actionable)
- Unresolved: <count>
  - Line <N>: <reason>

### <file_path>
...

---
Total: <X> fixed, <Y> skipped, <Z> unresolved across <N> files
```
