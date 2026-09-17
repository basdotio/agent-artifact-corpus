---
name: elaborate
description: Elaborate on specifications through detailed, structured interviews
allowed-tools: AskUserQuestion, Write, Read
argument-hint: <@path/to/spec.md or description>
---

When invoked with arguments:
- If the argument is a file path (contains `.md` or path separators), read that file and use its content as the base for the interview, then write the refined spec back to the same file
- If the argument is plain text (description), use that as the initial requirement and create a new spec file with an appropriate name (e.g., `projects/spec-<summary>.md`)

When invoked without arguments:
- First ask what the spec should be about and where to save it, then proceed with the detailed interview

---

## Gap Analysis for Existing Files

When a file path is provided, do NOT start interviewing immediately after reading. First evaluate the content and present the following as conversational text:

- **Well-defined areas**: Briefly list items that need no further clarification
- **Ambiguous or missing areas**: Items that are insufficiently defined, contradictory, or absent. Explain what is missing in one line for each

After presenting, focus the interview on the ambiguous or missing areas. Do not re-ask about well-defined areas (only address them if the user wants to revise).

---

## Interview Quality Rules

### Principles for Question Design

1. **Prioritize questions that surface implicit assumptions**
   - Challenge what the speaker unconsciously takes for granted
   - Bring unspoken expectations, constraints, and dependencies to light

2. **Show how each option affects downstream decisions**
   - Add context like "choosing this means you'll need to decide X later" or "this narrows down options for Y"
   - Go beyond simple pros/cons — reveal the chain of consequences

3. **Avoid superficial or obvious questions**
   - Do not ask about things that can be inferred from information already provided
   - Defer trivial details and prioritize structural decisions first

4. **Flag contradictions and unexplored combinations**
   - When answers contradict each other, raise it immediately
   - Present gaps like "achieving both A and B requires C, but C hasn't been decided yet"

### Question Order

Interview in three phases. Move to the next phase only when the current phase is sufficiently covered.

1. **Why** — Purpose and motivation
   - Why is this needed? What problem does it solve?
   - What happens if this is not built?
   - Who benefits and how?

2. **What** — Scope and requirements
   - What exactly should be achieved?
   - What is in scope and out of scope?
   - What are the success criteria?

3. **How** — Approach and implementation
   - How should it be built?
   - What are the technical constraints and tradeoffs?
   - What are the dependencies?

### Question Format

- 1–4 questions per round (using AskUserQuestion)
- Include tradeoff explanations for each option
- Keep options representative — users can always provide custom input via "Other"

---

Be very in-depth and continue interviewing continually until it's complete, then write the spec to the file.
