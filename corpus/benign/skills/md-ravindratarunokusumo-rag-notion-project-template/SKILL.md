---
name: "skill-name"
description: "Short description of what this skill does."
---

# Trigger and Scope

## When to use

- Describe concrete task signals that should trigger this skill.

## When not to use

- Describe clear boundaries and non-goals.

# Inputs

## Arguments

- Describe `$ARGUMENTS` parsing rules.
- Document defaults.
- Document edge cases and invalid argument handling.

# Execution Workflow

1. List required prechecks.
2. List ordered execution steps.
3. List required validations before returning.

# Validation

- Required commands/tests to establish confidence.
- Expected outputs or pass criteria.

# Output Contract

- Required response structure.
- Required artifacts and where they are written.
- How to report partial completion and blockers.

# Safety

- Forbidden actions.
- Recovery/fallback behavior when preconditions fail.
