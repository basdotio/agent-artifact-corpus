# better-auth-convex

An agent skill for setting up, repairing and debugging [Better Auth](https://better-auth.com) on a Convex + TanStack Start app through the `@convex-dev/better-auth` component. It follows the upstream docs at [labs.convex.dev/better-auth](https://labs.convex.dev/better-auth) and the `examples/tanstack` app in [get-convex/better-auth](https://github.com/get-convex/better-auth), plus a short set of field notes that are marked as not upstream.

## When to use it

- Adding email/password or plugin-based auth to a Convex + TanStack Start project
- Auth works most of the time but you see stale tokens, white screens after idling, `NoAuthProvider`, queries firing before auth is ready, or out-of-memory errors on deploy
- Wiring SSR with `expectAuth`, `initialToken` and `getToken()`
- Keeping an app-owned `users` table in sync with triggers
- Looking up the component client API, the `convex()` plugin options, supported plugins or Local Install

## Versions it targets

Checked against npm on 2026-10-03:

| Package | Version | Notes |
|---|---|---|
| `@convex-dev/better-auth` | 0.12.5 (latest) | peer `better-auth >=1.6.11 <1.7.0`, `convex ^1.25.0` |
| `better-auth` | `~1.6.15` | latest on npm is 1.7.x, which is outside the component's peer range, so pin it |
| `convex` | 1.25.0 or later | |

## Install

```bash
npx skills add Sstobo/skills --skill better-auth-convex
```

## Example prompts

- "Add Better Auth to this Convex + TanStack Start app with email and password."
- "Users get a white screen after leaving the app open for a while. Fix the auth flow."
- "Create a row in my `users` table whenever someone signs up."

## Files

| File | What it holds |
|---|---|
| [`SKILL.md`](SKILL.md) | Mode picker, packages, env vars, file map, and the six load-bearing rules |
| [`references/setup-guide.md`](references/setup-guide.md) | Step-by-step install for a fresh app, plus protected routes, SSR queries, sign in/out and calling `auth.api` |
| [`references/gotchas.md`](references/gotchas.md) | Symptom-to-fix notes: docs-backed first, field notes at the bottom, production checklist |
| [`references/repair-checklist.md`](references/repair-checklist.md) | Procedure for fixing an existing flaky auth setup against the canonical shape |
| [`references/core-reference.md`](references/core-reference.md) | `createClient` methods, `convex()` plugin options, triggers, supported plugins, Local Install, experimental features, migrations |
