---
name: coding-standards
description: >
  TypeScript coding patterns and implementation standards for this project.
  Load when implementing new logic, refactoring existing code, handling errors,
  or when unsure how to structure state, side effects, or component architecture.
  Covers Result<T,E> pattern, composable logic design, and component architecture decisions.
---

# Coding Standards

## Result<T, E>

### Definition

```typescript
// shared/types.ts — single source of truth, never redefine per-feature
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };
```

### When to use

- Internal domain functions where callers need structured failure reasons
- Server actions / route handlers
- Hooks / composables managing async operations

### When NOT to use

- Expected absence → use `T | undefined` or `T | null`
- Promote absence to domain error only at the boundary layer (handler/service), never in low-level adapters

### Examples

```typescript
// Domain function
function parseId(input: unknown): Result<string, "Invalid ID"> {
  return typeof input === "string" && input !== ""
    ? { ok: true, value: input }
    : { ok: false, error: "Invalid ID" };
}

// Server action
export async function createPost(
  formData: FormData,
): Promise<Result<Post, string>> {
  const title = formData.get("title");
  if (!title) return { ok: false, error: "Title required" };

  try {
    const post = await db.insert({ title });
    return { ok: true, value: post };
  } catch (error) {
    console.error("DB error:", error);
    return { ok: false, error: "Failed to create post" };
  }
}

// Hook
function useCreatePost() {
  const [result, setResult] = useState<Result<Post, string> | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const create = async (formData: FormData) => {
    setIsLoading(true);
    const res = await createPost(formData);
    setResult(res);
    setIsLoading(false);
    return res;
  };

  return { create, result, isLoading };
}
```

## Composable Logic Design

_Applies to: React Hooks, Vue Composables, Svelte Runes, Solid Primitives, etc._

1. Extract pure logic — separate business logic from framework code
2. Isolate side effects — keep I/O separate from pure logic
3. Accept state as arguments — make logic testable
4. Return computed values — return derived state and operations

## Component Architecture

### Pattern 1: Direct Import

Components directly import stores/utilities/logic.

**Use when:** simple single-purpose components, no reuse needs, small-to-medium complexity.

### Pattern 2: Feature Layer + Presentational Components

Feature layer handles logic, components receive props.

**Use when:** reusable across contexts, complex business logic, clear server/client separation needed.

**Decision:** start with Pattern 1. Refactor to Pattern 2 when reuse, testing, or complexity demands it.

## Comments

Only for:

- Complex type hints that cannot be expressed in code
- Critical non-obvious logic (with ADR reference if applicable)

Never for:

- Usage examples — write tests instead
- Redundant descriptions of what the code does
