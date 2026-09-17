---
name: issue-workflow
description: Provides guidance on issue/ticket workflow management during development sessions. Supports multiple project management providers (Linear, JIRA, etc.). Use when working on issues, updating tickets, or managing state transitions.
---

# Issue Workflow Management

This skill guides you through managing issue/ticket states during development work across multiple project management providers.

## RFC2119 Keywords

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC2119.

## Supported Providers

| Provider | URL Pattern | MCP Required |
|----------|-------------|--------------|
| Linear | `https://linear.app/*/issue/*` | `linear@claude-plugins-official` |
| JIRA | `https://*.atlassian.net/browse/*` | JIRA MCP (Atlassian) |

## State Transition Requirements

1. **Start of work**: You MUST move the issue to "In Progress" (or equivalent started state)
2. **During work**: You SHOULD add comments for significant progress or blockers
3. **Completion**: You MUST move the issue to "Done" (or equivalent completed state) with completion notes

## When to Update Issues

You MUST update issues:
- When starting work on an issue
- When completing work

You SHOULD update issues:
- When encountering blockers or changing approach
- When acceptance criteria change

## Provider Detection

You MUST automatically detect providers from these formats:

### URL-Based (Highest Priority)
- Linear: `https://linear.app/*/issue/*`
- JIRA: `https://*.atlassian.net/browse/*` or `https://*.jira.com/browse/*`

### Issue ID Pattern
- Pattern: `[A-Z]{2,10}-\d+` (e.g., CIR-123, PROJ-456)
- This pattern MAY match multiple providers
- If ambiguous, check context or ask user

## MCP Availability

Before performing any operation, you MUST verify the required MCP is available.

If MCP is NOT available:
```
The [Provider] MCP is not configured. To enable issue tracking:
1. Install the plugin: `claude plugin install [provider]@claude-plugins-official`
2. Authenticate when prompted

Would you like to continue without issue tracking?
```

You MUST NOT attempt to call unavailable MCP tools.

## Provider-Specific Tool Reference

### Linear MCP Tools

```json
// Get issue
mcp__plugin_linear_linear__get_issue({ "id": "CIR-123" })

// List team statuses
mcp__plugin_linear_linear__list_issue_statuses({ "team": "team-id" })

// Update issue
mcp__plugin_linear_linear__update_issue({ "id": "uuid", "state": "In Progress" })

// Add comment
mcp__plugin_linear_linear__create_comment({ "issueId": "uuid", "body": "Comment" })
```

### JIRA MCP Tools

```json
// Get issue
mcp__atlassian_jira__get_issue({ "issueKey": "PROJ-456" })

// Get transitions
mcp__atlassian_jira__get_transitions({ "issueKey": "PROJ-456" })

// Transition issue
mcp__atlassian_jira__transition_issue({ "issueKey": "PROJ-456", "transitionId": "21" })

// Add comment
mcp__atlassian_jira__add_comment({ "issueKey": "PROJ-456", "body": "Comment" })
```

## Workflow Commands

- `/issue-work [issue-id-or-url]` - Start working on an issue (moves to In Progress)
- `/issue-update [comment]` - Add progress update or modify issue
- `/issue-done [comment]` - Complete work (moves to Done)

## Session Context

You MUST track within the conversation:
- The active issue ID
- The provider being used

Output format: `Active issue: [ID] ([Provider])`

This enables subsequent commands without re-specifying the issue or provider.
