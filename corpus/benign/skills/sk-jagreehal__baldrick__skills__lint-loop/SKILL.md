---
name: lint-loop
description: "Iteratively fix all linting errors until clean. Use when: fix lint, lint errors, lint loop, baldrick lint-fix. Triggers on: lint, fix lint, lint errors, lint loop."
---

# Lint Fix Loop

Iteratively fix linting errors until the codebase is clean.

> **Philosophy:** Fix errors properly, don't suppress them. Understand why the rule exists.

---

## The Job

1. Run lint command to see all errors
2. Fix ONE error at a time
3. Run lint again to verify fix didn't break anything
4. Repeat until zero errors

---

## Iteration Flow

```
┌─────────────────────────────────────────────────┐
│ 1. Run lint command                             │
│ 2. If zero errors → COMPLETE                    │
│ 3. Pick ONE error to fix                        │
│ 4. Understand why the rule exists               │
│ 5. Fix the error properly                       │
│ 6. Run lint again to verify                     │
│ 7. Loop back to step 1                          │
└─────────────────────────────────────────────────┘
```

---

## Fix Priority

Fix errors in this order:

1. **Type errors** - These often cause other errors
2. **Import errors** - Missing/wrong imports
3. **Unused variables** - Dead code
4. **Style errors** - Formatting, naming
5. **Complexity warnings** - Refactoring needed

---

## Fixing Guidelines

**DO:**
- Understand why the lint rule exists
- Fix the root cause
- Check if the fix is consistent with codebase patterns
- Run tests after fixing

**DON'T:**
- Add `// eslint-disable` comments (except for rare valid cases)
- Suppress errors without understanding them
- Make changes that break functionality

---

## Stop Condition

When lint command returns zero errors:
1. Output: `<promise>COMPLETE</promise>`

If stuck on an error:
1. Note why in progress.txt
2. If it's a false positive, document and disable with comment
3. If truly blocked, output: `<promise>BLOCKED</promise>`

---

## Example Usage

User: "Fix all lint errors"

The skill will:
1. Run lint command
2. Fix errors one by one
3. Report when all errors are fixed

---

## Checklist Per Iteration

- [ ] Ran lint command
- [ ] Identified ONE error to fix
- [ ] Understood why the rule exists
- [ ] Fixed the error properly (not suppressed)
- [ ] Verified fix with another lint run
- [ ] Verified tests still pass
