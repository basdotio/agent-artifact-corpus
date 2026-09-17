---
name: Code Standards
description: This skill should be used when the user asks about "code quality", "file size limits", "function length", "KISS", "DRY", "YAGNI", "SRP", "best practices", "clean code", "cyclomatic complexity", "code review checklist", "refactoring rules", or mentions specific thresholds for lines of code, function sizes, or code complexity metrics.
version: 0.1.0
---

# Code Standards

Practical code quality standards with concrete "rules of thumb" - actionable thresholds rather than philosophy.

## Core Principles

### KISS (Keep It Simple, Stupid)
Prefer the simplest solution that works. Avoid "clever" code, magic, and over-engineering.

### DRY (Don't Repeat Yourself)
Remove duplication when it's real duplication. Avoid premature abstraction.

### YAGNI (You Aren't Gonna Need It)
Build features/abstractions only for real, current needs - not hypothetical future ones.

### SRP (Single Responsibility Principle)
One module/class/function should have one reason to change.

### Separation of Concerns
Keep UI, domain logic, persistence, integration, and config separated.

### Principle of Least Surprise
Code should behave as a reader expects.

### Fail Fast, Loudly
Validate inputs early; crash with clear errors rather than silently continuing.

## Size Limits

### File Size (Lines of Code)

| Level | LOC | Action |
|-------|-----|--------|
| Target | 100-300 | Ideal |
| Soft limit | 400 | Consider splitting (warning) |
| Hard limit | 800 | Must refactor (critical) |

When a file grows too large, ask what responsibilities got mixed (SRP), then split by domain or feature.

### Function/Method Size

| Level | LOC | Action |
|-------|-----|--------|
| Target | 10-30 | Ideal |
| Soft limit | 50 | Review (warning) |
| Hard limit | 80 | Must refactor (critical) |

If a function cannot be named clearly, it's doing too much.

### Cyclomatic Complexity

| Score | Action |
|-------|--------|
| >10 | Review required |
| >15 | Refactor strongly |
| >20 | Almost always too complex |

## Language-Specific Thresholds

Different languages have different conventions. See `references/language-thresholds.md` for complete per-language limits.

## Naming & Readability

- Prefer clear names over comments
- Use consistent vocabulary (e.g., "user" everywhere, not sometimes "customer")
- Avoid abbreviations unless universally known
- Boolean names: `isEnabled`, `hasAccess`, `shouldRetry`

## Comments & Documentation

- Comment **why**, not **what**
- Don't narrate obvious code
- If code needs a long comment to understand "what", rewrite the code

## Error Handling & Reliability

- Don't swallow errors - log/return them meaningfully
- Use typed errors / error codes consistently
- Add context at boundaries (I/O, API calls)
- Handle retries with backoff + limits; make retry logic explicit

## Testing Guidelines

- Test behavior, not implementation
- Keep unit tests fast; integration tests for boundaries
- Follow the test pyramid:
  - Many unit tests
  - Fewer integration tests
  - Minimal end-to-end tests
- Every bug fix should add a test that would have caught it

## Configuration Best Practices

**What goes to config vs code:**
- **Config**: Environment-specific values (URLs, keys, feature flags, timeouts)
- **Code**: Business rules and behavior

**12-Factor App style:**
- Config in env vars (or config file loaded per env)
- No secrets in git
- Provide defaults (safe) + validation on startup
- Make config observable (print effective config at startup without secrets)

## Architecture / Boundaries

- Keep pure domain logic free of I/O
- Create adapters for DB, external APIs, queues
- Prefer explicit dependencies (DI) over hidden globals/singletons
- Avoid "God objects" - no huge service that does everything

## Git & Code Review Hygiene

- Small PRs (ideally < 300-500 LOC changed)
- Clear commit messages, one logical change per commit
- Review checklist: readability, tests, error handling, security, performance

## Security Basics

- Validate + sanitize external input
- Use parameterized queries
- Principle of least privilege for credentials
- Don't log secrets/PII
- Dependabot/Snyk + lockfile hygiene

## Review Checklist

Quick validation for code reviews:

- [ ] Can I explain this code in 30 seconds?
- [ ] File/function size within limits? If not, is there a clear reason?
- [ ] One responsibility per module/class?
- [ ] No hidden global state / surprising side effects?
- [ ] Errors handled meaningfully (no silent failures)?
- [ ] Config validated; no secrets in repo?
- [ ] Tests cover the important behavior?
- [ ] Formatting/lint/type checks pass?

## Using This Skill

### Analyzing Code

To check code against standards:
1. Read the target file(s)
2. Calculate approximate LOC for file and functions
3. Identify complexity hotspots
4. Report violations using structured table format

### Output Format

Report violations using this table format:

| File | Issue | Severity | Line | Suggestion |
|------|-------|----------|------|------------|
| `src/service.ts` | File exceeds 400 LOC (742) | Warning | - | Split by domain |
| `src/service.ts:45` | Function `processOrder` exceeds 80 LOC (112) | Critical | 45-157 | Extract helper functions |

Severity levels:
- **Info**: Within soft limits but worth noting
- **Warning**: Exceeds soft limits, should address
- **Critical**: Exceeds hard limits, must address

## Additional Resources

### Reference Files

For detailed thresholds and patterns, consult:
- **`references/language-thresholds.md`** - Per-language size limits and conventions
- **`references/refactoring-patterns.md`** - Common refactoring techniques for violations

### Plugin Commands

Use plugin commands for automated analysis:
- `/code-standards:check [path]` - Analyze files
- `/code-standards:fix [path]` - Auto-refactor violations
- `/code-standards:checklist` - Output review checklist
