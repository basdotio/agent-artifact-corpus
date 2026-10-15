---
name: engineering-standards
description: This skill should be used before writing or changing code in any repository, for example when starting work in an existing codebase, creating a new project, module, or service, deciding how to structure code, or when the user mentions SOLID, clean architecture, design patterns, LLD, code quality, conventions, or refactoring. It explains how to audit and follow an existing repo's conventions, how to propose a low-level design for a new repo, and the code-level standards for naming, functions, errors, logging, configuration, security, and dependencies, with stack guides for Python (FastAPI, Celery, Redis), Android (Kotlin), web frontends, and GCP.
---

# Engineering standards

Code is read far more often than it is written, usually by someone in a hurry who did not write it. The standards below exist so that a person opening any file Claude touched finds the structure they expect, names that say what things are, and errors that explain themselves.

## The one rule

Write no code until a design approach is agreed. In an existing repository the approach is "follow what is already there", which takes an audit to learn. In a new repository it is a low-level design proposal the user approves.

## Existing repository

1. Audit the repository with references/existing-repo-audit.md: docs first, then manifests and tool configs, then two or three representative files per layer, then tests.
2. Write the conventions summary from that reference and put it in the plan's Context section. Every executor follows it.
3. Follow the conventions even where you would choose differently. A consistent codebase is easier to maintain than one that is locally perfect in a few places.
4. When you find design problems, add them to a tech-debt list (template in the audit reference) instead of fixing them. Mention the list at handoff.
5. Refactor only with the user's approval, and in commits separate from feature work.

## New repository

1. Settle scope, scale, team size, hosting, and budget with clarifying questions (planning skill).
2. Propose the architecture and low-level design in a decision brief. The defaults in references/new-project-setup.md are a starting point, not an answer: a modular monolith with layered or clean architecture for backends, MVVM with a repository layer on Android, and feature folders with component-driven UI on the web.
3. Propose the folder structure, tooling (formatter, linter, type checker, test runner, pre-commit, CI), and the first slices from the same reference.
4. Scaffold only after approval, as the first slice: tooling, CI, and an empty test that passes.

## Design principles

references/design-principles.md explains SOLID, KISS, YAGNI, DRY, composition over inheritance, and dependency direction in plain words, with short examples and the cases where each does not apply. The short version:

- Each module has one reason to change.
- Business logic depends on interfaces, and infrastructure (database, HTTP, queues) is injected.
- Dependencies point inward: API and infrastructure depend on services, services depend on the domain, never the reverse.
- Add an abstraction on the third repetition, not the first.
- Prefer composition to inheritance, and small explicit functions to clever ones.

## Code-level standards

references/code-standards.md has the details. The rules a reviewer will check first:

- Names say what a thing is or does, in the repo's naming style. Include units (timeout_seconds) and avoid abbreviations nobody uses.
- Functions do one thing. Treat more than about 40 lines or more than four parameters as a smell.
- Errors are never swallowed. Catch specific exceptions, add context, and map domain errors to transport errors (HTTP status, UI message) only at the edge.
- Logs are structured, carry a request or job ID, and never contain secrets, tokens, or personal data.
- Configuration comes from environment variables through one typed settings object, and .env.example stays in sync.
- Types are explicit: type hints in Python, strict TypeScript, Kotlin null safety without `!!`.
- Comments explain why. No commented-out code, and no TODO without an owner or issue.
- No blocking I/O in async code, a timeout on every network call, and idempotent background jobs.

## Security

references/security.md covers input validation, injection, authorization on every endpoint, secrets, SSRF, path traversal, deserialization, dependency scanning, and Android-specific issues. Check it whenever a change touches input handling, authentication, files, external calls, or secrets.

## Dependencies

- Prefer the standard library and what the repository already uses.
- Before adding a package, confirm it exists under that exact name (typosquatting is real), is maintained, and has a license the project can use. Check the current version in the registry instead of trusting memory, and pin it.
- Ask the user before adding, removing, or upgrading any dependency. The shell guard asks too.

## Stack guides

Load only the guide for the stack in front of you:

- references/stack-python.md for FastAPI, Pydantic, SQLAlchemy, Alembic, Celery, and Redis.
- references/stack-android.md for Kotlin, MVVM, Compose, coroutines, Hilt, Room, and Firebase on Android.
- references/stack-web.md for TypeScript and React-style frontends.
- references/stack-gcp.md for Cloud Run, IAM, Secret Manager, Cloud SQL, Firestore, Pub/Sub, and Cloud Tasks.

If the repository uses a different stack, apply the principles above and the repository's own conventions.
