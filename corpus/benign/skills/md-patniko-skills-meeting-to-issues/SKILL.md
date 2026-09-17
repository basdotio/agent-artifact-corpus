---
name: meeting-to-issues
description: Parse meeting transcripts to extract action items and create GitHub issues after user confirmation. Converts discussions into trackable work items.
license: MIT
compatibility: Requires gh CLI authenticated with repo access.
metadata:
  author: patrick
  version: "1.0"
allowed-tools: bash gh jq
---

# Meeting to Issues

Transform meeting transcripts into structured GitHub issues with intelligent action item extraction.

## When to Use

- After team meetings, planning sessions, or retrospectives
- Converting recorded decisions into trackable work
- Extracting action items from standup notes or async discussions
- Creating issues from Zoom/Teams/Slack transcripts

## Workflow

### Step 1: Share the Transcript

Provide the meeting transcript in any format:
- Copy-paste from Zoom/Teams/Google Meet
- Upload a text file
- Share meeting notes from Notion/Confluence
- Paste Slack thread content

### Step 2: Extract & Review Issues

The agent will:
1. Parse the transcript for action items, decisions, and tasks
2. Generate proposed GitHub issues with:
   - Clear, actionable titles
   - Detailed descriptions with context
   - Suggested labels (bug, enhancement, task, etc.)
   - Priority indicators
   - Assignee suggestions (if mentioned)
   - Links to related issues (if discussed)

3. Present issues for your review in a readable format

### Step 3: Confirm & Create

Review the proposed issues and either:
- **Approve all** - Create all issues as-is
- **Edit specific issues** - Modify titles, descriptions, or labels
- **Remove issues** - Exclude items that shouldn't be tracked
- **Add issues** - Include anything the agent missed

Once confirmed, the agent creates all issues in your specified repository.

## Analysis Criteria

The agent evaluates transcript content to identify:

### Actionable Items
- Explicit assignments: "John will fix the auth bug"
- Todo items: "We need to update the docs"
- Decisions requiring implementation: "Let's add dark mode support"
- Bugs reported: "Users are seeing timeout errors"
- Feature requests: "Can we add export to CSV?"

### Context Extraction
- **Who**: People mentioned in connection with tasks
- **What**: Technical details, requirements, acceptance criteria
- **Why**: Business justification, user impact
- **When**: Deadlines or urgency indicators
- **Where**: Components, files, or systems mentioned

### Intelligent Labeling
- `bug` - Error reports, crashes, broken functionality
- `enhancement` - New features, improvements
- `documentation` - Docs updates, README changes
- `task` - General work items, refactoring
- `question` - Clarifications needed, open discussions
- `urgent` - Time-sensitive items
- `blocked` - Dependencies mentioned

## Example Usage

**Input transcript:**
```
[10:00] Sarah: The login page is throwing 500 errors for Gmail users.
[10:01] Mike: I can look into that today. Probably an OAuth scope issue.
[10:02] Sarah: Thanks. Also, we should add the export feature users have been requesting.
[10:03] Mike: Good idea. Maybe that's a separate story though.
[10:04] Sarah: Agreed. Let's also update the API docs - they're outdated.
[10:05] Mike: I'll handle the login bug. Can you or Alex take the docs?
```

**Proposed issues:**

1. **Fix 500 errors on login for Gmail users**
   - Description: Users authenticating with Gmail are encountering 500 errors on the login page. Initial investigation suggests this may be an OAuth scope configuration issue.
   - Labels: `bug`, `urgent`
   - Suggested assignee: Mike
   - Priority: High

2. **Add data export feature**
   - Description: Users have requested the ability to export their data. Discussed in standup - should be tracked as a separate feature request.
   - Labels: `enhancement`
   - Priority: Medium

3. **Update API documentation**
   - Description: The API documentation is currently outdated and needs to be refreshed to reflect the current state of the API.
   - Labels: `documentation`
   - Suggested assignee: Sarah or Alex
   - Priority: Medium

### Step 4: Create Issues

After confirmation:

```bash
Creating issues in owner/repo...
✓ #123 Fix 500 errors on login for Gmail users
✓ #124 Add data export feature  
✓ #125 Update API documentation

Created 3 issues successfully.
```

## Data Format

Issues are structured as JSON before creation:

```json
{
  "issues": [
    {
      "title": "Fix 500 errors on login for Gmail users",
      "body": "Users authenticating with Gmail are encountering 500 errors...",
      "labels": ["bug", "urgent"],
      "assignee": "mike",
      "priority": "high",
      "reasoning": "Explicit bug report with technical details and assignee mentioned"
    }
  ]
}
```

## Best Practices

### For Better Results
- Include full context in transcripts (who said what)
- Mention specific components, files, or systems
- Note any explicit assignments or deadlines
- Include technical details (error messages, versions, etc.)

### Review Checklist
- ✓ Titles are clear and actionable
- ✓ Descriptions have enough context for someone not in the meeting
- ✓ Labels accurately categorize the work
- ✓ No duplicate issues with existing backlog
- ✓ Priorities reflect actual urgency
- ✓ Assignees are correct (or left unassigned)

## Safety Features

- **No automatic creation** - Issues only created after explicit approval
- **Review phase** - All issues presented for editing before submission
- **Dry-run option** - Preview what would be created without committing
- **Rollback support** - Issues created in batch can be closed if needed
- **Audit trail** - All created issues link back to the meeting/transcript

## Configuration

The skill can be customized per repository:

```bash
# Create in a specific repo
Repository: owner/repo

# Apply custom label mappings
Label mapping: bug → incident, enhancement → feature-request

# Default assignees
Default assignee: None (leave unassigned)

# Auto-apply labels
Additional labels: from-meeting, needs-refinement
```

## Files

```
meeting-to-issues/
├── SKILL.md              # This file
├── scripts/
│   ├── parse.sh          # Extract action items from transcript
│   ├── create-issues.sh  # Batch create issues via gh CLI
│   └── preview.sh        # Show what would be created
├── transcript.txt        # User-provided transcript (git-ignored)
├── proposed-issues.json  # Extracted issues (git-ignored)
└── created-issues.json   # Created issue references (git-ignored)
```

## Notes

- Requires `gh` CLI authenticated with write access
- Run `gh auth status` to verify permissions
- Supports Markdown formatting in issue bodies
- Can handle multiple meeting formats (timestamps optional)
- Works with partial transcripts or bullet-point notes
- Agent will ask clarifying questions if context is unclear

## Limitations

- Cannot auto-assign to users not in the repository
- Labels must exist in target repository (creates standard ones if missing)
- Long transcripts may need to be split for optimal parsing
- Highly ambiguous discussions may require manual clarification
