---
name: cr-pr
description: PR review comment management. Use when user wants to view or address PR review comments from any source.
triggers:
  - "pr comments"
  - "review feedback"
  - "address reviews"
  - "coderabbit comments"
  - "pr review comments"
  - "unresolved comments"
  - "review comments on my pr"
  - "fix pr feedback"
  - "what feedback on my pr"
  - "show pr reviews"
  - "pending review comments"
  - "resolve review comments"
  - "check my pr"
---

# PR Review Comment Management

When the user wants to view or address review comments on a pull request, delegate to the `cr-pr-manager` subagent.

## When to Use

Use this skill when the user:
- Asks about PR comments or review feedback
- Wants to see unresolved review comments
- Mentions CodeRabbit comments on a PR
- Wants to address or resolve review feedback
- Asks about comments from reviewers (bots or humans)

## What the Subagent Handles

The `cr-pr-manager` subagent will:

1. **Identify PR**
   - Auto-detect from current branch
   - Or use specified PR number

2. **Fetch ALL Comments**
   - CodeRabbit comments via MCP
   - GitHub review comments (other bots)
   - GitHub reviews (human reviewers)

3. **Categorize by Reviewer**
   - CodeRabbit (AI review bot)
   - Other bots (SonarCloud, Codacy, Snyk, etc.)
   - Human reviewers (team members)

4. **Present Comments**
   - Group by reviewer, then by severity/file
   - Show resolution status
   - Include file paths and line numbers

5. **Interactive Actions**
   - View full comment details
   - Apply suggested fixes
   - Mark as resolved
   - Reply to comments
   - Filter by reviewer/file/severity

## Comment Sources

This skill aggregates feedback from multiple sources:
- **CodeRabbit MCP**: AI review comments with fix suggestions
- **GitHub API**: Human reviewer comments and other bot feedback

## Example Triggers

- "Show me the PR review comments"
- "What are the unresolved comments on my PR?"
- "Help me address the CodeRabbit feedback"
- "Are there any review comments I need to fix?"
