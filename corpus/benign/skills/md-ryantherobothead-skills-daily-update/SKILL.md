---
name: daily-update
description: Draft a daily standup update using a user-specified template and gathered context. Use when preparing for standups, writing async status updates, or summarizing daily progress. Supports context from calendar events, task/issue trackers, free-form notes, and Obsidian daily notes.
---

# Daily Update

Generate a polished daily standup update by gathering context from multiple sources and formatting it according to a user-specified template.

## Usage

When the user requests a daily update, follow this workflow:

1. **Locate the template** - Ask for or find the template file
2. **Gather context** from available sources
3. **Draft the update** following the template structure
4. **Present for review** and iterate if needed

## Template Format

Templates are markdown files with section headers that define the update structure. The agent fills in each section based on gathered context.

### Example Template (Agile Standup)

```markdown
## Yesterday / Since Last Update
<!-- What was accomplished since the last standup -->

## Today / Next
<!-- What you plan to work on -->

## Blockers / Questions
<!-- Anything preventing progress, or questions for the team -->
```

### Example Template (Weekly Summary)

```markdown
## Highlights
<!-- Key accomplishments this week -->

## In Progress
<!-- Work that's ongoing -->

## Upcoming
<!-- What's planned for next week -->

## Risks & Blockers
<!-- Issues that need attention -->
```

### Example Template (Async Update)

```markdown
## Status: 🟢 On Track | 🟡 At Risk | 🔴 Blocked

## Progress
<!-- What moved forward -->

## Next Steps
<!-- Immediate priorities -->

## Need Input On
<!-- Decisions or feedback needed from others -->
```

## Context Sources

Gather information from these sources when available:

### 1. Calendar Events

Look for recent and upcoming calendar entries:
- **Meetings attended** → Evidence of collaboration, decisions made
- **Upcoming meetings** → Context for "Today" plans
- **Recurring syncs** → Regular touchpoints to mention

**How to use:**
- Ask the user about their calendar or check integrated calendar tools
- Note key meetings and their outcomes
- Flag upcoming meetings that relate to current work

### 2. Task/Issue Trackers

Pull from project management tools (Jira, GitHub Issues, Linear, etc.):
- **Recently closed/completed** → "Yesterday" accomplishments
- **In progress items** → "Today" focus areas
- **Blocked items** → Blockers section
- **Newly assigned** → Upcoming work

**How to use:**
- Query for issues updated in the last 24-48 hours
- Check for status transitions (In Progress → Done, etc.)
- Note any issues marked as blocked

### 3. Free-form Notes

User-provided context:
- Bullet points of what they worked on
- Rough notes from the day
- Copy-pasted Slack messages or emails
- Mental notes they want to include

**How to use:**
- Accept raw input from the user
- Synthesize into coherent update items
- Preserve important details while improving clarity

### 4. Obsidian Daily Notes

Parse the user's PersonalLog daily notes for context:
- **`## Notes` section** → Human-written reflections and logs
- **`## Servitor` section** → Previous AI-generated summaries
- **Linked entities** → People involved, projects referenced
- **Tasks/checkboxes** → Completed and pending items

**How to use:**
- Read the current day's note and optionally yesterday's
- Extract completed tasks (checked boxes)
- Note meetings or events mentioned
- Identify blockers or questions raised

## Drafting Process

### Step 1: Gather Context

Collect information from available sources. Not all sources will be available for every update—use what's accessible.

```
Sources checked:
- [ ] Calendar events (past 24h, next 24h)
- [ ] Task tracker (recently updated issues)
- [ ] Free-form notes (user-provided)
- [ ] Obsidian daily notes
```

### Step 2: Categorize Items

Map gathered items to template sections:

| Context Item | Template Section |
|-------------|------------------|
| Completed task | Yesterday/Accomplishments |
| Attended meeting | Yesterday (with outcome) |
| In-progress work | Today/Next |
| Scheduled meeting | Today (as context) |
| Blocked issue | Blockers |
| Question raised | Blockers/Questions |
| New assignment | Today/Upcoming |

### Step 3: Draft Each Section

For each template section:
1. Pull relevant items from categorized context
2. Write concise, action-oriented bullets
3. Include enough detail to be useful without being verbose
4. Link to issues/PRs/docs where helpful

### Step 4: Review and Refine

Before presenting the draft:
- Ensure each section has content (or explicitly note "No blockers")
- Check for appropriate level of detail
- Verify nothing sensitive is included unintentionally
- Confirm the tone matches the intended audience

## Writing Guidelines

### Be Specific, Not Vague

```markdown
# ❌ Vague
- Worked on the API

# ✅ Specific
- Implemented pagination for /api/users endpoint (PR #234)
```

### Focus on Outcomes, Not Just Activity

```markdown
# ❌ Activity-focused
- Had a meeting with the design team

# ✅ Outcome-focused
- Aligned with design on v2 dashboard layout; ready for implementation
```

### Keep It Scannable

- Use bullet points, not paragraphs
- Lead with the most important information
- Keep bullets to 1-2 lines max
- Group related items together

### Acknowledge Blockers Honestly

```markdown
# ❌ Downplaying
- Waiting on some things

# ✅ Clear and actionable
- Blocked on API credentials from DevOps (requested 2 days ago, following up today)
```

## Example Output

Given this context:
- Closed PR #456 for user auth refactor
- Attended sprint planning (assigned PROJ-123)
- Calendar shows 1:1 with manager tomorrow
- Obsidian note mentions "still waiting on design specs for dashboard"

**Draft using Agile Standup template:**

```markdown
## Yesterday
- Merged user auth refactor (PR #456) - improves session handling
- Sprint planning: picked up PROJ-123 (notification system)

## Today
- Start implementation for PROJ-123
- 1:1 with manager at 2pm

## Blockers
- Waiting on design specs for dashboard redesign (following up with design team)
```

## Customization

### Template Location

Common locations for templates:
- `~/.config/daily-update/template.md`
- `<project>/.daily-update-template.md`
- Obsidian vault: `!meta/templates/daily_update_standup.md`

### Per-Project Templates

Different projects may need different formats. Support:
- Project-specific templates in repo root
- Team-specific templates for different audiences
- Multiple templates (standup vs. weekly vs. async)

### Audience Adaptation

Adjust detail level based on audience:
- **Team standup**: Technical details, PR/issue numbers
- **Manager update**: Higher-level progress, strategic blockers
- **Cross-functional**: Less jargon, more context

## Integration with Obsidian Vault

When working with the PersonalLog vault:

1. **Read context from daily notes** at `Periodic/Daily/YYYY-MM-DD.md`
2. **Respect the note structure** - distinguish `## Notes` from `## Servitor`
3. **Optionally write the update** to the Servitor section of the daily note
4. **Link to relevant entities** (people, projects, dates)

Example integration:
```markdown
## Servitor

### Daily Update (generated YYYY-MM-DD)

[Generated standup content here]
```
