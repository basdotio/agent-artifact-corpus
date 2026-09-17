---
name: plan-generator
description: Create self-updating plan files for complex projects with phased breakdown and autonomous execution tracking. Generates feature-specific plans (e.g., PLAN-auth.md, PLAN-api.md) that enable autonomous work across sessions. Use when user wants comprehensive project planning with phases and detailed steps.
---

# Plan Generator Skill

This skill creates standalone plan files for complex projects that enable autonomous, phased execution with real-time progress tracking.

## When to Use This Skill

Use this skill when:
- User asks to create a project plan or PLAN file
- User wants to break down a complex project into phases and steps
- User needs a self-contained planning document for large initiatives

Do NOT use this skill when:
- User wants to EXECUTE an existing plan (use `plan-executor` skill instead)
- User references an existing PLAN file to continue work

## Plan File Naming

Plans are feature/project-specific and can be named flexibly:
- Single feature: `PLAN-{feature}.md` (e.g., `PLAN-auth.md`, `PLAN-api.md`)
- Main project plan: `PLAN.md`
- Multiple plans can coexist in one repository for different features

**Always ask the user what filename they want** or suggest based on the project/feature name.

## Plan File Structure

When creating a plan file, follow this exact structure:

### 1. Instructions for Claude Code (TOP OF FILE)

This section MUST be first. Keep it concise (~15 lines):

```markdown
## Instructions for Claude Code

When working on this plan:
1. **Use the `plan-executor` skill** to execute this plan
2. **Work autonomously** through phases without stopping for approval (unless blocked)
3. **Document findings** in the Notes & Decisions section

**Execution Mode:** [direct|worker]
**Auto-continue:** [yes|no]
**Commit after phase:** [yes|no] (include PLAN file: [yes|no])
```

### 2. Current Phase Indicator

Simple status at the top:
- `**Current Phase:** Phase 1: [Phase Name]`
- `**Current Phase:** COMPLETE`

### 3. Project Overview

- Clear description of the end goal
- Context about what the project achieves
- Key requirements (bulleted list)
- Any constraints or dependencies

### 4. Phase Breakdown

Each phase should include:

```markdown
## Phase N: [Phase Name]

Brief description of what this phase accomplishes.

### Step N.1: [Step title]
Detailed, actionable step description with context and requirements.

### Step N.2: [Another step title]
Description for this step...
```

**Step Format Notes:**
- Steps are markdown headings (`### Step N.X: Title`), NOT checkbox list items
- Each step ID follows the format `{phase}.{step}` (e.g., `0.1`, `1.2`, `2.3`)
- Include inline examples within phases when helpful (e.g., config structures, code snippets)

### 5. Notes & Decisions Section

Major section after all phases: `## Notes & Decisions`

Template structure for each phase:
```markdown
### Phase N: [Phase Name] (Status)
- Implementation details and approach taken
- Why decisions were made
- Deviations from original plan with explanations
- Technical details for future reference
```

### 6. Completion Checklist

Final section with overall project readiness criteria:
```markdown
## Completion Checklist

Before marking this project complete:
- [ ] All phases marked complete
- [ ] All tests passing
- [ ] Build successful
- [ ] Documentation complete
```

## Generating the Plan File

When this skill is invoked:

1. **Determine filename**: Ask user for desired filename or suggest based on project (e.g., "I'll create PLAN-auth.md for this authentication feature")

2. **Ask about preferences**:

   a) **Execution mode**:
      - **Direct mode**: Execute steps in the main session (simpler, good for small plans)
      - **Worker mode**: Delegate to sub-agents (recommended for large/complex plans)

   b) **Auto-continue preference**:
      - **Yes**: Automatically start the next phase without asking
      - **No**: Ask for confirmation before each new phase (default)

   c) **Commit preferences**:
      - **Yes, include PLAN file**: Commit code changes AND updated PLAN file together
      - **Yes, exclude PLAN file**: Commit only code changes
      - **No**: User will handle commits manually

3. **Gather project details** from the user if not already provided

4. **Break down the project**:
   - Identify logical phases (typically 3-8 phases, including Phase 0 for setup if needed)
   - For each phase, identify concrete steps (3-10 steps per phase)
   - Consider including inline examples (configs, schemas) in relevant phases

5. **Create the plan file** with:
   - Instructions section at the TOP (referencing `plan-executor` skill)
   - Current Phase indicator with execution preferences
   - Complete project overview
   - All phases with detailed, actionable steps
   - Empty Notes & Decisions section
   - Completion checklist
   - (JSON state will be initialized automatically by plan-executor on first run)

6. **Make it standalone**: The file should contain enough context that referencing it in a fresh session gives Claude complete understanding of the project

## Key Principles

- **Instructions first**: Always put Claude instructions at the top of the file
- **Reference plan-executor**: The instructions section should tell Claude to use the `plan-executor` skill
- **Detailed steps**: Each step should be actionable with clear requirements
- **Include examples**: Inline examples (configs, schemas, code snippets) make steps clearer
- **Self-referential**: Plan should reference "this file" not a hardcoded filename

## Example Usage

### Example 1: Single Feature Plan

User: "Create a plan for building a JWT authentication system with refresh tokens"

Claude should:
1. Suggest: "I'll create `PLAN-auth.md` for this authentication feature"
2. Ask about execution mode, auto-continue, and commit preferences
3. Break down into phases like:
   - Phase 0: Dependencies and project structure
   - Phase 1: JWT token generation and validation
   - Phase 2: Refresh token implementation
   - Phase 3: Middleware integration
   - Phase 4: Testing
4. Create detailed steps for each phase with inline examples (e.g., JWT payload structure)
5. Generate PLAN-auth.md with all structure including the JSON state block
6. Inform user: "I've created PLAN-auth.md. Reference it with `@PLAN-auth.md` to begin execution"

### Example 2: Main Project Plan

User: "Create a plan for building a CLI tool with subcommands and configuration support"

Claude should:
1. Suggest: "I'll create `PLAN.md` for this project"
2. Follow same process as Example 1
3. User can later create additional feature-specific plans alongside (e.g., PLAN-config.md)
