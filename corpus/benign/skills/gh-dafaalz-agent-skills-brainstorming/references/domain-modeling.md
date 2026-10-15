# Domain modeling and ADR decision filters

Guidelines for structuring domain entities and applying strict selection filters before authoring Architecture Decision Records (ADRs).

## 1. Domain entity alignment

During architectural exploration, ground entities in concrete business processes before writing implementation plans:

1. **Ubiquitous language.** Identify the core business nouns, lifecycle verbs, and state transitions used by stakeholders. Unify naming across database columns, API routes, and code classes.
2. **Synchronize with repository context.** Record verified domain terminology directly in `CODEBASE.md` or the active ADR document. Never invent separate dictionary files that fragment documentation.
3. **Bounded contexts.** Separate domain models that serve different business workflows. For example, an `Order` entity in checkout contains payment details, while an `Order` entity in fulfillment tracks warehouse packages. Define clear seams rather than forcing a single bloated entity.

## 2. Three strict ADR selection filters

Not every engineering decision warrants a formal Architecture Decision Record. Author an ADR only when the proposal satisfies at least one of these three filters:

1. **Hard to reverse.** The decision creates architectural or operational lock-in with high migration costs. Examples include database engine selection, primary key strategies, synchronous vs asynchronous messaging architectures, and multi-tenant partitioning schemes.
2. **Surprising without context.** The decision chooses a counter-intuitive approach that future engineers would question or refactor away without historical context. Examples include choosing polling over WebSockets due to edge proxy limitations, or choosing manual SQL queries over an ORM for specific throughput bottlenecks.
3. **Real trade-offs.** The decision involves genuine technical sacrifices where gaining one attribute requires losing another. Examples include prioritizing read latency over immediate consistency, or choosing strict schema validation over ingestion flexibility.

## 3. Exclusion gate

Do not generate an ADR for:
- Routine framework conventions (such as standard route registration or typical controller templates).
- Obvious bug fixes and performance patches.
- Decisions governed strictly by existing linter rules or language idioms.
