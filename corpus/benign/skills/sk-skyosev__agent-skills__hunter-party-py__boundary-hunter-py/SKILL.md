---
name: boundary-hunter-py
description: |
  Audit Python packages and modules for black-box boundary violations — leaked internals via exports, coupling through
  shared types, Law of Demeter chains, missing abstraction layers around externals, and over-exported APIs.

  Use when: reviewing package structure, shrinking public API surface, enforcing encapsulation,
  preparing modules for replacement, or untangling tight coupling between layers.
  Reports omit empty sections — no placeholder headings, empty tables, or negative statements like "no issues found".
disable-model-invocation: true  
---

# Boundary Hunter

Audit Python code for **module boundary violations** — places where implementation details leak through exports,
where modules reach into each other's internals, or where coupling makes replacement impossible. The goal: **every
package is a black box, replaceable from its interface alone.**

## When to Use

- Reviewing package boundaries before or after a refactor
- Shrinking a package's public API to what is actually consumed
- Preparing a package to be replaceable (rewritable from interface alone)
- Untangling tight coupling between layers or packages
- Wrapping external dependencies behind internal abstractions
- Enforcing unidirectional dependency flow between layers

## Core Principles

1. **A package is its interface.** The public API is defined by a combination of `__all__`, `__init__.py` re-exports,
   naming conventions (`_` prefix for private), and documentation. Everything not part of the public API is an
   implementation detail. Exports should describe _what the package does_, never _how it does it_. If a consumer must
   understand internals to use the API correctly, the boundary is broken.

2. **Minimal public surface.** Export only what is consumed or serves as a deliberate extension point. Every additional
   export is a coupling point that constrains future changes. Use `__all__`, explicit `__init__.py` re-exports, or
   `_` prefix naming to signal the intended public surface. Not every package needs `__all__` — but the boundary
   should be inferable without reading internals.

3. **Depend on abstractions, not concretions.** Modules should depend on protocols (ABCs, `typing.Protocol`) owned by
   the consumer or a shared kernel — not on concrete implementations from other packages. If module A imports a class
   from module B, A is coupled to B's implementation. If A imports a Protocol that B happens to implement, A is coupled
   only to the protocol contract.

4. **Dependency direction must follow architectural intent.** In a layered architecture, dependencies flow inward:
   infrastructure → application → domain. A domain module importing a concrete implementation from infrastructure is a
   boundary violation. **Exception:** type-only imports (under `TYPE_CHECKING`) from a shared kernel or contracts layer
   that both sides depend on are not violations — this is standard DDD practice. Runtime import cycles are always
   violations.

5. **Wrap externals — don't let them leak.** Third-party types and APIs should not appear in domain or application layer
   interfaces. Wrap them behind owned types so the external can be replaced without changing consumers.
   Infrastructure/adapter modules _are_ the wrapping layer — they may use external types in their implementation and
   even in their own interface when they serve as the system edge. The rule is strict for inward layers, relaxed at the
   boundary with the outside world.

6. **One reach, not a chain.** A consumer should call a module's API directly — not reach through it into a transitive
   dependency's API. `a.get_b().get_c().do_thing()` (Law of Demeter violation) exposes B's and C's existence to A's
   caller. If a consumer needs something from a transitive dependency, the immediate dependency should expose it through
   its own API.

7. **Primitives flow; implementation types stay home.** Data that flows between packages should be expressed as
   primitive types, dataclasses, TypedDicts, or shared domain types — not as package-internal classes that force
   consumers to import from the implementation. NewType wrappers (e.g., `UserId`, `Millimetres`) are fine to cross
   boundaries when they represent _domain contracts_; they are violations when they encode _implementation details_
   (e.g., internal cache keys, serialization formats).

## What to Hunt

### 1. Leaked Internals

Internal helpers, intermediate types, constants, or utility functions that are exported but serve no external consumer.

**Signals:**

- Symbol in `__all__` or `__init__.py` that has zero external import sites
- Exported type includes implementation-specific fields (e.g., internal caches, memoization keys)
- A type's structure reveals _how_ the module works, not _what_ it produces
- Utility/helper functions exported alongside domain API
- Names with leading underscore conventions violated (public exposure of `_private` names)

**Action:** Remove from `__all__` / `__init__.py`, or if consumed externally, evaluate whether the consumer should own
the concept.

### 2. Over-Exported `__init__.py` Files

`__init__.py` that re-exports everything from every internal module, turning the entire package into a public API.

**Signals:**

- `from .internal_module import *` patterns
- `__init__.py` re-exports symbols that no external package imports
- Consumers import deep paths (`package.internal.helper`) bypassing the `__init__.py`
- Missing `__all__` in packages with ambiguous public surface — entire module namespace is implicitly public
   (note: `__all__` is one way to define the boundary; `_` prefix naming and explicit `__init__.py` re-exports are
   also valid)

**Action:** Replace `from .x import *` with explicit named imports of the public API. Define the public surface
via `__all__`, explicit re-exports, or `_` prefix naming. Block deep imports via conventions or package structure.

### 3. Coupling Through Shared Types

Two packages that share a type where neither owns it, or where one package's internal type appears in another package's
function signatures.

**Signals:**

- Package A imports a type defined inside package B's internal modules (not B's public API)
- A "shared types" module that grows unboundedly, coupling all importers
- Function signature contains a parameter typed as another package's internal class

**Action:** Move shared types to a shared kernel / contracts layer owned by neither package. Or, define the type in the
consumer and have the producer conform to it (dependency inversion via Protocol).

### 4. Law of Demeter Violations (Train Wrecks)

Long chains of attribute access or method calls that traverse multiple levels of abstraction.

**Signals:**

- `a.b.c.d` chains accessing nested attributes across package boundaries
- Functions that unpack deeply into a parameter's structure
- Consumer code that "knows" the internal structure of a returned value three levels deep

**Action:** Expose a direct API on the immediate dependency. If the consumer needs `c.d`, then the module owning `c`
should provide a method or property for it.

### 5. Missing Abstraction Over Externals

Third-party library types or APIs used directly in domain or application layer interfaces, coupling consumers to a
specific library.

**Signals:**

- Function parameter or return type in domain/application code is a type imported from a third-party package
- Package re-exports a third-party type as part of its own API
- Switching the underlying library would require changing consumer code
- Framework-specific types (e.g., `django.http.HttpRequest`, `flask.Request`, `sqlalchemy.Session`) in domain or
  application layers

**Acceptable:** Infrastructure/adapter modules using external types in their own interface — they _are_ the wrapping
layer. Flag only when these types leak inward into domain/application consumers.

**Action:** Define an owned Protocol or ABC that wraps the external type. The wrapping module is the only place that
imports from the external. Consumers depend on the owned interface.

### 6. Cyclic Dependencies

Two or more packages that import from each other, directly or transitively.

**Signals:**

- Package A imports from B, and B imports from A (direct cycle)
- Longer chains: A → B → C → A (transitive cycle)
- `__init__.py` files that create implicit cycles by re-exporting across boundaries
- `ImportError` at runtime due to circular imports
- Imports deferred inside functions to avoid circular import errors (symptom of structural problem)

**Action:** Runtime cycles are must-fix — break by extracting the shared concept into a third module, or inverting the
dependency direction. `TYPE_CHECKING`-guarded import cycles between co-evolving modules may be acceptable if explicitly
justified.

### 7. Dependency Direction Violations

A lower-level module importing from a higher-level module, breaking the intended layering.

**Signals:**

- Domain module importing from infrastructure or UI layer
- Shared utility importing from a feature module
- A "core" package that depends on a "feature" package

**Action:** Invert the dependency. Define a Protocol or ABC in the lower layer; implement it in the higher layer. Wire
via dependency injection, factory, or configuration.

## Audit Workflow

### Phase 1: Map Module Boundaries

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
2. **Identify packages.** A package is typically a directory with an `__init__.py`, but also consider PEP 420
   namespace packages (directories without `__init__.py` that still function as packages). If the project uses
   `pyproject.toml`, `setup.cfg`, or `setup.py` to define package boundaries, use those as the source of truth.
   List all packages and their public API surface.
3. **Catalogue exports.** For each package, list its public exports (from `__init__.py`, `__all__`, and naming
   conventions). Classify each as: class, function, constant, type alias, Protocol/ABC.
4. **List external dependencies.** For each package, list imports from third-party packages. Note which external types
   appear in the package's public interface.

### Phase 2: Analyze Dependency Graph

1. **Build import map.** For each package, list which other internal packages it imports from.
2. **Check direction.** If the project has an intended layering (domain → application → infrastructure), verify all
   arrows point in the correct direction.
3. **Detect cycles.** Identify direct and transitive cycles. Check for deferred imports inside functions as cycle
   symptoms.
4. **Measure fan-in / fan-out.** Packages with high fan-in (many importers) are stability anchors — changes are costly.
   Packages with high fan-out (many imports) are fragile — sensitive to changes elsewhere.

### Phase 3: Audit Export Surface

For each package:

1. **Dead exports.** Is every export consumed by at least one external package? Use grep as a first-pass heuristic:
   ```bash
   # Find all __all__ definitions and public exports
   rg '__all__\s*=' --type py
   rg 'from\s+\.\w+\s+import' --type py --glob '**/__init__.py'

   # For each exported symbol, check external usage
   rg 'from\s+package_path\s+import.*SymbolName' --type py
   rg 'import\s+package_path\..*SymbolName' --type py
   ```
   This misses wildcard imports, aliased imports, and dynamic imports. Verify each candidate finding manually before
   reporting — a grep miss is not proof of zero usage.
2. **Leaked internals.** Do any exports expose implementation details (internal caches, intermediate representations,
   helper utilities)?
3. **External type leaks.** Do any exports use third-party types in their signatures?

### Phase 4: Audit Consumer Access Patterns

For each package's consumers:

1. **Deep imports.** Are consumers importing from internal modules (bypassing the `__init__.py`)?
   ```bash
   EXCLUDE='--glob !**/*_test.py --glob !**/test_*.py --glob !**/tests/** --glob !**/venv/** --glob !**/.venv/**'

   # Deep imports bypassing __init__.py (substitute actual package names)
   rg --pcre2 'from\s+package\.internal' --type py $EXCLUDE
   rg --pcre2 'from\s+package\._' --type py $EXCLUDE
   ```
2. **Train wrecks.** Are consumers accessing nested attributes across boundaries?
   ```bash
   # Find deep attribute chains (3+ levels)
   rg --pcre2 '\w+\.\w+\.\w+\.\w+' --type py $EXCLUDE
   ```
3. **Knowledge coupling.** Do consumers make decisions based on implementation details of the imported package (e.g.,
   checking internal state, knowing about internal data structures)?

### Phase 5: Evaluate Replaceability

For each package, answer:

1. **Could this package be rewritten from its interface alone?** If a new developer needed to rewrite the package, would
   the public types + function signatures be sufficient? Or would they need to read consumers to understand implicit
   contracts?
2. **What would break if the implementation changed completely?** If the answer is "only the package's tests", the
   boundary is clean. If consumers would break, the boundary leaks.
3. **Are there implicit contracts not captured in the interface?** Ordering guarantees, side effects, mutation of
   parameters, callback timing — anything consumers depend on that isn't in the type signature.

## Output Format

Produce a single report. Save as `YYYY-MM-DD-boundary-hunter-audit-{$LLM-name}.md` in the project's docs folder (or
project root if no docs folder exists).

```md
# Boundary Hunter Audit — {date}

## Scope

- Surface: {diff / path / codebase}
- Files: {count or list}
- Exclusions: {list}

## Package Map

| Package       | Public Exports | External Deps | Fan-In | Fan-Out |
| ------------- | -------------- | ------------- | ------ | ------- |
| domain/shapes | 5 types, 2 fns | 0             | 8      | 1       |
| infra/svg     | 3 fns          | 1 (svgwrite)  | 2      | 4       |

## Dependency Graph Issues

### Cycles

- A → B → A (via {symbols})

### Direction Violations

- domain/X imports from infra/Y ({symbol}, {file:line})

## Export Surface Issues

### Dead Exports

| # | Package     | Export     | Type     | External Consumers |
| - | ----------- | ---------- | -------- | ------------------ |
| 1 | package/path | `helper_fn` | function | 0                  |

### Leaked Internals

| # | Package     | Export          | Why Internal          | Action        |
| - | ----------- | --------------- | --------------------- | ------------- |
| 1 | package/path | `_InternalCache` | Implementation detail | Remove export |

### External Type Leaks

| # | Package     | Export / Signature          | External Type  | Action                 |
| - | ----------- | -------------------------- | -------------- | ---------------------- |
| 1 | package/path | `process(input: LibType)` | `lib.LibType`  | Wrap behind owned type |

## Consumer Access Violations

### Deep Imports (Bypassing `__init__.py`)

| # | Consumer     | Imported Path              | Should Use |
| - | ------------ | -------------------------- | ---------- |
| 1 | file.py:line | `package.internal.helper`  | `package`  |

### Law of Demeter Violations

| # | Location     | Chain     | Depth | Action            |
| - | ------------ | --------- | ----- | ----------------- |
| 1 | file.py:line | `a.b.c.d` | 4     | Expose API on `a` |

## Replaceability Assessment

### {Package Name}

- Replaceable from interface? {yes/no — why}
- Implicit contracts: {ordering, side effects, timing, etc.}
- Coupling risk: {low/med/high}

## Recommendations (Priority Order)

1. **Must-fix**: {runtime cycles, direction violations, external leaks in domain layer}
2. **Should-fix**: {dead exports, leaked internals, deep imports}
3. **Consider**: {replaceability improvements, `__init__.py` cleanup, train wrecks}
```

## Operating Constraints

- **No code edits.** This skill produces an audit report only. Implementation is a separate step.
- **No empty sections.** Include only categories with findings. Omit a heading, table, or list entirely when it would contain zero items — do not include empty tables, placeholder subsections, or negative statements like "no dead exports", "none found", or "no issues".
- **Scope: module boundaries only.** Encapsulation, coupling, dependency direction, API surface. Do not flag type
  invariants (→ invariant-hunter-py), type design (→ type-hunter-py), structural complexity (→ simplicity-hunter-py),
  class/interface design (→ solid-hunter-py), missing documentation (→ doc-hunter-py), security (→ security-hunter-py),
  test quality (→ test-hunter-py), or cosmetic style (→ slop-hunter-py). If a finding doesn't answer "is this boundary
  clean?", it doesn't belong here.
- **Evidence required.** Every finding must cite `file/path.py:line` with the exact code or import statement.
- **Architecture-first.** Understand the project's intended layering before flagging violations. Ask if unclear.
- **Pragmatism over purism.** Not every coupling is worth breaking. Small utilities shared between two closely related
  modules may be fine. Flag, but don't insist on architectural astronautics.
- **Measure, don't guess.** Use `rg` and import analysis to count actual consumers, not hypothetical ones.
- **Challenge assumptions.** If the current structure makes a deliberate trade-off (e.g., a shared types module for
  co-evolving packages), acknowledge it rather than mechanically flagging it.
