---
name: rewrite-and-clean
description: Reimplement a messy git branch with clean, narrative-quality commit history suitable for code review. Use when a branch has WIP commits, debug commits, or trial-and-error history that needs to be transformed into a reviewable story before creating a PR.
---

# Rewrite and Clean

Transform a messy development branch into a clean branch with narrative-quality git history that tells reviewers the "what" and "why" without the trial-and-error.

## Quick Start

**Current state:** Your feature branch has 20+ commits of WIP, fixes, reverts, and debugging.

**Outcome:** A new `-clean` branch with 3-5 logical commits that tell a clear implementation story.

```bash
# You're on feature/auth-system with messy history
git log --oneline  # Shows: WIP, fix typo, revert, debug, etc.

# This skill helps you create feature/auth-system-clean with:
# - Commit 1: Add authentication infrastructure
# - Commit 2: Implement login and registration
# - Commit 3: Add comprehensive auth tests
```

## When to Use This

- **Before code review:** Your branch works but the commit history is chaotic
- **After exploration:** You tried multiple approaches and want to show the final path
- **For documentation:** Your team values git history as a learning resource
- **Tutorial-quality history:** Each commit should be understandable in isolation

## Workflow

### Step 1: Validate Source Branch

Before starting, ensure your current branch is in good shape:

```bash
# Check for uncommitted changes
git status

# Check you're up to date with main
git fetch origin main
git log HEAD..origin/main  # Should be empty or you need to rebase

# Verify no merge conflicts
git merge-base --is-ancestor origin/main HEAD
```

**Requirements:**
- No uncommitted changes
- No merge conflicts
- Up to date with `main` (or you know why it's not)

### Step 2: Analyze the Diff

Understand the complete scope of changes:

```bash
# See all changes from main
git diff main...HEAD

# Get file-level overview
git diff --stat main...HEAD

# Review commit history to understand the journey
git log main..HEAD --oneline
```

**Goal:** Form a mental model of what the final state should be and how to logically build toward it.

### Step 3: Create Clean Branch

Create the new branch from your current position:

```bash
# If on feature/auth-system, creates feature/auth-system-clean
CURRENT_BRANCH=$(git branch --show-current)
git checkout -b "${CURRENT_BRANCH}-clean"
```

**Naming convention:** `{original-branch-name}-clean`

### Step 4: Plan the Commit Storyline

Break down the implementation into logical stages. Each commit should:

- Introduce a **single coherent idea**
- Be **self-contained** (explains one concept)
- Build on previous commits **incrementally**
- Read like **tutorial steps**, not development chaos

**Example planning:**

```markdown
Storyline for auth-system-clean:

1. Add database schema and models for users
   - Why: Foundation for authentication
   - Files: migrations/, models/user.ts

2. Implement authentication endpoints
   - Why: Core login/register functionality
   - Files: routes/auth.ts, middleware/auth.ts

3. Add JWT token handling
   - Why: Session management
   - Files: lib/jwt.ts, middleware/verify-token.ts

4. Add rate limiting and security
   - Why: Protect against abuse
   - Files: middleware/rate-limit.ts

5. Add comprehensive tests
   - Why: Ensure reliability
   - Files: tests/auth.test.ts
```

### Step 5: Reimplement the Work

Reset to `main` and recreate changes commit by commit:

```bash
# Reset the clean branch to main (keeps working directory)
git reset --soft $(git merge-base main HEAD)

# Now stage and commit according to your plan
git add migrations/ models/user.ts
git commit -m "Add database schema for user authentication

- Create users table with email, password_hash, created_at
- Add User model with password hashing utilities
- Include migration for initial schema"

# Continue for each planned commit...
```

**Commit message guidelines:**

```
<type>: <short summary>

<detailed explanation of what and why>

- Bullet point details
- Additional context
- Related considerations
```

**Each commit must:**
- Have a clear, descriptive message
- Include body text explaining WHY (not just what)
- Reference relevant issues/docs if applicable
- Add inline comments in code where intent isn't obvious

### Step 6: Verify Correctness

The final state must exactly match the original branch:

```bash
# Compare the final trees
ORIGINAL_BRANCH="${CURRENT_BRANCH%-clean}"  # Remove -clean suffix
git diff $ORIGINAL_BRANCH..$CURRENT_BRANCH-clean

# Should output: (nothing)
# Any differences mean you missed something
```

**Critical:** The `-clean` branch must produce identical code to the original branch, just with cleaner history.

**About `--no-verify`:**
- Individual commits don't need to pass all tests
- Use `--no-verify` sparingly for known issues
- Final commit MUST pass all checks
- If you need `--no-verify` often, your commit breakdown may be wrong

### Step 7: Open Pull Request

Create PR from clean branch:

```bash
# Push the clean branch
git push -u origin $CURRENT_BRANCH-clean

# Create PR using GitHub CLI
gh pr create --base main --head $CURRENT_BRANCH-clean
```

**PR description must include:**
- Link to original branch
- Explanation of why history was rewritten
- Confirmation that final state is identical

**Example PR template:**

```markdown
## Summary
[Description of what this feature does]

## Implementation
This PR contains a clean commit history for reviewer comprehension.

- Original branch: #123 or `feature/auth-system`
- Commits restructured from 24 → 5 for narrative clarity
- Final state verified identical to original branch

## Commits
1. Add database schema for user authentication
2. Implement authentication endpoints
3. Add JWT token handling
4. Add rate limiting and security
5. Add comprehensive tests

## Testing
[How to test this PR]
```

## Guidelines

### ✅ Do

- Create commits that build on each other incrementally
- Write commit messages that explain WHY, not just what
- Add code comments where intent isn't obvious
- Verify final state matches original exactly
- Keep commit messages professional and clear
- Reference the original branch in the PR

### ❌ Don't

- Add yourself as author/contributor on commits
- Include attribution lines like "🤖 Generated with Claude Code"
- Include co-author tags like "Co-Authored-By: Claude Sonnet"
- Change any functionality from the original branch
- Make commits that depend on future commits to work
- Use `--no-verify` unless truly necessary

### Commit Message Anti-Patterns

**Bad:**
```
WIP
fix
update
refactor
clean up
```

**Good:**
```
Add user authentication endpoint

Implements login and registration routes with bcrypt password
hashing and JWT token generation. Includes rate limiting to
prevent brute force attacks.
```

## Examples

### Example 1: Feature Branch with Trial and Error

**Original branch (18 commits):**
```
a1b2c3d WIP: trying auth
d4e5f6g fix typo
g7h8i9j actually implement login
j0k1l2m add register
m3n4o5p fix lint errors
p6q7r8s remove console.logs
s9t0u1v add tests
v2w3x4y fix failing test
y5z6a7b update test
b8c9d0e refactor
e1f2g3h final cleanup
```

**Clean branch (4 commits):**
```
Commit 1: Add authentication infrastructure
- Database schema for users
- Password hashing utilities
- JWT configuration

Commit 2: Implement login and registration endpoints
- POST /auth/login with credential validation
- POST /auth/register with email verification
- Rate limiting middleware

Commit 3: Add token refresh mechanism
- Refresh token generation and storage
- Token rotation on refresh
- Expired token cleanup job

Commit 4: Add comprehensive authentication tests
- Unit tests for password hashing
- Integration tests for login/register flows
- Security tests for rate limiting
```

### Example 2: Bug Fix with Investigation

**Original branch (12 commits):**
```
investigate memory leak
add logging
more logging
try fix 1
revert fix 1
try fix 2
it works!
remove debug logging
add test
fix test
update test
cleanup
```

**Clean branch (2 commits):**
```
Commit 1: Fix memory leak in WebSocket connection handler

Root cause: Event listeners were not being removed when connections
closed, causing references to accumulate.

Solution: Add cleanup in disconnect handler to remove all listeners
and clear connection references from the connection pool.

Commit 2: Add test for WebSocket connection cleanup

Verifies that repeated connect/disconnect cycles don't cause
memory accumulation. Checks that connection pool size returns
to zero after all connections close.
```

## Advanced: Automation Tips

### Save Your Storyline Plan

```bash
# Create a commit plan file
cat > /tmp/commit-plan.md << 'EOF'
# Commit Plan for feature-clean

## Commit 1: Foundation
Files: ...
Why: ...

## Commit 2: Core Logic
Files: ...
Why: ...
EOF
```

### Diff-Driven Commits

```bash
# See what files changed
git diff --name-only main...original-branch

# Group by logical component
git diff main...original-branch -- src/auth/ | less
```

### Compare Histories

```bash
# See original commit messages for context
git log main..original-branch --oneline > /tmp/original-history.txt

# Use this to understand what was tried
```

## Troubleshooting

**Q: My clean branch has different behavior than original**

Check:
```bash
git diff original-branch..clean-branch
# Should be empty. Any diff shows missing changes.
```

**Q: Commits depend on each other in wrong order**

Your storyline planning may need adjustment. Consider:
- Can infrastructure commits come first?
- Are you mixing setup + usage in one commit?

**Q: Individual commits don't pass tests**

This is OK if:
- Final commit passes all tests
- Each commit is logically complete
- You're documenting with `--no-verify` why

**Q: Should I squash everything first?**

No! Work from the full diff between main and your branch. Squashing loses information you might need.

## Reference

Original inspiration: [Steve Ruiz's Git History Workflow](https://gist.github.com/steveruizok/0a342344fffd6b7e8e36a0c07770893a)

## Success Criteria

Your clean branch is ready when:

- [ ] Final state exactly matches original branch (`git diff` is empty)
- [ ] Each commit introduces one coherent idea
- [ ] Commit messages explain WHY, not just what
- [ ] Commits build incrementally (earlier commits don't reference later ones)
- [ ] No attribution/co-author/generated-by lines
- [ ] PR includes link to original branch
- [ ] All tests pass on final commit
