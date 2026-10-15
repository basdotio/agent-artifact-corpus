# Test phase (steps 0–4)

## 0. Ask first

One `AskUserQuestion` round before anything runs: environments to never touch (prod URLs/env vars exported in the shell, payment/AI providers), whether real third-party calls are allowed, devices/browsers in scope, what "done" means. Write the answers into the rule templates.

## 1. Feature map

One read-only `qa-mapper` agent (or you, for a small app) walks the code, not memory:
entry points (routes, CLI commands, screens) → features → sub-features → states (idle/loading/empty/error/busy) → cross-feature flows (auth → create → edit → export → share) → integrations (storage, payments, AI, email).

Output: a numbered tree where every leaf is testable on its own and names its files. Show it to the user with the plan.

## 2. Unit plan

Split the map into **units an agent can finish well in one run** — typically one feature leaf or one cross-flow, ~30–80 cases. 30 units of 50 cases beats 3 units of 500. For each unit:

```
U<n> <name>
  files:     <paths the unit exercises>
  surface:   UI | API | CLI | data
  cases:     happy path, edges, states, failure injection (lost/5xx/429 answers, reloads, two tabs), a11y/keyboard if UI
  bar:       /regression references/<platform>.md (+ project ui/ux skill if it exists)
  load:      small | medium | high
```

Order units so high-load ones run alone. Publish the plan as the first version of the tracker, with the units in `D.units` (`{"U1": {"name": "…", "files": ["paths"]}}`): `done.mjs` checks coverage against them, and a unit's `files` decide when a later commit makes its last pass stale.

## 3. Tester brief (one `qa-tester` per unit, Sonnet)

- "Read and follow `<tooling>/VERIFYRULES.md`" — testers use the verifier rules (sandbox, ports, prod/secrets, headless, load).
- Its unit only; its sandbox (`mkbox.sh <unit-id> <port>`: built from the commit of main, `SANDBOX_SHA` records which, test-only env file, own data dirs) and ports.
- Drive it the way a user would — real headless browser for UI, the real CLI against the local server — plus failure injection by intercepting requests.
- **Reproduce every finding twice** before reporting it; save the script that reproduces it.
- Report per finding: `title · severity (B blocker / M major / m minor) · where (file/function) · repro steps · script path · expected vs actual`. Then `cases run / passed`. (Format is built into the agent.)

## 4. Triage into the list

- Dedupe across units by root cause; group findings that share one fix.
- Assign IDs, severity and a bucket: **now** (clear fix) vs **later** (needs a product decision or design pass). Severity policy for new findings from any agent: B and M → `now`, `m` → `later` by default (`add.mjs` does it; `--now` only on the user's word); `later` reaches `now` only at the user's gate.
- Assign each fix-now group a **workstream** by file scope so fixers in parallel don't collide (see fix-verify.md).
- Record the pass: `st.mjs pass <cycle> <units|all> <B/M/m new findings> --platforms <p,…>` (it stamps main's sha). Without it `done.mjs` can't tell a converged cycle from an untested one.
- Return the list to the user — counts by severity, then the items — and **stop until they confirm**. Their answers on "later" items become notes on those items.
