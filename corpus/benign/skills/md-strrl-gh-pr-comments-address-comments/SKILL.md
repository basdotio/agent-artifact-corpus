---
name: address-comments
description: Help address GitHub PR review comments. Use when the user mentions PR reviews, code review feedback, reviewer comments, or needs to resolve review threads.
allowed-tools: Bash(gh pr-comments:*), Bash(gh issue create:*), Read, Edit, Grep, Glob, AskUserQuestion, mcp__conductor__AskUserQuestion
---

# Addressing PR Review Comments

This skill helps you work with GitHub PR review comments using the `gh-pr-comments` CLI extension.

> **IMPORTANT**: Always use the `AskUserQuestion` tool to get user confirmation before making any changes or decisions. Never act autonomously on review comments without explicit user approval.

## Comment Types

There are two types of comments on a PR:

1. **review_comment** (inline): Attached to specific lines of code
   - Have a file path and line number
   - Can be marked as resolved
   - May be "outdated" if the code has changed

2. **issue_comment** (general): Not attached to code
   - Appear in the PR conversation
   - Cannot be resolved (only hidden)
   - **IMPORTANT**: Some reviewers (like Claude Code) post review feedback as issue comments. These should be treated the same as review comments - analyze the feedback, make changes, and reply accordingly.

## Available Commands

```bash
# List unresolved comments (resolved hidden by default)
gh pr-comments list

# List all comments including resolved
gh pr-comments list --all

# Show hierarchical tree view
gh pr-comments tree

# View full details of a comment
gh pr-comments view <comment-id>

# Reply to a comment
gh pr-comments reply <comment-id> --body "message"

# Mark comments as resolved
gh pr-comments resolve <comment-id> [comment-id...]

# Hide (minimize) comments
gh pr-comments hide <comment-id> --reason resolved

# Clean up reviews with all comments resolved
gh pr-comments cleanup
```

## Workflow for Addressing Comments

1. **List**: Start with `gh pr-comments list --json` to see all comments (both review_comment and issue_comment types)
2. **Identify actionable feedback**:
   - For `review_comment`: These are always actionable code review feedback
   - For `issue_comment`: Check if the content contains review feedback or suggestions that require code changes. Reviewers like Claude Code often post detailed reviews as issue comments.
3. **Understand**: Use `gh pr-comments view <id>` to see full context including diff (for review_comment) or full message (for issue_comment)
4. **Ask User (REQUIRED)**: **You MUST use the `AskUserQuestion` tool** to let the user choose how to handle each actionable comment. Never skip this step or make assumptions:
   - **Fix it now** - Make code changes, reply, and resolve/hide
   - **Fix it later** - Create a GitHub issue to track, reply with link, optionally resolve/hide
   - **No changes needed** - Reply explaining why, then resolve/hide
5. **Execute**: Based on user choice, take the appropriate action
6. **Reply**: **IMPORTANT** - Always reply before resolving/hiding. Explain what was done or why no changes were made
7. **Resolve/Hide**:
   - For `review_comment`: Use `gh pr-comments resolve <id>` to mark as resolved
   - For `issue_comment`: Use `gh pr-comments hide <id> --reason resolved` to minimize (issue comments cannot be resolved)

### Handling "Fix it now"

When the user wants to address the comment immediately:
```bash
# 1. Make the code changes using Edit tool

# 2. Reply explaining what was fixed
gh pr-comments reply <id> --body "Fixed: <brief description of what was changed>"

# 3. Mark as resolved
gh pr-comments resolve <id>
```

### Handling "Fix it later"

When the user chooses to defer a fix:
```bash
# Create a GitHub issue to track the work
gh issue create --title "<concise-title>" --body "From PR review: <link-to-comment>

<description of what needs to be done>"

# Reply to the comment with the issue link
gh pr-comments reply <id> --body "Tracked in #<issue-number>"

# Optionally resolve the comment
gh pr-comments resolve <id>
```

### Handling "No changes needed"

When the suggested change is not appropriate:
```bash
# Reply with explanation
gh pr-comments reply <id> --body "No changes needed: <clear explanation>"

# Resolve the comment
gh pr-comments resolve <id>
```

## CRITICAL: Always Use AskUserQuestion

**You MUST use the `AskUserQuestion` tool before taking any action on a comment.** Never assume what the user wants - always ask first.

Use `AskUserQuestion` to:
- Let the user choose how to handle each comment (fix now, fix later, or no changes needed)
- Confirm code changes before applying them
- Validate your understanding of reviewer feedback
- Get user approval before resolving or hiding comments

**DO NOT** make decisions on behalf of the user. Even if a fix seems obvious, always present it and get explicit confirmation.

## Best Practices

- **ALWAYS use AskUserQuestion** before deciding how to handle a comment
- Group related comments by file and address them together
- Read the surrounding code context, not just the commented line
- If a comment is a question, reply instead of making code changes
- Be respectful and professional in all replies
- Provide clear explanations for decisions
- Use `--json` flag for programmatic parsing
- After resolving all comments in a review, use `cleanup` to minimize the review
