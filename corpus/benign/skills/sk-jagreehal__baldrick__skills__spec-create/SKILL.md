---
name: spec-create
description: "Create a feature specification for Baldrick. Use when: create a spec, new feature, write spec for, plan this feature. Triggers on: create spec, baldrick create, new spec, feature spec."
---

# Spec Creator

Create detailed feature specifications for the Baldrick autonomous agent system.

> **Philosophy:** Skills manufacture work items. Baldrick consumes them.

---

## The Job

1. Receive a feature description from the user
2. Ask 2-3 essential clarifying questions (with lettered options)
3. Generate a structured spec following Spec Format v1
4. Save to `specs/[feature-name].md`

**Important:** Do NOT implement. Just create the spec.

---

## Spec Format

**Required YAML Frontmatter:**

```yaml
---
id: feature-name-v1      # Unique identifier (kebab-case + version)
title: "Feature Title"
passes: false
priority: medium         # high | medium | low
risk: standard           # spike | integration | standard | polish
created: YYYY-MM-DD
depends_on: []           # Array of spec IDs this depends on (optional)
---
```

**Required Sections:**

1. **One-liner** - What this does in 10 words
2. **Context** - User, Trigger, Success criteria
3. **Scope** - In/Out boundaries
4. **Examples** - Concrete input/output table
5. **Scenarios** - Gherkin BDD scenarios
6. **Done When** - Verifiable checklist (checkboxes)

---

## Clarifying Questions Format

Ask with lettered options for quick responses:

```
1. What is the primary goal?
   A. New user onboarding
   B. Power user workflow
   C. Admin management
   D. Other: [specify]

2. What is the scope?
   A. Minimal viable (just core)
   B. Full-featured
   C. Just backend/API
   D. Just UI
```

User can respond with "1A, 2B" for speed.

---

## Story Sizing

Each spec must be completable in ONE Baldrick iteration (one context window).

**Right-sized:**

- Add a database column and migration
- Add a UI component to an existing page
- Update a server action with new logic
- Add a filter dropdown to a list

**Too big (split these):**

- "Build the entire dashboard" → Split into: schema, queries, UI, filters
- "Add authentication" → Split into: schema, middleware, login UI, sessions
- "Refactor the API" → Split into one story per endpoint

**Rule of thumb:** If you cannot describe the change in 2-3 sentences, it is too big.

---

## Priority/Risk Guidelines

**Priority:**

- `high` - Core functionality, blocking other work
- `medium` - Important but not blocking (default)
- `low` - Nice to have, polish

**Risk:**

- `spike` - Unknown territory, research needed
- `integration` - Touches multiple systems
- `standard` - Normal feature work (default)
- `polish` - UI tweaks, cleanup

---

## Example Spec

```markdown
---
id: task-priority-v1
title: "Add Priority Field to Tasks"
passes: false
priority: high
risk: standard
created: 2026-01-11
depends_on: []
---

# Add Priority Field to Tasks

## One-liner

Allow users to set high/medium/low priority on tasks.

## Context

- **User**: Task owner
- **Trigger**: Editing or creating a task
- **Success**: Priority persists and displays correctly

## Scope

- **In**: Priority field, colored badge display, filter by priority
- **Out**: Priority-based notifications, auto-priority based on due date

## Examples

| Input | Expected |
|-------|----------|
| Set priority to "high" | Red badge appears |
| Filter by "high" | Only high-priority tasks shown |

## Scenarios

### Set priority on new task

Given I am creating a new task
When I select "high" priority
Then the task is saved with priority "high"
And a red badge is displayed

### Filter by priority

Given I have tasks with mixed priorities
When I select "High" in the filter
Then only high-priority tasks are shown

## Done When

- [ ] Priority dropdown in task form
- [ ] Colored badge on task cards (red/yellow/gray)
- [ ] Filter dropdown works
- [ ] Build passes
- [ ] Tests pass
```

---

## Output

- **Format:** Markdown (`.md`)
- **Location:** `specs/`
- **Filename:** `[feature-name].md` (kebab-case, matches id without version)

---

## Checklist Before Saving

- [ ] Asked clarifying questions with lettered options
- [ ] Spec is completable in one iteration (small enough)
- [ ] Has unique `id` field
- [ ] Has all required sections including `## Done When`
- [ ] Priority and risk fields set appropriately
- [ ] Done When criteria are verifiable (not vague)
- [ ] Saved to `specs/[feature-name].md`
