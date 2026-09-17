---
name: interview
description: Conduct a comprehensive discovery interview using Socratic questioning to develop detailed project specifications and validate assumptions.
---

# Project Specification Interview

Use this skill to conduct a deep, structured discovery interview that extracts all information needed to write a complete, unambiguous specification.

## When to Use

- **After a brief** – Use the engineering-brief or venture-feasibility skill first
- **Vague requirements** – Turn "build a dashboard" into a complete spec
- **Uncovering unknowns** – Surface hidden assumptions and contradictions
- **Specification creation** – Interview output becomes your spec
- **Team alignment** – Ensure shared understanding before starting

## Interview Principles

1. **One question at a time** – Never ask multiple questions. Let each answer inform your next question.
2. **Ask non-obvious questions** – Skip surface-level inquiries. Probe edges, contradictions, and unstated assumptions.
3. **Go deep before wide** – When you hit something interesting, drill down before moving on.
4. **Challenge assumptions** – When something seems "obvious," ask why.
5. **Seek contradictions** – "Earlier you said X, but now Y—help me reconcile."
6. **Use the codebase** – Reference actual code, types, and patterns when relevant.

## Areas to Explore

### Problem Domain
- What's the user pain or current workaround?
- Who's affected?
- How is this currently handled?

### Scope & Boundaries
- What's MVP vs vision?
- What are explicit non-goals?
- Where's the cut line?

### Technical Constraints
- Hard constraints?
- Architecture approach?
- Blast radius of failure?
- Technical debt tolerance?

### User Experience
- What's the happy path?
- What are error states?
- Cognitive load expectations?

### Data & State
- Sources of truth?
- State persistence?
- Data lifecycle?

### Edge Cases & Scale
- What breaks at scale?
- Degradation at zero usage?
- Failure recovery?

### Dependencies & Contracts
- External dependencies?
- Downstream consumers?
- Backwards compatibility needs?

### Success & Failure
- Success metrics?
- Failure criteria?
- Kill conditions?

## Running the Interview

1. Prepare context (have the brief available)
2. Ask one question at a time
3. Listen for contradictions
4. Dig into interesting details
5. Synthesize periodically
6. Continue until you can write an unambiguous spec

## When to Stop

You're done when you have enough information to write a specification including:
- Problem statement and success metrics
- Scope and non-goals
- Technical architecture and constraints
- Data model and lifecycle
- API or interface design
- Edge cases and error handling
- Deployment and operations
- Testing strategy

## Output: The Specification

1. Announce you're ready to write the spec
2. Ask where to save it (suggest SPEC.md)
3. Write the spec with complete clarity
4. Get stakeholder approval

---

**Pro tip**: The best interviews feel like conversations. Listen more than you talk.
