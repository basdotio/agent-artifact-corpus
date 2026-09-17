---
name: update-agents-md
description: "Maintain AGENTS.md files across a repo: find and review every AGENTS.md, apply hygiene rules (fix outdated or incorrect guidance, reduce verbosity, split large sections into docs and link them), add newly learned context from the current conversation, and provide a concise enumerated update summary. Use when asked to update AGENTS files, run/sweep the agents update skill, or when AGENTS.md maintenance is required across a repository or subfolder."
---

# Update AGENTS.md

## Overview

Keep AGENTS.md files accurate, concise, and within size limits by sweeping the repo, updating stale guidance, and reporting changes in a short numbered list.

## Workflow

### 1) Locate the scope

- Use `CODEX_WORKTREE` as the root if set; otherwise use the current working directory.
- Find all AGENTS.md files with `rg --files -g 'AGENTS.md'`.
- Read each AGENTS.md in full before editing.

### 2) Delegate subfolder updates

- If a subfolder has its own AGENTS.md and the changes are specific to that subfolder, deploy a subagent to update it.
- If delegation is unavailable, update it directly and note the limitation.

### 3) Apply hygiene rules

- Fix anything outdated or incorrect, even if unrelated to the immediate request.
- Tighten verbose sections without losing meaning.
- If a section grows to hundreds of lines, move it into `docs/` (or an existing docs file) and link it from a single references list near the top of AGENTS.md.
- Do not allow any AGENTS.md to exceed 1000 lines; split content into docs and link it if needed.
- Keep edits ASCII unless the file already uses non-ASCII characters.

### 4) Add new learnings

- If the current conversation reveals reusable guidance, add it to the most relevant AGENTS.md.

### 5) Report

- Provide a concise enumerated list of updates made.
- If no changes were needed, state that explicitly.
