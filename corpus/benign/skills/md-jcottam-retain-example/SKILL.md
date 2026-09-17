---
name: example
description: Demonstrate the SKILL.md pattern. Replace this with a real skill.
---

# Example Skill

## When to activate

When the user asks about example skills or how the skills system works.

## Behavior

- Explain that skills are markdown files in `workspace/skills/<name>/SKILL.md`
- Each skill has YAML frontmatter with `name` and `description` fields
- The system prompt includes a catalog of skill names and descriptions
- When a skill is relevant, use the `read_skill` tool to load its full instructions
- Use `/skills` to list installed skills
