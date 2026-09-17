---
name: error-triage
description: Diagnose and minimally fix failing notebook cells. Reads the failing cell, inspects the error output, checks dependencies, applies the smallest fix, and reruns only what is needed.
license: MIT
compatibility: opencode, claude-code, codex
metadata:
  audience: data-scientists
  workflow: debugging
---

## What I do

I diagnose and fix errors in Jupyter notebook cells with minimal disruption. I:

1. Read the failing cell
2. Extract the traceback summary
3. Check upstream dependencies for context
4. Apply the smallest correct fix
5. Rerun only the necessary cells to validate

## When to use me

- "Fix this error"
- "Why is this cell failing?"
- "Debug cell 5"
- "What's wrong with this notebook?"

## How I work

### Step 1: Read the Failing Cell

```bash
notebook-tools read-cells --notebook <path> --index <N> --pretty
```

### Step 2: Get the Error Output

```bash
notebook-tools cell-output --notebook <path> --index <N> --pretty
```

This returns a structured traceback summary, not raw JSON.

### Step 3: Check Upstream Dependencies

```bash
notebook-tools get-dependencies --notebook <path> --index <N> --mode upstream --pretty
```

This identifies which cells the failing cell depends on.

### Step 4: Read Context (if needed)

Only read upstream cells that are directly relevant to the error:

```bash
notebook-tools read-cells --notebook <path> --index <M> --summary-mode compact --pretty
```

### Step 5: Apply the Fix

```bash
notebook-tools edit-cell --notebook <path> --index <N> --edit-mode replace --content "<fixed-code>"
```

### Step 6: Validate

Run the smallest valid slice to verify:

```bash
notebook-tools run-cells --notebook <path> --index <N> --pretty
```

If the fix depends on upstream state, include dependencies:

```bash
notebook-tools run-cells --notebook <path> --index <M> --index <N> --pretty
```

### Step 7: Report

Report:
- Root cause of the error
- The fix applied
- Cells read, changed, and run
- Whether the fix was validated
- Any remaining risks (e.g., hidden state dependency)

## Rules

- Always read the error output before guessing the cause
- Check upstream dependencies before proposing a fix
- Apply the smallest possible change
- Rerun the minimum cells needed to validate
- If the fix may depend on hidden state, say so explicitly
- In file-only mode, recommend live validation if the fix is not trustworthy

## Confirmation Required

If the fix involves deleting cells or restructuring the notebook, ask for confirmation first.

## Dependencies

Requires `notebook-tools` CLI. Live validation requires `ipykernel` and `jupyter_client`.
