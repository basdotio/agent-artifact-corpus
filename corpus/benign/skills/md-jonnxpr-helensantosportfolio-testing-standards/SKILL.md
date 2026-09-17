---
name: testing-standards
description: Testing standards for the Helen Santos Portfolio static-site workspace.
---

# Skill - testing-standards (Helen Santos Portfolio)

## When to use

- Build validation, smoke testing, regression checks, or test maintenance in this static-site workspace.

## Rules

- Preserve existing build scripts, minified artifacts, and deterministic behavior.
- Keep tests and validations lightweight, reproducible, and free of real external service dependencies.
- Prefer semantic, accessibility, and responsive-flow verification over brittle implementation-detail assertions.
- Do not introduce flaky waits or `sleep`.

## Validation flow

- `npm run build` for source CSS/JS changes
- smoke test the affected sections on desktop and mobile viewport
- run any existing automated tests when the workspace already uses them

## Mandatory final code review, cross-validation, and factual integrity

- Final approval requires build evidence plus affected-flow validation.
