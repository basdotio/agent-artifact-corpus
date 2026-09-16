---
name: project-style-coding
description: Apply and preserve the existing code style of the current repository when adding or modifying code. Use when implementing bug fixes, features, refactors, tests, or docs that must match local naming, structure, patterns, and review expectations.
---

# Project Style Coding

## Goal

Match the repository's existing style before changing behavior.
Prioritize consistency, minimal diffs, and low-risk integration.

## Workflow

1. Identify the target area and read nearby files first.
2. Extract local conventions from real code before editing:
- naming style for variables, functions, types, and constants
- component and hook structure
- state management and side-effect patterns
- error handling, logging, and message tone
- import ordering and file organization
3. Reuse existing utilities and shared components when possible.
4. Make the smallest change that fixes the issue.
5. Keep unrelated refactors out of the same patch.
6. Validate with project-standard checks (at minimum type check/build for touched area).
7. Report risk points and what was validated.

## Style Rules

- Follow existing naming and API shapes in the touched module.
- Keep function boundaries and control flow similar to surrounding code.
- Preserve current comment density; add comments only where logic is non-obvious.
- Use the same error and status message style already used in the feature.
- Avoid introducing new dependencies unless required by the task.

## Review Mode

When asked to review code:

1. List findings first, ordered by severity.
2. Include file references for each finding.
3. Focus on regressions, edge cases, race conditions, stale state, and missing tests.
4. If no issues are found, state that clearly and note residual risk/test gaps.

## Output Checklist

Before finalizing, confirm:

- behavior change is correct for the target scenario
- style matches neighboring code
- no unrelated files were changed intentionally
- validation command(s) were run and results are reported
