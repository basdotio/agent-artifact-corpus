---
name: python-clean-code
description: Write clean, maintainable Python code following PEP 8, type hints, and pragmatic clean architecture. Use when writing Python code, creating new Python projects, refactoring existing code, or reviewing Python implementations. Triggers on Python file creation, code generation requests, project scaffolding, or refactoring tasks.
---

# Python Clean Code

Write clean, maintainable Python code with proper structure and conventions.

## When Triggered

When activated, **immediately read the relevant reference files** and apply guidelines without asking for confirmation:

- **For any Python code**: Read `references/coding-style.md`
- **For project structure decisions**: Read `references/project-structure.md`
- **For FastAPI/API projects**: Read `references/vertical-slice-api.md`

Always apply these guidelines proactively and automatically.

## Core Principles

1. **Type hints always** - Every function signature and class attribute
2. **Self-explanatory code** - Comments explain *why*, not *what*
3. **Small focused functions** - Single responsibility, early returns
4. **Flat project structure** - Virtual layers, not rigid folders

## Quick Reference

### Naming

```python
variable_name = "snake_case"
CONSTANT_VALUE = "UPPER_SNAKE_CASE"
def function_name() -> None: ...
class ClassName: ...
```

### Data Structures

```python
# Small structures → dataclass
@dataclass
class Point:
    x: float
    y: float

# If Pydantic available → use it for validation
class UserCreate(BaseModel):
    email: str
    name: str = Field(min_length=1)

# Complex behavior → regular class
class OrderProcessor:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
```

### Function Design

```python
# ✅ Good: early return, clear naming
def get_user_discount(user: User, order: Order) -> Decimal:
    if not user or not order:
        return Decimal("0")

    if order.total <= MIN_ORDER_FOR_DISCOUNT:
        return Decimal("0")

    return VIP_DISCOUNT if user.is_vip else STANDARD_DISCOUNT


# ❌ Bad: nested, unclear
def calc(u, o):
    d = 0
    if u:
        if o:
            if o.total > 100:
                if u.is_vip:
                    d = 0.2
    return d
```

### Expressive Conditions

```python
# ✅ Extract complex conditions
is_business_hours = 9 <= current_hour <= 17
is_weekday = current_day < 6
can_process = is_business_hours and is_weekday and not is_holiday

if can_process:
    process_order()
```

## Project Initialization

Generate new project scaffold:

```bash
python scripts/init_project.py my-project --output /path/to/dir
```

Creates:
```
my-project/
├── pyproject.toml
├── Makefile
├── src/my_package/
│   ├── base.py          # Abstract interfaces
│   ├── config.py        # Configuration
│   ├── entities/        # Domain models
│   ├── services/        # Business logic
│   ├── workflows/       # Orchestration
│   └── infrastructure/  # External systems
└── tests/
```

## Reference Files

The following reference files are automatically consulted when this skill is triggered:

- **`references/coding-style.md`** - Comprehensive Python coding conventions: naming, type hints, imports, docstrings, and best practices
- **`references/project-structure.md`** - Clean architecture patterns, dependency injection, project layout, and common anti-patterns
- **`references/vertical-slice-api.md`** - FastAPI vertical slice architecture for feature-based API organization

## Code Review Checklist

Before completing Python code:

- [ ] Type hints on all functions and class attributes
- [ ] `snake_case` variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants
- [ ] No magic numbers - use named constants
- [ ] Functions do one thing, max 20-30 lines
- [ ] Early returns instead of nested conditions
- [ ] No comments explaining *what* code does
- [ ] Imports grouped: stdlib → third-party → local
