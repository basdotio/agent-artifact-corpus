---
name: skill-builder
description: Creates new or updates existing Claude Code skills. Use when user says "create a skill", "build a skill", "new skill", "make a skill", "extract a skill from this", "save this as a skill", "turn this into a skill", or "update the X skill". Also use when user says "skillify" or wants to capture a workflow pattern from the current session.
---

# Skill Builder

Build well-structured Claude Code skills following Anthropic's official best practices.

## Important: Detect Invocation Mode

Before starting, determine which mode applies:

### Mode A: Fresh Build (no prior context)
User explicitly asks to create a new skill from scratch. Follow Steps 1-6 below interactively.

### Mode B: Extract from Session Context
User invokes mid-session or end-of-session wanting to capture what was just done as a skill. Phrases like "turn this into a skill", "save this as a skill", "extract a skill from this", "skillify this".

For Mode B:
1. **Mine the conversation** for the workflow that was just performed:
   - What tools were used? (Read, Write, Edit, Bash, Grep, Glob, MCP tools)
   - What was the sequence of steps?
   - What decisions were made and why?
   - What errors were hit and how were they resolved?
   - What files/paths were involved?
2. **Identify the generalizable pattern** — strip session-specific details (file paths, variable names, project-specific config) and extract the reusable workflow
3. **Draft the skill automatically** — don't ask the user to re-explain what they just did. Synthesize from context. Present the draft for review.
4. **Ask only what you can't infer**: skill name, scope (global vs project), and any ambiguous trigger phrases
5. Skip to Step 5 (Validate) then Step 6 (Create)

### Mode C: Update Existing Skill
User wants to improve a skill based on what happened in this session. Phrases like "update the X skill", "fix the X skill", "the X skill needs to handle Y".

For Mode C:
1. **Read the existing skill**: `~/.claude/skills/{name}/SKILL.md` or `.claude/skills/{name}/SKILL.md`
2. **Identify what changed** from session context:
   - New edge cases discovered?
   - Steps that were missing or wrong?
   - Better error handling needed?
   - New trigger phrases the user tried?
3. **Apply targeted edits** to the existing SKILL.md — don't rewrite from scratch
4. **Show a diff summary** of what changed and why
5. Run the validation checklist (Step 5)

---

## Interactive Build (Mode A)

### Step 1: Define the Use Case

Ask the user to describe what they want the skill to do. Identify:

1. **Category** - which type:
   - Document/Asset Creation (consistent output generation)
   - Workflow Automation (multi-step processes)
   - MCP Enhancement (workflow guidance for MCP tools)
2. **Trigger phrases** - what would a user say to invoke this?
3. **Steps** - what sequence of actions does the skill orchestrate?
4. **Tools needed** - built-in (Read, Write, Edit, Bash, Grep, Glob) or MCP?

Format the use case:
```
Use Case: [Name]
Trigger: User says "[phrase1]" or "[phrase2]"
Steps:
1. [First action]
2. [Second action]
...
Result: [What success looks like]
```

### Step 2: Generate the Frontmatter

Create valid YAML frontmatter following these CRITICAL rules:

- `name`: kebab-case only, no spaces/capitals/underscores, must match folder name
- `description`: MUST include WHAT it does + WHEN to use it (trigger conditions). Under 1024 chars. No XML tags. Include specific phrases users might say.
- Delimiters: must use `---` on both sides

**Description formula:** `[What it does] + [When to use it] + [Key capabilities]`

Good example:
```yaml
---
name: my-skill-name
description: Analyzes design files and generates developer handoff documentation. Use when user uploads .fig files, asks for "design specs", "component documentation", or "design-to-code handoff".
---
```

Validate against these anti-patterns:
- Too vague: "Helps with projects" (BAD)
- Missing triggers: "Creates multi-page documentation systems" (BAD)
- Too technical: "Implements the Project entity model with hierarchical relationships" (BAD)

### Step 3: Write the Instructions

Use this structure in the SKILL.md body (after frontmatter):

```markdown
# [Skill Name]

## Instructions

### Step 1: [First Major Step]
[Specific, actionable instructions]
- Use exact tool names and commands
- Include expected output descriptions

### Step 2: [Next Step]
...

## Examples

### Example 1: [Common scenario]
User says: "[trigger phrase]"
Actions:
1. [What happens]
2. [What happens]
Result: [Outcome]

## Common Issues

### [Error/Problem]
**Cause:** [Why it happens]
**Solution:** [How to fix]
```

Best practices for instructions:
- Be specific and actionable: `Run \`python scripts/validate.py --input {filename}\`` not "Validate the data"
- Put critical instructions at the top with `## Important` or `## Critical` headers
- Use bullet points and numbered lists, not paragraphs
- Keep SKILL.md under 5,000 words; move detailed docs to `references/`
- Reference bundled files clearly: `Before writing queries, consult \`references/api-patterns.md\``

### Step 4: Choose a Pattern

Select the best structural pattern for the skill:

1. **Sequential Workflow** - steps in specific order with dependencies
2. **Multi-MCP Coordination** - phases spanning multiple services
3. **Iterative Refinement** - generate, check quality, improve loop
4. **Context-Aware Tool Selection** - decision tree for which tool/approach
5. **Domain-Specific Intelligence** - specialized knowledge + compliance checks

### Step 5: Validate

Run this checklist before finalizing:

- [ ] Folder named in kebab-case
- [ ] File is exactly `SKILL.md` (case-sensitive)
- [ ] YAML frontmatter has `---` delimiters
- [ ] `name` field: kebab-case, no spaces, no capitals
- [ ] `description` includes WHAT and WHEN
- [ ] No XML tags (`<` or `>`) in frontmatter
- [ ] Instructions are specific and actionable
- [ ] Error handling / common issues section included
- [ ] Examples provided
- [ ] References clearly linked (if applicable)

### Step 6: Create the Skill

Write the skill folder to the appropriate location:
- **User-global skills:** `~/.claude/skills/{skill-name}/SKILL.md`
- **Project skills:** `.claude/skills/{skill-name}/SKILL.md`

Ask the user which scope they prefer.

If the skill needs supporting files:
- `scripts/` for executable code (Python, Bash, etc.)
- `references/` for documentation loaded as-needed
- `assets/` for templates, fonts, icons

Do NOT create a README.md inside the skill folder. All docs go in SKILL.md or references/.

## Session Extraction Tips (Mode B)

When extracting a skill from the current session:

### What to capture
- **Tool call sequences** — the exact tools used, in order
- **Decision points** — where you chose between approaches and why
- **Validation steps** — what you checked before proceeding
- **Error recovery** — what went wrong and the fix
- **File patterns** — types of files read/written (generalize paths)

### What to generalize
- Replace specific file paths with `{project-root}`, `{filename}`, `{component-name}` etc.
- Replace hardcoded values with parameters
- Replace project-specific tool names with the generic tool category
- Keep domain knowledge (the "why") but parameterize the "what"

### Draft output format
Present the extracted skill to the user as:
```
Here's the skill I extracted from this session:

**Name:** {name}
**Triggers:** {when it activates}
**Steps captured:**
1. {step}
2. {step}
...

**Edge cases found:**
- {from errors/issues in session}

Want me to create this at ~/.claude/skills/{name}/SKILL.md or .claude/skills/{name}/SKILL.md?
Any adjustments before I write it?
```

### Merging with existing skills
If the extracted workflow overlaps with an existing skill:
1. Read the existing skill
2. Identify net-new steps, edge cases, or trigger phrases
3. Propose merging rather than creating a duplicate
4. Apply edits to the existing skill and show what changed

## Common Issues

### Skill doesn't trigger
**Cause:** Description is too vague or missing trigger phrases.
**Solution:** Add specific phrases users would actually say. Ask Claude: "When would you use the [skill name] skill?" and adjust based on what's missing.

### Skill triggers too often
**Cause:** Description is too broad.
**Solution:** Add negative triggers: "Do NOT use for [unrelated task] (use [other-skill] instead)." Be more specific about scope.

### Instructions not followed
**Cause:** Instructions too verbose, buried, or ambiguous.
**Solution:** Keep concise, use bullet points, put critical instructions at top with ## Important headers. Move detailed reference docs to `references/`.
