---
name: env-hygiene
description: "Check and sanitize env files when the user asks to check env files, remove secrets, or validate env examples."
---

# Env Hygiene

Use this skill to sanitize env files and ensure examples are safe and well-documented.

## Workflow

1) Scan tracked files for secrets/domains/host paths.
2) Ensure env values are not hardcoded in compose files.
3) Check `.env.<name>.example`:
   - Optional/default values are commented out
   - No empty values
   - Placeholders for secrets
4) Ensure root `.env` only has global vars.
5) Report findings and fixes.

## Output

- List of issues and fixes
- Confirmation of safety for commit

## Reference

See `references/env-guidelines.md`.
