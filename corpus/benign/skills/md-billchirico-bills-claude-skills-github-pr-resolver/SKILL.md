---
name: github-pr-resolver
description: "Resolve GitHub PR review comments and fix failing CI checks. Creates a team with teammates to process threads in parallel, tracks ALL threads across ALL pages, processes each with individual commits, marks each resolved immediately, and verifies all resolved + CI passing before completion."
---

# GitHub PR Resolver

Process **ALL** PR review comments, make fixes, resolve threads immediately, and ensure CI passes.

## Critical Rules

1. **Fetch ALL pages** - GitHub returns max 100 items per request. Always paginate until `hasNextPage: false`
2. **Track with todos** - Create a `TaskCreate` item for each unresolved thread before processing
3. **One commit per thread** - Never batch fixes into a single commit
4. **Resolve immediately** - Mark each thread resolved on GitHub RIGHT AFTER fixing it, not at the end
5. **CI must pass** - Task is NOT complete until all CI checks are green. Fix failures and retry.
6. **USE TEAMMATES (MANDATORY)** - You MUST create a team with `TeamCreate`, spawn teammates with the `Task` tool using `team_name`, and coordinate via the shared task list. Teammates work in parallel automatically. Do NOT use `run_in_background` agents.

## API Access

**Prefer GitHub MCP when available**, fall back to `gh` CLI.

| Operation      | MCP Tool                                 | CLI Fallback              |
| -------------- | ---------------------------------------- | ------------------------- |
| Read PR        | `mcp__github__pull_request_read`         | `gh pr view`              |
| Resolve thread | `mcp__github__pull_request_review_write` | `gh api graphql` mutation |
| Check status   | Included in PR read                      | `gh pr checks`            |

## Workflow

### Step 1: Fetch ALL Threads (with Pagination)

```
1. Fetch PR details and review threads
2. Check hasNextPage - if true, fetch next page with cursor
3. Repeat until hasNextPage is false
4. Count total unresolved threads across ALL pages
```

**MCP:**

```
mcp__github__pull_request_read(owner, repo, pullNumber)
-> Check response for pagination, fetch additional pages if needed
```

**CLI (GraphQL):**

```bash
gh api graphql -f query='
query($owner: String!, $repo: String!, $prNumber: Int!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $prNumber) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo { hasNextPage, endCursor }
        nodes {
          id, isResolved, path, line
          comments(first: 10) { nodes { body, author { login } } }
        }
      }
    }
  }
}' -f owner=OWNER -f repo=REPO -F prNumber=NUMBER
```

### Step 2: Create Team and Task List

**First, create a team:**

```
TeamCreate:
  team_name: "pr-resolver-<prNumber>"
  description: "Resolve PR #<prNumber> review threads"
```

**Then, for each unresolved thread (`isResolved: false`), create a task in the team's task list:**

```
TaskCreate:
  subject: "[#] <path>:<line> - <summary> (@<author>)"
  description: |
    Thread ID: <id>
    Author: @<author>
    Link: https://github.com/<owner>/<repo>/pull/<prNumber>#discussion_r<commentId>
    Comment: <body>
    Repository: <owner>/<repo>
    PR Number: <prNumber>
    Branch: <branch>
    File: <path>
    Line: <line>
  activeForm: "Resolving <path>:<line> (@<author>)"
```

**Building the comment link:**

- Extract `commentId` from the first comment's `id` field (the numeric portion after the last `/` or the `databaseId`)
- Format: `https://github.com/<owner>/<repo>/pull/<prNumber>#discussion_r<commentId>`

**GraphQL to get comment IDs:**

```bash
gh api graphql -f query='
query($owner: String!, $repo: String!, $prNumber: Int!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $prNumber) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo { hasNextPage, endCursor }
        nodes {
          id, isResolved, path, line
          comments(first: 1) {
            nodes {
              databaseId
              body
              author { login }
            }
          }
        }
      }
    }
  }
}' -f owner=OWNER -f repo=REPO -F prNumber=NUMBER
```

Verify with `TaskList` - count must match total unresolved from Step 1.

### Step 3: Spawn Teammates to Process Threads in Parallel

> **CRITICAL: USE TEAMMATES FOR PARALLEL PROCESSING**
>
> You MUST spawn teammates using the `Task` tool with the `team_name` parameter.
> Teammates automatically work in parallel, pick up tasks from the shared task list,
> and send you messages when they complete or need help.

**Workflow:**

```
1. Group threads by file (threads in the same file go to one teammate)
2. Spawn one teammate per file group using Task tool with team_name
3. Each teammate independently:
   a. Claims and starts task: TaskUpdate(taskId, owner: "<teammate-name>", status: "in_progress")
   b. Reads file, makes fix
   d. git add [file] && git commit -m "[type]([scope]): [description]"
   e. Resolves thread on GitHub immediately
   f. Verifies isResolved: true
   g. Marks completed: TaskUpdate(taskId, status: "completed")
   h. Checks TaskList for more unassigned tasks
   i. Sends message to team lead when all assigned tasks are done
4. Receive automatic messages from teammates as they complete
5. Handle any failures by messaging the teammate or spawning a new one
```

**Spawning teammates (ALL in a SINGLE message for parallel execution):**

When you have 3 files to fix, spawn THREE teammates in ONE message:

```
YOUR SINGLE RESPONSE MUST CONTAIN:
+--------------------------------------------------------------+
|  Task #1: subagent_type="general-purpose"                    |
|           team_name="pr-resolver-<prNumber>"                 |
|           name="resolver-utils"                              |
|           description="Fix PR threads in src/utils.ts"       |
|           prompt="[teammate instructions for file 1]"        |
+--------------------------------------------------------------+
|  Task #2: subagent_type="general-purpose"                    |
|           team_name="pr-resolver-<prNumber>"                 |
|           name="resolver-api"                                |
|           description="Fix PR threads in src/api.ts"         |
|           prompt="[teammate instructions for file 2]"        |
+--------------------------------------------------------------+
|  Task #3: subagent_type="general-purpose"                    |
|           team_name="pr-resolver-<prNumber>"                 |
|           name="resolver-models"                             |
|           description="Fix PR threads in src/models.ts"      |
|           prompt="[teammate instructions for file 3]"        |
+--------------------------------------------------------------+
```

**Teammate prompt template:**

> **IMPORTANT:** Before spawning teammates, read the team config file at
> `~/.claude/teams/pr-resolver-<prNumber>/config.json` to get your own leader name.
> Inject that name into the prompt template below as `[leaderName]`.

```
You are a teammate on the "pr-resolver-<prNumber>" team.
Your job is to fix PR review threads and resolve them.

Repository: [owner]/[repo]
PR Number: [prNumber]
Branch: [branch]
Team Lead: [leaderName]

Your assigned threads (all in the same file):

Thread 1:
- Task ID: [taskId]
- Thread ID: [threadId]
- File: [path]
- Line: [line]
- Comment: [body]
- Author: @[author]

[...repeat for each thread in this file...]

Instructions for EACH thread:
1. Claim task: TaskUpdate(taskId: "[taskId]", owner: "<your-name>", status: "in_progress")
2. Read the file and understand the context
3. Make the fix requested in the comment
4. Commit: git add [path] && git commit -m "[type]([scope]): [description]"
5. Resolve thread on GitHub using gh CLI:
   gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "[threadId]"}) { thread { isResolved } } }'
6. Verify resolution succeeded
7. Mark completed: TaskUpdate(taskId: "[taskId]", status: "completed")

After all threads are done:
8. Check TaskList for any remaining unassigned tasks you can pick up
9. Send a message to the team lead reporting completion:
   SendMessage(type: "message", recipient: "[leaderName]", content: "All threads resolved for [path]", summary: "Completed [path] threads")
```

**Parallelization rules:**

- **ALL teammate spawns MUST be in ONE message** - This is the ONLY way to start them concurrently
- Threads in the same file: send to a single teammate to avoid conflicts
- Each teammate commits and resolves independently
- Teammates go idle between turns - this is normal, they are waiting for input
- Messages from teammates are delivered to you automatically

**WRONG (sequential - do NOT do this):**
```
Message 1: Task(team_name=...) for file A
Message 2: Task(team_name=...) for file B  <- waits for A to finish first
Message 3: Task(team_name=...) for file C  <- waits for B to finish first
```

**CORRECT (parallel - do THIS):**
```
Message 1: Task for file A + Task for file B + Task for file C  <- all start concurrently
```

**Resolve thread (MCP):**

```
mcp__github__pull_request_review_write(owner, repo, pullNumber, threadId, action: "RESOLVE")
```

**Resolve thread (CLI):**

```bash
gh api graphql -f query='
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread { id, isResolved }
  }
}' -f threadId="<THREAD_ID>"
```

**Verify resolution succeeded:**

```bash
gh api graphql -f query='
query($threadId: ID!) {
  node(id: $threadId) {
    ... on PullRequestReviewThread { isResolved }
  }
}' -f threadId="<THREAD_ID>"
```

### Step 4: Monitor Teammates and Push Changes

**Teammates send messages automatically when they finish:**

```
1. Wait for messages from all teammates (delivered automatically)
2. Check TaskList - all todos should be "completed"
3. If a teammate reports failure, message them with guidance or spawn a replacement
4. When all tasks are complete, push all commits
```

**Push all commits:**

```bash
git push origin $(gh pr view <PR> --json headRefName -q '.headRefName')
```

**Handle conflicts (rare with file-based grouping):**

```bash
# If push fails due to conflicts from parallel commits
git pull --rebase origin <branch>
git push origin <branch>
```

### Step 5: Wait for CI and Fix Failures

**This is a loop - repeat until all checks pass:**

```
1. Wait for CI checks to complete (not just "running")
2. Check status of ALL checks
3. If ANY check fails:
   a. Identify the failure (lint, test, build, types, etc.)
   b. Fix the issue
   c. Commit with appropriate message
   d. Push
   e. Go back to step 1
4. Only proceed when ALL checks show "success" or "skipped"
```

**Check CI status:**

```bash
# Wait for checks to complete (poll until no "pending" or "in_progress")
gh pr checks <PR> --watch

# Or check status directly
gh pr checks <PR> --json name,state,conclusion
```

**Fix patterns for common CI failures:**

```bash
# Lint failures
npm run lint -- --fix && git add . && git commit -m "fix(lint): resolve linting errors"

# Type errors
# Fix the type issues in code
git add . && git commit -m "fix(types): resolve TypeScript errors"

# Test failures
# Fix failing tests or update assertions
git add . && git commit -m "fix(tests): update failing test assertions"

# Build failures
# Fix build issues
git add . && git commit -m "fix(build): resolve build errors"
```

**After each fix, push and wait again:**

```bash
git push origin $(gh pr view <PR> --json headRefName -q '.headRefName')
# Then loop back: wait for CI, check results
```

### Step 6: Shutdown Team and Final Verification

Only proceed here when Step 5 confirms all CI checks pass.

**Shutdown all teammates:**

```
For each teammate:
  SendMessage(type: "shutdown_request", recipient: "<teammate-name>", content: "All work complete, shutting down")
Wait for all teammates to confirm shutdown.
```

**Clean up the team:**

```
TeamDelete  (removes team and task directories)
```

**Verify ALL of the following:**

1. **Zero unresolved threads** - Re-fetch ALL pages (paginate until `hasNextPage: false`):

   ```bash
   gh api graphql -f query='...' # Same query as Step 1
   # Count threads where isResolved: false - must be 0
   ```

2. **All todos completed** - `TaskList` shows all items with status `completed`

3. **All CI checks passing**:
   ```bash
   gh pr checks <PR> --json name,conclusion | jq 'all(.conclusion == "success" or .conclusion == "skipped")'
   # Must return true
   ```

**If verification fails:**

- Unresolved threads remain -> Go back to Step 3
- CI checks failing -> Go back to Step 5
- Todos incomplete -> Review what was missed

## Commit Convention

| Comment Pattern                 | Commit Type |
| ------------------------------- | ----------- |
| Bug fix, null check, validation | `fix`       |
| Add, implement, missing         | `feat`      |
| Rename, refactor, change X to Y | `refactor`  |
| Documentation, comments         | `docs`      |
| Performance                     | `perf`      |
| Style, formatting               | `style`     |

**Scope:** Extract from path - `src/services/User.ts` -> `services`

## Completion Checklist

**The task is NOT complete until ALL boxes can be checked:**

- [ ] Fetched ALL pages (paginated until `hasNextPage: false`)
- [ ] Created team with `TeamCreate`
- [ ] Created task for each unresolved thread
- [ ] Spawned teammates for independent files in parallel (single message, multiple Task calls with `team_name`)
- [ ] All teammates completed successfully (confirmed via messages and TaskList)
- [ ] Each thread was resolved on GitHub **immediately** after fixing
- [ ] All todos show `completed`
- [ ] Each thread has its own commit
- [ ] Changes pushed
- [ ] **ALL CI checks are passing** (success or skipped, no failures)
- [ ] Re-verified: zero unresolved threads across ALL pages
- [ ] Re-verified: CI status shows all green
- [ ] Teammates shut down with `SendMessage` shutdown_request
- [ ] Team cleaned up with `TeamDelete`

**DO NOT mark task complete if CI is still running or failing. Wait and fix.**
