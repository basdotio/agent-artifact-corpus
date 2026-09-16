---
allowed-tools: Bash(make codegen:*), Bash(make build:*), Bash(make lint:*), Bash(make test_provider:*), Bash(git status:*), Bash(git diff:*)
description: Validate changes are ready to commit (codegen, build, lint, tests)
---

## Context

- Current git status: !`git status`
- Files changed in provider/: !`git diff --name-only HEAD | grep "^provider/" || echo "none"`

## Your Task

You are validating that code changes are ready to commit. Run these checks in order, stopping if any fail:

### Step 1: Codegen Verification
If ANY files in `provider/*.go` were modified (check the context above), run:
```
make codegen
```
Then run `git status` to verify schema.json and SDK files were regenerated.

### Step 2: Build
```
make build
```

### Step 3: Lint
```
make lint
```

### Step 4: Tests
```
make test_provider
```

### Step 5: Final Status
Run `git status` to show the final state of the worktree.

## Output Format

After all checks complete, provide a summary:

```
READY TO COMMIT
- Codegen: VERIFIED (or SKIPPED if no provider changes)
- Build: PASSED
- Lint: PASSED
- Tests: PASSED (X/X)
```

Or if issues were found:

```
NOT READY - Issues Found
- [Which check failed and why]
- [Command to fix]
```

## Important Notes

- If codegen wasn't needed, note "SKIPPED - no provider/*.go changes"
- If any step fails, stop and report the issue with the fix command
- Provider tests use mocked HTTP - no API token needed
