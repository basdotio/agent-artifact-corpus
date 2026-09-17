---
name: ask
description: Read-only repository investigation and Q&A for prompts that start with `$ask {PROMPT}`. Use when the user wants analysis or answers based on local files but explicitly forbids edits or write actions.
---

# Ask

## Overview

Perform read-only investigation of the local repo and answer the user’s question based on file evidence.
Never modify files or run commands that write to disk.

## Trigger

Use this skill when the user prompt begins with `$ask `.

## Non-Negotiables (Read-Only)

- Do not edit files, create files, or apply patches.
- Do not run commands that write to disk (installs, builds, tests that write artifacts, formatters, generators).
- If a write action is required to answer, stop and ask for permission first.

## Workflow

1. Parse `{PROMPT}` from `$ask {PROMPT}` and restate the question briefly.
2. Scope the search to likely directories and files; prefer `rg` and `Get-Content`.
3. Read only the files needed; avoid loading large files unless necessary.
4. Answer the question with evidence from files and mention exact file paths.
5. If the answer is uncertain, say what is missing and what file would clarify it.

## Scope Heuristics

- Prefer repo files like `README.md`, `specification.md`, `src/`, `api/`, `public/`.
- Avoid `node_modules`, `dist`, and other generated outputs unless explicitly asked.
- If a folder is huge, narrow by filename or keyword before opening files.

## Response Guidelines

- Provide concise answers; include file path references and line numbers when feasible.
- Use fenced code blocks for excerpts; keep excerpts short and relevant.
- Do not suggest edits unless the user explicitly asks outside `$ask`.
