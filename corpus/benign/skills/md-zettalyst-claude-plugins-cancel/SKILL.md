---
name: cancel
description: Cancel active clarify loop
---

# Cancel Clarify Loop

When this skill is invoked, cancel the active clarification loop by:

1. Delete the state file: `.claude/clarify.local.md`
2. Confirm cancellation to the user

Execute:
```bash
rm -f .claude/clarify.local.md
```

Then inform the user:
```
Clarify loop cancelled.

You can start a new loop with /clarify.
```
