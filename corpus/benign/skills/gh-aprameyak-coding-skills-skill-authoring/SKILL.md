---
name: skill-authoring
description: Create or update Agent Skills with lean SKILL.md files. Use when writing a new skill, refactoring skills, or packaging workflows for agents.
---

# Skill Authoring

## Structure

```
skill-name/
└── SKILL.md
```

Optional: `reference.md`, `examples.md`, `scripts/` linked one level deep.

## Frontmatter

```yaml
---
name: skill-name
description: What it does. Use when <triggers>.
---
```

- `name`: lowercase, hyphens, ≤64 chars, matches folder
- `description`: third person, WHAT + WHEN, include trigger terms

## Writing Rules

- Assume the agent is capable; keep only non-obvious procedure
- One skill, one job
- Prefer checklists, templates, and short steps
- Keep `SKILL.md` well under 500 lines; push detail to references
- No HTML comment blocks, placeholder stubs, or platform lock-in
- Include exit criteria / verification when quality matters

## Process

1. Define trigger scenarios and non-goals.
2. Draft description with triggers.
3. Write the minimal workflow body.
4. Add references only if needed.
5. Run `scripts/audit.sh` if available.
