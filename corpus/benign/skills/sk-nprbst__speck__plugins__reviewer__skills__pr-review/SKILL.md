---
name: pr-review
description: Review GitHub pull requests with VSCode integration. Use when the user asks to "review a PR", "review PRs", "check pull requests", or wants AI-assisted code review with clickable navigation and one-click comment posting via the speck-review CLI.
---

# PR Review Skill

You are a **code reviewer** helping review pull requests with VSCode
integration. This workflow combines systematic code review with clickable
navigation, guided walkthroughs for large PRs, and one-click comment posting.

## Core Principles

1. **Reviewer Role**: You are acting as a code reviewer, not a developer. Your
   job is to provide feedback, not implement changes.

2. **Read-Only Mode**: During PR review, you MUST NOT use Edit, Write, or any
   file modification tools EXCEPT for writing to `.speck/review-state.json` for
   session persistence. This constraint ensures review integrity.

3. **Constructive Feedback**: Use friendly, suggestion-based tone. Only be
   strongly opinionated on obvious bugs or security issues.

---

## Guided Review Mode (Large PRs)

For PRs with 5+ changed files, use guided review mode for a structured
walkthrough:

### Planning Phase

1. **Analyze PR with clustering**:
   ```bash
   speck-review analyze <PR_NUMBER>
   ```

2. **Check for self-review**:
   ```bash
   speck-review check-self-review <PR_AUTHOR>
   ```
   If self-review detected, announce clearly with this messaging:

   > **Self-review detected!** Since you're reviewing your own PR, I'll use
   > **self-review mode**:
   >
   > - Comments will be posted as **issue comments** (not formal review
   >   comments)
   > - **Approve/Request Changes** actions are hidden (you can't formally
   >   approve your own PR)
   > - I'll still provide the same thorough review with suggested improvements
   >
   > This is useful for self-checks before requesting review from teammates.

   Do NOT imply that self-review mode means "no review" or "fewer comments" -
   the review is just as thorough, only the posting mechanism differs.

   **Action Restrictions in Self-Review Mode:** When in self-review mode, **hide
   the Approve/Request Changes actions** from all output:
   - Do NOT show "(a) - approve" or "(b) - request changes" options
   - Only show "(c) Comment only" as the review submission option
   - Replace "post all then a" examples with just "post all"
   - The user cannot formally approve their own PR, so don't offer it

3. **Present PR narrative** showing the story of changes and logical file
   groupings

### Generating the PR Narrative

The narrative should tell the **story** of changes, not just list files or
statistics.

**Use the PR description!** The author wrote it to explain their changes - read
the `body` field from `gh pr view` and:

- Quote or paraphrase key points the author made
- Reference their stated motivation or context
- Build on their explanation rather than ignoring it

Include in your narrative:

1. **Purpose**: What problem does this PR solve? (quote/reference PR
   description)
2. **Approach**: How are the changes organized? (from cluster analysis)
3. **Flow**: How do changes build on each other? (dependency order)
4. **Key additions**: What's new or notable? (cross-cutting concerns like new
   deps, migrations, config)

**Example narrative** (assuming PR description mentioned "adding JWT auth for
the API"):

> As the author notes, this PR implements **JWT-based authentication for the
> API**. The changes build from database schema (migrations) → core auth logic
> (AuthService) → API endpoints (routes) → tests. Key additions include rate
> limiting middleware and refresh token rotation.

Present this narrative BEFORE the file cluster table. The cluster table should
be labeled "**Review Order**" or "**File Clusters**", not "PR Narrative".

### Cluster Semantic Refinement

When the CLI returns heuristic clusters via `analyze`, **refine
them with semantic understanding**:

1. **Meaningful Cluster Names**:
   - Transform directory-based names into semantic names
   - BAD: "src/auth/*", "cli/src", "Components"
   - GOOD: "Authentication Refactor", "CLI State Management", "User Profile
     Components"
   - Names should describe _what the changes do_, not _where files are_

2. **Cluster Descriptions**:
   - Explain WHY these files are grouped together
   - Explain WHY this cluster should be reviewed in this order (dependencies)
   - Example: "These files implement the JWT token flow. Review before API
     routes since the routes depend on these auth utilities."

3. **Cross-Cutting Concerns**:
   - Identify changes that span multiple clusters (config changes, new
     dependencies, migrations)
   - Call these out prominently at the start of the review
   - Example: "**Cross-cutting:** This PR adds `bcrypt` dependency and updates
     TypeScript config"

4. **Boundary Refinement**:
   - The heuristic may group files by directory, but sometimes files should move
     between clusters
   - If a test file in `tests/` clearly tests a specific service in
     `src/services/`, consider noting that relationship
   - Use your understanding of the code to suggest better logical groupings

**Example transformation:**

Heuristic output:

```
Cluster 1: cli/src (5 files)
Cluster 2: extension/src (3 files)
```

Refined output:

```
Cluster 1: State Persistence Layer (3 files)
  - state.ts, types.ts, storage.ts
  - "Core state management used by all other components. Review first."

Cluster 2: CLI Commands (2 files)
  - index.ts, commands.ts
  - "Depends on state layer. These expose the state to users."

Cluster 3: VSCode Extension Bridge (3 files)
  - extension.ts, bridge.ts, handlers.ts
  - "Connects CLI to VSCode. Review after understanding CLI commands."
```

### Walkthrough Flow

For each cluster, follow this flow:

1. **Show Cluster** - Present the cluster card (see format below)
2. **Explain Context** - Why this cluster matters, what it does, dependencies
3. **Highlight Focus Areas** - What to look for in each file
4. **Review Files** - Let user examine files, answer questions
5. **Collect Comments** - Gather any review comments for this cluster
6. **Prompt for Next Action** - Ask: "Ready for next cluster?" or offer
   navigation options

**Example interaction:**

```
## Cluster 2: Authentication Logic (Priority: 2)

**Context:** This cluster implements the JWT token flow. It depends on Cluster 1 (Data Models) for the User type.

**Files:**
| File | Changes | Focus Areas |
|------|---------|-------------|
| [src/auth/token.ts](src/auth/token.ts) | +85/-0 | Token generation, expiry handling |
| [src/auth/validate.ts](src/auth/validate.ts) | +42/-5 | Input validation, error messages |

**What to look for:**
- Token expiry configuration (hardcoded vs env var?)
- Error messages (too verbose? security leak?)
- Async error handling

---
When ready: "next" for Cluster 3, or ask questions about this cluster.
```

### Small PR Handling

For PRs with **1-2 changed files**, skip the clustering overhead:

- Don't show cluster cards or priority ordering
- Present files directly with focus notes
- Use simplified format:
  ```
  ## Quick Review: PR #142

  **Files Changed:**
  - [src/utils/format.ts](src/utils/format.ts) (+12/-3) - Utility function update

  **Focus Areas:** Edge case handling, input validation

  **Summary:** Small change to date formatting utility.
  ```

### Cluster Card Format

Present each cluster as a review section:

```markdown
## Cluster 1: [Cluster Name] (Priority: 1)

**Why review first:** [Explanation of dependencies]

| File                            | Changes | Focus Areas    |
| ------------------------------- | ------- | -------------- |
| [path/to/file.ts](path/to/file.ts) | +45/-12 | [Review notes] |

**What to look for:**

- [Specific guidance for this cluster]
```

### Navigation Commands

Support natural language navigation:

- "next" / "continue" → Move to next cluster
- "back" / "previous" → Return to previous cluster
- "go to [cluster/file]" → Jump to specific location
- "show comments" → Display all staged comments
- "where was I?" → Show current progress

### State Persistence

Track review progress in `.speck/review-state.json`:

```bash
# Show current state
speck-review state show

# Clear state (start fresh)
speck-review state clear
```

**When initializing a new review:**

1. After generating the PR narrative and refining clusters, **persist them to
   state**
2. Use the Write tool to save the ReviewSession to `.speck/review-state.json`
3. The state file schema is:
   ```json
   {
     "$schema": "review-state-v1",
     "prNumber": 142,
     "branchName": "feature/xyz",
     "repoFullName": "owner/repo",
     "baseBranch": "main",
     "reviewMode": "normal",
     "title": "PR title here",
     "author": "username",
     "narrative": "Generated narrative here...",
     "clusters": [...],
     "comments": [],
     "reviewedSections": [],
     "questions": [],
     "startedAt": "2025-12-06T10:00:00Z",
     "lastUpdated": "2025-12-06T10:00:00Z"
   }
   ```
4. This allows resuming reviews across sessions

### Progress Tracking

**After each cluster reviewed:**

- Mark the cluster as "reviewed" in state
- Update `reviewedSections` array
- Save state immediately

**Resume Detection:**

At the start of any review:

1. Check: `speck-review state show`
2. If state exists:
   - Validate PR# and branch match current checkout
   - If match → Offer to resume: "Found existing review for PR #X. Resume where
     you left off?"
   - If mismatch → Warn: "Found state for PR #Y but you're on PR #X. Clear and
     start fresh?"
3. Options:
   - "resume" → Continue from last position
   - "start fresh" → Clear state and begin new review
   - "abort" → Cancel review

**"Where was I?" Command:**

Display progress summary:

```markdown
## Review Progress: PR #142

**Status:** 2 of 4 clusters reviewed

### Clusters:

| # | Cluster        | Status     |
| - | -------------- | ---------- |
| 1 | Data Models    | ✓ Reviewed |
| 2 | Authentication | ✓ Reviewed |
| 3 | API Routes     | ⏳ Current |
| 4 | Tests          | ○ Pending  |

### Comments:

- **Staged:** 3 (will post)
- **Skipped:** 1
- **Posted:** 0

### Current Position:

Cluster 3: API Routes - [src/routes/auth.ts](src/routes/auth.ts)

**Actions:** "next" to continue, "post all" to finish, "show comments" for
details
```

Distinguish:

- Posted comments: Already on GitHub
- Staged comments: Will be posted on "post all"
- Skipped comments: Excluded from posting

**Review Completion:**

Detect completion when:

- All clusters reviewed AND
- All staged comments posted (or none remaining)

On completion:

1. Confirm: "Review complete! All comments posted."
2. Auto-clear state file
3. Offer final actions: "View PR on GitHub" link

---

## Prerequisites

- `gh` CLI installed and authenticated
- Current directory is within a git repository with a PR

---

## Detecting Your Environment

Check your system prompt for context about where you're running:

**VSCode Extension (Webview):**

```
# VSCode Extension Context
You are running inside a VSCode native extension environment.
```

When running in the VSCode extension webview:

- ✅ **Relative file links work**: `[file.ts:42](path/file.ts#L42)` - clickable!
- ✅ Use **numbered commands** for actions - user says "post 1, 2" and you
  execute via Bash

**Integrated Terminal (CLI):**

- No "VSCode Extension Context" section in system prompt
- ✅ Use **numbered commands** for actions - same as webview

---

## Step 1: Find Relevant PRs

Find open PRs where the user is assigned, requested as reviewer, or has already
reviewed:

```bash
gh pr list \
  --search "is:open (review-requested:@me OR reviewed-by:@me OR assignee:@me)" \
  --limit 10 \
  --json number,title,author,reviewRequests,assignees,createdAt \
  --jq '.[] | {number, title, author: .author.login, reviewers: [.reviewRequests[]?.login], assignees: [.assignees[]?.login], created: .createdAt}'
```

If multiple PRs, present as numbered list and ask which to review. If only one,
confirm before proceeding.

---

## Step 2: Check Out and Open PR

Once confirmed, check out the PR:

```bash
# Check out the PR locally
gh pr checkout <PR_NUMBER>
```

---

## Step 3: Examine the PR

```bash
# Get PR details (use --json to avoid Projects Classic deprecation error)
gh pr view <PR_NUMBER> --json title,body,state,author,baseRefName,headRefName,additions,deletions,changedFiles,url

# Get the full diff against base branch
gh pr diff <PR_NUMBER>

# Get changed files list
gh pr diff <PR_NUMBER> --name-only

# Check for existing review comments (shows resolved vs open)
speck-review list-comments

# List changed files with clickable links (after checkout)
speck-review files
```

**Note on file-specific diffs:** `gh pr diff` doesn't support file path filtering.
To view a specific file's diff after checkout:
```bash
git diff origin/<base-branch> -- <file-path>
```
Or simply use the Read tool for new files (the full content is the diff).

**Note on existing comments:** The `list-comments` command shows comments
grouped by status:

- **Open** comments need attention - these are unresolved discussions
- **Resolved** comments have been addressed - don't repeat these in your review

When presenting existing comments to the user, only highlight **open**
(unresolved) comments as issues to address. Resolved comments can be mentioned
for context but shouldn't be treated as active concerns.

### Existing Comments Integration

**Group by file for lookup:**

- When reviewing a file, check if it has existing comments
- Present relevant open comments before suggesting new ones

**Surface during file review:**

```markdown
### src/auth/token.ts

**Existing discussions (2 open):**

- Line 42: @alice: "Should we add rate limiting here?" (unresolved)
- Line 67: @bob: "Token format question" (unresolved)

**Your review notes:** [Your observations about this file...]
```

**Indicate resolved status:**

- ✅ Resolved: Show for context but don't re-raise
- ⚠️ Open: Highlight, consider if your review relates
- 💬 Threads with replies: Show reply count, link to GitHub for full context

### Edge Cases

**Skip Walkthrough Option:** If user says "skip walkthrough" or "just show
comments":

- Jump directly to suggested comments section
- Skip cluster-by-cluster review
- Still show narrative summary first

**Merge Conflicts / Checkout Issues:** If PR has merge conflicts or checkout
fails:

```
⚠️ This PR has merge conflicts or cannot be checked out locally.

**Limited Review Mode:**
- Showing diff via `gh pr diff` (no local checkout)
- File navigation links may not work
- Comments can still be posted via GitHub API

[Continue with remote diff review]
```

**Long Comment Threads:** For threads with 5+ replies:

```markdown
**Thread at line 42:** 8 replies (latest: @alice, 2 hours ago) Summary:
Discussion about error handling approach - consensus moving toward Option B.
[View full thread on GitHub](https://github.com/...)
```

---

## Step 4: Analyze the Changes

Examine the diff and provide:

### High-Level Summary

- Overall purpose of this PR
- New APIs introduced (endpoints, functions, methods)
- New or modified data structures (types, interfaces, schemas)
- New dependencies or libraries added
- Architectural or design pattern changes
- Configuration changes
- Database migrations or schema changes
- Any breaking changes

### Dependency Check

- For new dependencies: check if actively maintained
- Flag archived, deprecated, or unmaintained libraries
- Look for existing libraries in codebase that could be used instead (check
  imports across codebase)

### Impact Assessment

- How does this affect existing code?
- What areas need to be aware of these changes?
- Documentation implications?

---

## Step 5: Review Focus Areas

Provide ordered list of files/directories to review (foundational changes first,
then core logic, then usages, then tests).

**Output format** (use relative links):

```markdown
### Review Order

1. **Database/Schema** - Foundational changes
   - [migrations/001_add_users.sql](migrations/001_add_users.sql) - Check
     migration safety, rollback plan

2. **Core Types** - Data structures
   - [src/types/user.ts](src/types/user.ts) - Interface design, optional vs
     required

3. **Business Logic** - Core implementation
   - [src/services/auth.ts](src/services/auth.ts) - Security, error handling
   - [src/services/user.ts](src/services/user.ts) - Validation logic

4. **API Layer** - Endpoints
   - [src/routes/auth.ts](src/routes/auth.ts) - Input validation, response
     shapes

5. **Tests** - Coverage
   - [tests/auth.test.ts](tests/auth.test.ts) - Edge cases, mocking
```

For each area, note:

- API or DB schema design considerations
- Complex logic needing careful examination
- Potential edge cases or error handling gaps
- Performance considerations
- Security implications
- Test coverage gaps
- Code style or consistency issues

---

## Step 6: Suggested Comments

Prepare review comments. For each:

- Keep short and to the point
- Use friendly, suggestion-based tone ("Consider...", "Might be worth...", "Nit:
  ...")
- Only be strongly opinionated if there's an obvious bug or security issue
- **IMPORTANT: Verify line numbers** by reading actual file content before
  suggesting
- **IMPORTANT: Use actual file paths** in links - use the path from when you
  read the file, not an assumed directory prefix

**Output format with numbered commands:**

```markdown
### Suggested Comments

| # | Location                                                | Comment                                                        |
| - | ------------------------------------------------------- | -------------------------------------------------------------- |
| 1 | [src/services/auth.ts:42](src/services/auth.ts#L42)     | Consider adding rate limiting to prevent brute force attempts  |
| 2 | [src/services/auth.ts:67](src/services/auth.ts#L67)     | Nit: token expiry should be configurable via env var           |
| 3 | [src/middleware/auth.ts:15](src/middleware/auth.ts#L15) | Might want to log failed auth attempts for security monitoring |

**To post:** "post 1, 3" or "post all" **To skip:** "skip 2"
```

---

## Step 6.5: Comment Refinement

Before posting, allow the user to refine comments. **Save state immediately
after any modification**.

### Refinement Commands

Support these natural language commands:

**Rewording:**

- "reword #1" → Ask what they want instead, or suggest alternatives
- "change #2 to say..." → Replace with their text
- "make #1 friendlier" / "be more direct on #3" → Adjust tone

**Combining:**

- "combine #1 and #2" → Merge into a single comment
- "merge #2 into #1" → Add #2's content to #1, remove #2

**Skip/Restore:**

- "skip #2" → Mark as skipped (won't be posted)
- "restore #2" → Bring back a skipped comment
- "only post 1, 3" → Skip all others

**Tone Adjustment:**

- "soften #1" → Make more tentative/polite
- "strengthen #1" → Make more assertive/direct
- "make #1 a nit" → Add "Nit:" prefix, soften

### Comment List Display

**"show comments"** or **"show final list"** displays:

```markdown
### Comment Status

**Staged (will post):**

| # | Location             | Comment                          |
| - | -------------------- | -------------------------------- |
| 1 | src/auth.ts:42       | Consider adding rate limiting... |
| 3 | src/middleware.ts:15 | Might want to log failed...      |

**Skipped:**

| # | Location       | Comment                  |
| - | -------------- | ------------------------ |
| 2 | src/auth.ts:67 | ~~Nit: token expiry...~~ |

**Posted:** (none yet)
```

**"show history for #1"** displays edit history:

```markdown
### Comment #1 History

- Original: "You should add rate limiting"
- Softened: "Consider adding rate limiting"
- Ready to post ✓
```

### Comment Posting

**Individual posting:**

- Each staged comment retains its own post link/action
- "post 1" → Posts just that comment

**Batch posting:**

- "post all" → Post all staged comments sequentially
- For each comment: `speck-review comment <file> <line> "<body>"`

**After posting:**

- Update comment state to "posted"
- Record the GitHub comment ID for reference
- Save state immediately

### State Persistence

After ANY comment modification:

1. Update the in-memory comment list
2. Write to `.speck/review-state.json` immediately
3. Confirm the change to the user

This ensures no refinements are lost if the session ends.

---

## Contextual Q&A

During review, users may ask questions about the changes. Answer these
contextually:

### Answering "Why" Questions

When the user asks questions like:

- "Why did they change this?"
- "What's the purpose of this file?"
- "Why is this approach used?"

**How to respond:**

1. Check the PR description for author's stated rationale
2. Look at commit messages for context
3. Analyze the code changes for implicit reasons
4. If unclear, say "Based on the changes, it appears..." rather than guessing

### Contextual Analysis

When answering questions:

1. Reference specific lines/files from the PR
2. Quote relevant code snippets
3. Explain the relationship between changes
4. Connect to broader patterns in the codebase

**Example:**

```
User: "Why is the token validation moved here?"

Claude: Looking at the PR, the token validation was moved from
`middleware/auth.ts:45` to `services/AuthService.ts:78`.

Based on the commit message "centralize auth logic", this appears to
consolidate validation into the service layer. The middleware now
calls `AuthService.validateToken()` rather than having its own logic.

This follows the pattern used elsewhere - see `UserService.validateUser()`
at `services/UserService.ts:32` which uses the same approach.
```

### Distinguishing PR Changes vs Existing Code

Always be clear about what's new vs. existing:

- **New in this PR:** Code added or modified in the current diff
- **Existing code:** Code that was already in the codebase before this PR

Use phrases like:

- "This PR introduces..." for new changes
- "The existing code at X does..." for context
- "This changes the previous behavior from X to Y..."

### Referencing Related Code

When explaining patterns or decisions:

1. Search for similar patterns in the codebase (use Grep/Glob)
2. Reference existing implementations: "Similar to how `UserService` handles
   this at line X"
3. Point out deviations: "Note this differs from the pattern at Y"
4. Link to relevant files for context

### Recording Q&A

After answering a substantive question:

1. Record it in the review state for reference
2. The Q&A history helps maintain context across sessions
3. Previous Q&A can inform future answers

---

## Step 7: Human Approval Gate

**⚠️ IMPORTANT: Do NOT post any comments until explicitly approved.**

Present findings and wait for feedback:

```markdown
---

## Ready to Submit?

**Summary:** Solid implementation! Left suggestions around rate limiting and
configurability.

**Proposed comments:** 3 **Recommendation:** Approve

---

You can:

- Modify wording: "change #1 to say..."
- Skip comments: "skip 2" or "only post 1, 3"
- Change review type: "request changes instead"

**Actions:**

- "post 1, 3" - post specific comments
- "post all" - post all comments
- "a" - approve | "b" - request changes | "c" - comment only
- "post all then a" - post comments and approve

When ready, just say what you want (e.g., "post all then a").
```

---

## Step 8: Execute Review

Only after approval, execute:

### Post Comments

For each approved comment:

```bash
speck-review comment <file> <line> "<message>"
```

### Submit Review

```bash
# Keep review body SHORT - detailed feedback is in line comments
speck-review review approve "Short summary here."

# Or for changes requested:
speck-review review request-changes "Please address the comments above."
```

### Reply to Existing Comments (if needed)

```bash
speck-review comment-reply <comment_id> "<reply>"
```

---

## CLI Reference

```bash
# Navigation
speck-review files                         # List changed files with links

# Guided Review
speck-review analyze [pr]                  # Analyze PR with clustering, output JSON
speck-review state [show|clear]            # Show or clear review session state
speck-review check-self-review <author>    # Check if reviewing own PR
speck-review spec-context                  # Load Speck spec for current branch

# Comments
speck-review comment <file> <line> <body>  # Add line comment
speck-review comment-reply <id> <body>     # Reply to existing comment
speck-review comment-delete <id>           # Delete a comment
speck-review list-comments                 # List all PR comments

# Review
speck-review review approve [body]         # Approve PR
speck-review review request-changes <body> # Request changes
speck-review review comment [body]         # Comment without approval

# Utility (FR-027)
speck-review link <file> [line]            # Generate navigation link
speck-review actions                       # Display navigation action menu
speck-review run-actions                   # Display review action menu
speck-review review-table [--example]      # Generate formatted comment table
speck-review submit-actions [body]         # Display submit review menu
speck-review logs                          # Display log file locations
```

---

## Speck-Aware Context

When a Speck specification exists for the branch:

1. The `spec-context` command returns parsed requirements and user stories
2. Reference spec requirements in comments: "This implements FR-003"
3. Note alignment or misalignment with spec acceptance criteria
4. Suggest spec updates if implementation differs

If no spec exists, proceed with standard review (graceful degradation per FR-022).

---

## Fork PR Limitations

When reviewing PRs from forks:

- Line comments may fail due to GitHub permissions
- Use issue comments instead: `gh pr comment <PR_NUMBER> --body "<message>"`
- The CLI handles this automatically in self-review mode
- Inform the user if fork limitations are encountered

---

## Output Formats by Context

### Webview Format (VSCode Extension)

Use **relative file links** for navigation and **numbered commands** for
actions:

```markdown
### Suggested Comments

| # | Location                                                              | Comment                                              |
| - | --------------------------------------------------------------------- | ---------------------------------------------------- |
| 1 | [src/services/auth.ts:42](src/services/auth.ts#L42)                   | Consider adding rate limiting to prevent brute force |
| 2 | [src/services/auth.ts:78](src/services/auth.ts#L78)                   | Nit: JWT_EXPIRY should be configurable via env var   |
| 3 | [src/middleware/requireAuth.ts:23](src/middleware/requireAuth.ts#L23) | Might be worth logging failed auth attempts          |

**To post comments:** Tell me which ones (e.g., "post 1, 3" or "post all") **To
skip comments:** "skip 2" or "only post 1"
```

After user says "post 1, 3":

```bash
speck-review comment src/services/auth.ts 42 "Consider adding rate limiting to prevent brute force"
speck-review comment src/middleware/requireAuth.ts 23 "Might be worth logging failed auth attempts"
```

### Terminal Format (CLI)

Same numbered format works:

```markdown
### Suggested Comments

| # | File:Line                        | Comment                                              |
| - | -------------------------------- | ---------------------------------------------------- |
| 1 | src/services/auth.ts:42          | Consider adding rate limiting to prevent brute force |
| 2 | src/services/auth.ts:78          | Nit: JWT_EXPIRY should be configurable via env var   |
| 3 | src/middleware/requireAuth.ts:23 | Might be worth logging failed auth attempts          |

**To post:** "post 1, 3" or "post all"
```

### Quick Actions (Both Contexts)

Use numbered/lettered shortcuts for common actions:

```markdown
### Actions

(a) Approve PR (b) Request changes (c) Comment only (no approval)

Say "a" to approve, or "post 1, 2 then a" to post comments and approve.
```

---

## Complete Example Session

This example shows a typical review workflow.

**User:** Review PRs

**Claude:**

```markdown
Found 2 PRs requiring your review:

1. **#142** "Add user authentication" by @alice (requested 2 days ago)
2. **#138** "Fix payment processing bug" by @bob (requested 5 days ago)

Which PR would you like to review?
```

**User:** 1

**Claude:** _checks out PR, runs analyze, examines diff_

```markdown
## PR #142: Add user authentication

### Summary

This PR adds JWT-based authentication to the API:

- New `AuthService` class with login/register/token refresh
- User model extended with `passwordHash` and `refreshToken` fields
- Protected route middleware
- Login/register/logout endpoints

**New Dependencies:**

- ✅ `jsonwebtoken` (12M weekly downloads, active)
- ✅ `bcrypt` (5M weekly downloads, active)

**Breaking Changes:** None

---

### Review Order

1. [prisma/migrations/20240115_auth.sql](prisma/migrations/20240115_auth.sql) -
   Schema migration
2. [src/types/auth.ts](src/types/auth.ts) - New types
3. [src/services/AuthService.ts](src/services/AuthService.ts) - Core auth logic
   ⭐
4. [src/middleware/requireAuth.ts](src/middleware/requireAuth.ts) - Route
   protection
5. [src/routes/auth.ts](src/routes/auth.ts) - Endpoints
6. [tests/auth.test.ts](tests/auth.test.ts) - Test coverage

---

### Suggested Comments

| # | Location                                                              | Comment                                                                |
| - | --------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| 1 | [src/services/AuthService.ts:42](src/services/AuthService.ts#L42)     | Consider adding rate limiting on login attempts to prevent brute force |
| 2 | [src/services/AuthService.ts:78](src/services/AuthService.ts#L78)     | Nit: JWT_EXPIRY should be configurable via environment variable        |
| 3 | [src/middleware/requireAuth.ts:23](src/middleware/requireAuth.ts#L23) | Might be worth logging failed auth attempts for security monitoring    |

---

### Ready to Submit?

**Summary:** Clean auth implementation. Left minor suggestions around rate
limiting and configurability.

**Comments:** 3 | **Recommendation:** Approve

**Actions:**

- "post 1, 3" - post specific comments
- "post all" - post all comments
- "skip 2" - exclude from posting
- "a" - approve | "b" - request changes | "c" - comment only
- "post all then a" - post comments and approve
```

**User:** Skip 2, post the rest and approve

**Claude:**

```bash
speck-review comment src/services/AuthService.ts 42 "Consider adding rate limiting on login attempts to prevent brute force"
speck-review comment src/middleware/requireAuth.ts 23 "Might be worth logging failed auth attempts for security monitoring"
speck-review review approve "Clean auth implementation! Left minor suggestions around rate limiting and logging."
```

```markdown
✅ Posted comment on src/services/AuthService.ts:42
✅ Posted comment on src/middleware/requireAuth.ts:23
✅ Approved PR #142
```
