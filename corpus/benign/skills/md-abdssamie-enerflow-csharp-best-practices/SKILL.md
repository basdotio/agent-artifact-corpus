---
name: csharp-best-practices
description: Directs agents to avoid bad C# practices like magic strings and poor architecture.
license: MIT
compatibility: opencode
metadata:
  language: csharp
  framework: dotnet
---

## What I do

- **Enforce Enums over Strings**: I identify usage of "magic strings" in control flow (especially `switch` statements) and recommend converting them to strongly-typed `Enums`.
- **Promote Clean Architecture**: I check that Domain entities do not depend on Infrastructure or External libraries (like DWSIM).
- **Encourage Modern C# Features**: I suggest using `file-scoped namespaces`, `primary constructors`, and `records` where appropriate for .NET 10+.
- **Enforce Sequential IDs**: I flag usage of `Guid.NewGuid()`. Always use `Enerflow.Domain.Common.IdGenerator.NextGuid()` (which uses MassTransit's `NewId`) to ensure database-friendly sequential identifiers.
- **Identify Maintainability Risks**: I flag hardcoded values, large methods, and tight coupling.
- **Block Non-Production Shortcuts**: I strictly forbid "hacky" workarounds or non-production shortcuts when hitting constraints. If stuck, **STOP and ask the User**. User feedback is the only valid solution to structural hurdles.

## When to use me

- **Code Reviews**: Run me when reviewing new or modified C# code to ensure standards are met.
- **Refactoring**: Use me to identify areas for improvement in legacy code.
- **Implementation**: Consult me before implementing new features to ensure the design starts clean.

## Examples of Bad vs Good Practice

### Bad: Magic Strings in Switch
```csharp
// Bad: Relies on string literals which are prone to typos and hard to refactor
var units = systemOfUnits.ToUpperInvariant() switch
{
    "SI" => ...
    "CGS" => ...
    _ => ...
};
```

### Good: Enum Usage
```csharp
// Good: Uses strict Enum types
public enum SystemOfUnits { SI, CGS, English }

var units = unitType switch
{
    SystemOfUnits.SI => ...
    SystemOfUnits.CGS => ...
    _ => ...
};
```

### Bad: Domain Leaking
```csharp
// Bad: Domain DTO referencing DWSIM types directly
public class SimulationJob {
    public DWSIM.Thermodynamics.PropertyPackage Package { get; set; }
}
```

### Good: Anti-Corruption Layer
```csharp
// Good: Domain uses its own Enum, Mapper handles the conversion
public class SimulationJob {
    public Enerflow.Domain.Enums.PropertyPackage Package { get; set; }
}
```

### Bad: Non-Sequential Guid
```csharp
// Bad: Random Guids cause database fragmentation
var id = Guid.NewGuid();
```

### Good: Sequential NewId
```csharp
// Good: Uses IdGenerator for database-friendly sequential IDs
var id = Enerflow.Domain.Common.IdGenerator.NextGuid();
```
