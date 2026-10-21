---
name: codebase-overview
description: Use when asked to create or update a repository's codebase overview doc — inspects the repo and writes an accurate, grounded CODEBASE_OVERVIEW.md for humans and future AI agents.
---

# Codebase Overview Skill

You create or update a repository-level `CODEBASE_OVERVIEW.md` for humans and future AI coding agents.

The overview must be accurate, concrete, and grounded in the current repository state. Do not invent implemented features, passing tests, scripts, APIs, directories, or architectural decisions.

## Main Goal

Create or update a Markdown file named `CODEBASE_OVERVIEW.md`.

Prefer this location order:

1. `docs/CODEBASE_OVERVIEW.md` if a `docs/` directory exists.
2. Root-level `CODEBASE_OVERVIEW.md` if that is the existing convention.
3. Ask only if both exist and it is unclear which one is canonical.

If an overview already exists, update it in place. Preserve useful existing structure, but correct stale or inaccurate content.

## Required Behaviour

Before writing, inspect the repository. Use read-only tools — `Glob`, `Grep`, `Read`. Do not use `cat`/`find`/`ls` via Bash when a dedicated tool fits.

Map the structure first:

- `Glob` `**/*` (or scoped patterns) to see the file tree.
- `Read` likely project files when present: `README.md`, `AGENTS.md`, `CLAUDE.md`, `pyproject.toml`, `package.json`, `pnpm-lock.yaml`, `uv.lock`, `requirements.txt`, `Makefile`, `docker-compose.yml`, `Dockerfile`, `.github/workflows/*`, `docs/*`.

For Python projects, inspect source and test structure.
For JavaScript or TypeScript projects, inspect source, package scripts, config, and tests.
For monorepos, identify each major app, package, or service separately.

Do not run destructive commands.
Do not install dependencies unless the user explicitly asks.
Do not run long test suites unless asked. If test status is needed, inspect existing docs or run the smallest obvious command only when safe.

## Accuracy Rules

Be blunt and precise. Use wording like:

- Implemented
- Partially implemented
- Scaffolded only
- Not implemented
- Not verified
- Expected but absent

Do not use vague claims such as "appears robust" unless backed by code or tests.

Do not say tests pass unless you actually ran them in the current session or the repository contains a clearly recent record saying they pass.

If you did not run tests, say:

    Test status was not verified during this update.

If you did run tests, include the command run and a result summary.

## Recommended Document Structure

Use this structure unless the repo clearly needs something else:

```
# Codebase Overview

Last updated: YYYY-MM-DD

## Purpose
## Current Implementation Status
## Codebase Map
## Main Components
## Runtime Shape
## Public API / Interfaces
## Data Model / Domain Model
## Configuration And Dependencies
## Tests And Verification
## Important Design Decisions
## Known Gaps / Not Yet Implemented
## Operational Notes
## Risks / Things Future Agents Should Not Assume
## Suggested Next Steps
```

Section intent:

- **Purpose** — what this repository is for.
- **Current Implementation Status** — what is implemented, partially implemented, scaffolded, absent.
- **Codebase Map** — concise directory tree of important files and directories.
- **Main Components** — major apps, packages, services, modules, libraries.
- **Runtime Shape** — how the code runs: app factories, entrypoints, CLIs, workers, jobs, APIs, scripts.
- **Public API / Interfaces** — HTTP endpoints, CLI commands, library entrypoints, data contracts.
- **Data Model / Domain Model** — key domain objects and important fields.
- **Configuration And Dependencies** — package managers, dependency files, env vars, config files, workspace structure.
- **Tests And Verification** — test locations, commands, known latest results. Only claim tests pass if verified.
- **Important Design Decisions** — significant architecture choices, constraints, trade-offs.
- **Known Gaps / Not Yet Implemented** — missing features, scaffolds, TODOs, intentional absences.
- **Operational Notes** — how to run locally, common commands, state/persistence behaviour, ports, gotchas.
- **Risks / Things Future Agents Should Not Assume** — warnings for future agents and humans.
- **Suggested Next Steps** — concrete next implementation steps.

Drop sections that genuinely do not apply rather than padding them.

## Repository Inspection Checklist

When creating or updating the overview, check:

- top-level structure
- package/workspace configuration
- source directories
- test directories
- docs
- scripts and commands
- API route definitions
- CLI entrypoints
- app factories
- config/env handling
- database or persistence code
- seed data
- migrations
- Docker/deployment files
- CI workflows
- existing TODOs or scaffolds
- generated or ignored directories

## Style

Write for a technical human who has not seen the repo before.
Use concise but complete explanations.
Prefer concrete file paths.
Avoid hype. Avoid generic filler.
Do not include huge code snippets.
Use tables only when they make the information easier to scan.

## Handling Existing Overviews

If `CODEBASE_OVERVIEW.md` already exists:

1. Read it.
2. Check whether each major section is still accurate.
3. Update stale sections.
4. Add new directories or features.
5. Remove or clearly mark obsolete claims.
6. Preserve useful details.
7. Do not rewrite everything unless it is badly wrong.

## Handling Unclear Areas

If a feature is scaffolded but not wired up, say so. Example:

    The `harness/` directory exists but currently contains no implemented runner.

If a file exists but is empty, say so. Example:

    `tasks/task_01_sla_breach/` exists as a scaffold but does not yet contain prompts, tests, or metadata.

If two components appear intended to be equivalent but there is no automated contract test proving equivalence, say that.

## Output Requirements

After updating the file, report:

- the path updated
- the main changes made
- anything uncertain
- whether tests or validation commands were run

Do not claim the repository is complete unless the overview proves it.
