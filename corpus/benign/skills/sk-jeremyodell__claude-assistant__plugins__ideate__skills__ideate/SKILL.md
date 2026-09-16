---
name: ideate
description: Transform ideas into validated, dependency-mapped Linear stories. Activates when user wants to develop a new feature idea, create Linear stories from a concept, brainstorm and plan implementation, or mentions "new feature", "I want to build", "break into stories", "create issues for". Commands: /ideate, /ideate:brainstorm, /ideate:pressure-test, /ideate:plan, /ideate:stories, /ideate:upload, /ideate:setup.
---

# Ideate Skill

Transforms raw ideas into structured, validated, implementation-ready Linear stories.

## Workflow

```
/ideate "your feature idea"
    ↓
Phase 1: Brainstorm (superpowers:brainstorming)
    ↓
Phase 2: Pressure Test (mandatory validation)
    ↓
Phase 3: Plan (superpowers:writing-plans)
    ↓
Phase 4: Stories (decompose with dependencies)
    ↓
Phase 5: Upload (Linear parent + sub-issues)
```

## Commands

### `/ideate "idea"`
Full workflow from idea to Linear stories.

### `/ideate:brainstorm "idea"`
Flesh out idea using superpowers:brainstorming. Creates design.md.

### `/ideate:pressure-test`
Mandatory validation: scope drift, assumptions, risks, YAGNI, edge cases.
Requires user sign-off. Creates pressure-test.md.

### `/ideate:plan`
Create implementation plan using superpowers:writing-plans. Creates plan.md.

### `/ideate:stories`
Decompose plan into stories with dependencies and labels. Creates stories.md.

### `/ideate:upload`
Upload to Linear as parent issue + sub-issues with blocking relations.

### `/ideate:setup`
Configure Linear team, project, and default labels.

## Artifacts

All phases save to `docs/features/YYYY-MM-DD-<slug>/`:

- `design.md` - Brainstorm output
- `pressure-test.md` - Validation with sign-off
- `plan.md` - Implementation plan
- `stories.md` - Stories with dependencies
- `ui/` - Frontend designer output (if applicable)

## Story Format

Each story includes:
- Summary (one line)
- Acceptance Criteria (checkboxes)
- Technical Notes
- Test Approach
- Dependencies (blocked by / blocks)
- Labels (auto-suggested)

## Linear Integration

- Parent issue: "Feature: [name]"
- Sub-issues: Individual stories
- Blocking relations: Native Linear "blocked by" fields
- Descriptions: Human-readable dependency section

## Dependencies

- `superpowers` plugin (brainstorming, writing-plans skills)
- `frontend-designer` plugin (if UI features)
- Linear MCP server

## Configuration

Per-project config in `.claude/ideate.local.md`:

```yaml
---
linear_team: "Engineering"
linear_project: "Product Development"
default_labels:
  - "from-ideate"
---
```
