---
name: structured-reasoning
description: A cognitive framework specifically for complex problem solving using First Principles and Chain of Thought.
---
# Structured Reasoning (The Fixer 🧠)

## Scope (STRICT)
- **ONLY** activates for **complex problem solving** where the answer is not obvious.
- Does **NOT** plan task sequences (that's `task-orchestrator`).
- Does **NOT** select skills (that's `meta-governor`).

## When to Activate
- Debugging with no clear root cause.
- Architecture decisions with multiple valid approaches.
- Performance issues with unclear bottleneck.
- Any "Why is this happening?" question.

## When NOT to Activate
- Clear bug with obvious fix.
- Simple implementation request.
- User already specified the approach.

## Method: MECE Decomposition
1.  **Situation**: What do we know?
2.  **Complication**: What's the conflict or unknown?
3.  **Hypothesis**: What could explain it? (Max 3 hypotheses)
4.  **Test**: How to validate each hypothesis?
5.  **Conclusion**: Which hypothesis survived?

## Cost: Medium
