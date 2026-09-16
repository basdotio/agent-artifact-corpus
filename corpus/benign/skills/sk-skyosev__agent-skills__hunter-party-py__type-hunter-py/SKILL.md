---
name: type-hunter-py
description: |
  Audit Python code for weak type design — primitive obsession, stringly-typed APIs,
  broad unions, structural vs nominal confusion, type aliases hiding intent, and
  models that fail to make illegal states unrepresentable.

  Use when: reviewing type annotations for expressiveness, tightening domain models,
  reducing runtime checks via the type system, or preparing for stricter mypy/pyright
  configuration.
  Reports omit empty sections — no placeholder headings, empty tables, or negative statements like "no issues found".
disable-model-invocation: true
---

# Type Hunter

Audit code for **type design weaknesses** — places where the type system could prevent bugs but doesn't because the
types are too loose, too broad, or too clever. The goal: **types express domain intent precisely** so misuse is caught
at check-time and refactors are safe.

This skill focuses on type *design* — whether the right types exist and are used. For *enforcement* questions
(whether existing invariants hold post-construction, loose optionality, defensive access, error suppression), see
invariant-hunter-py.

## When to Use

- Reviewing type annotations for expressiveness and safety
- Tightening domain models before a refactor
- Reducing runtime validation by encoding invariants in the type system
- Preparing for stricter mypy/pyright configuration
- Auditing Python codebases transitioning from untyped to typed

## Core Principles

1. **Types encode domain rules.** `str` says nothing about what a value represents. `OrderId` (via `NewType`) says it's
   an order identifier — the type checker prevents mixing it with a user ID. Narrow types encode business meaning and
   let the compiler catch misuse.

2. **Make illegal states unrepresentable.** If an `Order` can be in state `"shipped"` but `tracking_number` is
   `Optional[str]`, the type allows shipped orders without tracking numbers. Better: model `ShippedOrder` as a separate
   dataclass that requires `tracking_number: str`.

3. **Unions should be exhaustively handled.** A `Union[Success, Failure, Pending]` is only as good as the handling of
   each variant. If new variants are added, the type checker should flag unhandled cases — use `assert_never()` and
   pattern matching with exhaustiveness checking.

4. **Don't fight the type system.** `cast()`, `# type: ignore`, and `Any` are escape hatches, not design tools. If
   you need them frequently, the types are misaligned with the actual data flow. Fix the types, not the checker.

5. **Type aliases should clarify, not obscure.** `UserId = str` is documentation; `NewType("UserId", str)` is
   enforcement. `Callback = Callable[[int, str, bool, Optional[dict]], Awaitable[Optional[str]]]` is a puzzle — name
   the parameters via a `Protocol`.

## What to Hunt

### 1. Primitive Obsession

Using `str`, `int`, `float`, `dict`, `list` where a domain type would be safer and more meaningful.

**Signals:**

- Functions accepting `str` for IDs, codes, slugs, URLs, emails, paths
- Functions accepting `int` for quantities, amounts, indices, timestamps
- `dict[str, Any]` as a function parameter or return type (domain data without shape)
- `list[str]` where the items have domain meaning (e.g., list of order IDs)
- Multiple parameters of the same primitive type that could be accidentally swapped:
  `def transfer(amount: int, from_id: str, to_id: str)` — `from_id` and `to_id` are interchangeable to the type
  checker

**Action:** Recommend `NewType`, dataclass, or `TypedDict` for domain-specific types. For ID types, `NewType` prevents
accidental mixing while having zero runtime cost.

### 2. Stringly-Typed APIs

Using string literals where `Literal` unions, `Enum`, or union types would provide type safety.

**Signals:**

- `str` parameter with runtime checks like `if status not in ("active", "inactive", "banned")`
- Dict keys used as a discriminator without `Literal` or `TypedDict` narrowing
- Error codes as bare strings instead of `Literal` union or `Enum`
- `**kwargs: Any` hiding structured options that should be typed
- Configuration dicts (`dict[str, Any]`) instead of typed config dataclasses

**Action:** Replace with `Literal["active", "inactive", "banned"]` for small closed sets, or `enum.Enum` /
`enum.StrEnum` for larger sets with behavior. Use `TypedDict` or dataclass for structured dictionaries.

### 3. Over-Broad Unions and `Optional` Overuse

Unions that are wider than the actual possible values, or `Optional` used where the *type definition* should not
permit absence.

**Boundary with invariant-hunter:** type-hunter owns "this type *should not be* `Optional` — redesign the model."
invariant-hunter owns "given a correctly non-Optional type, downstream code still does unnecessary `is not None`
checks." If the type definition is wrong, it belongs here. If the type is right but consumers don't trust it, it
belongs in invariant-hunter.

**Signals:**

- `Optional[X]` on a field that is always set after `__init__` or after a specific lifecycle point
  — the type definition itself is too loose
- `Union[str, int, float, bool, None]` — too broad, indicates unclear data model
- Return type `Optional[X]` where `None` means "not found" and also means "error" — conflated semantics
- `X | None` passed through multiple layers requiring `is not None` checks at every level
- `Optional` on fields that *should* force the caller to provide a value

**Action:** Narrow unions to the actual possible types. Split `Optional` into different return paths (e.g.,
raise exception for errors, return empty collection instead of `None`). Use `@overload` to narrow return types based on
input. Use separate dataclass variants instead of `Optional` fields that depend on state.

### 4. Structural vs. Nominal Confusion

Misuse of `Protocol` (structural typing) where a nominal type (ABC/base class) would be safer, or vice versa.

**Signals:**

- `Protocol` used for domain types where accidental structural matches are dangerous (e.g., any object with a
  `.process()` method satisfies `Processor`, even if it's unrelated)
- ABC/base class used for adapter interfaces where structural typing via `Protocol` would allow easier extension
- `isinstance()` checks in code that should use `Protocol` or union narrowing
- Overuse of `Any` to bridge between incompatible types that should share a proper protocol

**Action:**

- Use **nominal types** (ABC, base class) for domain concepts where identity matters: `Order`, `User`, `Payment`.
- Use **structural types** (`Protocol`) for capability interfaces: `Serializable`, `Renderable`, `Repository`. These
  describe what an object can do, not what it is.

### 5. Weak Discriminated Unions

Union types that lack a reliable discriminator field, forcing unsafe isinstance checks or `hasattr()` calls.

**Signals:**

- `Union[A, B, C]` where there's no common field with `Literal` type to distinguish variants
- `isinstance()` chains to narrow a union that should have a discriminator
- `hasattr()` checks to determine which variant of a union is present
- `type: str` field that should be `type: Literal["a"]` in each variant

**Action:** Add a `Literal` discriminator field to each variant. Use `@dataclass` variants with a shared `type`
field that narrows via `Literal`. Leverage pattern matching with `match/case` for exhaustive variant handling.

Example of well-discriminated union:

```python
from dataclasses import dataclass
from typing import Literal, Union

@dataclass
class Success:
    type: Literal["success"] = "success"
    value: str

@dataclass
class Failure:
    type: Literal["failure"] = "failure"
    error: str

Result = Union[Success, Failure]

def handle(result: Result) -> None:
    match result:
        case Success(value=v):
            print(v)
        case Failure(error=e):
            print(e)
```

### 6. Type Alias Soup

Type aliases that obscure rather than clarify, or missing aliases where they'd improve readability.

**Signals:**

- Deeply nested generics: `dict[str, list[tuple[int, Optional[str]]]]` used inline instead of named
- `TypeAlias` that just renames a primitive: `Name: TypeAlias = str` — provides documentation but no safety
- Multiple aliases for the same shape: `UserMap = dict[str, User]` and `UserDict = dict[str, User]`
- `Callable` types with 3+ parameters used inline: `Callable[[int, str, bool, dict[str, Any]], Awaitable[str]]`

**Action:**

- Replace `TypeAlias = str` with `NewType("X", str)` when the alias should prevent mixing
- Name complex generics: `OrderIndex: TypeAlias = dict[str, list[Order]]`
- For complex `Callable` signatures, define a `Protocol` with `__call__` for named parameters
- Eliminate duplicate aliases — one name per shape

### 7. Unsafe Narrowing and Type Guards

Incorrect or missing type narrowing that forces unsafe assertions or casts.

**Signals:**

- `cast()` used to narrow a type that could be narrowed via `isinstance()`, pattern matching, or `TypeGuard`
- `# type: ignore` on assignments that would pass with proper narrowing
- Missing `TypeGuard` function for custom narrowing logic (e.g., checking a dict has certain keys)
- `assert isinstance(x, Foo)` used for narrowing in production code (disabled by `-O` flag)
- `x: Any` followed by field access without narrowing — no type checking on the access

**Action:** Replace `cast()` with `isinstance()` checks or `TypeGuard` functions. Use pattern matching for union
narrowing. Reserve `cast()` for situations where the type checker genuinely cannot infer the correct type and runtime
checking is impossible or too expensive.

### 8. Generic Type Misuse

Overuse, underuse, or incorrect use of `TypeVar`, `Generic`, and `ParamSpec`.

**Signals:**

- `TypeVar` without constraints or bounds that should be constrained: `T = TypeVar("T")` where only `int | str` is
  valid — should be `T = TypeVar("T", int, str)` or `T = TypeVar("T", bound=Numeric)`
- `Generic[T]` class where `T` is only used once (doesn't relate input to output)
- Overly generic function where a simple union or overload would be clearer
- Missing `TypeVar` where a function should preserve the input type in its return
- `ParamSpec` / `Concatenate` used where a simpler `Protocol` would suffice

**Action:** Add bounds or constraints to `TypeVar` when only specific types are valid. Remove unnecessary generics
(use union or overload instead). Add generics when a function's return type truly depends on its input type.

## Audit Workflow

### Phase 1: Gain Context

1. **Resolve audit surface.** The prompt may specify the scope as:
   - **Diff**: files changed on the current branch vs base (`main`/`master`)
   - **Path**: specific files, folders, or layers
   - **Codebase**: the entire project
   If unspecified, default to **codebase**. For diff mode, resolve the file list:
   ```bash
   BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo main)
   SCOPE=$(git diff --name-only $(git merge-base HEAD $BASE)...HEAD)
   ```
   Constrain all subsequent scans to the resolved surface.
2. Identify the type checking configuration (mypy, pyright, pytype) and strictness level (`strict`, `basic`,
   `off`). Check `pyproject.toml`, `mypy.ini`, or `pyrightconfig.json`.
3. Identify domain models — data classes, TypedDicts, Pydantic models. These are the priority for type design.

### Phase 2: Scan for Type Design Signals

```bash
# Primitive-heavy function signatures
rg 'def \w+\(.*: (str|int|float|bool)(,|\))' --type py

# dict[str, Any] usage (untyped dicts)
rg 'dict\[str,\s*Any\]|Dict\[str,\s*Any\]' --type py

# Optional overuse
rg 'Optional\[|: .+ \| None' --type py

# Type escape hatches
rg '(: Any\b|cast\(|# type: ignore|# pyright: ignore)' --type py

# Stringly typed checks
rg '(if .+ (==|!=|in|not in) ["\x27]|\.get\(["\x27])' --type py

# isinstance chains (potential weak discrimination)
rg 'isinstance\(' --type py | head -30

# TypeVar and Generic usage
rg '(TypeVar|Generic\[|ParamSpec)' --type py

# NewType usage (or lack thereof)
rg 'NewType\(' --type py

# Enum usage
rg '(class \w+\(.*Enum\)|class \w+\(.*StrEnum\))' --type py

# Complex inline types (long Callable or deeply nested generics)
rg 'Callable\[\[.{40,}\]' --type py
```

### Phase 3: Evaluate Domain Models

1. Review dataclasses, TypedDicts, and Pydantic models for:
   - Primitive fields that should be `NewType` or domain types
   - `Optional` fields that should be required or split into separate models
   - Missing discriminator fields on union variants
   - Mutable fields that should be `frozen=True`

2. Review function signatures for:
   - `str`/`int` parameters that carry domain meaning
   - Return types that are too broad (e.g., `dict[str, Any]` when the shape is known)
   - `Any` parameters or returns where a `Protocol` or union would be correct

### Phase 4: Evaluate Type Safety Points

1. For each `cast()`, `# type: ignore`, `Any`: could proper narrowing or a better type design eliminate it?
2. For each union: is there an exhaustive discriminator? Are all variants handled (check for `assert_never()`)?
3. For each `Protocol`: is structural typing appropriate, or should this be nominal?
4. For each `TypeVar`: are constraints or bounds appropriate?

### Phase 5: Produce Report

## Output Format

Save as `YYYY-MM-DD-type-hunter-audit-{$LLM-name}.md` in the project's docs folder (or project root if no docs folder
exists).

```md
# Type Hunter Audit — {date}

## Scope

- Surface: {diff / path / codebase}
- Files: {count or list}
- Type checker: {mypy / pyright / pytype / none}
- Strictness: {strict / basic / off}
- Exclusions: {list}

## Findings

### Primitive Obsession

| # | Symbol | Location | Current Type | Suggested Type | Risk |
| - | ------ | -------- | ------------ | -------------- | ---- |
| 1 | `transfer()` args | file:line | `str, str` | `AccountId, AccountId` via NewType | High — IDs swappable |

### Stringly-Typed APIs

| # | Symbol | Location | String Usage | Suggested Type | Risk |
| - | ------ | -------- | ------------ | -------------- | ---- |
| 1 | `set_status()` | file:line | `status: str` checked at runtime | `Literal["active", "inactive"]` | Medium |

### Over-Broad Unions / Optional Overuse

| # | Symbol | Location | Current Type | Issue | Action |
| - | ------ | -------- | ------------ | ----- | ------ |
| 1 | `Order.tracking` | file:line | `Optional[str]` | Always set after shipping | Split into ShippedOrder |

### Structural vs. Nominal Confusion

| # | Symbol | Location | Current Design | Issue | Action |
| - | ------ | -------- | -------------- | ----- | ------ |
| 1 | `Processor` | file:line | Protocol | Domain type — accidental match risk | Use ABC |

### Weak Discriminated Unions

| # | Union | Location | Issue | Action |
| - | ----- | -------- | ----- | ------ |
| 1 | `Event` | file:line | No Literal discriminator | Add `type: Literal[...]` to each variant |

### Type Alias Issues

| # | Alias | Location | Issue | Action |
| - | ----- | -------- | ----- | ------ |
| 1 | `UserId = str` | file:line | Alias, not enforced | Use `NewType("UserId", str)` |

### Unsafe Narrowing

| # | Location | Escape Hatch | Action |
| - | -------- | ------------ | ------ |
| 1 | file:line | `cast(User, data)` | Use isinstance + TypeGuard |

### Generic Misuse

| # | Symbol | Location | Issue | Action |
| - | ------ | -------- | ----- | ------ |
| 1 | `process[T]` | file:line | Unbounded TypeVar, only int/str valid | Add constraint |

## Recommendations (Priority Order)

1. **Must-fix**: {primitive IDs, missing discriminators on critical unions, unsafe narrowing in domain logic}
2. **Should-fix**: {Optional overuse, stringly-typed APIs, broad unions}
3. **Consider**: {type alias cleanup, generic tightening, structural→nominal conversions}
```

## Operating Constraints

- **No code edits.** This skill produces an audit report only. Implementation is a separate step.
- **No empty sections.** Include only categories with findings. Omit a heading, table, or list entirely when it would contain zero items — do not include empty tables, placeholder subsections, or negative statements like "no dead exports", "none found", or "no issues".
- **Scope: type design only.** Do not flag runtime enforcement gaps (→ invariant-hunter-py), structural complexity
  (→ simplicity-hunter-py), naming issues (→ slop-hunter-py), test gaps (→ test-hunter-py), security
  (→ security-hunter-py), module boundary violations (→ boundary-hunter-py), or documentation gaps
  (→ doc-hunter-py). If a finding doesn't answer "could a better type prevent a bug here?", it doesn't belong
  here.
- **Evidence required.** Every finding must cite `file/path.py:line` with the exact type definition or usage.
- **Pragmatism beats purity.** Not every `str` needs a `NewType`. Flag type weaknesses where a bug is likely — ID
  parameters that could be swapped, states modeled with Optional that should be discriminated, unions without
  exhaustive handling. Skip trivial cases where the primitive type is genuinely sufficient.
- **Python version awareness.** Note when suggestions require specific Python versions (e.g., `match/case` requires
  3.10+, `type` statement requires 3.12+, `TypeGuard` requires 3.10+ or `typing_extensions`).
