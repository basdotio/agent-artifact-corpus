---
name: review-module
description: Audit a module for Clean Architecture and boundary compliance
argument-hint: <module-name>
user-invocable: true
allowed-tools: Read, Glob, Grep
context: fork
agent: Explore
---

Audit the module at `packages/server/src/modules/$ARGUMENTS[0]/` for compliance with
our architecture rules (see @docs/02-ARCHITECTURE.md Section 4):

## Check List

1. **No cross-module imports** — scan all .ts files for imports from `../other-module/`
2. **Domain purity** — domain/ files must not import Effect, Kysely, Redis, or any framework
3. **Port interfaces only** — ports/ files must contain only interfaces/types, no implementations
4. **Adapter dependencies** — adapters/ can import from ports/ and domain/, never reverse
5. **index.ts exports** — module's index.ts only exports Layer, events, and port interfaces
6. **EventBus usage** — inter-module communication uses EventBus, not direct function calls
7. **Branded types** — uses PlayerId, ZoneId etc. from shared/kernel/, not raw strings

Report each violation with file path and line number. End with a compliance score.
