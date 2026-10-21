---
name: better-auth-convex
description: Set up, repair, and troubleshoot Better Auth with Convex and TanStack Start using the @convex-dev/better-auth component (0.12.x). Use when configuring authentication in a Convex + TanStack Start project, wiring sign up/sign in/sign out, fixing an unreliable auth flow (stale tokens, white screens, NoAuthProvider, queries firing before auth is ready, hanging loaders, out-of-memory on deploy), configuring SSR with expectAuth, adding triggers for an app-owned users table, or as a reference for the component client API, the convex plugin, supported plugins, and Local Install. Triggers on Better Auth, betterauth, @convex-dev/better-auth, auth.ts, ConvexBetterAuthProvider, AuthBoundary, expectAuth, registerRoutesLazy, triggersApi, Local Install.
---

# Better Auth + Convex + TanStack Start

Better Auth runs as a Convex component (`@convex-dev/better-auth`), wired through TanStack Start SSR. This skill mirrors the upstream docs at [labs.convex.dev/better-auth](https://labs.convex.dev/better-auth) (source: `docs/content/docs/*.mdx` in [get-convex/better-auth](https://github.com/get-convex/better-auth)) and the `examples/tanstack` app in that repo. Last synced against component **0.12.5**, Better Auth **~1.6.15**.

**Code wins over docs. Confirm against the live files before following any snippet.** For anything not covered here, Better Auth's own docs apply unchanged: [better-auth.com/docs](https://better-auth.com/docs).

## Pick your mode

| Mode | You are... | Start with |
|------|-----------|------------|
| **Setup** | Wiring auth into a fresh Convex + TanStack Start app | `references/setup-guide.md` |
| **Repair** | Fixing an existing flow that is flaky or crashing | `references/repair-checklist.md` |
| **Gotchas** | Hitting a specific symptom | `references/gotchas.md` |
| **Reference** | Component client API, convex plugin options, triggers, Local Install, plugins | `references/core-reference.md` |

## Quick reference

### Packages

```bash
npm install convex@latest @convex-dev/better-auth
npm install better-auth@~1.6.15
npm install @types/node --save-dev
```

Component peer range: `better-auth >=1.6.11 <1.7.0`, `convex ^1.25.0`. Pin `better-auth` with `~`. Version drift is the usual cause of phantom type errors. `better-auth` on npm is already on 1.7.x (1.7.7 when last checked), so an unpinned `npm install better-auth` lands outside the peer range.

### Environment variables

```bash
npx convex env set BETTER_AUTH_SECRET=$(openssl rand -base64 32)
npx convex env set SITE_URL http://localhost:3000
```

```bash
# .env.local
CONVEX_DEPLOYMENT=dev:adjective-animal-123
VITE_CONVEX_URL=https://adjective-animal-123.convex.cloud
VITE_CONVEX_SITE_URL=https://adjective-animal-123.convex.site   # .site, not .cloud
VITE_SITE_URL=http://localhost:3000
```

### File map

| File | Purpose |
|------|---------|
| `convex/convex.config.ts` | `app.use(betterAuth)` |
| `convex/auth.config.ts` | `providers: [getAuthConfigProvider()]` |
| `convex/auth.ts` | `authComponent = createClient(...)`, `createAuth`, `getCurrentUser` |
| `convex/http.ts` | `authComponent.registerRoutes(http, createAuth)` (or `registerRoutesLazy`) |
| `src/lib/auth-client.ts` | `createAuthClient({ plugins: [convexClient()] })` |
| `src/lib/auth-server.ts` | `convexBetterAuthReactStart(...)` → `handler`, `getToken`, `fetchAuth*` |
| `src/routes/api/auth/$.ts` | Proxies `/api/auth/*` to Convex via `handler` |
| `src/routes/__root.tsx` | `getToken()` in `beforeLoad`, `ConvexBetterAuthProvider` with `initialToken` |
| `src/router.tsx` | `ConvexQueryClient(url, { expectAuth: true })` + `setupRouterSsrQueryIntegration` |
| `src/routes/_authed.tsx` | `beforeLoad` redirect when `!context.isAuthenticated` |

### Backend auth check

```ts
// throws ConvexError("Unauthenticated") when no valid session
const user = await authComponent.getAuthUser(ctx)

// returns undefined when no valid session
const user = await authComponent.safeGetAuthUser(ctx)
```

Both validate the session row, not just the JWT. `ctx.auth.getUserIdentity()` is cheaper but does not validate the session.

## Load-bearing rules

1. **Sign in, sign up, and sign out happen on the client only.** Convex functions run over websockets and cannot set cookies, so `auth.api.signIn*` style server calls do not apply. Use `authClient.signIn.*` from the browser.
2. **Gate Convex queries on Convex auth state, not Better Auth's.** Use `useConvexAuth()` or `<Authenticated>` from `convex/react`. Better Auth's `useSession()` reports signed in before Convex has validated the token, and authenticated queries will throw in that window.
3. **`expectAuth: true` on `ConvexQueryClient` is required for seamless SSR** and it only settles before the first authentication. **Reload the page on sign out** (`fetchOptions.onSuccess: () => location.reload()`), otherwise signing back in fires queries before auth is ready.
4. **Pass `initialToken` to `ConvexBetterAuthProvider`** from the root route's `beforeLoad`. Without it the client has to fetch a token after hydration and authenticated queries race the socket.
5. **JWTs expire in 15 minutes by default** (`convex({ jwt: { expirationSeconds } })`), sessions in 7 days. A stale JWT with a live session throws `Unauthenticated` from Convex, so any long-lived signed-in page needs `AuthBoundary` (experimental) or equivalent error handling. See `references/gotchas.md`.
6. **The default component schema cannot be altered.** Adding a plugin that needs schema changes, custom indexes, or direct access to auth tables requires Local Install. Supported without it: anonymous, email OTP, generic OAuth, JWT, magic link, one tap, phone number, two factor, username. SSO is incompatible everywhere. Passkey needs Local Install (dropped from the bundled schema in 0.11).

## Reference files

| File | Load when |
|------|-----------|
| `references/setup-guide.md` | Greenfield install, exact upstream steps, plus SSR, sign out, `auth.api` from the server |
| `references/gotchas.md` | Debugging a symptom. Docs-backed fixes first, field notes flagged at the bottom |
| `references/repair-checklist.md` | Repairing an existing broken flow end to end |
| `references/core-reference.md` | Component client API, convex plugin options, triggers, Local Install, debugging flags, experimental features, migrations |
