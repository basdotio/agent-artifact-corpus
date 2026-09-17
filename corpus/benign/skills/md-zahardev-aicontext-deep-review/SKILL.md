---
name: deep-review
description: Comprehensive code review — architecture + correctness. Scope with args — diff (default), branch, all, path, or IDE selection. Delegates to reviewer agent for large scope.
disable-model-invocation: true
---

## Determine scope

Follow `.aicontext/prompts/review-scope.md` to determine scope and count changed lines.

## Run review

- **Small scope (~200 changed lines or fewer, or IDE selection):** follow `.aicontext/prompts/deep-review.md` directly
- **Large scope (more than ~200 changed lines, or `all`):** launch `reviewer` agent with the prompt path `.aicontext/prompts/deep-review.md` and the scope description
