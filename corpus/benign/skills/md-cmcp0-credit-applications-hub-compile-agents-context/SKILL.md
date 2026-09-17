---
name: compile-agents-context
description: Generate and maintain AGENTS.md as a living project context document by scanning the repository, discovering agents/skills, and extracting conventions. Use when initializing Codex context for a repo, refreshing stale AGENTS.md, or after significant project structure changes.
---

# Compile Agents Context

## Overview

Use this skill to run the old `init` command workflow as a Codex-native skill. It standardizes AGENTS discovery and regeneration with explicit options.

## Inputs

- `scan_depth`: `shallow`, `medium`, or `deep` (default `medium`)
- `include_dependencies`: `true` or `false` (default `true`)
- `auto_watch`: `true` or `false` (default `true`)

## Workflow

### 1. Discover project context

- Read root project files (`README`, manifests, config files).
- Scan directories according to `scan_depth`:
  - `shallow`: root + first-level key folders.
  - `medium`: default, includes feature/service folders.
  - `deep`: broad scan for full architecture and conventions.

### 2. Discover agents and skills

- Search for agents in `.cursor/agents`, `.cline/agents`, `.agents`, `agents`, `.ai`, `prompts`, `system-prompts`.
- Search for skills in `.cursor/skills`, `.codex/skills`, `.agents/skills`, and user-level paths if accessible.
- Capture each discovered item with name, location, purpose, and trigger scenarios.

### 3. Extract conventions

- Capture coding and formatting standards from lint/format configs.
- Capture architecture, testing, and build/deploy patterns from project files and docs.
- Include dependency context only when `include_dependencies=true`.

### 4. Generate or refresh AGENTS.md

- Write a complete `AGENTS.md` in repository root.
- Include project overview, stack, structure, agent ecosystem, skill registry, conventions, and workflows.
- Preserve existing high-signal custom instructions when regenerating.

### 5. Configure auto-maintenance rule (optional)

- If `auto_watch=true`, create/update `.cursor/rules/agents-maintainer.md`.
- Define a rule that prompts AGENTS refresh when significant project structure changes occur.

## Reference

Use `/Users/carloscaceres/local/marius/code_samples/credit-applications-hub/.agents/skills/context-compilation-guide/SKILL.md` for the detailed section template and generation depth guidance.

## Output Contract

- Updated `/Users/carloscaceres/local/marius/code_samples/credit-applications-hub/AGENTS.md`
- Optional `/Users/carloscaceres/local/marius/code_samples/credit-applications-hub/.cursor/rules/agents-maintainer.md`
- Short summary listing files updated and discovery statistics
