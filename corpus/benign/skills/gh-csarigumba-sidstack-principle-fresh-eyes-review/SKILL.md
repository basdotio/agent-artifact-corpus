---
name: principle-fresh-eyes-review
description: Principle. Apply before any change is called ready to ship. The agent that wrote the code does not grade it; a reviewer with a clean context reads the diff and the evidence and returns a verdict. A claim of done arrives with evidence, never alone.
---

# Fresh eyes review

**Rule:** The writer of a change never issues its verdict. A separate reviewer, started with a clean context, reads the diff, the plan, and the evidence, and returns `ship`, `fix`, or `stop`.

## Why

A context that produced a change has already rationalized its gaps; it reads its own diff as correct because it remembers intending it to be. A fresh context has only the artifact and the claim, which is what a human reviewer on `main` would have.

## How to apply

1. Give the reviewer exactly: base and head refs, the plan with its done-when checks, the evidence directory, and the verifier's table. Nothing from the writer's conversation.
2. The reviewer checks each done-when item against a cited artifact. An item without one is `fix`, not "probably fine".
3. The reviewer looks for what the writer is least likely to see: tests weakened or skipped, scope beyond the plan, a comment used to justify a workaround, a pattern the repo forbids.
4. Findings name a file and line and a concrete fix. A verdict without findings is only valid as `ship`.
5. A `fix` goes back to the writer with the findings; the reviewer does not fix it.

## Smells that mean you skipped this

- "Self-reviewed and looks good."
- Reviewer and writer are the same session or share a context.
- A verdict that cites no artifact path.
- A `ship` verdict on a diff the reviewer never read in full.
