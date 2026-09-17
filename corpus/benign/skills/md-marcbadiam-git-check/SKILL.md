---
name: git-check
description: Comprehensive git workflow that validates changes before commit. Use when asked to commit, push, review changes, check for errors, or when finishing work. Performs linting, type checking, testing, and secret scanning before allowing commits. Auto-generates commit messages from diffs and confirms before pushing.
---

# Git Check

Validates code changes and manages git commit/push workflow with safety checks.

## Overview

This skill ensures code quality before commits by running:
- Linter checks (ESLint, Pylint, etc.)
- TypeScript/build verification
- Test suite execution
- Secret/credential scanning
- Change review and confirmation

## Workflow

### 1. Check Current State

```bash
# Get current status
git status

# View staged and unstaged changes
git diff HEAD
```

If no changes detected, inform user and exit.

### 2. Run Validation Checks

**Always run these checks in parallel:**

```bash
# Linter check (adjust command for project)
npm run lint || yarn lint || pnpm lint

# Type check / build verification
npm run type-check || npm run build --dry-run || tsc --noEmit

# Test suite
npm test || yarn test || pnpm test
```

**For secret scanning**, check for patterns:
- API keys, tokens, passwords in code
- `.env` files accidentally staged
- Private keys, certificates
- Database credentials

See `references/secret-patterns.md` for common patterns to detect.

### 3. Handle Inconsistencies

**If any check fails:**

1. **Stop and report** all errors clearly
2. **Show specific errors** with file locations
3. **Ask user how to proceed:**
   - Fix issues and retry
   - Skip specific checks (with confirmation)
   - Abort commit

Example message:
```
❌ Validation failed:

**Linting errors:**
- src/api.ts:42 - 'response' is defined but never used
- src/utils.ts:15 - Missing semicolon

**Test failures:**
- 2 tests failed in auth.test.ts

How would you like to proceed?
- Fix these issues
- Skip linting and continue
- Abort commit
```

### 4. Review Changes

If all checks pass, show summary:

```bash
# Show concise diff summary
git diff --stat HEAD

# List affected files
git diff --name-only HEAD
```

Ask user to confirm these are the intended changes.

### 5. Generate Commit Message

**Auto-generate from diff:**

```bash
# Analyze changes
git diff --cached --stat
git log --oneline -5  # Match existing style
```

Generate message following these patterns:
- If adding features: `Add <feature description>`
- If fixing bugs: `Fix <bug description>`
- If refactoring: `Refactor <component>`
- If updating deps: `Update <dependency>`
- If docs: `Document <topic>`

**Example messages:**
```
Add user authentication with JWT tokens

Fix null pointer exception in payment processor

Refactor database connection pooling

Update React to v18.2.0
```

**Show generated message to user for approval/editing.**

### 6. Stage and Commit

```bash
# Stage all changes (or specific files if requested)
git add .

# Commit with approved message
git commit -m "<message>"
```

### 7. Push Confirmation

After successful commit, ask:
```
✓ Commit created successfully

Push to remote? [y/n]
```

If yes:
```bash
# Check if branch has upstream
git rev-parse --abbrev-ref --symbolic-full-name @{u}

# Push with appropriate flags
git push || git push -u origin $(git branch --show-current)
```

## Guidelines

### Safety Rules

- **Never force push** without explicit user confirmation
- **Never skip hooks** (--no-verify) unless user explicitly requests
- **Never commit secrets** - always block and warn
- **Never amend pushed commits** without warning about force push requirement
- **Always show what will be committed** before committing

### Error Handling

- Run checks in parallel for speed
- Report all errors at once (don't stop at first)
- Provide actionable error messages
- Suggest fixes when obvious

### Commit Message Style

- Imperative mood ("Add feature" not "Added feature")
- No period at end of subject line
- 50 chars or less for subject
- Blank line between subject and body
- Wrap body at 72 characters
- Reference issues if applicable (#123)

### Check Adaptation

Detect and use appropriate commands for the project:
- **Node.js**: npm/yarn/pnpm
- **Python**: pytest, pylint, mypy
- **Rust**: cargo test, cargo clippy
- **Go**: go test, go vet
- **Other**: Look for scripts in package.json, Makefile, etc.

## Examples

### Example 1: Clean Commit Flow

```
User: "Commit my changes"

1. ✓ Git status: 3 modified files
2. ✓ Linting: No errors
3. ✓ Type check: Passed
4. ✓ Tests: 42 passed
5. ✓ Secrets: None detected

Changes to commit:
  src/auth.ts      +45 -12
  src/api.ts       +23 -8
  tests/auth.test  +31 -4

Generated message:
  "Add OAuth2 authentication flow"

Commit with this message? [Y/n/edit]
> Y

✓ Committed: abc1234

Push to origin? [y/N]
> y

✓ Pushed to origin/main
```

### Example 2: Handling Failures

```
User: "Commit these changes"

1. ✓ Git status: 2 modified files
2. ❌ Linting: 3 errors
3. ⏭ Type check: Skipped (lint failed)
4. ⏭ Tests: Skipped (lint failed)
5. ⏭ Secrets: Skipped (lint failed)

❌ Linting errors found:

  src/api.ts:15 - Unexpected console statement
  src/api.ts:23 - Missing return type
  src/utils.ts:8 - Unused variable 'temp'

How to proceed?
1. Fix these issues first
2. Skip linting and commit anyway
3. Review the errors in detail
4. Abort

> 1

Okay, please fix the linting errors and try again.
```

### Example 3: Secret Detection

```
User: "Commit my work"

1. ✓ Git status: 1 modified file
2. ✓ Linting: Passed
3. ✓ Type check: Passed
4. ✓ Tests: Passed
5. ❌ Secrets: BLOCKED

🚨 Secret detected in src/config.ts:

  Line 42: API_KEY = "sk-live-abc123..."
  This looks like a production API key!

This MUST be removed or moved to environment variables
before committing.

How to proceed?
1. I'll fix it (abort commit)
2. This is a test key, commit anyway
3. Show me the full context

> 1

Commit aborted. Please remove the secret and try again.
```

## Edge Cases

### No Tests Configured
If no test command found, skip with warning: "No test suite detected, skipping tests"

### Merge Conflicts
If merge conflicts exist:
1. Stop immediately
2. List conflicted files
3. Instruct user to resolve before committing

### Detached HEAD
Warn user and ask for confirmation before committing in detached HEAD state.

### Large Diffs
If diff exceeds 1000 lines:
1. Show summary statistics only
2. Warn about large commit
3. Ask if user wants to review full diff or split into multiple commits
