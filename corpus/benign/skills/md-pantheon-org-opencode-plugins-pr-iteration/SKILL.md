---
name: pr-iteration
description:
  Guide the agent through iterative PR/MR refinement to ensure all CI checks, tests, linting, and validation passes
  before considering the work complete. Never declare success until all automated checks pass.
license: MIT
compatibility: opencode
metadata:
  category: workflow
  tool: git
---

## What I Do

I ensure that all Pull Requests (PRs) or Merge Requests (MRs) pass **every automated check** before being declared
complete. I guide the agent through iterative refinement until CI is green.

## Core Principles

1. **Iterate until all checks pass** - Never declare "done" while any check is failing
2. **Run checks locally first** - Fix issues locally before pushing to avoid CI noise
3. **Address cascading failures systematically** - Fix one category at a time (lint → typecheck → test → build)
4. **Commit incremental fixes** - Save progress as you fix issues, don't batch all fixes into one commit
5. **Verify after each fix** - Re-run the failed check to confirm it's resolved

## When to Use Me

- Creating a new PR/MR from scratch
- Addressing CI failures on an existing PR/MR
- Refactoring code that affects multiple packages
- Adding features that require cross-package changes
- Merging dependent PRs in sequence

## Iteration Workflow

### Phase 1: Pre-Flight Checks (Before Creating PR)

```bash
# 1. Install dependencies
bun install

# 2. Run linting
bun run lint

# 3. Run type checking
bun run typecheck

# 4. Run tests
bun run test

# 5. Run build
bun run build
```

**If any check fails → FIX IT before proceeding**

### Phase 2: PR Creation & Initial Validation

After creating PR/MR:

```bash
# 1. Verify all checks pass locally
bun run lint && bun run typecheck && bun run test && bun run build

# 2. Push and wait for CI

# 3. Monitor CI results
```

### Phase 3: Iterative Fix Loop

**While any check is failing:**

```
CHECK → FAIL → FIX → COMMIT → PUSH → RE-CHECK → (REPEAT UNTIL PASS)
```

**Priority order for fixing failures:**

1. **Linting errors** (formatting, style) - Usually quickest to fix
2. **Type errors** - May require interface changes
3. **Test failures** - Logic bugs or test updates needed
4. **Build failures** - Often the most complex

### Phase 4: Final Verification

```bash
# Run full check suite one more time
bun run lint
bun run typecheck
bun run test
bun run build
```

**Only declare PR ready when ALL checks pass.**

## Common Failure Patterns & Fixes

### Pattern 1: Linting Failures

**Symptom**: CI fails on `bun run lint` or biome/eslint errors

**Fix Process**:

```bash
# Run auto-fix first
bun run lint --fix
# or
biome check --write .

# If manual fixes needed, address each error
# Re-run lint to verify
bun run lint
```

**Iterate until**: `bun run lint` exits 0

### Pattern 2: Type Errors

**Symptom**: `bun run typecheck` or `tsc` fails

**Fix Process**:

```bash
# Run type check
bun run typecheck

# Fix each error:
# - Add missing types
# - Fix interface mismatches
# - Update imports

# Re-run typecheck
bun run typecheck
```

**Iterate until**: `bun run typecheck` exits 0

### Pattern 3: Test Failures

**Symptom**: Tests fail locally or in CI

**Fix Process**:

```bash
# Run failing test
bun test path/to/failing-test.ts

# Debug and fix
# - Check test expectations
# - Verify mock setup
# - Review logic changes

# Re-run test
bun test path/to/failing-test.ts

# Run full test suite
bun run test
```

**Iterate until**: All tests pass

### Pattern 4: Build Failures

**Symptom**: `bun run build` or `nx build` fails

**Fix Process**:

```bash
# Run build with verbose output
bunx nx run-many --target=build --all --verbose

# Identify failing package
# Check error message

# Common causes:
# - Missing dependencies in package.json
# - Import errors
# - TypeScript compilation errors

# Fix issue
# Re-run build
bun run build
```

**Iterate until**: Build succeeds

### Pattern 5: Cross-Package Failures

**Symptom**: Changes in one package break another

**Fix Process**:

```bash
# Identify affected packages
bunx nx affected:graph

# Build dependency graph first
bunx nx run-many --target=build --projects=dependency-package

# Then build dependent
bunx nx run-many --target=build --projects=dependent-package

# Run tests on affected packages
bunx nx affected:test
```

**Iterate until**: All affected packages build and test successfully

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Validate PR
on: [pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v1

      - name: Install
        run: bun install

      - name: Lint
        run: bun run lint

      - name: Type Check
        run: bun run typecheck

      - name: Test
        run: bun run test

      - name: Build
        run: bun run build
```

### Required Status Checks

Configure branch protection to require:

- ✅ Lint passing
- ✅ Type check passing
- ✅ Tests passing
- ✅ Build passing

**No PR should be mergeable until all checks pass.**

## Debugging CI Failures

### Step 1: Replicate Locally

```bash
# Run the exact command that failed in CI
# (Check your workflow file for the command)
biome ci --reporter=github --diagnostic-level=error . --verbose

# Compare results
```

### Step 2: Check Environment Differences

Common differences:

- **Node/Bun version** - Match CI version exactly
- **Operating system** - CI runs Linux; develop on Linux/macOS/WSL
- **Clean state** - CI starts fresh; you may have cached files

```bash
# Clean and reinstall
rm -rf node_modules bun.lockb
bun install

# Re-run checks
```

### Step 3: Fix and Verify

```bash
# Fix the issue

# Verify locally
bun run lint && bun run typecheck && bun run test && bun run build

# Commit and push
git add .
git commit -m "fix: resolve CI failures"
git push
```

### Step 4: Monitor CI

- Watch CI logs for new failures
- Repeat fix loop if needed

## Multi-PR Dependency Management

When merging PRs with dependencies (e.g., PR B depends on PR A):

### Step 1: Merge Base PR First

```bash
# Merge PR A
git checkout main
git merge feat/pr-a

# Verify CI passes on main
```

### Step 2: Rebase Dependent PR

```bash
# PR B branch
git checkout feat/pr-b
git rebase main

# Re-run all checks
bun run lint && bun run typecheck && bun run test && bun run build

# Push rebased branch
git push --force-with-lease
```

### Step 3: Iterate Until Green

If checks fail after rebase:

```
FAIL → ANALYZE (conflicts? dependency changes?) → FIX → PUSH → RE-CHECK
```

**Dependencies may introduce breaking changes requiring fixes in dependent PR.**

## Commit Strategy During Iteration

### Incremental Commits

Save progress as you fix issues:

```bash
# Fix lint errors
git add .
git commit -m "style: fix linting errors"

# Fix type errors
git add .
git commit -m "fix: resolve type errors"

# Fix tests
git add .
git commit -m "test: update failing tests"
```

### Squash Before Merge (Optional)

If you prefer clean history:

```bash
# After all checks pass
git rebase -i main
# Squash fix commits
```

## Emergency Recovery

### CI is completely broken

```bash
# 1. Check if it's a configuration issue
cat package.json | grep -A 5 '"scripts"'

# 2. Verify tools are installed
bunx biome --version
bunx tsc --version

# 3. Check for environment issues
echo $NODE_VERSION
echo $BUN_VERSION

# 4. Clean slate
rm -rf node_modules bun.lockb
bun install

# 5. Re-run checks
```

### Infinite fix loop

If you keep fixing and CI keeps failing:

1. **Take a break** - Step away, review with fresh eyes
2. **Check CI logs carefully** - Read the full error message
3. **Run exact CI command locally** - Don't assume your command is equivalent
4. **Ask for help** - Sometimes a second pair of eyes helps

## Success Criteria

A PR is **ONLY** ready when:

- ✅ `bun run lint` passes (0 errors, 0 warnings)
- ✅ `bun run typecheck` passes (0 type errors)
- ✅ `bun run test` passes (all tests green)
- ✅ `bun run build` passes (all packages build)
- ✅ CI pipeline is green
- ✅ No merge conflicts with target branch

**If any check fails → CONTINUE ITERATING**

## Remember

✅ **DO**:

- Run checks locally before pushing
- Fix one category at a time
- Commit incremental fixes
- Verify after each fix
- Monitor CI after every push
- Rebase dependent PRs after base PR merges

❌ **NEVER**:

- Declare PR ready with failing checks
- Ignore CI failures
- Batch all fixes into one giant commit
- Skip local verification and rely on CI
- Merge with "will fix later" mentality

## Quick Reference

```bash
# Full validation suite
bun run lint && bun run typecheck && bun run test && bun run build

# Fix linting
bun run lint --fix

# Fix types
bun run typecheck  # then fix errors manually

# Run specific test
bun test path/to/test.ts

# Build specific package
bunx nx run package-name:build
```
