---
name: example-skill
description: Use when working with examples, tutorials, or skill documentation. Invoke when the user asks about skill configuration, manifest structure, or creating new skills.
allowed-tools: Read, Glob, Grep
---

# Example Skill

This is an example skill demonstrating the SKILL.md format.

## What Skills Provide

Skills are **instructions and context** injected into the agent's system prompt. They help the agent understand:

- When to use certain techniques or tools
- Project-specific conventions and patterns
- Domain knowledge and best practices

## What Skills Do NOT Provide

Skills are not for:

- CLI tools (use package managers or plugins)
- MCP servers (use plugins with plugin.json)
- Hooks (use plugins)
- Slash commands (use plugins)

For those capabilities, create a full Claude Code plugin with `.claude-plugin/plugin.json`.

## SKILL.md Format

Skills are defined by a single SKILL.md file with YAML frontmatter:

```markdown
---
name: my-skill
description: When to use this skill...
allowed-tools: Read, Write, Bash
---

# My Skill

Instructions and documentation here...
```

### Required Frontmatter Fields

| Field | Description |
|-------|-------------|
| `name` | Skill identifier (kebab-case, 1-64 chars) |
| `description` | **Critical** - tells Claude when to invoke the skill |

### Optional Frontmatter Fields

| Field | Description |
|-------|-------------|
| `allowed-tools` | Comma-separated or YAML array of allowed tools |

## Discovery

The `description` field is crucial for skill discovery. Claude uses it to decide when to invoke the skill.

**Good descriptions:**
- "Use when managing git branches, resolving merge conflicts, or reviewing commit history"
- "Use when working with React components, hooks, or state management"

**Bad descriptions:**
- "Git utilities" (too vague)
- "React helper" (won't trigger reliably)

## Example Use Cases

This skill covers:

1. Explaining skill structure and format
2. Helping users create new skills
3. Demonstrating best practices for skill documentation
