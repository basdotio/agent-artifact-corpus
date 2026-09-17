---
name: python-quality
description: Run formatting, linting, and tests using uv + Ruff + pytest
---

# Python Quality Check Skill

Use this skill when asked to:
- "check quality"
- "make CI pass"
- "fix lint errors"
- "run tests"
- "prepare for PR"

## Workflow

Execute these steps in order:

### 1. Sync Dependencies

```bash
uv sync --all-groups
```

### 2. Format Code

```bash
uv run ruff format .
```

### 3. Lint and Auto-fix

```bash
uv run ruff check . --fix
```

### 4. Run Tests

```bash
uv run pytest -q
```

## On Failure

If any step fails:

1. **Format fails**: Check for syntax errors first
2. **Lint fails**: Review unfixable issues, explain the root cause
3. **Tests fail**: 
   - Show the failing test output
   - Explain the root cause
   - Propose a minimal fix
   - Update tests if behavior change is intentional

## Quick Script

For automated checks, use:

```bash
uv run python .github/skills/python-quality/scripts/check.py
```

## Success Criteria

- All files formatted consistently
- No lint errors (warnings may be acceptable)
- All tests pass
- No decrease in test coverage (if measured)
