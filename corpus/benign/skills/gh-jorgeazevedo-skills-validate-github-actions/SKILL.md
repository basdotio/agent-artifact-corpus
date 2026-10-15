---
name: validate-github-actions
description: 'Validate GitHub Actions workflow YAML files using actionlint and zizmor. Use when creating or modifying GitHub Actions workflows.'
compatibility: Requires actionlint and zizmor
---

# Validate GitHub Actions Workflows

Do NOT write custom Python/Node scripts to validate workflows. Always use `actionlint` and `zizmor`.

## Procedure

1. Check whether the project's `.tool-versions` already includes `actionlint` and `zizmor`. If not, add the missing ones (e.g. `actionlint latest`, `zizmor latest`) and run `mise install`.
2. Run `actionlint .github/workflows/<file>.yml` on the target file(s).
3. Run `zizmor .github/workflows/<file>.yml` on the target file(s).
4. Fix any reported errors and re-run until clean.
