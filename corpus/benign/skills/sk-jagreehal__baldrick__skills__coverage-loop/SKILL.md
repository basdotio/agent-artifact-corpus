---
name: coverage-loop
description: "Iteratively improve test coverage until target is reached. Use when: improve coverage, test coverage, coverage target, baldrick coverage. Triggers on: coverage, test coverage, coverage loop."
---

# Coverage Loop

Iteratively write tests until a target coverage percentage is reached.

> **Philosophy:** Meaningful coverage over hitting numbers. Test business logic first.

---

## The Job

1. Receive target coverage percentage from user
2. Run coverage command to check current state
3. Identify most critical uncovered code paths
4. Write tests for ONE uncovered area per iteration
5. Verify coverage improved
6. Repeat until target reached

---

## Iteration Flow

```
┌─────────────────────────────────────────────────┐
│ 1. Run coverage command                         │
│ 2. Check current percentage vs target           │
│ 3. If target reached → COMPLETE                 │
│ 4. Identify highest-value uncovered code        │
│ 5. Write test for ONE uncovered area            │
│ 6. Run coverage again to verify                 │
│ 7. Append progress to progress.txt              │
│ 8. Loop back to step 1                          │
└─────────────────────────────────────────────────┘
```

---

## Priority Order for Coverage

Focus on coverage in this order:

1. **Business logic** - Core application functionality
2. **Error handling** - Catch blocks, validation
3. **Edge cases** - Boundary conditions
4. **Utilities** - Helper functions
5. **UI logic** - Component behavior (not rendering)

**Skip:**
- Generated code
- Type definitions
- Configuration files
- Simple getters/setters

---

## Progress Format

Append to progress.txt after each iteration:

```
## Coverage Loop - [Date/Time]
- Before: 65%
- After: 68%
- Added: Test for `validateEmail()` in `src/utils/validation.ts`
- Focus: Business logic validation
---
```

---

## Stop Condition

When coverage reaches target percentage:
1. Output: `<promise>COMPLETE</promise>`

If stuck after multiple iterations:
1. Note why in progress.txt
2. Output: `<promise>BLOCKED</promise>` with explanation

---

## Example Usage

User: "Run coverage loop to 80%"

The skill will:
1. Check current coverage (e.g., 65%)
2. Write tests until 80% is reached
3. Report progress after each iteration

---

## Checklist Per Iteration

- [ ] Ran coverage command
- [ ] Identified most valuable uncovered code
- [ ] Wrote test for ONE area (not multiple)
- [ ] Verified test passes
- [ ] Verified coverage increased
- [ ] Updated progress.txt with before/after
