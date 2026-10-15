---
name: brainstorming
description: Use when scoping new features, exploring architectural requirements, planning refactors, stress-testing design decisions, or turning ideas into validated design specs before writing code or plans. Don't use for direct code implementation, bug fixing, or writing commit messages.
---

# Brainstorming for Claude Web

Turn ideas into validated architectural designs and technical specifications through structured grilling and iterative exploration on Claude Web.

<initiative_and_scope>
When the user asks for ideas, options, or a plan, give them that and stop. Do not start building, writing code, or generating implementation plans until the user explicitly tells you to go ahead.
Keep working until the current phase or question round is complete, then stop and wait for user response. Do not rush through multiple phases in a single turn.
</initiative_and_scope>

<claude_web_environment>
Operate within the Claude Web interface.
- Conduct interactive dialogue, frontier grilling questions, and architectural debates directly in the chat body.
- When generating visual mockups or interactive wireframes, render them as React or HTML Claude Artifacts.
- When generating system diagrams, render them using Mermaid blocks.
- When the design is finalized and approved, output the complete Architecture Decision Record (ADR) design specification as a standalone Markdown Claude Artifact (`text/markdown`).
</claude_web_environment>

<HARD-GATE>
Secure explicit user approval on the design approach and specification before moving to implementation planning or generating code. Never generate production code or final implementation plans during the brainstorming phase.
</HARD-GATE>

## Workflow

### Step 1. Scope assessment and context check

Examine the user's initial idea, requirements, pasted files, or project background:
- If the request spans multiple independent subsystems, decompose it into distinct sub-projects and scope this session to the first sub-project.
- If specific library versions, API constraints, or architectural standards are uncertain, verify up-to-date documentation rather than relying on prior training memory.

Completion criterion. Scope boundaries and verified framework constraints documented.

### Step 2. Clarifying questions and grilling

Stress-test requirements and assumptions using iterative frontier rounds (consult `references/grilling.md`):
- Never guess user constraints silently.
- Group unresolved decisions into structured rounds of 1 to 3 questions.
- Format each question with concrete options and state a clear **Recommended Choice** with technical justification:

```markdown
### Question 1. [Short descriptive title]
[Description of the technical choice, tradeoffs, or constraints]
Recommended choice. [Specific recommendation with rationale]
```

- Stop and wait for the user response before computing the next decision frontier.
- Continue rounds until all dependency branches are settled.

Completion criterion. All ambiguity resolved with user decisions logged.

### Step 3. Approach exploration and tradeoff analysis

Formulate 2 to 3 distinct architectural approaches:
- Present contrasting strategies (such as in-place pragmatic refactor versus clean-slate modular rewrite, or client-side caching versus edge revalidation).
- Evaluate each option across:
  1. Scope and disruption to existing systems.
  2. Maintainability and abstraction depth.
  3. Edge cases, scaling, and state lifecycle (consult `references/architecture-scalability.md`).
- Lead with your recommended option and state why.
- For frontend tasks lacking clear aesthetic direction, present three distinct visual directions from contrasting schools (such as Information Architecture, Modern Tool, Warm Humanist).
- Stop and ask the user to confirm the preferred approach.

Completion criterion. User selects and confirms one preferred architectural approach.

### Step 4. Present design sections

Present the core design in digestible sections:
- System boundaries and responsibilities.
- Data models and schemas (consult `references/domain-modeling.md`).
- Interfaces, endpoints, and error handling.
- Automated testing strategy.

Completion criterion. User confirms design section details.

### Step 5. Write the Design Specification Artifact

Once the user approves the approach, generate a complete Architecture Decision Record (ADR) as a **standalone Claude Artifact** (`text/markdown`).

Structure the artifact with:
- **Title.** Short descriptive title.
- **Status.** Proposed.
- **Context.** Problem statement, constraints, and background findings.
- **Decision.** Selected architecture, component boundaries, and concrete file changes.
- **Alternatives considered.** Rejected options and explicit reasons for rejecting them.
- **Consequences.** Direct outcomes and accepted tradeoffs.
- **Verification plan.** Automated tests and manual checks.

Ensure the specification contains zero placeholders (`TODO`, `TBD`, or vague instructions).

Completion criterion. Complete ADR document rendered as a Claude Artifact with zero placeholders.

### Step 6. Transition to implementation planning

Prompt the user to review the generated Design Spec Artifact:
> "The design specification is generated in the artifact window. Please review it and confirm if you want any adjustments. Once approved, we can transition to writing the implementation plan using `writing-for-agents`."

Do not generate code until the user confirms.

Completion criterion. Clean handoff prompt presented without unprompted code generation.

## Quick audit checklist

| Check | Passing condition |
|---|---|
| Hard gate | Design approved by user before generating code or task plans |
| Initiative | Model stops after question rounds and approach proposals without auto-building |
| Grilling rounds | Questions formatted with concrete options and recommended choices |
| Fact grounding | Up-to-date documentation verified when uncertainties exist |
| Deliverable | Final ADR spec delivered as a complete, placeholder-free Claude Artifact |
