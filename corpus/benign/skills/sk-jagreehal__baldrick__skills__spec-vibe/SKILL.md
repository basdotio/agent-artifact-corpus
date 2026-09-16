---
name: spec-vibe
description: "Fast spec creation with sensible defaults. No questions asked. Use when: quick spec, vibe spec, fast spec, baldrick vibe. Triggers on: vibe, quick spec, fast spec, no questions."
---

# Vibe Spec Creator

Generate a feature specification immediately with sensible defaults. No clarifying questions.

> **Philosophy:** Speed over perfection. Make reasonable assumptions and generate.

---

## The Job

1. Receive feature name and description from user
2. Make sensible assumptions based on context
3. Generate complete spec following Spec Format v1
4. Save to `specs/[feature-name].md`

**CRITICAL:** Do NOT ask questions. Just generate the spec immediately.

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
3. **Scope** - In/Out boundaries (assume reasonable defaults)
4. **Examples** - Concrete input/output table with REAL data
5. **Scenarios** - Gherkin BDD scenarios (happy path + one error case)
6. **Done When** - Verifiable checklist (checkboxes)

---

## Assumptions to Make

When details are unclear, assume:

- **User**: The primary user of the application
- **Trigger**: User-initiated action (button click, form submit)
- **Scope**: Minimal viable implementation
- **Priority**: medium
- **Risk**: standard

---

## Story Sizing

Each spec must be completable in ONE Baldrick iteration.

**Right-sized:**

- Add a database column and migration
- Add a UI component to an existing page
- Update a server action with new logic

**Too big (split these):**

- "Build entire dashboard"
- "Add authentication"

---

## Example Output

```markdown
---
id: task-priority-v1
title: "Add Task Priority"
passes: false
priority: medium
risk: standard
created: 2026-01-11
depends_on: []
---

# Add Task Priority

> **One-liner:** Allow users to set high/medium/low priority on tasks.

## Context

- **User**: Task owner
- **Trigger**: Creating or editing a task
- **Success**: Priority persists and displays correctly

## Scope

- **In**: Priority field, colored badge display
- **Out**: Priority-based notifications, auto-priority

## Examples

| Input | Expected |
|-------|----------|
| Set priority "high" | Red badge appears |
| Default | Gray badge (medium) |

## Scenarios

### Set priority on task

Given I am editing task "Review PR"
When I select "high" priority
Then the task is saved with priority "high"
And a red badge is displayed

### Invalid priority rejected

Given I am editing a task
When I submit with invalid priority "urgent"
Then I see error "Invalid priority"

## Done When

- [ ] Priority dropdown in task form
- [ ] Colored badge on task cards
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

- [ ] Did NOT ask clarifying questions
- [ ] Made reasonable assumptions
- [ ] Has unique `id` field
- [ ] Spec is completable in one iteration
- [ ] Has all required sections including `## Done When`
- [ ] Used REAL data in examples (not `[placeholder]`)
- [ ] Saved to `specs/[feature-name].md`
