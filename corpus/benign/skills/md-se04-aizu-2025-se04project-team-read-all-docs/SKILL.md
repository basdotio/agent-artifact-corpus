---
name: read-all-docs
description: Read and summarize docs in doc/ and module READMEs
compatibility: opencode
metadata:
  audience: maintainers
  workflow: docs
---
## What I do
- Scan `doc/` recursively
- Read module-level `README.md` files (e.g. `composeApp/`, `domain/`, `data/`, `presentation/*`)
- Provide a concise summary of key guidelines and rules
- Ask follow-up questions if any doc is missing or unclear

## When to use me
Use this when you need a full project context refresh from documentation.

## Output format
- Summary grouped by topic (architecture, rules, workflows)
- List of docs read (including module READMEs)

## Notes
- Do not modify files
- Do not run network commands
