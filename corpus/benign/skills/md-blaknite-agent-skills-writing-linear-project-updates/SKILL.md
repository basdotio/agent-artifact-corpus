---
name: writing-linear-project-updates
description: Collaboratively draft Linear project updates through dialogue. Use when writing project updates, status reports, or progress summaries for Linear projects.
---

# Writing Linear Project Updates

Collaborate with the user to craft clear, informative project updates through iterative refinement.

Load skills: using-linear, reading-pull-requests

## Starting Point

The user provides a Linear project URL or project identifier. Load the `using-linear` skill and fetch the project details including:
- Project name, description, and content (PRD/scope)
- Current issues and their states
- Recent project updates (for tone/format reference)

For issues that are "In Review", use the `reading-pull-requests` skill to fetch PR details. This provides context on what's actively being reviewed without requiring the user to explain it manually.

## Rubber Duck Process

Act as a thinking partner. Your job is to help the user clarify what they want to communicate through helpful questions.

### Core Questions to Explore

Ask these through natural conversation, not as a checklist:

1. **Status** - Is the project on track, at risk, or off track?
2. **Progress** - What shipped or moved forward since the last update?
3. **Blockers** - Are there any blockers, risks, or dependencies to call out?
4. **Timeline** - What's the outlook? When do key milestones ship?

### How to Collaborate

- Start by reviewing the project state and issues
- Ask targeted questions about what's changed
- Propose a draft once you have enough context
- Iterate on tone, structure, and content based on feedback
- Keep it conversational, not an interrogation

## Drafting the Update

When enough context exists, propose a draft update. Structure:

**Header**: Health status emoji + summary line with milestone/timeline

**What's happening**: Current work in progress, what's in review, what shipped

**Next steps**: What needs to happen to complete the current milestone

**Blockers/Risks** (if any): Call out anything that could derail progress

**Related work** (optional): Tangential items that readers may care about

### Health Status

- 🟢 **On Track** - Progressing as planned
- 🟡 **At Risk** - Potential issues that need attention
- 🔴 **Off Track** - Blocked or significantly delayed

### Writing Principles

- **Concise** - Respect the reader's time. No essays.
- **Informative** - What changed? What's next? Any concerns?
- **Honest** - Don't hide problems. Surface risks early.
- **Actionable** - Clear enough that readers know if they need to act.

## Finalizing

Present the draft and ask: "Does this capture the current state? Ready to post?"

Once confirmed, post using the Linear GraphQL API:

```bash
LINEAR_TOKEN=$(linear auth token)

# First get the project UUID from the slug
PROJECT_UUID=$(curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_TOKEN" \
  -d '{"query": "{ project(id: \"PROJECT_SLUG\") { id } }"}' | jq -r '.data.project.id')

# Use a double-quoted multiline string for the body so newlines are preserved.
# Do NOT use backslash line continuations (\) or literal \n in the string.
BODY="**What shipped:**
First paragraph here.

**In progress:**
Second paragraph here."

# Use jq to build the JSON payload. jq --arg handles all escaping correctly.
PAYLOAD=$(jq -n \
  --arg projectId "$PROJECT_UUID" \
  --arg health "onTrack" \
  --arg body "$BODY" \
  '{
    "query": "mutation($input: ProjectUpdateCreateInput!) { projectUpdateCreate(input: $input) { success projectUpdate { url } } }",
    "variables": {
      "input": {
        "projectId": $projectId,
        "health": $health,
        "body": $body
      }
    }
  }')

curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_TOKEN" \
  -d "$PAYLOAD" | jq '.'
```

Replace:
- `PROJECT_SLUG` with the slug from the URL (e.g., `a74ff3a2c8d4`)
- `health` with one of: `onTrack`, `atRisk`, `offTrack`
- `BODY` with the actual update content as a double-quoted multiline string
