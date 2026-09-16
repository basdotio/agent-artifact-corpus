---
name: pr-review-helper
description: "Gather PR review context: all comments (including review suggestions), diff context, and CI status; download GitHub Actions logs on failures. Prefer GitHub MCP for reads, fall back to gh CLI when needed."
---

# pr-review-helper

Collect baseline information for PR review with minimal back-and-forth. Prefer GitHub MCP for all reads; if MCP lacks data or is unavailable, fall back to `gh` CLI.

## Required Inputs

- Repository owner/name
- PR number

If any are missing, ask the user once. Do not guess.

## Workflow (Prefer GitHub MCP)

1. **PR overview**
   - Use `mcp__github__pull_request_read` with `method: get` to capture title, author, base/head branches, and head SHA.

2. **All comments and review suggestions**
   - Review comment threads: `mcp__github__pull_request_read` with `method: get_review_comments`.
     - Extract: file path, line, author, body.
     - If a suggestion block exists, capture the suggested patch and map it to the diff hunk.
   - Review summary: `mcp__github__pull_request_read` with `method: get_reviews`.
     - Capture approvals, change requests, and top-level review bodies.
   - PR/issue comments: `mcp__github__pull_request_read` with `method: get_comments`.
     - Include non-review discussion.

3. **Diff context**
   - Use `mcp__github__pull_request_read` with `method: get_diff` for full diff.
   - If the diff is large, also request `method: get_files` to scope by file before drilling into relevant hunks.

4. **CI status**
   - Use `mcp__github__pull_request_read` with `method: get_status` for the head SHA.
   - Identify failing checks. If failures appear to be GitHub Actions, proceed to logs.

5. **GitHub Actions logs (when failures exist)**
   - If MCP does not provide sufficient log details, fall back to `gh` CLI.
   - Suggested flow:
     - `gh pr checks <PR>` to list failing runs and run IDs.
     - `gh run view <run-id> --log-failed` to extract the failure reason.
     - If logs are truncated or need full context:
       - `gh run download <run-id>` then inspect the downloaded logs.

## TiDB-specific CI heuristics

Apply these rules when the repository is `pingcap/tidb` or a TiDB fork:

- If the diff does not touch parser-related files, treat parser test failures as likely flaky noise and do not block on them unless the logs show a direct causal link to the change.
- Treat `fast_test_tiprow`, `idc-jenkins-ci-tidb/unit-test`, and `pull-build-next-gen` as equivalent unit-test surfaces. Summarize them as one signal instead of three independent blockers.
- If any one of those equivalent jobs is the blocker and the failure looks flaky or infra-related, recommend replying `/retest` immediately instead of waiting for the other two to finish or fail.
- While CI is pending or rerunning, do not keep the user blocked on the same PR. Suggest switching to another ready issue, review, or coding task and come back when fresh CI signal arrives.

## Fallback Workflow (gh CLI Only)

Use this when MCP is unavailable or incomplete.

1. **PR overview**
   - `gh pr view <PR> --json title,author,baseRefName,headRefName,headRefOid`

2. **Comments and review threads**
   - `gh pr view <PR> --json comments,reviews,reviewThreads`
   - Parse `reviewThreads` for file/line and suggestion blocks.

3. **Diff**
   - `gh pr diff <PR>`

4. **CI status and logs**
   - `gh pr checks <PR>`
   - `gh run view <run-id> --log-failed`
   - `gh run download <run-id>` if full logs are needed

## Output Expectations

Provide a concise summary with:

- Review comments grouped by file/line, including suggestion patches if present
- Non-review discussion comments that may affect changes
- CI status: pass/fail, failing jobs, and key error messages
- For TiDB PRs, separate likely ignorable flaky failures from actionable failures
- Clear action items for the PR author

Do not post new comments, re-run CI, or update the PR unless the user explicitly asks.
