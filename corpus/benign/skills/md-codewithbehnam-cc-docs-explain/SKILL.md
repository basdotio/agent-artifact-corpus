---
name: explain
description: >
  Explain code using ASCII diagrams, analogies, and step-by-step walkthroughs.
  Use when the user asks "how does this work?", "explain this code", "walk me
  through this", "what does this do?", or "help me understand this".
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob
---

## Context

- Current file or symbol: $ARGUMENTS
- Repository root: !`git rev-parse --show-toplevel 2>/dev/null || pwd`

## Task

Explain the code identified by $ARGUMENTS (or the most recently discussed code if no argument is given):

1. Read the relevant source file(s) fully. Follow imports and dependencies one level deep to understand the full picture.

2. Identify what the code does at a high level before diving into details.

3. Structure the explanation as follows:

### The Analogy
Compare the code to something from everyday life. A cache is like a sticky note on your monitor. A message queue is like a restaurant ticket rail. Pick the most fitting analogy and explain it in 2-3 sentences.

### The Big Picture (ASCII Diagram)
Draw an ASCII diagram showing the structure, data flow, or component relationships. Use arrows (`-->`, `==>`) to show direction. Keep it under 30 lines. Examples:

```
Request --> [Auth Middleware] --> [Router] --> [Handler] --> DB
                |                                  |
             401 Denied                       [Cache] --> Redis
```

### Step-by-Step Walkthrough
Walk through the code in execution order, not file order. For each significant step:
- What happens
- Why it happens (the design intent)
- What could go wrong (edge cases or assumptions)

### The Gotcha
One common mistake or misconception about this code that even experienced developers get wrong. Be specific.

### Key Files
List the most important files for understanding this area, with one-line descriptions.

Keep the tone conversational. Prefer short sentences. Avoid jargon unless it is defined. If the target is not found, say so clearly and suggest what the user might look for instead.
