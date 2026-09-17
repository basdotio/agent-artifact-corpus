---
name: auto-issue-fixer
description: Automate the complete GitHub issue lifecycle. Fetches all issues, prioritizes by importance and execution speed, implements fixes using TDD, creates PRs, monitors for reviews, handles feedback autonomously, and notifies when complete. Uses extensive subagent parallelization for context efficiency.
triggers:
  - "auto fix issues"
  - "auto fix issue"
  - "process github issues"
  - "fix next issue"
  - "run auto issue fixer"
  - "automate issue fixing"
  - "auto fix issue #"
prerequisites:
  - gh (GitHub CLI, authenticated)
  - git
  - jq (for JSON parsing)
arguments:
  - name: ISSUE_NUMBER
    required: false
    description: Specific issue number to fix (skips discovery/prioritization phase)
  - name: MAX_ISSUES
    required: false
    description: Maximum number of issues to process in one run (default 1, ignored if ISSUE_NUMBER is set)
  - name: LABELS
    required: false
    description: Filter issues by labels (comma-separated, ignored if ISSUE_NUMBER is set)
  - name: EXCLUDE_LABELS
    required: false
    description: Exclude issues with these labels (comma-separated)
  - name: DRY_RUN
    required: false
    description: Analyze and plan without implementing (default false)
  - name: MAX_FEEDBACK_ITERATIONS
    required: false
    description: Maximum rounds of PR feedback to process (default 3)
  - name: REVIEW_TIMEOUT_MINUTES
    required: false
    description: How long to wait for reviews before proceeding (default 30)
  - name: BOT_WAIT_MINUTES
    required: false
    description: Minutes to wait for bot reviews (Copilot, Claude) after CI passes (default 5)
  - name: QUIET_PERIOD_MINUTES
    required: false
    description: Minutes of no new reviews required before marking PR ready (default 3)
  - name: AUTO_MERGE
    required: false
    description: Automatically merge PR when complete (true/false, default false). If true, merges after all reviews addressed. If false, notifies user for manual merge.
---

# Auto Issue Fixer

Fully autonomous GitHub issue lifecycle automation with TDD implementation.

## Overview

**Codex note:** This skill references Claude Code subagents (`Task(...)`). In Codex, run the equivalent steps with tool calls (for example `functions.shell_command` and `multi_tool_use.parallel`) or run them sequentially. See [`../../COMPATIBILITY.md`](../../COMPATIBILITY.md).

This skill runs completely autonomously:
1. Fetches and prioritizes all open issues
2. Selects the highest-priority issue
3. Implements the fix using TDD (Red-Green-Refactor)
4. Creates a PR and requests review
5. Monitors and addresses CI failures and review feedback
6. Notifies the user when ready for final review

**Workflow**: PRs are created immediately to trigger CI and review requests. The skill monitors feedback and addresses it autonomously. When complete, it tags the user for final review and merge.

---

## Single Issue Mode

When `ISSUE_NUMBER` is provided, the skill skips the discovery and prioritization phases and directly processes the specified issue:

```bash
# Example: Fix only issue #1198
/auto-issue-fixer --issue-number 1198

# Or use the dedicated command
/fix-issue 1198
```

**Behavior changes in single issue mode:**
- Phase 1 (Issue Discovery and Prioritization) is **skipped entirely**
- The specified issue is loaded directly
- `MAX_ISSUES` and `LABELS` arguments are ignored
- All other phases (Setup, TDD Implementation, PR, Feedback Loop, Completion) run normally

**Status message for single issue mode:**
```
================================================================================
AUTO-ISSUE-FIXER: STARTING - Processing specified issue #1198
================================================================================
```

---

## Status Output

**IMPORTANT**: Output clear status messages at each stage so the user can follow progress. Use this format:

```
================================================================================
AUTO-ISSUE-FIXER: [PHASE] - [ACTION]
================================================================================
```

### Required Status Messages

Output these messages at each stage:

| Phase | Message |
|-------|---------|
| Start | `AUTO-ISSUE-FIXER: STARTING - Fetching issues from repository` |
| Issues found | `AUTO-ISSUE-FIXER: FOUND {N} ISSUES - Analysing priorities...` |
| Issue selected | `AUTO-ISSUE-FIXER: SELECTED ISSUE #{N} - {title}` |
| Sync | `AUTO-ISSUE-FIXER: SYNCING - Pulling latest from origin/main` |
| Planning | `AUTO-ISSUE-FIXER: PLANNING - Creating TDD implementation plan` |
| RED phase | `AUTO-ISSUE-FIXER: TDD RED - Writing failing tests` |
| GREEN phase | `AUTO-ISSUE-FIXER: TDD GREEN - Implementing to pass tests` |
| REFACTOR phase | `AUTO-ISSUE-FIXER: TDD REFACTOR - Cleaning up implementation` |
| PR created | `AUTO-ISSUE-FIXER: PR CREATED - #{N} {url}` |
| Monitoring | `AUTO-ISSUE-FIXER: MONITORING - Waiting for CI and reviews` |
| Bot wait | `AUTO-ISSUE-FIXER: WAITING - Waiting for bot reviews (Copilot, Claude)` |
| Feedback | `AUTO-ISSUE-FIXER: FEEDBACK - Processing {N} items` |
| Quiet period | `AUTO-ISSUE-FIXER: VERIFYING - Quiet period check ({N} min remaining)` |
| Complete | `AUTO-ISSUE-FIXER: COMPLETE - PR #{N} ready for review` |
| Merging | `AUTO-ISSUE-FIXER: MERGING - Auto-merge enabled, merging PR #{N}` |
| Merged | `AUTO-ISSUE-FIXER: MERGED - PR #{N} merged successfully` |
| No issues | `AUTO-ISSUE-FIXER: NO ISSUES - No actionable issues found` |
| Error | `AUTO-ISSUE-FIXER: ERROR - {description}` |

---

## Phase 1: Issue Discovery and Prioritization

> **Note**: This phase is skipped entirely when `ISSUE_NUMBER` is provided. Jump directly to Phase 2 with the specified issue.

### 1.1 Fetch All Issues

```bash
scripts/list-all-issues.sh [--labels LABELS] [--exclude LABELS]
```

This fetches all open issues with metadata needed for prioritization.

### 1.2 Parallel Complexity Analysis

Launch Explore subagents in parallel (batches of 5 issues) to analyze implementation complexity:

```
Launch parallel Explore agents (one per batch):

"Analyze these GitHub issues for implementation complexity:

Issues: {batch_of_5_issues}

For each issue, evaluate:
1. Number of files likely affected (search codebase for keywords)
2. Presence of reproduction steps (clear = easier)
3. Clarity of expected outcome
4. Existing test coverage for affected areas
5. Similar past issues/PRs as reference

Return JSON:
{
  "issues": [
    {"number": N, "complexity_score": 0-100, "estimated_files": N, "has_repro": bool, "notes": "..."}
  ]
}"
```

### 1.3 Auto-Exclude Issues

Before scoring, automatically exclude issues that should not be processed:

| Condition | Reason | Detection |
|-----------|--------|-----------|
| **Has open linked PR** | Already being worked on | `has_linked_pr == true` from script |
| Assigned to human | Someone is handling it | `assignees` contains non-bot users |
| Label: `auto-fixing` | Currently being processed | Label check |
| Label: `auto-fixed` | Already completed | Label check |
| Label: `wontfix` | Intentionally not fixing | Label check |
| Label: `duplicate` | Duplicate of another | Label check |
| Label: `blocked` | Blocked by dependency | Label check |
| Label: `on-hold` | Intentionally paused | Label check |

The `list-all-issues.sh` script detects linked PRs via GitHub's timeline API:
- Finds `CROSS_REFERENCED_EVENT` (PR mentions issue)
- Finds `CONNECTED_EVENT` (PR explicitly linked)
- Only counts **OPEN** PRs (closed/merged PRs don't block)

```bash
# Example output showing issue with linked PR
{
  "number": 874,
  "title": "Enforce capacity limit",
  "has_linked_pr": true,
  "linked_pr_count": 1,
  "linked_prs": [879]
}
```

**This issue would be SKIPPED** - PR #879 is already addressing it.

### 1.4 Calculate Priority Scores

**Combined Score Formula**: `(Importance * 0.6) + (Speed * 0.4)`

**Importance Score (0-100)**:
| Factor | Weight | Scoring |
|--------|--------|---------|
| Labels | 30% | `security`: 95, `priority-critical`: 90, `priority-high`: 80, `bug`: 70, `enhancement`: 40 |
| Age | 20% | >30 days: 80, >14 days: 60, >7 days: 40, <7 days: 20 |
| Author | 15% | Maintainer: 80, Contributor: 60, External: 40 |
| Assignees | 10% | Unassigned: 70, Assigned to bot: 80, Assigned to human: 20 |
| Comments | 15% | >5: 70, 3-5: 50, 1-2: 30, 0: 20 |
| Milestone | 10% | Current: 90, Next: 60, None: 30 |

**Speed Score (0-100)** - From subagent analysis:
| Factor | Weight | Scoring |
|--------|--------|---------|
| Description length | 20% | <200 chars: 80, 200-500: 60, 500-1000: 40, >1000: 20 |
| Files affected | 30% | 1 file: 90, 2-3: 70, 4-5: 40, >5: 20 |
| Complexity keywords | 25% | "typo/fix/update": 80, "add/change": 60, "refactor": 30, "rewrite/architecture": 10 |
| Has reproduction | 15% | Yes: 80, Partial: 50, No: 30 |
| Has suggested fix | 10% | Yes: 90, Partial: 60, No: 40 |

See [references/prioritization-criteria.md](references/prioritization-criteria.md) for full scoring details.

### 1.5 Select Top Issue

Automatically select the issue with highest combined score. Output prioritization report:

```markdown
## Issue Prioritization

| Rank | Issue | Title | Importance | Speed | Combined |
|------|-------|-------|------------|-------|----------|
| 1 | #123 | Fix null pointer | 75 | 85 | 79 |
| 2 | #456 | Add validation | 70 | 70 | 70 |

**Selected**: #123 - High importance AND quick to implement
```

---

## Phase 2: Setup and Planning

### 2.1 Sync with Remote

Pull the latest changes before starting any work:

```bash
git fetch origin
git pull --rebase origin main
```

This ensures we're working with the latest codebase and avoids merge conflicts later.

### 2.2 Create Worktree

Use the existing worktree setup script:

```bash
../fix-github-issue/scripts/setup-worktree.sh $ISSUE_NUMBER
```

This creates an isolated worktree at `.worktrees/issue-$ISSUE_NUMBER`.

### 2.3 Mark Issue In Progress

Add a label to indicate work has started:

```bash
gh issue edit $ISSUE_NUMBER --add-label "auto-fixing"
```

This prevents other runs from picking up the same issue and signals to humans that automated work is underway.

### 2.4 Load Issue Context

```bash
../fix-github-issue/scripts/load-issue.sh $ISSUE_NUMBER
```

### 2.5 Create TDD Plan

Launch Explore subagent to create a TDD-specific implementation plan:

```
Launch Explore agent:

"Create a TDD implementation plan for issue #{number}: {title}

Issue details:
{issue_body}

Explore the codebase and return a plan with:

## Phase 1: RED - Failing Tests
List specific test cases to write first:
- Test file path
- Test function name
- What behavior it verifies
- Expected failure reason

## Phase 2: GREEN - Minimal Implementation
List minimal code changes to make tests pass:
- File path
- Function/method to modify
- Specific change description

## Phase 3: REFACTOR - Cleanup
List refactoring opportunities:
- DRY violations to fix
- Naming improvements
- Performance optimizations

## Verification Commands
Detect and list:
- Test command (npm test, pytest, go test, etc.)
- Lint command
- Build command

Return structured markdown using templates/tdd-plan.md format"
```

---

## Phase 3: TDD Implementation

### 3.1 RED Phase - Write Failing Tests

1. Create or update test file based on the TDD plan
2. Write test cases that define expected behavior
3. Run tests to verify they fail:

```bash
{TEST_COMMAND}
# Expected: FAIL (tests should fail before implementation)
```

**Critical**: If tests pass before implementation, the tests may not be testing the right behavior. Review and adjust test cases.

### 3.2 GREEN Phase - Minimal Implementation

1. Write the minimum code to make tests pass
2. Focus on correctness, not elegance
3. Run tests after each change:

```bash
{TEST_COMMAND}
# Expected: PASS
```

### 3.3 REFACTOR Phase

1. Clean up implementation while keeping tests green
2. Apply DRY principles
3. Improve naming and structure
4. Final verification:

```bash
{TEST_COMMAND} && {LINT_COMMAND} && {BUILD_COMMAND}
```

### 3.4 Background Test Monitoring

Launch background subagent for continuous feedback:

```
Launch background agent:

"Monitor test and lint status continuously.

Run every 30 seconds:
- {TEST_COMMAND}
- {LINT_COMMAND}

Report immediately when:
- All tests pass (GREEN achieved)
- New test failures (regression detected)
- Lint errors introduced

Return: Status updates as work progresses"
```

---

## Phase 4: Submit PR

### 4.1 Final Verification

Run all checks before committing:

```bash
{TEST_COMMAND} && {LINT_COMMAND} && {TYPECHECK_COMMAND} && {BUILD_COMMAND}
```

### 4.2 Commit Changes

```bash
git add -A
git commit -m "$(cat <<'EOF'
fix: [Brief description from issue title]

- [Change 1]
- [Change 2]

TDD Approach:
- Added [N] test cases for [scenario]
- Verified [edge case] handling

Closes #ISSUE_NUMBER

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

### 4.3 Create PR

```bash
git push -u origin HEAD
gh pr create --title "fix: [Brief description]" --body-file templates/pr-body.md
```

The PR is created immediately to trigger CI checks and allow reviewers to be notified.

### 4.4 Record PR Number

```bash
PR_NUMBER=$(gh pr view --json number -q '.number')
echo "Created PR #$PR_NUMBER"
```

---

## Phase 5: Feedback Loop

This phase handles ALL PR feedback including CI failures, code reviews, inline comments, and general discussion. The skill must track and address each piece of feedback before marking the PR ready.

### 5.1 Fetch All Current Feedback

Before monitoring for changes, get the current state of all feedback:

```bash
scripts/fetch-pr-comments.sh $PR_NUMBER --json > /tmp/pr-feedback-state.json
```

This returns structured data including:
- **Review threads** (inline code comments with resolution status)
- **Reviews** (approve/request changes/comment with body text)
- **General comments** (discussion on the PR)
- **Actionable items** (items requiring response or code changes)

### 5.2 Launch Parallel Monitors

Start background agents to monitor for new feedback:

```bash
# Monitor for any new PR activity (reviews, threads, comments)
scripts/monitor-pr.sh $PR_NUMBER --timeout $REVIEW_TIMEOUT_MINUTES &
MONITOR_PID=$!

# Separately monitor CI status
scripts/wait-for-ci.sh $PR_NUMBER --timeout 15 &
CI_PID=$!
```

The monitor-pr.sh script detects:
- `THREAD_RECEIVED` - New inline code review comment
- `REVIEW_RECEIVED` - New review (approve/request changes)
- `COMMENT_RECEIVED` - New general PR comment
- `THREAD_UNRESOLVED` - Thread was re-opened
- `MERGED` / `CLOSED` / `TIMEOUT`

### 5.3 Handle CI Failures

When CI fails, diagnose and fix:

```
Launch Explore agent:

"CI has failed for PR #{pr_number}.

Failure logs:
{ci_failure_logs}

Current changes (git diff):
{diff_summary}

Diagnose:
1. Root cause of each failure
2. Specific code changes needed
3. Whether new tests are required

Return: Actionable fix plan with file paths and code changes"
```

Apply fixes, commit, and push:

```bash
git add -A
git commit -m "fix: Address CI failures

- [Fix 1]
- [Fix 2]"
git push
```

### 5.4 Categorize Review Feedback

When feedback arrives, categorize each item:

```bash
# Get all unresolved actionable items
scripts/fetch-pr-comments.sh $PR_NUMBER --unresolved-only --json
```

For each feedback item, classify it:

| Category | Detection | Action Required |
|----------|-----------|-----------------|
| **Code Change Request** | Keywords: "fix", "change", "update", "remove", "add", "please", "should", "must" | Modify code, reply, resolve thread |
| **Question** | Ends with "?", starts with "why", "how", "what", "could you" | Answer question, resolve thread |
| **Suggestion (in scope)** | "Consider", "maybe", "alternatively", "what about" + related to current change | Evaluate, implement or explain, resolve thread |
| **Suggestion (out of scope)** | Suggestion about unrelated code, broad refactoring | Thank, offer to create issue, resolve thread |
| **Nitpick** | "nit:", "minor:", style preferences | Apply if trivial, explain if not, resolve thread |
| **Approval/Praise** | "LGTM", "looks good", "nice", "approved" | Thank briefly, no code change needed |
| **Concern/Blocker** | "Blocking", "must fix", "security", "breaking" | Prioritize fixing, escalate if unclear |

### 5.5 Process Feedback with Subagents

Launch parallel agents to handle different feedback types:

```
Launch parallel Explore agents:

1. Code Changes Agent:
   "Process these review comments that require code changes:

   {code_change_items_json}

   For each comment:
   1. Understand what change is being requested
   2. Locate the relevant code in the codebase
   3. Apply the change (read file first, then edit)
   4. Prepare a confirmation reply: 'Done: [brief description]'

   Return JSON:
   {
     'changes': [{'file': 'path', 'description': 'what changed'}],
     'replies': [{'thread_id': 'id', 'reply': 'text'}]
   }"

2. Response Agent:
   "Process these review comments that need responses only:

   {response_items_json}

   For each comment, draft appropriate reply:
   - If QUESTION: Answer directly with context from codebase
   - If SUGGESTION (out of scope): Thank, explain scope, offer to create issue
   - If CONCERN: Explain the reasoning or acknowledge and fix
   - If APPROVAL: Brief thanks

   Return JSON:
   {
     'replies': [{'thread_id': 'id', 'reply': 'text', 'should_resolve': bool}]
   }"
```

### 5.6 Reply to Threads and Resolve

Use the `reply-to-thread.sh` script to reply and optionally resolve in one step:

**If code change was applied:**
```bash
scripts/reply-to-thread.sh "$THREAD_ID" "Done - [description of fix]" --resolve
```

**If declining the suggestion (with reason):**
```bash
scripts/reply-to-thread.sh "$THREAD_ID" "Thanks for the suggestion. I kept the current approach because:

1. [Technical reason]
2. [Scope reason]

Happy to discuss further." --resolve
```

**If answering a question:**
```bash
scripts/reply-to-thread.sh "$THREAD_ID" "[Answer to the question]" --resolve
```

**If need to discuss further (don't resolve):**
```bash
scripts/reply-to-thread.sh "$THREAD_ID" "Good point. [Response]. What do you think?"
# Don't use --resolve - leave open for continued discussion
```

**Post general PR comment (not a thread reply):**
```bash
gh pr comment $PR_NUMBER -b "$COMMENT_TEXT"
```

### 5.7 Resolution Rules

**ALWAYS reply before resolving** - Never resolve without an explanation.

**When to resolve (use `--resolve` flag):**
- Code change was applied as requested → Reply "Done - [what changed]"
- Question was answered → Reply with answer
- Suggestion declined → Reply with reason why
- Nitpick addressed → Reply "Fixed" or "Left as-is because [reason]"

**When NOT to resolve:**
- Waiting for reviewer to confirm fix is acceptable
- Disagreement needs further discussion
- Reviewer explicitly asks to leave open
- Unsure if change is correct

**Every thread must end with one of:**
1. Reply + Resolve (action taken or declined with reason)
2. Reply only (needs discussion)
3. Escalation to human (can't determine action)

### 5.8 Reply Templates

**For code changes applied:**
```markdown
Done - [brief description of what was changed].
```

**For questions answered:**
```markdown
[Direct answer to the question]

[Optional: Link to relevant code or documentation]
```

**For suggestions declined (in scope):**
```markdown
Thanks for the suggestion! I considered this but kept the current approach because:

- [Technical reason: e.g., "This aligns with the existing pattern in `utils/validation.ts`"]
- [Practical reason: e.g., "The suggested change would require updating 15 call sites"]

Happy to discuss further if you'd like to reconsider.
```

**For suggestions declined (out of scope):**
```markdown
Good point! This change is outside the scope of this PR (which focuses on [issue focus]).

I've created issue #[N] to track this improvement separately. Would you like me to prioritize it next?
```

**For concerns/blockers:**
```markdown
Thanks for flagging this. I've addressed it by:

- [Change 1]
- [Change 2]

Please let me know if this addresses your concern or if you'd like further changes.
```

### 5.9 Handle Conflicting Feedback

When reviewers disagree:

1. **Identify the conflict**: Same code, different suggestions
2. **Check reviewer authority**: Maintainer opinion typically takes precedence
3. **If equal authority**:
   - Summarize both perspectives in a comment
   - Implement the more conservative/safe option
   - Ask for consensus: "I went with [X] but happy to switch if you both prefer [Y]"
4. **If unclear**: Escalate to human

### 5.10 Iteration Loop

```
ITERATION=0
MAX_ITERATIONS=$MAX_FEEDBACK_ITERATIONS
BOT_WAIT_MINUTES=5  # Time to wait for Copilot/Claude after CI
QUIET_PERIOD_MINUTES=3  # Time with no new reviews before marking ready

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))

    # 1. Fetch current feedback state (ALL types - threads, reviews, comments)
    FEEDBACK=$(scripts/fetch-pr-comments.sh $PR_NUMBER --json)
    UNRESOLVED=$(echo "$FEEDBACK" | jq '.summary.unresolved_threads')
    CHANGES_REQUESTED=$(echo "$FEEDBACK" | jq '.summary.changes_requested')
    ACTIONABLE_COMMENTS=$(echo "$FEEDBACK" | jq '.summary.actionable_comments')

    # 2. If nothing to address, DON'T break yet - must wait for bot reviews
    if [ "$UNRESOLVED" -eq 0 ] && [ "$CHANGES_REQUESTED" -eq 0 ] && [ "$ACTIONABLE_COMMENTS" -eq 0 ]; then
        info "No pending feedback - waiting for potential bot reviews..."
        # Continue to step 5 to wait for bots
    else
        # 3. Process all actionable items
        # (Use subagents as described above)

        # 4. Commit any changes
        git add -A
        if ! git diff --cached --quiet; then
            git commit -m "Address review feedback (iteration $ITERATION)"
            git push
        fi
    fi

    # 5. Wait for CI
    scripts/wait-for-ci.sh $PR_NUMBER --timeout 10

    # 6. CRITICAL: Wait for bot reviews AFTER CI completes
    # Copilot often arrives 2-5 minutes after CI passes
    info "Waiting $BOT_WAIT_MINUTES minutes for bot reviews (Copilot, Claude)..."
    scripts/monitor-pr.sh $PR_NUMBER --timeout $BOT_WAIT_MINUTES --interval 30

    # 7. Re-fetch feedback - bots may have added new items
    FEEDBACK=$(scripts/fetch-pr-comments.sh $PR_NUMBER --json)
    UNRESOLVED=$(echo "$FEEDBACK" | jq '.summary.unresolved_threads')
    CHANGES_REQUESTED=$(echo "$FEEDBACK" | jq '.summary.changes_requested')
    ACTIONABLE_COMMENTS=$(echo "$FEEDBACK" | jq '.summary.actionable_comments')

    # 8. Check if truly ready (nothing pending after bot wait)
    if [ "$UNRESOLVED" -eq 0 ] && [ "$CHANGES_REQUESTED" -eq 0 ] && [ "$ACTIONABLE_COMMENTS" -eq 0 ]; then
        info "All feedback addressed - verifying quiet period..."

        # 9. Quiet period check - ensure no new reviews for 3 minutes
        QUIET_START=$(date +%s)
        QUIET_OK=true

        for i in $(seq 1 $QUIET_PERIOD_MINUTES); do
            sleep 60
            CURRENT_FEEDBACK=$(scripts/fetch-pr-comments.sh $PR_NUMBER --json)
            NEW_UNRESOLVED=$(echo "$CURRENT_FEEDBACK" | jq '.summary.unresolved_threads')
            NEW_CHANGES=$(echo "$CURRENT_FEEDBACK" | jq '.summary.changes_requested')

            if [ "$NEW_UNRESOLVED" -gt 0 ] || [ "$NEW_CHANGES" -gt 0 ]; then
                warn "New feedback arrived during quiet period - reprocessing..."
                QUIET_OK=false
                break
            fi
        done

        if [ "$QUIET_OK" = true ]; then
            info "Quiet period complete - proceeding to mark PR ready"
            break
        fi
        # Otherwise continue loop to process new feedback
    fi
done

if [ $ITERATION -ge $MAX_ITERATIONS ]; then
    # Escalate to human
    gh pr comment $PR_NUMBER -b "## Escalation

After $MAX_ITERATIONS feedback iterations, some items remain unresolved.
Human review requested.

Remaining:
- Unresolved threads: $UNRESOLVED
- Changes requested: $CHANGES_REQUESTED
- Actionable comments: $ACTIONABLE_COMMENTS"
fi
```

### 5.11 Wait for Bot Reviews (CRITICAL)

**IMPORTANT**: Bot reviewers like Copilot and Claude often submit reviews AFTER CI completes. These reviews contain valuable feedback that MUST be addressed before marking the PR ready.

**Known bot reviewers to wait for:**
| Bot | Username Pattern | Typical Delay |
|-----|------------------|---------------|
| GitHub Copilot | `copilot[bot]`, `github-copilot` | 2-5 min after CI |
| Claude | `claude[bot]`, `claude-code` | 1-3 min after CI |
| CodeRabbit | `coderabbitai[bot]` | 3-7 min after CI |
| Dependabot | `dependabot[bot]` | Immediate |
| Renovate | `renovate[bot]` | Immediate |

**Waiting strategy after each push:**

```bash
# After pushing changes:
scripts/wait-for-ci.sh $PR_NUMBER --timeout 15

# CRITICAL: Wait for bot reviews AFTER CI completes
# Copilot especially often arrives 2-5 minutes after CI passes
info "Waiting for bot reviews (Copilot, Claude, etc.)..."
BOT_WAIT_MINUTES=5
scripts/monitor-pr.sh $PR_NUMBER --timeout $BOT_WAIT_MINUTES --interval 30

# Then re-check ALL feedback - bots may have added new items
FEEDBACK=$(scripts/fetch-pr-comments.sh $PR_NUMBER --json)
```

**Never skip this wait** - Copilot reviews in particular contain security and quality feedback that is critical to address.

### 5.12 Quiet Period Verification

Before marking the PR as ready, verify there's been a "quiet period" with no new reviews:

```bash
# After processing all feedback:
QUIET_PERIOD_MINUTES=3
LAST_CHECK_TIME=$(date +%s)

while true; do
    # Wait for quiet period
    sleep 60

    # Fetch current state
    CURRENT_FEEDBACK=$(scripts/fetch-pr-comments.sh $PR_NUMBER --json)
    CURRENT_TIME=$(date +%s)

    # Check for new items since last check
    NEW_THREADS=$(echo "$CURRENT_FEEDBACK" | jq '.summary.unresolved_threads')
    NEW_CHANGES=$(echo "$CURRENT_FEEDBACK" | jq '.summary.changes_requested')
    NEW_ACTIONABLE=$(echo "$CURRENT_FEEDBACK" | jq '.summary.actionable_comments')

    if [ "$NEW_THREADS" -gt 0 ] || [ "$NEW_CHANGES" -gt 0 ] || [ "$NEW_ACTIONABLE" -gt 0 ]; then
        # New feedback arrived - process it and reset quiet period
        info "New feedback detected - processing..."
        # (Process feedback as per 5.4-5.6)
        LAST_CHECK_TIME=$(date +%s)
        continue
    fi

    # Check if quiet period has elapsed
    ELAPSED=$((CURRENT_TIME - LAST_CHECK_TIME))
    if [ $ELAPSED -ge $((QUIET_PERIOD_MINUTES * 60)) ]; then
        info "Quiet period complete - no new reviews for $QUIET_PERIOD_MINUTES minutes"
        break
    fi
done
```

### 5.13 Iteration Limits and Escalation

- **Max iterations**: Default 3 (configurable via MAX_FEEDBACK_ITERATIONS)
- **Per iteration**: Fetch all feedback → process → push → wait for CI → **wait for bot reviews** → wait for response
- **Bot review wait**: Always wait at least 5 minutes after CI for Copilot/Claude reviews
- **Quiet period**: Verify 3 minutes of no new activity before marking ready
- **Escalation triggers**:
  - MAX_FEEDBACK_ITERATIONS exceeded
  - Reviewer explicitly requests human review
  - Feedback requires architectural decisions
  - Conflicting reviewer opinions without resolution

---

## Phase 6: Completion

### 6.1 Verify Completion Criteria

**CRITICAL**: The PR must meet ALL criteria before marking ready. This is the final gate to ensure no reviews are missed.

All must be true before marking ready:

```bash
# 1. CI green
CI_STATUS=$(gh pr checks $PR_NUMBER --json bucket -q '[.[] | .bucket] | unique')
[ "$CI_STATUS" = '["pass"]' ] || exit 1

# 2. No unresolved review threads
REVIEW_DATA=$(gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes { isResolved }
        }
        reviews(first: 50) {
          nodes {
            id
            state
            author { login }
            body
          }
        }
        comments(first: 100) {
          nodes {
            id
            author { login }
            body
          }
        }
      }
    }
  }' -f owner="$OWNER" -f repo="$REPO" -F pr="$PR_NUMBER")

UNRESOLVED=$(echo "$REVIEW_DATA" | jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length')
[ "$UNRESOLVED" = "0" ] || { echo "ERROR: $UNRESOLVED unresolved threads"; exit 1; }

# 3. No reviews requesting changes (includes Copilot, Claude, human reviews)
CHANGES_REQUESTED=$(echo "$REVIEW_DATA" | jq '[.data.repository.pullRequest.reviews.nodes[] | select(.state == "CHANGES_REQUESTED")] | length')
[ "$CHANGES_REQUESTED" = "0" ] || { echo "ERROR: $CHANGES_REQUESTED reviews requesting changes"; exit 1; }

# 4. No unaddressed bot reviews (Copilot, Claude, etc.)
BOT_PATTERNS="copilot|claude|coderabbit|github-actions"
UNADDRESSED_BOT_REVIEWS=$(echo "$REVIEW_DATA" | jq --arg bots "$BOT_PATTERNS" '
  [.data.repository.pullRequest.reviews.nodes[] |
   select(.author.login | test($bots; "i")) |
   select(.state == "CHANGES_REQUESTED" or (.state == "COMMENTED" and .body != null and .body != "" and (.body | test("(?i)(fix|issue|error|should|must|recommend)"))))] | length')
[ "$UNADDRESSED_BOT_REVIEWS" = "0" ] || { echo "ERROR: $UNADDRESSED_BOT_REVIEWS unaddressed bot reviews"; exit 1; }

# 5. Quiet period verified (no new reviews in last 3 minutes)
# This should have been done in Phase 5, but verify again
echo "All completion criteria verified"
```

**Why each check matters:**
| Check | Purpose |
|-------|---------|
| GitHub merge state | **CRITICAL**: If GitHub says BLOCKED, do NOT mark ready |
| CI green | Code compiles, tests pass |
| No unresolved threads | All inline comments addressed |
| No changes requested | All formal review requests addressed (LATEST review per author) |
| No unaddressed bot reviews | **Copilot/Claude feedback addressed** |
| Quiet period | No late-arriving reviews pending |

**CRITICAL: Latest Review Per Author**

GitHub shows the LATEST review from each reviewer, not all historical reviews. The skill MUST match this behavior:

```bash
# WRONG: Checks all historical reviews (might miss current "changes requested")
CHANGES_REQUESTED=$(echo "$REVIEWS" | jq '[.[] | select(.state == "CHANGES_REQUESTED")]')

# RIGHT: Get latest review per author, then check status
LATEST_REVIEWS=$(echo "$REVIEWS" | jq '
  group_by(.author.login) |
  map(sort_by(.createdAt) | last) |
  [.[] | select(. != null)]
')
CHANGES_REQUESTED=$(echo "$LATEST_REVIEWS" | jq '[.[] | select(.state == "CHANGES_REQUESTED")]')
```

**CRITICAL: Respect GitHub's Merge State**

Before marking ready, check GitHub's own merge state:
- `mergeStateStatus: BLOCKED` → Do NOT mark ready (unresolved conversations, missing approvals)
- `reviewDecision: CHANGES_REQUESTED` → Reviewer has requested changes
- `mergeable: CONFLICTING` → Merge conflicts exist

### 6.2 Mark PR Ready for Review

```bash
scripts/mark-pr-ready.sh $PR_NUMBER
```

This script:
1. Verifies all CI checks pass
2. Verifies all review threads are resolved
3. If PR is a draft, marks it as ready (`gh pr ready`)
4. **Adds `ready` label** to the PR
5. **Tags the logged-in user** for notification
6. Posts a completion summary comment

The comment tags the user so they receive a GitHub notification:

```markdown
## Ready for Manual Review

@username - This PR is ready for your review.

### Summary
All automated work has been completed:
- All CI checks passing
- All review feedback addressed
- All review threads resolved

### Next Steps
1. Review the changes
2. Approve if satisfied
3. Merge when ready
```

The user tag ensures the human gets notified when the skill completes its work.

### 6.3 Generate Completion Report

Output summary using [templates/completion-report.md](templates/completion-report.md):

```markdown
## Auto Issue Fixer - Complete

### Issue
- **Number**: #123
- **Title**: Fix null pointer in user service

### PR
- **Number**: #456
- **Status**: Ready for review
- **URL**: https://github.com/owner/repo/pull/456

### TDD Summary
| Phase | Result |
|-------|--------|
| RED | 3 test cases written |
| GREEN | 2 files modified |
| REFACTOR | 1 cleanup applied |

### Feedback Handled
- Code changes: 2
- Responses: 1
- Iterations: 2/3

**Next step**: Human review and merge
```

### 6.4 Update Issue Labels

Swap the in-progress label for a completed label:

```bash
gh issue edit $ISSUE_NUMBER --remove-label "auto-fixing" --add-label "auto-fixed"
```

This signals that automated work is complete and the PR is ready for human review.

### 6.5 Auto-Merge Decision

Based on the `AUTO_MERGE` argument, either merge automatically or leave for human:

```bash
if [ "$AUTO_MERGE" = "true" ]; then
    info "AUTO-ISSUE-FIXER: MERGING - Auto-merge enabled, merging PR #$PR_NUMBER"

    # Final safety checks before merge
    # 1. Verify CI is still green (could have changed)
    CI_STATUS=$(gh pr checks $PR_NUMBER --json bucket -q '[.[] | .bucket] | unique')
    if [ "$CI_STATUS" != '["pass"]' ]; then
        error "CI no longer passing - aborting auto-merge"
        gh pr comment $PR_NUMBER -b "## Auto-Merge Aborted

CI checks are no longer passing. Manual intervention required.

Current CI status: $CI_STATUS"
        exit 1
    fi

    # 2. Verify no new reviews arrived (final check)
    FINAL_CHECK=$(scripts/fetch-pr-comments.sh $PR_NUMBER --json)
    FINAL_UNRESOLVED=$(echo "$FINAL_CHECK" | jq '.summary.unresolved_threads')
    FINAL_CHANGES=$(echo "$FINAL_CHECK" | jq '.summary.changes_requested')

    if [ "$FINAL_UNRESOLVED" -gt 0 ] || [ "$FINAL_CHANGES" -gt 0 ]; then
        error "New feedback arrived - aborting auto-merge"
        gh pr comment $PR_NUMBER -b "## Auto-Merge Aborted

New review feedback arrived after completion. Processing required.

- Unresolved threads: $FINAL_UNRESOLVED
- Changes requested: $FINAL_CHANGES"
        exit 1
    fi

    # 3. Merge the PR
    if gh pr merge $PR_NUMBER --squash --delete-branch; then
        info "AUTO-ISSUE-FIXER: MERGED - PR #$PR_NUMBER merged successfully"

        # Post success comment (will be on the now-closed PR)
        gh pr comment $PR_NUMBER -b "## Auto-Merged

PR was automatically merged after all criteria were met:
- All CI checks passing
- All review feedback addressed
- All review threads resolved
- Quiet period verified

Issue #$ISSUE_NUMBER has been closed." 2>/dev/null || true

    else
        error "Merge failed - may require manual intervention"
        gh pr comment $PR_NUMBER -b "## Auto-Merge Failed

Attempted to merge but failed. Possible reasons:
- Branch protection rules require additional approvals
- Merge conflicts detected
- Required status checks changed

Please merge manually."
        exit 1
    fi

else
    # AUTO_MERGE is false or not set - leave for human
    info "AUTO-ISSUE-FIXER: COMPLETE - PR #$PR_NUMBER ready for review"

    # The mark-pr-ready.sh script already posted a comment tagging the user
    # Just ensure the user knows to merge manually
fi
```

**Auto-merge safety checks:**
| Check | Why |
|-------|-----|
| CI still green | Status could have changed since last check |
| No new reviews | Late-arriving feedback must be addressed |
| Squash merge | Clean commit history |
| Delete branch | Cleanup after merge |

**When auto-merge is aborted:**
- Posts a comment explaining why
- Leaves PR open for manual intervention
- Does NOT retry automatically (prevents loops)

---

## Escalation Triggers

Stop and escalate to human when:

| Condition | Action |
|-----------|--------|
| CI fails after 3 attempts | Report failures, request help |
| Reviewer requests architectural changes | Flag as out of scope |
| MAX_FEEDBACK_ITERATIONS exceeded | Post summary, request guidance |
| Reviewer explicitly requests human | Stop and notify |
| Merge conflicts | Attempt rebase; if fails, escalate |
| No test framework detected | Warn and proceed without TDD |

Escalation message:
```markdown
## Escalation Required

**Issue**: #{issue_number}
**PR**: #{pr_number}
**Reason**: {escalation_reason}

### Context
{relevant_details}

### Attempted Solutions
{what_was_tried}

### Recommended Action
{suggestion}
```

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/list-all-issues.sh` | Fetch all open issues with metadata |
| `scripts/fetch-pr-comments.sh` | Fetch all PR feedback (threads, reviews, comments) with categorization |
| `scripts/monitor-pr.sh` | Poll for new reviews, threads, and comments |
| `scripts/wait-for-ci.sh` | Wait for CI completion |
| `scripts/reply-to-thread.sh` | Reply to a review thread and optionally resolve it |
| `scripts/mark-pr-ready.sh` | Convert draft to ready for review |

**Reused from other skills**:
| Script | Source |
|--------|--------|
| `setup-worktree.sh` | fix-github-issue |
| `load-issue.sh` | fix-github-issue |
| `create-pr.sh` | fix-github-issue |
| `load-pr-feedback.sh` | pr-feedback-workflow |
| `resolve-thread.sh` | pr-feedback-workflow |

---

## Subagent Usage Summary

| Phase | Type | Purpose | Parallel |
|-------|------|---------|----------|
| 1 | Explore (x N) | Complexity analysis (batches of 5) | YES |
| 2 | Explore | TDD plan creation | NO |
| 3 | Background | Continuous test monitoring | YES |
| 5 | Background (x 2) | CI + Review monitors | YES |
| 5 | Explore (x 2) | Code changes + Responses | YES |

**Token efficiency**: Main context handles orchestration; subagents handle all codebase exploration and monitoring.

---

## Quick Start

```bash
# Fix a specific issue by number
/auto-issue-fixer --issue-number 1198

# Or use the dedicated slash command
/fix-issue 1198

# Fix the highest-priority issue (leaves PR for human to merge)
/auto-issue-fixer

# Fix and auto-merge when complete (fully autonomous)
/auto-issue-fixer --auto-merge

# Fix issues with specific label
/auto-issue-fixer --labels bug

# Dry run - analyze without implementing
/auto-issue-fixer --dry-run

# Process up to 3 issues with auto-merge
/auto-issue-fixer --max-issues 3 --auto-merge

# Fully autonomous with custom wait times
/auto-issue-fixer --auto-merge --bot-wait-minutes 7 --quiet-period-minutes 5

# Fix specific issue with auto-merge
/fix-issue 1198 --auto-merge
```

**Auto-merge behavior:**
- `--auto-merge` (or `AUTO_MERGE=true`): Merges PR automatically after all reviews addressed
- Without flag: Notifies user and leaves PR open for manual merge (default)

---

## Related Skills

- [fix-github-issue](../fix-github-issue/SKILL.md): Manual issue fixing with worktrees
- [pr-feedback-workflow](../pr-feedback-workflow/SKILL.md): Dedicated PR feedback handling
- [cleanup-issue](../cleanup-issue/SKILL.md): Post-merge cleanup
