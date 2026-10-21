# Gotchas and Failure Modes

Sections under "Docs-backed" are in the upstream docs or example app. Sections under "Field notes" were observed in real projects and are not upstream; verify the canonical setup first, because several of them turned out to be symptoms of a missing canonical step.

---

## Docs-backed

### Queries throw right after sign in, or on first client render

**Cause:** Something calls an authenticated Convex query before Convex has validated the token. Two common paths:

- Gating on `authClient.useSession()` instead of Convex auth state. Better Auth reports a user before Convex does.
- `expectAuth: true` missing from `ConvexQueryClient`, so the client runs queries unauthenticated after hydration and loses SSR data.

**Fix:** `new ConvexQueryClient(url, { expectAuth: true })`. Gate UI with `<Authenticated>` / `useConvexAuth()` from `convex/react`, never `useSession()`. Pass `initialToken={context.token}` to `ConvexBetterAuthProvider`.

### Queries fail after sign out then sign in

**Cause:** `expectAuth: true` only holds queries before the first authentication. After sign out the client is in a post-auth state and fires queries immediately on the next sign in.

**Fix:** `authClient.signOut({ fetchOptions: { onSuccess: () => location.reload() } })`.

### Stale JWT with a live session (white screen after being idle)

**Cause:** JWT default lifetime is 15 minutes (`jwt.expirationSeconds: 900`), session default is 7 days. An authenticated query with the old token throws `ConvexError("Unauthenticated")` from `getAuthUser`, and an unhandled throw takes down the route tree.

**Fix:** `AuthBoundary` (experimental). It catches auth errors, subscribes to a session-validated user query, and calls `onUnauth` when the user is really gone.

```ts
// convex/auth.ts
export const { getAuthUser } = authComponent.clientApi()
```

```ts
// src/lib/utils.ts
import { ConvexError } from 'convex/values'
export const isAuthError = (error: unknown) => {
  const message =
    (error instanceof ConvexError && error.data) ||
    (error instanceof Error && error.message) ||
    ''
  return /auth/i.test(message)
}
```

```tsx
// src/lib/auth-client.tsx
import { useNavigate } from '@tanstack/react-router'
import { AuthBoundary } from '@convex-dev/better-auth/react'
import { api } from '~/convex/_generated/api'
import { isAuthError } from '~/lib/utils'
import { authClient } from '~/lib/auth-client'

export const ClientAuthBoundary = ({ children }: PropsWithChildren) => {
  const navigate = useNavigate()
  return (
    <AuthBoundary
      authClient={authClient}
      onUnauth={() => navigate({ to: '/sign-in' })}
      getAuthUserFn={api.auth.getAuthUser}
      isAuthError={isAuthError}
    >
      {children}
    </AuthBoundary>
  )
}
```

```tsx
// src/routes/_authed.tsx
component: () => (
  <ClientAuthBoundary>
    <Outlet />
  </ClientAuthBoundary>
),
```

One boundary at the authed layout is enough for most apps. `isAuthError` must read `ConvexError.data`, because that is where the payload lives; `.message` alone misses it. If your backend throws its own auth errors, make sure the text matches `/auth/i` (`Unauthenticated`, `Unauthorized`, `Not authenticated` all match).

Longer JWT: `convex({ authConfig, jwt: { expirationSeconds: 60 * 30 } })`. Trade-off is a longer window where a revoked session still validates by JWT alone.

### `ERR_MODULE_NOT_FOUND` during SSR

`vite.config.ts` → `ssr: { noExternal: ['@convex-dev/better-auth'] }`.

### `CONVEX_SITE_URL is not set` / `should be set to your Convex Site URL`

Thrown by `convexBetterAuthReactStart` at startup. `VITE_CONVEX_SITE_URL` must be the `.convex.site` URL, present in the TanStack server environment (`.env.local`).

### Out of memory on `convex dev` / `convex deploy`

`JavaScript execution ran out of memory (maximum memory usage: 64 MB)`. Use `registerRoutesLazy`, import plugins from subpaths, and inspect with `--debug-bundle-path`. Details in `core-reference.md`.

### JWT validation errors after upgrading to 0.10+

RS256 key migration. `convex({ authConfig, jwksRotateOnTokenGenerationError: true })` until keys rotate, then remove.

### "Base URL could not be determined" on every request (0.12)

Only for cross-domain setups (Vite SPA, Expo). Set `baseURL: process.env.CONVEX_SITE_URL`. TanStack Start already sets `baseURL: siteUrl`.

### Plugin needs a table or field that does not exist

The default schema is fixed. Check the supported list in `core-reference.md`; otherwise Local Install and `npx auth generate`.

### `resend.sendEmail` type error inside `createAuth`

`ctx` may be a query ctx. Wrap with `requireActionCtx(ctx)` from `@convex-dev/better-auth/utils`.

### Unindexed query warnings from the component

The adapter picks an index when one exists and logs which index to add otherwise. Adding indexes requires Local Install (custom indexes section in `core-reference.md`).

### Symptom → fix table

| Symptom | Fix |
|---|---|
| TS errors in `convex/auth.ts` right after creating it | Save, keep `npx convex dev` running |
| Type errors mentioning better-auth internals | `npm install better-auth@~1.6.15` |
| `BETTER_AUTH_SECRET is not defined` | `npx convex env set BETTER_AUTH_SECRET=$(openssl rand -base64 32)` |
| Session not persisting | `SITE_URL` exact match, no trailing slash. Check the cookie in DevTools |
| Email verification / reset link goes to wrong host | `SITE_URL` on the Convex deployment is wrong for that environment |
| `/api/auth/*` 404 | Route file `src/routes/api/auth/$.ts` missing, or `basePath` mismatch between `convexBetterAuthReactStart`, the route, and `convex({ options: { basePath } })` |
| `NoAuthProvider` / no auth provider found | `convex/auth.config.ts` missing `getAuthConfigProvider()`, or deployed to a different deployment than the client's `VITE_CONVEX_URL` |
| Authenticated data flashes then disappears after hydration | `expectAuth: true` missing |
| Every reload of a signed-in page throws | `initialToken` not passed, or `beforeLoad` not calling `getToken()` |

---

## Field notes (not upstream)

### expectAuth hydration race

**Symptom:** full reload of a signed-in page shows the error component; retrying fixes it.

**First check:** `initialToken={context.token}` on `ConvexBetterAuthProvider` and `getToken()` in the root `beforeLoad`. With both in place the client authenticates before queries run and this race should not happen.

**Workaround if it persists:** an error component on the authed layout that resets itself a few times before showing a fallback.

```tsx
function AuthedErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  const retries = useRef(0)
  useEffect(() => {
    if (isAuthError(error)) return    // AuthBoundary handles it
    if (retries.current < 3) {
      retries.current += 1
      const t = setTimeout(reset, retries.current * 500)
      return () => clearTimeout(t)
    }
  }, [error, reset])
  if (isAuthError(error) || retries.current < 3) return null
  return <button onClick={reset}>Something went wrong. Retry</button>
}
```

### Convex `useQuery` results in `useEffect` deps

Result objects can be new references on each emission. Extract a primitive first: `const profileId = profile?._id`.

### Lazy profile creation

If you do not use triggers, do not throw `Profile not found` on a normal first login. Prefer the triggers pattern in `core-reference.md`, which creates the app user row in the same transaction as the auth user.

### Public nav for signed-in users

If SSR cookies do not reach the server (some hosting setups), the root `beforeLoad` sees no token and a signed-in user lands on the marketing page with only sign-in CTAs. Render the public nav's CTA from `useConvexAuth()` client-side so it flips to "Go to dashboard" once auth settles.

---

## Production checklist

- Fresh `BETTER_AUTH_SECRET` per deployment.
- `npx convex env set SITE_URL https://yourapp.com` on the prod deployment.
- `VITE_CONVEX_URL` / `VITE_CONVEX_SITE_URL` point at the prod deployment.
- Email sender domain verified.
- Consider Better Auth `rateLimit` on auth endpoints.
