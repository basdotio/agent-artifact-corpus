---
name: creating-agent-skills
description: Creates Agent Skills for Claude Code following official standards. Use when the user wants to create a Skill, teach Claude new capabilities, add specialized knowledge, or create reusable instructions. Keywords: create skill, new skill, teach Claude, add capability, skill creation.
allowed-tools: Write, Read, List, Bash
---

# Creating Agent Skills

This Skill helps you create well-structured Agent Skills for Claude Code following the official documentation standards.

## What are Agent Skills?

Skills are markdown files that teach Claude how to do something specific. When you ask Claude something that matches a Skill's purpose, Claude automatically applies it. Skills are **model-invoked** - Claude decides which Skills to use based on your request.

## When to Create a Skill

Create a Skill when you want to:
- Give Claude specialized knowledge (e.g., "review PRs using our standards")
- Teach Claude domain-specific workflows (e.g., "process PDF forms")
- Establish consistent patterns (e.g., "generate commit messages in our format")
- Provide reference documentation that Claude can use contextually

## Skill Locations

Choose where to create the Skill based on who needs it:

| Location   | Path                    | Applies to                        |
|------------|-------------------------|-----------------------------------|
| Personal   | ~/.claude/skills/       | You, across all projects          |
| Project    | .claude/skills/         | Anyone working in this repository |
| Plugin     | skills/ (in plugin dir) | Anyone with the plugin installed  |

## Creating a Skill: Step-by-Step

### 1. Choose a Clear Name

Use lowercase with hyphens, descriptive of the task:
- ✅ Good: `pr-review`, `commit-messages`, `pdf-processing`
- ❌ Bad: `skill1`, `helper`, `misc`

### 2. Write a Strong Description

The description is **critical** - Claude uses it to decide when to use the Skill.

Include:
1. **What the Skill does** (specific capabilities)
2. **When to use it** (trigger terms users would say)
3. **Requirements** (if any external packages needed)

**Example of a good description:**
```
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction. Requires pypdf and pdfplumber packages.
```

**Example of a bad description:**
```
description: Helps with documents
```

### 3. Structure the SKILL.md File

Every Skill needs a `SKILL.md` file with this structure:

```markdown
---
name: your-skill-name
description: Brief description of what this Skill does and when to use it
allowed-tools: Tool1, Tool2  # Optional: restrict tools
---

# Your Skill Name

## Quick Start / Instructions
Provide clear, step-by-step guidance for Claude.

## Examples
Show concrete examples of using this Skill.

## Best Practices
Include tips, gotchas, and common patterns.

## Requirements (if applicable)
List any external packages or dependencies.
```

### 4. Available Metadata Fields

Use these optional fields in the YAML frontmatter:

- **name** (required): Unique identifier, lowercase-with-hyphens
- **description** (required): When and how to use this Skill
- **allowed-tools**: Comma-separated list to restrict tool access (e.g., `Read, Grep, Glob`)
- **version**: Semantic version (e.g., `1.0.0`)
- **author**: Creator's name or organization
- **tags**: Comma-separated keywords for discovery

### 5. Use Progressive Disclosure for Complex Skills

For complex Skills, create a directory structure:

```
my-skill/
├── SKILL.md              # Overview and quick start
├── REFERENCE.md          # Detailed API documentation
├── EXAMPLES.md           # Extended examples
└── scripts/
    ├── helper.py         # Utility scripts
    └── validate.py       # Validation tools
```

In `SKILL.md`, reference other files:
```markdown
For detailed API reference, see [REFERENCE.md](REFERENCE.md).
For more examples, see [EXAMPLES.md](EXAMPLES.md).
```

Claude will load these files only when needed, keeping the initial context lean.

## Tool Restrictions with allowed-tools

Use `allowed-tools` to limit what Claude can do with the Skill:

```yaml
---
name: read-only-analyzer
description: Analyzes files without making changes
allowed-tools: Read, Grep, Glob
---
```

This is useful for:
- Read-only Skills that shouldn't modify files
- Security-sensitive workflows
- Skills with limited scope (e.g., only data analysis)

If `allowed-tools` is omitted, Claude uses its standard permission model.

## Skills vs. Other Options

| Use this         | When you want to...                                    | When it runs                   |
|------------------|--------------------------------------------------------|--------------------------------|
| **Skills**       | Give Claude specialized knowledge automatically        | Claude chooses when relevant   |
| **Slash commands** | Create explicit prompts you trigger                  | You type /command to run it    |
| **CLAUDE.md**    | Set project-wide instructions                          | Loaded into every conversation |
| **Subagents**    | Delegate tasks to separate context with its own tools  | Claude delegates or you invoke |
| **Hooks**        | Run scripts on events (e.g., lint on file save)       | Fires on specific tool events  |
| **MCP servers**  | Connect Claude to external tools and data sources      | Claude calls MCP tools as needed |

**Key insight:** Skills add knowledge; MCP provides tools. Use both together: MCP connects Claude to your database, Skills teach Claude your data model.

## Testing Your Skill

1. **Create the Skill directory and SKILL.md**
2. **Restart Claude Code** to load the new Skill
3. **Verify it loaded**: Ask "What Skills are available?"
4. **Test it**: Ask a question that matches the description

Example test:
```
User: "How does this code work?"
Expected: Claude offers to use the `explaining-code` Skill
```

## Troubleshooting

### Skill Not Triggering

**Problem:** Claude doesn't use your Skill when you expect it to.

**Solution:** Make the description more specific with trigger terms users would say.

❌ Vague: `description: Helps with documents`

✅ Specific: `description: Extract text from PDFs, fill forms, merge documents. Use when working with PDF files, forms, or document extraction.`

### Skill Doesn't Load

**Check:**
- File must be named exactly `SKILL.md` (case-sensitive)
- YAML frontmatter must start on line 1 with `---`
- YAML must use spaces for indentation, not tabs
- File path must be correct: `.claude/skills/my-skill/SKILL.md`

**Debug:** Run `claude --debug` to see loading errors.

### Multiple Skills Conflict

**Problem:** Claude uses the wrong Skill or seems confused.

**Solution:** Make descriptions more distinct with specific trigger terms.

Example:
- Skill A: "sales data in Excel files and CRM exports"
- Skill B: "log files and system metrics"

Avoid having both mention just "data analysis".

## Best Practices

1. **Keep SKILL.md focused**: Use supporting files for detailed docs
2. **Write descriptions users would say**: Include natural keywords
3. **Show examples**: Concrete examples help Claude understand
4. **Test thoroughly**: Try various phrasings that should trigger it
5. **Version your Skills**: Use semantic versioning for major changes
6. **Document requirements**: List all external packages needed
7. **Use progressive disclosure**: Reference detailed docs instead of embedding everything

## Distribution

**Project Skills**: Commit `.claude/skills/` to version control

**Plugins**: Create `skills/` directory in your plugin root

**Personal**: Keep in `~/.claude/skills/` for personal use

## Skill Creation Workflow

When creating a new Skill, follow this process:

1. **Identify the need**: What specialized task needs a Skill?
2. **Choose location**: Personal, project, or plugin?
3. **Write description**: Focus on trigger terms and capabilities
4. **Draft instructions**: Clear, step-by-step guidance
5. **Add examples**: Show concrete usage patterns
6. **Test loading**: Restart Claude, verify Skill appears
7. **Test trigger**: Ask questions that should activate it
8. **Iterate**: Refine description based on testing
9. **Document requirements**: List any dependencies
10. **Share**: Commit or distribute as appropriate

## Example: Complete Simple Skill

```markdown
---
name: generating-commit-messages
description: Generates clear commit messages from git diffs. Use when writing commit messages, reviewing staged changes, or when the user says "commit" or "git diff".
---

# Generating Commit Messages

## Instructions

1. Run `git diff --staged` to see changes
2. I'll suggest a commit message with:
   - Summary under 50 characters
   - Detailed description
   - Affected components

## Best practices

- Use present tense ("Add feature" not "Added feature")
- Explain what and why, not how
- Separate summary from body with blank line

## Example

For changes adding a login form:
```
Add user login form component

Implements email/password authentication UI with:
- Form validation
- Error message display
- Remember me checkbox

Components: Auth, UI
```
```

## References

- Official docs: https://code.claude.com/docs/en/skills
- Skill authoring best practices: https://code.claude.com/docs/en/skills-best-practices








