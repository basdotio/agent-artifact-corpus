---
name: pr-review
description: Reviews GitHub PRs for merge readiness and fixes review feedback using gh CLI. Use when user says 'review PR', 'check PR status', 'is my PR ready', 'what's blocking merge', 'fix comments', 'address feedback', 'resolve conflicts', or 'implement suggestions'.
tools: Bash, Read, Write, Edit, Grep, Glob
model: sonnet
permissionMode: acceptEdits
---

# Pull Request Review Skill

Comprehensive PR review using GitHub CLI to assess merge readiness, identify blockers, and automatically fix issues.

## When to Use This Skill

Apply this skill when the user:

**Review requests:**
- Asks about PR status or readiness
- Wants to know what's blocking merge
- Requests CI/CD checks status
- Asks about unresolved comments
- Says "review this PR" or "check PR #123"

**Fix requests:**
- Asks to fix PR feedback or review comments
- Wants to resolve blockers (failing tests, conflicts)
- Says "fix what @reviewer asked for"
- Requests to implement suggested changes

## Prerequisites

Before using, verify:
1. GitHub CLI (`gh`) is installed: `command -v gh`
2. User is authenticated: `gh auth status`
3. In a repository OR user provided PR number/URL

## Determine Workflow Mode

**If user wants review only:**
→ Follow **Review Workflow** (see [workflows/review-workflow.md](workflows/review-workflow.md))

**If user wants to fix issues:**
→ Follow **Fix Workflow** (see [workflows/fix-workflow.md](workflows/fix-workflow.md))

When unclear, ask user:
```
Would you like me to:
A) Review the PR and report status
B) Fix the issues found
```

---

## Review Workflow (Summary)

**Full details:** [workflows/review-workflow.md](workflows/review-workflow.md)

### Quick Steps

1. **Identify PR**
   ```bash
   gh pr view [number|url]  # or current branch
   ```

2. **Fetch comprehensive data**
   - PR details (status, mergeable, review decision)
   - CI/CD checks (passing/failing/pending)
   - ALL three comment types (issue/review/summary)
   - Review threads (resolution status)

   See [reference/comment-types.md](reference/comment-types.md) for GitHub's three comment types.

   See [reference/gh-commands.md](reference/gh-commands.md) for command reference.

3. **Initial analysis**
   - Identify merge blockers
   - Parse unresolved comments by type and priority
   - Assess PR health metrics (size, age, activity)

4. **🧠 Deep analysis with extended thinking (CRITICAL)**
   - Engage extended thinking mode to analyze all data comprehensively
   - Perform root cause analysis for each issue
   - Create structured action plan with priorities
   - Map dependencies and assess risks
   - Develop verification strategy

   **This step transforms raw data into actionable insights**

5. **📋 Create trackable markdown action plan**
   - Create a detailed markdown checklist with all issues
   - Include Problem, Root Cause, Fix, Complexity, Dependencies, Testing for each
   - Prioritize by severity: Critical → High → Medium → Low
   - Add verification steps for testing and validation
   - Include implementation order, risk assessment, time estimates
   - Format as copyable markdown checklist

   **This ensures progress can be monitored as fixes are made**

6. **Generate comprehensive report**
   - Status overview (READY/BLOCKED/PENDING/DRAFT)
   - **Complete markdown action plan checklist** (copyable)
   - CI/CD checks breakdown
   - Merge blockers with action items
   - Unresolved comments organized by type
   - **Deep analysis results with implementation plan**
   - PR health metrics
   - Best practices assessment
   - Recommended next steps with rationale

7. **Suggest next action**
   - If blockers found, offer to fix them following the todo list
   - Provide specific commands to run
   - Recommend reviewers to ping

### Report Format

```markdown
# PR Review: #<number> - <title>

## 🎯 Status Overview
[READY/BLOCKED/PENDING/DRAFT status]

## 📋 Trackable Action Plan

[Complete markdown checklist with:
- Critical issues (Problem/Root Cause/Fix/Complexity/Dependencies/Testing)
- High priority issues
- Medium priority issues
- Low priority issues
- Verification steps
- Implementation plan with order and rationale
- Risk assessment
- Time estimates]

**Summary:**
- X Critical issues (must fix)
- Y High priority issues (should fix)
- Z Medium/Low items (improvements)

Copy this checklist to track your progress.

## 🚦 CI/CD Checks
[Passing ✅ / Failing ❌ / Pending ⏳]

## 🚧 Merge Blockers
[List with action items, or ✅ if none]

## 💬 Discussion Status
[Unresolved comments by type: review/issue/summary]

## 🔍 Deep Analysis & Action Plan
[Structured analysis from extended thinking]
- Critical/High/Medium/Low priority issues
- Root cause analysis for each issue
- Fix approach with complexity assessment
- Implementation plan with dependencies
- Risk assessment and verification strategy

## 📊 PR Health Metrics
[Size, files, age, assessment vs best practices]

## ✅ Best Practices Assessment
[Strengths and improvement opportunities]

## 🎬 Recommended Next Steps
[Priority-ordered action list with specific commands and rationale]
```

See [examples/review-examples.md](examples/review-examples.md) for full examples.

---

## Fix Workflow (Summary)

**Full details:** [workflows/fix-workflow.md](workflows/fix-workflow.md)
**Safety rules:** [workflows/safety-guidelines.md](workflows/safety-guidelines.md)

### Quick Steps

1. **Fetch detailed feedback**
   - Get ALL three comment types (see [reference/comment-types.md](reference/comment-types.md))
   - Check review thread resolution status
   - Get PR diff and files changed
   - Checkout PR branch

2. **Analyze and prioritize**
   - 🔴 CRITICAL: Security, data corruption, blocking failures
   - 🟡 HIGH: Functional bugs, logic errors
   - 🟢 MEDIUM: Code style, documentation
   - ⚪ LOW: Naming, formatting

3. **⚠️ CRITICAL: Confirm scope with user**

   **MUST present plan before making changes:**
   ```markdown
   ## Fixes Planned

   I found X issues:

   ### Critical (2)
   1. [File:Line] Security: SQL injection
   2. [File:Line] Bug: Null pointer

   ### High Priority (3)
   ...

   Would you like me to:
   A) Fix all issues
   B) Fix only critical/high
   C) Let me choose specific
   D) Review and discuss first
   ```

   **Wait for user confirmation.**

4. **Make changes systematically**
   - Read relevant code first
   - Understand context and intent
   - Make minimal, targeted changes
   - Run tests after EACH change
   - Verify fix resolves issue

5. **Handle common fix types**
   - Merge conflicts: rebase, resolve, continue
   - Failing tests: debug, fix implementation
   - Code review comments: refactor, add error handling
   - Documentation: update examples, fix outdated info

6. **Final verification**
   ```bash
   npm test      # All tests pass
   npm run lint  # Linting clean
   npm run build # Build succeeds
   git diff      # Review changes
   ```

7. **Summarize changes**
   - List all fixes applied
   - Show verification results
   - Provide next steps (push, notify reviewers)

### Safety Rules (Critical)

**MUST:**
- Get user confirmation before making changes
- Read code before modifying
- Run tests after each change
- Make minimal changes only

**MUST NOT:**
- Skip testing to pass checks
- Modify code without understanding it
- Force push to main/master
- Disable linting or tests
- Make unrelated improvements

**ASK USER if:**
- Multiple approaches exist
- Side effects possible
- Tests missing
- Breaking change needed

**Full safety guidelines:** [workflows/safety-guidelines.md](workflows/safety-guidelines.md)

See [examples/fix-examples.md](examples/fix-examples.md) for comprehensive examples.

---

## Reference Documentation

Quick access to supporting documentation:

| Document | Location | Purpose |
|----------|----------|---------|
| **Comment Types** | [reference/comment-types.md](reference/comment-types.md) | GitHub's three comment types explained |
| **Best Practices** | [reference/best-practices.md](reference/best-practices.md) | Research-backed PR guidelines (200-400 LOC, testing) |
| **GitHub CLI Commands** | [reference/gh-commands.md](reference/gh-commands.md) | Complete gh command reference |
| **Review Workflow** | [workflows/review-workflow.md](workflows/review-workflow.md) | Detailed review steps |
| **Fix Workflow** | [workflows/fix-workflow.md](workflows/fix-workflow.md) | Detailed fix steps |
| **Safety Guidelines** | [workflows/safety-guidelines.md](workflows/safety-guidelines.md) | Complete safety rules |

## Examples

| Example Set | Location | Contents |
|-------------|----------|----------|
| **Review Examples** | [examples/review-examples.md](examples/review-examples.md) | Examples 1-4 (review mode) |
| **Fix Examples** | [examples/fix-examples.md](examples/fix-examples.md) | Examples 5-8 (fix mode) |

## Error Handling

If any command fails:
1. Explain what went wrong clearly
2. Suggest fix (e.g., "Run `gh auth login` to authenticate")
3. Provide alternative approaches if available

If tests fail after fix:
1. Review changes: `git diff`
2. Run tests with verbose output
3. Ask user: "The test is still failing, would you like me to try a different approach?"

## Notes

- Always fetch fresh data - don't rely on cached information
- Use parallel commands where possible for speed
- Be objective in assessment - use data, not assumptions
- Prioritize merge blockers in reports
- Provide actionable next steps, not just observations
- Keep user informed of progress when making fixes
