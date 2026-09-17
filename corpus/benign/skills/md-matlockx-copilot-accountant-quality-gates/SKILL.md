---
name: quality-gates
description: Quality gate definitions, enforcement rules, 500 LOC limit, loop-back routing, commit conventions, and hook behavior. Load this skill when checking code quality or preparing to commit.
license: MIT
metadata:
  audience: ai-agents
  workflow: gates
---

# Quality Gates Skill

Defines what blocks a commit and how failures are routed back to the
responsible agent.

<!-- AIDEV-NOTE: This skill is the single reference for what constitutes a
     passing quality check. Both the QA agent and the git pre-commit hook
     enforce subsets of these gates. -->

## Gate Definitions

Every code change must pass ALL gates before it can be committed.

| Gate | What | How Verified | Hard block? |
|------|------|-------------|-------------|
| **Task** | Beads task exists with self-contained description | `bd show <id> --json` | Yes |
| **Tests** | Tests exist for changed code AND pass | `go test ./...` | Yes |
| **Lint** | No lint errors | `golangci-lint run` | Yes |
| **ADR** | ADR exists if change is architectural | Check `docs/adr/INDEX.md` | Yes |
| **Diff size** | Total diff under 500 LOC | `git diff --stat \| tail -1` | Yes |
| **Secrets** | No hardcoded credentials, tokens, or keys | Pattern grep | Yes |
| **Docs** | README/docs updated if user-facing behavior changed | Manual review | Yes |
| **AIDEV-NOTE** | Anchor comments on non-obvious logic | Manual review | Soft |
| **Commit format** | Conventional commit with task ID | Regex check | Yes |

## The 500 LOC Rule

No single task may produce a diff exceeding 500 lines of code (additions + deletions).

### How to measure

```sh
git diff --shortstat
# Example: 5 files changed, 342 insertions(+), 48 deletions(-)
# Total: 342 + 48 = 390 LOC ✓
```

### What counts

- Additions and deletions in source code files
- Test files count toward the limit (they are code)
- Generated code (protobuf, mocks) does NOT count — exclude with `-- . ':!generated/'`
- Documentation-only changes do NOT count

### When exceeded

If a task's diff exceeds 500 LOC:
1. Stop implementation
2. Route back to the Designer agent
3. Designer splits the task into smaller sub-tasks
4. Developer implements each sub-task separately

## Loop-Back Routing

When a gate fails, QA routes to the responsible agent:

| Failure | Responsible agent | Expected action |
|---------|------------------|----------------|
| Tests missing for changed code | **Developer** | Write tests (TDD: test first) |
| Tests fail | **Developer** | Fix failing tests |
| Lint errors | **Developer** | Fix lint issues |
| No Beads task | **Designer** | Create task retroactively |
| Task has no description | **Designer** | Add self-contained description |
| ADR missing for architectural change | **Designer** | Write ADR, update INDEX.md |
| Diff >500 LOC | **Designer** | Split into smaller tasks |
| Hardcoded secrets | **Developer** | Move to env vars / config |
| Docs out of date | **Developer** | Update docs |
| Commit format wrong | **Developer** | Rewrite commit message |

### Loop-Back Protocol

1. QA identifies the failure
2. QA states which gate failed and why
3. QA names the responsible agent
4. Responsible agent fixes the issue
5. QA re-runs ALL gates (not just the failed one)
6. Repeat until all gates pass

## Commit Message Format

Use Conventional Commits with a Beads task ID:

```
<type>(<scope>): <subject> [BD-<task-id>]

<body>
```

### Rules

- **type** (required): `feat`, `fix`, `refactor`, `test`, `chore`, `docs`, `style`, `perf`, `ci`, `build`
- **scope** (optional): module or package name
- **subject** (required): imperative mood, lowercase, no period
- **task ID** (required): `[BD-xxx]` where xxx is the Beads task ID
- **body** (recommended): what changed and why, not how

### Examples

```
feat(auth): add JWT token validation [BD-abc123]

Add middleware that validates JWT tokens on protected endpoints.
Tokens are verified against the JWKS endpoint configured in env.

test(auth): add JWT validation test cases [BD-abc123]

Table-driven tests covering valid tokens, expired tokens,
malformed tokens, and missing authorization headers.
```

## Task Description Requirements

Every Beads task must have a description detailed enough to create a Jira
item from it. The description must include:

1. **What**: Specific deliverables (files to create/modify, functions to implement)
2. **Why**: Business or technical motivation
3. **Acceptance criteria**: Concrete, testable conditions for "done"
4. **Scope**: Estimated LOC, files affected
5. **References**: Related ADRs, file paths, external links

### Example

```
Title: Add rate limiting middleware for API endpoints

What: Create a rate limiting middleware in internal/middleware/ratelimit.go
that uses a token bucket algorithm. Wire it into the HTTP router for all
/api/ routes.

Why: Public API endpoints are currently unprotected against abuse. A single
client can overwhelm the service with requests.

Acceptance criteria:
- [ ] Middleware limits requests to 100/minute per IP by default
- [ ] Limit is configurable via RATE_LIMIT_RPM env var
- [ ] Returns 429 with Retry-After header when limit exceeded
- [ ] Table-driven tests cover: under limit, at limit, over limit, reset
- [ ] golangci-lint passes

Scope: ~120 LOC (60 implementation + 60 tests), 2 files
References: ADR-003-rate-limiting.md
```

## Hook Enforcement

### Git Pre-Commit Hook (`hooks/pre-commit`)

Runs on every commit. Checks:
1. `go test ./... -race` — all tests pass with race detector
2. `golangci-lint run` — no lint errors
3. Diff size under 500 LOC
4. No hardcoded secrets (pattern grep)

If any check fails, the commit is rejected. Cannot be bypassed (no `--no-verify`).

### Git Commit-Msg Hook (`hooks/commit-msg`)

Validates every commit message:
1. Conventional Commits format (`<type>(<scope>): <subject>`)
2. Beads task ID present (`[BD-xxx]`)

### Installation

```sh
./hooks/install.sh          # Symlinks hooks into .git/hooks/
./hooks/install.sh --force  # Overwrite existing hooks
```

### What Is NOT Enforced by Hooks

These gates require agent judgment and are enforced by the QA agent:
- ADR existence for architectural changes
- Task description quality
- Documentation currency
- AIDEV-NOTE anchor comments
