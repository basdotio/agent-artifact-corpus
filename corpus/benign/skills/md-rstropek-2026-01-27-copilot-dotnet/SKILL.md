---
name: csharp-coding-guidelines
description: C# / .NET 10 coding guidelines for building maintainable, performant, and secure applications. Use this skill when generating C# or .NET code for applications.
---

# Agent Guidelines (C# / .NET 10)

You are an expert in modern C# and .NET 10 development. You write maintainable, performant, and secure code aligned with current .NET ecosystem best practices.

## Language & Formatting Conventions

- Use **file-scoped namespaces** (namespace without curly braces).
- Use **curly braces for all code blocks**, even single-line blocks.
- Prefer **expression-bodied members** only when they improve readability and do not hide complexity.
- Prefer **`var`** when the type is obvious from the right-hand side.
- Keep classes focused; avoid “god” services. Favor small, composable units.
- Avoid magic strings/numbers; use constants, options, or enums as appropriate.
- Prefer `using` directives at the top of the file; avoid unnecessary `global using` unless it reduces real duplication.

## C# Best Practices

- Enable and honor **nullable reference types**
  - Do not silence warnings without understanding the root cause.
  - Prefer clear null-handling (`ArgumentNullException.ThrowIfNull`, `is null` checks, `required` members, and correct annotations).
- Prefer **immutability** by default:
  - Use `record` / `record struct` where value semantics fit.
  - Prefer `init`-only setters and read-only collections.
- Prefer **pattern matching** and modern constructs where they clarify intent:
  - `switch` expressions, property patterns, and `is` patterns.
- Use **`required`** members judiciously for DTOs/options where it improves correctness.
- Use **`Span<T>`/`ReadOnlySpan<T>`** and `System.Text` APIs for performance-critical code, but keep code readable and only optimize when it matters.

## Async & Concurrency

- Use async/await end-to-end for I/O-bound operations.
- Avoid `.Result` and `.Wait()`.
- Prefer returning `Task`/`Task<T>` (or `ValueTask` only when justified by profiling and allocations).
- Pass `CancellationToken` through all public async entry points where cancellation is meaningful.
- For library-style code, prefer `ConfigureAwait(false)`; for ASP.NET Core app code it’s typically unnecessary.

## Error Handling

- Throw exceptions for exceptional conditions; do not use exceptions for normal control flow.
- Prefer precise exception types (`ArgumentException`, `InvalidOperationException`, etc.).
- Validate inputs early:
  - Use methods like `ArgumentException.ThrowIfNull`, `ArgumentException.ThrowIfNullOrEmpty`, and `ArgumentException.ThrowIfNullOrWhiteSpace`; avoid manual if statements.
  - Use guard clauses to keep the happy path clear.

## ASP.NET Core (Minimal APIs)

- Keep endpoints thin; move business logic into application/services layers.
- Use clear route naming, consistent status codes, and correct HTTP semantics.
- Validate request payloads and return meaningful problem details.
- Prefer typed results when it improves clarity (e.g., `Results<Ok<T>, NotFound>`), but avoid over-engineering.
- Use dependency injection via parameter binding or `IServiceProvider`/`HttpContext.RequestServices` only when needed.
- Prefer options pattern for configuration (`IOptions<T>`) and keep configuration strongly typed.

## Dependency Injection

- Register services with the narrowest suitable lifetime (Singleton/Scoped/Transient).
- Avoid capturing scoped services in singleton instances.
- Do not use service locator patterns unless bridging legacy constraints.

## Data Access (Entity Framework Core)

- Prefer async EF Core APIs (`ToListAsync`, `SingleOrDefaultAsync`, etc.).
- Use `AsNoTracking()` for read-only queries.
- Keep `DbContext` scoped; do not hold onto it beyond a request scope.
- Prefer explicit transactions only when necessary.
- Use migrations for schema changes; keep migrations focused and reviewed.

## API & Domain Design

- Keep domain models free of infrastructure concerns where practical.
- Prefer explicit DTOs for API boundaries; do not expose EF entities directly.
- Model invariants in constructors/factories when possible.
- Prefer `DateTimeOffset` for timestamps; store/communicate in UTC.

## Testing (xUnit)

- Write tests that are deterministic and isolated.
- Name tests for behavior (Given/When/Then style is fine).
- Prefer testing business logic without HTTP when possible; use integration tests where it adds value.
- Avoid asserting on exact exception messages; assert exception types and relevant data.
- Keep test setup reusable via fixtures, but avoid hidden global state.

## Security & Reliability

- Treat all external input as untrusted.
- Avoid reflecting secrets into logs or error messages.
- Prefer `ProblemDetails` for error responses; do not leak internal exception details in production.
