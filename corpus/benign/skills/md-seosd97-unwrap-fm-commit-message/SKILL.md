---
name: commit-message
description: Generate semantic commit messages. Use when committing changes or writing git commit messages.
---

# Commit Message (Semantic)

## Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

## Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code style (formatting, semicolons, etc.) |
| `refactor` | Code refactoring (no feature/fix) |
| `perf` | Performance improvement |
| `test` | Adding/updating tests |
| `build` | Build system or dependencies |
| `ci` | CI/CD configuration |
| `chore` | Maintenance tasks |
| `revert` | Revert previous commit |

## Scope (optional)

Component or area affected:
- `auth`, `api`, `ui`, `router`, `config`, etc.

## Rules

1. Subject: imperative mood, lowercase, no period, max 50 chars
2. Body: explain what and why (not how)
3. Footer: breaking changes, issue references

## Examples

```
feat(auth): add login with google

fix(api): handle null response from user endpoint

refactor(components): extract header into separate component

docs: update README with setup instructions

chore: update dependencies

feat(router)!: change route structure

BREAKING CHANGE: routes now use folder-based structure
```

## Breaking Changes

Use `!` after type/scope or add `BREAKING CHANGE:` in footer:

```
feat(api)!: change response format

BREAKING CHANGE: API now returns { data, meta } instead of raw data
```
