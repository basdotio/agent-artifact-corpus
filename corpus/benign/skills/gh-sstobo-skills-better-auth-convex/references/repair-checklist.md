# Repair Checklist: fixing a broken auth flow

Use when an existing Convex + Better Auth + TanStack Start app is unreliable. **Use the project's existing patterns. Surgical changes only. Do not rewrite auth unless it is fundamentally off the canonical shape.**

## Goal state

- Sign up, sign in, sign out work from the client. Sign out reloads.
- SSR renders authenticated data on first paint with no flash.
- Authenticated Convex queries never run before Convex has validated the token.
- A stale JWT with a live session recovers; a dead session redirects to sign in.
- No infinite spinners, no white screens.

## Inspect first

- `convex/convex.config.ts`, `convex/auth.config.ts`, `convex/auth.ts`, `convex/http.ts`
- `src/lib/auth-client.ts`, `src/lib/auth-server.ts`
- `src/router.tsx`, `src/routes/__root.tsx`, the authed layout route, `src/routes/api/auth/$.ts`
- `vite.config.ts`
- Sign in / sign up / sign out UI
- `package.json` versions: `@convex-dev/better-auth`, `better-auth`, `convex`
- `npx convex env list` for `BETTER_AUTH_SECRET`, `SITE_URL`; `.env.local` for `VITE_CONVEX_URL`, `VITE_CONVEX_SITE_URL`

## Compare against the canonical shape

Walk `setup-guide.md` step by step and diff. The usual drifts:

1. **Versions.** `better-auth` outside `>=1.6.11 <1.7.0`, or component below 0.10 (old `setupFetchClient` / `reactStartHandler` / `optionsOnly` shape). Migrate per `core-reference.md`.
2. **`auth.config.ts` still uses `{ applicationID, domain }`** instead of `getAuthConfigProvider()`. Also pass `authConfig` to `convex({ authConfig })`.
3. **`ConvexQueryClient` missing `expectAuth: true`.**
4. **Root route not calling `getToken()` in `beforeLoad`**, not calling `serverHttpClient?.setAuth(token)`, or not passing `initialToken` to `ConvexBetterAuthProvider`.
5. **Router still has `Wrap` with `ConvexProvider`** or `routerWithQueryClient`. Replace with `setupRouterSsrQueryIntegration`.
6. **UI gated on `authClient.useSession()`** instead of `useConvexAuth()` / `<Authenticated>`.
7. **Sign out without reload.**
8. **Sign in/out attempted from a server function or Convex function.** Move to the client.
9. **`getAuthUser` result null-checked** (it throws) or `safeGetAuthUser` result assumed non-null.
10. **`vite.config.ts` missing `ssr.noExternal`.**
11. **`basePath` mismatch** across `convexBetterAuthReactStart`, the API route, and `convex({ options: { basePath } })`.
12. **No `AuthBoundary`** on long-lived signed-in pages, so 15-minute JWT expiry white-screens. Wire per `gotchas.md`.
13. **Hand-rolled auth tables** or schema edits to the bundled component. Either remove them or move to Local Install.
14. **Profile row created lazily with throws on miss.** Prefer triggers (`core-reference.md`).

## Implementation requirements

- State assumptions before editing.
- Keep changes minimal. Preserve unrelated code.
- Add validators to any Convex function you touch.
- Do not commit or push.
- After changes:

```bash
npx convex dev --once
```

```bash
npm run build
```

- Fix only failures related to this repair. Report unrelated ones.

## Deliverable

What was broken, files changed, how the flow now works, commands run, and any env vars or deployment settings the user must verify.
