---
name: type-checking
description: Use when adding type hints, fixing type checker errors, expanding type coverage, or when user mentions "type check", "pyright", "basedpyright", "mypy", "type hints", "type errors", "type annotations", "typing", "Any type", "weak types".
---

# Type Checking with Pyright/Basedpyright

Use pyright or basedpyright for gradual type checking adoption.

## Core Principles

1. **Minimize Logic Changes**: Type checking should NOT change runtime behavior
2. **Test After Changes**: Always run tests after adding type hints
3. **Hunt Down Root Causes**: Never use `# type: ignore` as first resort

## Quick Start

When fixing type errors:

```bash
# 1. Run type checker
pyright <file-or-directory>
# or
basedpyright <file-or-directory>

# 2. Fix errors (see patterns.md for common fixes)

# 3. Verify no behavior changes
git diff main
pytest tests/
```

## Fix Priority Order

1. **Add proper type annotations** (Optional, specific types)
2. **Fix decorator return types**
3. **Use `cast()`** for runtime-compatible but statically unverifiable types
4. **Last resort: `# type: ignore`** only for legitimate cases

## Common Quick Fixes

### Field Defaults
```python
# Use keyword syntax
role: Role = Field(default=Role.MEMBER, description="...")

# Positional default - avoid
role: Role = Field(Role.MEMBER, description="...")
```

### Optional Parameters
```python
# Correct
def my_function(channel_id: Optional[str] = None):

# Wrong
def my_function(channel_id: str = None):
```

### Weak Types - NEVER Use
```python
# NEVER
items: list[Any]
data: dict
result: Any

# ALWAYS use specific types
items: list[DataItem]
data: dict[str, ProcessedResult]
result: SpecificType | OtherType
```

### Prefer cast() Over type: ignore
```python
from typing import cast

# Preferred
typed_results = cast(list[ResultProtocol], results)
selected = select_by_score(typed_results)

# Less clear
selected = select_by_score(results)  # type: ignore[arg-type]
```

## When to Use type: ignore

Only for:
1. Function attributes: `func._attr = val  # type: ignore[attr-defined]`
2. Dynamic/runtime attributes not in type system
3. External library quirks (protobuf, webhooks)
4. Legacy patterns requiring significant refactoring

DO NOT use for simple fixes (add Optional, fix return types, add imports).

## Reference Files

For detailed patterns and procedures:
- [references/patterns.md](references/patterns.md) - Common Pydantic + Pyright patterns with examples
- [references/expanding-coverage.md](references/expanding-coverage.md) - How to add new modules to type checking

**Remember**: Always verify changes with `git diff main` before committing.
