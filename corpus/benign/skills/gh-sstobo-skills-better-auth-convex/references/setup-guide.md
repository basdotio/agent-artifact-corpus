# Setup Guide: Better Auth + Convex + TanStack Start

Mirrors the upstream TanStack Start guide (`docs/content/docs/framework-guides/tanstack-start.mdx`) and `examples/tanstack`. Requires Convex 1.25.0+. Keep `npx convex dev` running throughout so generated types stay current.

Symptoms that appear after setup go to `gotchas.md`.

---

## Step 1: Install packages

```bash
npm install convex@latest @convex-dev/better-auth
npm install better-auth@~1.6.15
npm install @types/node --save-dev
```

## Step 2: Configure Vite for SSR

```ts
// vite.config.ts
export default defineConfig({
  // ...other config
  ssr: {
    noExternal: ['@convex-dev/better-auth'],
  },
})
```

## Step 3: Register the component

```ts
// convex/convex.config.ts
import { defineApp } from 'convex/server'
import betterAuth from '@convex-dev/better-auth/convex.config'

const app = defineApp()
app.use(betterAuth)

export default app
```

## Step 4: Convex auth config

```ts
// convex/auth.config.ts
import { getAuthConfigProvider } from '@convex-dev/better-auth/auth-config'
import type { AuthConfig } from 'convex/server'

export default {
  providers: [getAuthConfigProvider()],
} satisfies AuthConfig
```

This uses Convex's `customJwt` provider so token validation skips OIDC discovery.

## Step 5: Environment variables

```bash
npx convex env set BETTER_AUTH_SECRET=$(openssl rand -base64 32)
npx convex env set SITE_URL http://localhost:3000
```

```bash
# .env.local (cloud)
CONVEX_DEPLOYMENT=dev:adjective-animal-123
VITE_CONVEX_URL=https://adjective-animal-123.convex.cloud
VITE_CONVEX_SITE_URL=https://adjective-animal-123.convex.site
VITE_SITE_URL=http://localhost:3000
```

```bash
# .env.local (self hosted): site URL is one port above the convex URL
VITE_CONVEX_URL=http://127.0.0.1:3210
VITE_CONVEX_SITE_URL=http://127.0.0.1:3211
VITE_SITE_URL=http://localhost:3000
```

`convexBetterAuthReactStart` throws at startup if `VITE_CONVEX_SITE_URL` is missing or ends in `.convex.cloud`.

## Step 6: Better Auth instance

```ts
// convex/auth.ts
import { betterAuth } from 'better-auth/minimal'
import { createClient } from '@convex-dev/better-auth'
import { convex } from '@convex-dev/better-auth/plugins'
import authConfig from './auth.config'
import { components } from './_generated/api'
import { query } from './_generated/server'
import type { GenericCtx } from '@convex-dev/better-auth'
import type { DataModel } from './_generated/dataModel'

const siteUrl = process.env.SITE_URL!

export const authComponent = createClient<DataModel>(components.betterAuth)

export const createAuth = (ctx: GenericCtx<DataModel>) => {
  return betterAuth({
    baseURL: siteUrl,
    database: authComponent.adapter(ctx),
    emailAndPassword: {
      enabled: true,
      requireEmailVerification: false,
    },
    plugins: [
      // Required for Convex compatibility
      convex({ authConfig }),
    ],
  })
}

export const getCurrentUser = query({
  args: {},
  handler: async (ctx) => {
    return await authComponent.getAuthUser(ctx)
  },
})
```

Some TypeScript errors show until the file is saved and `convex dev` regenerates types. `getAuthUser` throws `ConvexError("Unauthenticated")` when there is no valid session; use `safeGetAuthUser` if you want `undefined` instead.

## Step 7: Auth client

```ts
// src/lib/auth-client.ts
import { createAuthClient } from 'better-auth/react'
import { convexClient } from '@convex-dev/better-auth/client/plugins'

export const authClient = createAuthClient({
  plugins: [convexClient()],
})
```

Better Auth client plugins (`magicLinkClient`, `twoFactorClient`, etc.) come from `better-auth/client/plugins` and sit alongside `convexClient()`.

## Step 8: TanStack server utilities

```ts
// src/lib/auth-server.ts
import { convexBetterAuthReactStart } from '@convex-dev/better-auth/react-start'

export const {
  handler,
  getToken,
  fetchAuthQuery,
  fetchAuthMutation,
  fetchAuthAction,
} = convexBetterAuthReactStart({
  convexUrl: process.env.VITE_CONVEX_URL!,
  convexSiteUrl: process.env.VITE_CONVEX_SITE_URL!,
  // basePath: '/custom/auth/path',   // optional, defaults to /api/auth
  // jwtCache: { enabled: true, isAuthError },   // experimental, see core-reference.md
})
```

These run on the TanStack server (loaders, server functions, route handlers). Session cookies authenticate automatically. They accept only a function reference and args; there is no third options argument.

## Step 9: Mount handlers

```ts
// convex/http.ts
import { httpRouter } from 'convex/server'
import { authComponent, createAuth } from './auth'

const http = httpRouter()
authComponent.registerRoutes(http, createAuth)

export default http
```

If deploys hit the 64 MB memory limit, switch to `registerRoutesLazy` (see `core-reference.md`).

```ts
// src/routes/api/auth/$.ts
import { createFileRoute } from '@tanstack/react-router'
import { handler } from '~/lib/auth-server'

export const Route = createFileRoute('/api/auth/$')({
  server: {
    handlers: {
      GET: ({ request }) => handler(request),
      POST: ({ request }) => handler(request),
    },
  },
})
```

## Step 10: Root route

```tsx
// src/routes/__root.tsx
/// <reference types="vite/client" />
import {
  HeadContent, Outlet, Scripts,
  createRootRouteWithContext, useRouteContext,
} from '@tanstack/react-router'
import * as React from 'react'
import { createServerFn } from '@tanstack/react-start'
import { ConvexBetterAuthProvider } from '@convex-dev/better-auth/react'
import type { ConvexQueryClient } from '@convex-dev/react-query'
import type { QueryClient } from '@tanstack/react-query'
import appCss from '~/styles/app.css?url'
import { authClient } from '~/lib/auth-client'
import { getToken } from '~/lib/auth-server'

// Get auth information for SSR using available cookies
const getAuth = createServerFn({ method: 'GET' }).handler(async () => {
  return await getToken()
})

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient
  convexQueryClient: ConvexQueryClient
}>()({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
    ],
    links: [
      { rel: 'stylesheet', href: appCss },
      { rel: 'icon', href: '/favicon.ico' },
    ],
  }),
  beforeLoad: async (ctx) => {
    const token = await getAuth()
    // All TanStack Query traffic is authenticated during SSR when a token exists.
    // serverHttpClient only exists during SSR.
    if (token) {
      ctx.context.convexQueryClient.serverHttpClient?.setAuth(token)
    }
    return { isAuthenticated: !!token, token }
  },
  component: RootComponent,
})

function RootComponent() {
  const context = useRouteContext({ from: Route.id })
  return (
    <ConvexBetterAuthProvider
      client={context.convexQueryClient.convexClient}
      authClient={authClient}
      initialToken={context.token}
    >
      <RootDocument>
        <Outlet />
      </RootDocument>
    </ConvexBetterAuthProvider>
  )
}

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head><HeadContent /></head>
      <body>{children}<Scripts /></body>
    </html>
  )
}
```

## Step 11: Router

```tsx
// src/router.tsx
import { createRouter } from '@tanstack/react-router'
import { QueryClient, notifyManager } from '@tanstack/react-query'
import { setupRouterSsrQueryIntegration } from '@tanstack/react-router-ssr-query' // install if missing
import { ConvexQueryClient } from '@convex-dev/react-query'
import { routeTree } from './routeTree.gen'

export function getRouter() {
  if (typeof document !== 'undefined') {
    notifyManager.setScheduler(window.requestAnimationFrame)
  }

  const convexUrl = (import.meta as any).env.VITE_CONVEX_URL!
  if (!convexUrl) throw new Error('VITE_CONVEX_URL is not set')

  // expectAuth: true blocks client-side Convex calls until authenticated.
  // Without it, SSR-authenticated data is lost right after first render.
  const convexQueryClient = new ConvexQueryClient(convexUrl, { expectAuth: true })

  const queryClient: QueryClient = new QueryClient({
    defaultOptions: {
      queries: {
        queryKeyHashFn: convexQueryClient.hashFn(),
        queryFn: convexQueryClient.queryFn(),
      },
    },
  })
  convexQueryClient.connect(queryClient)

  const router = createRouter({
    routeTree,
    defaultPreload: 'intent',
    context: { queryClient, convexQueryClient },
    scrollRestoration: true,
    defaultErrorComponent: (err) => <p>{err.error.stack}</p>,
    defaultNotFoundComponent: () => <p>not found</p>,
  })

  setupRouterSsrQueryIntegration({ router, queryClient })

  return router
}
```

No `Wrap` / `ConvexProvider` here: `ConvexBetterAuthProvider` in the root route already provides the Convex client. `routerWithQueryClient` from `@tanstack/react-router-with-query` is the old shape; replace it with `setupRouterSsrQueryIntegration`.

---

## Usage

### Protected routes

```tsx
// src/routes/_authed.tsx
import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/_authed')({
  beforeLoad: ({ context }) => {
    if (!context.isAuthenticated) {
      throw redirect({ to: '/sign-in' })
    }
  },
  component: () => <Outlet />,
})
```

Wrap `<Outlet />` in `ClientAuthBoundary` for stale-token recovery (see `gotchas.md`). Mirror it on `/sign-in` with `if (context.isAuthenticated) throw redirect({ to: '/' })`.

### SSR with TanStack Query

```tsx
import { createFileRoute } from '@tanstack/react-router'
import { useSuspenseQuery } from '@tanstack/react-query'
import { convexQuery } from '@convex-dev/react-query'
import { api } from '~/convex/_generated/api'

export const Route = createFileRoute('/_authed/')({
  loader: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(convexQuery(api.auth.getCurrentUser, {})),
      // more queries in parallel
    ])
  },
  component: App,
})

function App() {
  const { data: user } = useSuspenseQuery(convexQuery(api.auth.getCurrentUser, {}))
  return <div>{user.email}</div>
}
```

`ensureQueryData` is what the upstream guide uses. From `@tanstack/react-query` 5.102.0 it is deprecated in favour of `await context.queryClient.query({ ...convexQuery(fn, args), staleTime: 'static' })`, which is what the Convex TanStack Start docs now show. `ensureQueryData` still works in 5.x; `query()` needs 5.102.0 or later.

### Sign in / sign up (client only)

```ts
const { data, error } = await authClient.signIn.email(
  { email, password },
  {
    onSuccess: () => router.navigate({ to: '/' }),
    onError: (ctx) => alert(ctx.error.message),
  },
)
```

Sign in does not need a reload. Only sign out does.

### Sign out (reload required)

```ts
await authClient.signOut({
  fetchOptions: {
    onSuccess: () => location.reload(),
  },
})
```

`expectAuth: true` only takes effect before the first authentication. For apps that redirect on `!isAuthenticated`, the reload triggers the redirect, so no navigate call is needed.

### Showing UI by auth state

Use Convex's state, not Better Auth's:

```tsx
import { Authenticated, Unauthenticated, AuthLoading, useConvexAuth } from 'convex/react'
```

Better Auth's `useSession()` reports signed in before Convex has validated the token. Components that call authenticated queries must sit under `<Authenticated>` or check `useConvexAuth().isAuthenticated`.

### Calling `auth.api` from the server

`auth.api.*` runs inside a Convex function. Call that function from a server function via `fetchAuthMutation` or from the client via `useMutation`.

```ts
// convex/users.ts
import { mutation } from './_generated/server'
import { v } from 'convex/values'
import { createAuth, authComponent } from './auth'

export const updateUserPassword = mutation({
  args: { currentPassword: v.string(), newPassword: v.string() },
  handler: async (ctx, args) => {
    // getAuth returns the auth object plus headers carrying the session cookie
    const { auth, headers } = await authComponent.getAuth(createAuth, ctx)
    await auth.api.changePassword({
      body: { currentPassword: args.currentPassword, newPassword: args.newPassword },
      headers,
    })
  },
})
```

```ts
// src/routes/users.ts
import { createServerFn } from '@tanstack/react-start'
import { fetchAuthMutation } from '~/lib/auth-server'
import { api } from '~/convex/_generated/api'

export const updatePassword = createServerFn({ method: 'POST' }).handler(
  async ({ data: { currentPassword, newPassword } }) => {
    await fetchAuthMutation(api.users.updateUserPassword, { currentPassword, newPassword })
  },
)
```

### Sending email from Better Auth config

`createAuth` receives a Convex ctx that may be a query, mutation, or action ctx. Network calls need an action ctx; use the type guard.

```ts
import { requireActionCtx } from '@convex-dev/better-auth/utils'

emailVerification: {
  sendVerificationEmail: async ({ user, url }) => {
    await resend.sendEmail(requireActionCtx(ctx), { to: user.email, subject: 'Verify', html: `<a href="${url}">Verify</a>` })
  },
},
```

---

## Quick verification

1. `npx convex dev` and the Vite dev server both running.
2. Visit `http://localhost:3000`, sign up, sign in. Land on the protected route.
3. Hard reload while signed in. Content renders with no flash of signed-out UI.
4. Sign out. Page reloads and redirects to sign in.

Any failure: `gotchas.md`.
