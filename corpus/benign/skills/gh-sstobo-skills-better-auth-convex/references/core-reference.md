# Core Reference: component API, plugin options, features

Everything here is the Convex component layer. Better Auth's own options (sessions, `user.additionalFields`, `socialProviders`, hooks, `advanced`, rate limiting) work unchanged and are documented at [better-auth.com/docs/reference/options](https://better-auth.com/docs/reference/options). The one hard exception: the default component schema cannot be altered without Local Install.

## Versions

| Package | Version | Notes |
|---|---|---|
| `@convex-dev/better-auth` | 0.12.x | peer `better-auth >=1.6.11 <1.7.0`, `convex ^1.25.0` |
| `better-auth` | `~1.6.15` | pin with `~` |

Package subpaths: `.` (`createClient`, `createApi`, `GenericCtx`, `AuthFunctions`, `Triggers`), `/plugins` (server `convex`), `/client/plugins` (`convexClient`, `crossDomainClient`), `/auth-config`, `/react` (`ConvexBetterAuthProvider`, `AuthBoundary`), `/react-start`, `/nextjs`, `/utils` (`requireActionCtx`, `requireRunMutationCtx`), `/convex.config`, `/adapter`.

## `createClient(component, config?)`

```ts
export const authComponent = createClient<DataModel>(components.betterAuth, {
  verbose: false,                 // component-side logging
  local: { schema },              // Local Install only
  authFunctions, triggers,        // both or neither
})
```

Methods on the returned `authComponent`:

| Method | Ctx | Behaviour |
|---|---|---|
| `adapter(ctx)` | any | Database adapter for `betterAuth({ database })` |
| `getAuthUser(ctx)` | any | Validates identity, session row (unexpired), user row. **Throws** `ConvexError("Unauthenticated")` |
| `safeGetAuthUser(ctx)` | any | Same checks, returns `undefined` instead of throwing |
| `getAnyUserById(ctx, id)` | any | User by Better Auth id, no auth check |
| `getAuth(createAuth, ctx)` | any | `{ auth, headers }` for calling `auth.api.*` with the current session |
| `getHeaders(ctx)` | any | Headers carrying the session cookie (used by `getAuth`) |
| `setUserId(ctx, authId, userId)` | mutation | Writes your app user id onto the auth user row (`userId` field) |
| `clientApi()` | n/a | `{ getAuthUser }` query for `AuthBoundary` |
| `triggersApi()` | n/a | `{ onCreate, onUpdate, onDelete }` internal mutations, export from `convex/auth.ts` |
| `registerRoutes(http, createAuth, opts?)` | n/a | Mount HTTP routes |
| `registerRoutesLazy(http, createAuth, opts?)` | n/a | Same, without initializing Better Auth at registration |

`ctx.auth.getUserIdentity()` is available too and is cheaper, but it only checks the JWT, not the session row. The JWT payload carries `sessionId`, `iat`, and every user field except `id` and `image` by default.

### `registerRoutesLazy` and out of memory

If `convex dev` or `convex deploy` fails with `JavaScript execution ran out of memory (maximum memory usage: 64 MB)`:

```ts
// convex/http.ts
authComponent.registerRoutesLazy(http, createAuth, {
  basePath: '/api/auth',            // omit when default
  cors: true,                        // only if you need CORS
  trustedOrigins: [process.env.SITE_URL!],   // lets OPTIONS answer without loading Better Auth
})
```

Also import Better Auth plugins from subpaths (`better-auth/plugins/magic-link`, not `better-auth/plugins`). To inspect what is inflating the bundle:

```bash
npx convex dev --once --debug-bundle-path /tmp/convex-bundle
```

Check the `isolate` folder for `convex/http.ts`.

## `convex()` server plugin

```ts
convex({
  authConfig,                          // required, from convex/auth.config.ts
  jwt: {
    expirationSeconds: 900,            // default 15 minutes
    definePayload: ({ user, session }) => ({ name: user.name, email: user.email, role: user.role }),
  },
  jwks: process.env.JWKS,              // experimental static JWKS
  options: { basePath: '/custom/auth/path' },   // must match betterAuth basePath if customized
  jwksRotateOnTokenGenerationError: true,        // only during the 0.10 RS256 migration
})
```

`sessionId` and `iat` are always added to the payload. If Better Auth uses a custom `basePath`, pass the same value in `options.basePath` or the JWKS endpoint is wrong.

## `convexClient()` client plugin

No options. Provides type inference for `createAuthClient`. Import from `@convex-dev/better-auth/client/plugins`.

## `convexBetterAuthReactStart(opts)`

```ts
convexBetterAuthReactStart({
  convexUrl,           // .convex.cloud
  convexSiteUrl,       // .convex.site, validated at startup
  basePath?,           // default /api/auth
  cookiePrefix?,
  jwtCache?: { enabled: boolean; expirationToleranceSeconds?: number; isAuthError: (e: unknown) => boolean },
})
```

Returns `handler`, `getToken`, `fetchAuthQuery`, `fetchAuthMutation`, `fetchAuthAction`. `getToken` is cached per request on React 19. The `handler` strips hop-by-hop headers and sets `x-forwarded-host`/`x-better-auth-forwarded-host` so Better Auth sees the app origin.

## Triggers

Transactional callbacks when auth tables change. Unlike Better Auth `databaseHooks`, they run in the same transaction as the write, and work on every table in the auth schema. Throwing in a trigger fails that one database operation (earlier operations in the same endpoint call have already committed).

```ts
// convex/auth.ts
import { createClient, type AuthFunctions } from '@convex-dev/better-auth'
import { components, internal } from './_generated/api'

const authFunctions: AuthFunctions = internal.auth

export const authComponent = createClient<DataModel>(components.betterAuth, {
  authFunctions,
  triggers: {
    user: {
      onCreate: async (ctx, authUser) => {
        const userId = await ctx.db.insert('users', { email: authUser.email })
        await authComponent.setUserId(ctx, authUser._id, userId)
      },
      onUpdate: async (ctx, newUser, oldUser) => {
        if (oldUser.email !== newUser.email) {
          await ctx.db.patch(newUser.userId as Id<'users'>, { email: newUser.email })
        }
      },
      onDelete: async (ctx, authUser) => {
        const user = await ctx.db.get(authUser.userId as Id<'users'>)
        if (user) await ctx.db.delete(user._id)
      },
    },
  },
})

export const { onCreate, onUpdate, onDelete } = authComponent.triggersApi()
```

This is the upstream pattern for an app-owned `users` table. Read it back with:

```ts
export const safeGetUser = async (ctx: QueryCtx) => {
  const authUser = await authComponent.safeGetAuthUser(ctx)
  if (!authUser) return
  const user = await ctx.db.get(authUser.userId as Id<'users'>)
  if (!user) return
  return { ...user, ...withoutSystemFields(authUser) }
}
```

## Supported plugins (default schema)

Anonymous, Email OTP, Generic OAuth, JWT, Magic Link, One Tap, Phone Number, Two Factor, Username. Anything else that touches schema needs Local Install. **SSO is incompatible** even with Local Install (Node.js dependencies). **Passkey** was removed from the bundled schema in 0.11; use Local Install plus `@better-auth/passkey`.

Import server plugins from subpaths: `better-auth/plugins/two-factor`, `better-auth/plugins/magic-link`, `better-auth/plugins/email-otp`, `better-auth/plugins/anonymous`.

## Local Install

Puts the component in `convex/betterAuth/` so you own the schema, can add custom indexes, unsupported plugins, and Convex functions that read auth tables directly. Steps (from `features/local-install.mdx`):

1. `convex/betterAuth/convex.config.ts`: `defineComponent("betterAuth")`.
2. `convex/betterAuth/auth.ts`: only `export const auth = createAuth({} as any)` for schema generation. Never import at runtime.
3. Generate: `cd convex/betterAuth && npx auth generate` (the CLI is now `npx auth`, not `npx @better-auth/cli`).
4. Split `createAuthOptions(ctx)` (returns `satisfies BetterAuthOptions`) from `createAuth(ctx) => betterAuth(createAuthOptions(ctx))`.
5. `convex/betterAuth/adapter.ts`: `export const { create, findOne, findMany, updateOne, updateMany, deleteOne, deleteMany } = createApi(schema, createAuthOptions)`.
6. `convex/convex.config.ts`: import `betterAuth from './betterAuth/convex.config'`.
7. `createClient<DataModel, typeof authSchema>(components.betterAuth, { local: { schema: authSchema } })`.

Re-run `npx auth generate` after any options change that affects schema, and after upgrading Better Auth. Custom indexes: generate to `--output generatedSchema.ts`, then spread `tables` in `schema.ts` and add indexes there so regeneration does not overwrite them. Functions inside the component directory are never exposed to the internet even when public; give them return validators so callers get types.

## Debugging

```ts
createClient(components.betterAuth, { verbose: true })        // backend
new ConvexReactClient(url, { verbose: true })                  // client
```

## Experimental

### JWT caching

`fetchAuth*` reuse the JWT from request cookies when unexpired, saving a token request per SSR. `isAuthError` is required. In 0.12.5 (`dist/react-start/index.js`), when a call made with a cached token fails, it is retried once with a fresh token only if `isAuthError` does **not** match the error; matching errors are rethrown. Read the source for your installed version before relying on either behaviour:

```ts
// lib/utils.ts
import { ConvexError } from 'convex/values'
export const isAuthError = (error: unknown) => {
  const message =
    (error instanceof ConvexError && error.data) ||
    (error instanceof Error && error.message) ||
    ''
  return /auth/i.test(message)
}
```

```ts
convexBetterAuthReactStart({ convexUrl, convexSiteUrl, jwtCache: { enabled: true, isAuthError } })
```

### Static JWKS

Avoids the JWKS fetch on every HTTP token validation.

```ts
// convex/auth.ts
export const getLatestJwks = internalAction({
  args: {},
  handler: async (ctx) => createAuth(ctx).api.getLatestJwks(),
})
```

```bash
npx convex run auth:getLatestJwks | npx convex env set JWKS
```

Then `getAuthConfigProvider({ jwks: process.env.JWKS })` in `auth.config.ts` and `convex({ authConfig, jwks: process.env.JWKS })` in the plugin.

### AuthBoundary

See `gotchas.md` for the full wiring. Props: `authClient`, `onUnauth`, `getAuthUserFn` (from `authComponent.clientApi()`), `isAuthError`, and optional `renderFallback`.

## Migrations

| Version | Change |
|---|---|
| 0.12 | Better Auth 1.6.x (migration doc says 1.6.9+; the 0.12.5 peer range requires >=1.6.11). Cross-domain (SPA/Expo) apps must set `baseURL: process.env.CONVEX_SITE_URL`. CLI is `npx auth generate` |
| 0.11 | Better Auth 1.5. Passkey removed from bundled schema. `oauthApplication.redirectURLs` renamed `redirectUrls` |
| 0.10 | `getAuthConfigProvider()` (customJwt, RS256). `convex({ authConfig })` required. `jwksRotateOnTokenGenerationError: true` during migration. `convexBetterAuthReactStart` replaces `setupFetchClient` and `reactStartHandler`. `expectAuth: true`, `initialToken`, reload on sign out. `optionsOnly` param dropped |

Full steps: `docs/content/docs/migrations/*.mdx` upstream.
