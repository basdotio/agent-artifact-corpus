# guide.json

The reader is a capable engineer with no context on this part of the codebase. Be specific enough that they never have to guess which file or function you meant. Scale every section to the size of the task: a two-file bug gets a short guide.

```json
{
  "task": "Show checkout totals in EUR as well as GBP",
  "kind": "feature",
  "goal": {
    "current": ["checkoutView always formats totals as GBP"],
    "proposed": ["Basket currency (GBP or EUR) decides how the total is formatted"],
    "outOfScope": ["Exchange rates", "Router feature flags"]
  },
  "decisions": [{ "q": "Currency per basket or per user?", "a": "basket", "by": "user" }],
  "files": [
    { "path": "packages/utils/src/money.ts", "role": "modify", "symbols": ["formatGBP"],
      "why": "Only currency formatter", "change": "Add formatMoney(pence, currency); keep formatGBP as a wrapper" },
    { "path": "packages/utils/src/money.test.ts", "role": "test", "new": true,
      "why": "No coverage for money today", "change": "GBP and EUR cases; mirror slugify.test.ts" },
    { "path": "apps/web/src/router.ts", "role": "check", "why": "Calls checkoutView; must still type-check" }
  ],
  "steps": ["Write the failing EUR test in money.test.ts", "Add formatMoney beside formatGBP in money.ts", "..."],
  "guidance": ["Keep money in minor units end to end; format only at the edge (checkout.ts)"],
  "watch": [{ "risk": "formatGBP is re-exported; renaming it breaks @mono/utils consumers", "where": "packages/utils/src/index.ts", "level": "high" }],
  "verify": ["npm test", "checkoutView with an EUR basket shows €12.34"],
  "open": [{ "q": "Should EUR use en-IE or de-DE formatting?", "recommend": "en-IE, matching the en-GB house style" }]
}
```

## Fields

- `kind`: `bug`, `feature` or `change`. For bugs, `goal.current` is the symptom and `verify` includes the reproduction.
- `goal.proposed`: observable behaviour when done, not implementation.
- `files`, in the order to work: `modify`, `create`, `test`, `check` (may break, should not change) or `reference` (pattern to copy). `symbols` must exist in the file. `change` is required for modify, create and test.
- `steps`: 12 or fewer, plain language, each naming the file or symbol it touches.
- `guidance`: repo-specific rules and the existing pattern to mirror, with its path. Not generic advice anyone could write.
- `watch`: what will bite, located, rated `high`, `med` or `low`: callers and contracts, data and migrations, config and flags, auth, concurrency, silent failures.
- `verify`: the commands from the scan plus one end-to-end check.
- `open`: anything still unresolved, each with your recommendation.

## Rules

- No placeholders: "TBD", "handle edge cases", "add appropriate error handling", "as needed", "similar to step 2". Name the case.
- Guide, do not implement: no string longer than 8 lines.
- Prefer copying an existing pattern to inventing one. If you recommend something new, say why the existing way does not fit.
