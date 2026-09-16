# Next.js Integration (v16)

## What Matters

- **Next.js 16**: `middleware.ts` renamed to `proxy.ts`, function renamed to `proxy`
- **Next.js 15+**: `headers()`, `cookies()`, `params`, `searchParams` are all **async**
- Edge runtime NOT supported in proxy (nodejs only)
- Server components must use `auth.api.getSession()` with `await headers()`

## API Route Handler

Create `app/api/auth/[...all]/route.ts`:

```typescript
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { GET, POST } = toNextJsHandler(auth);
```

This creates all auth endpoints automatically:
- `/api/auth/sign-in/email`
- `/api/auth/sign-up/email`
- `/api/auth/sign-out`
- `/api/auth/session`
- `/api/auth/callback/:provider`

## Route Protection with Proxy (Next.js 16)

Create `proxy.ts` in project root:

```typescript
import { NextRequest, NextResponse } from "next/server";
import { getSessionCookie } from "better-auth/cookies";

export function proxy(request: NextRequest) {
  const sessionCookie = getSessionCookie(request);
  const { pathname } = request.nextUrl;

  // Redirect logged-in users away from auth pages
  if (sessionCookie && ["/signin", "/signup"].includes(pathname)) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // Protect dashboard routes
  if (!sessionCookie && pathname.startsWith("/dashboard")) {
    return NextResponse.redirect(new URL("/signin", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|.*\\.png$).*)"],
};
```

### Migration from middleware.ts

```bash
# Rename your file
mv middleware.ts proxy.ts

# Or use the codemod
npx @next/codemod@latest middleware-to-proxy .
```

```diff
// middleware.ts -> proxy.ts
- export function middleware(request: NextRequest) {
+ export function proxy(request: NextRequest) {
```

## Server Component Session (Next.js 16)

```typescript
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

export default async function DashboardPage() {
  // REQUIRED: headers() must be awaited
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    redirect("/signin");
  }

  return <h1>Welcome {session.user.name}</h1>;
}
```

## Dynamic Route with Params (Next.js 16)

```typescript
// app/users/[id]/page.tsx
import { auth } from "@/lib/auth";
import { headers } from "next/headers";

export default async function UserPage({
  params,
}: {
  params: Promise<{ id: string }>  // params is now a Promise
}) {
  const { id } = await params;  // Must await params

  const session = await auth.api.getSession({
    headers: await headers(),
  });

  return <h1>User {id}</h1>;
}
```

## Server Action Session (Next.js 16)

```typescript
"use server";

import { auth } from "@/lib/auth";
import { headers } from "next/headers";

export async function updateProfile(formData: FormData) {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    throw new Error("Unauthorized");
  }

  // Update user...
}
```

## Reading Cookies (Next.js 16)

```typescript
import { cookies } from "next/headers";

export default async function Page() {
  const cookieStore = await cookies();  // Must await
  const theme = cookieStore.get("theme");

  return <div>Theme: {theme?.value}</div>;
}
```

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Using `middleware.ts` in Next.js 16 | Deprecated warning | Rename to `proxy.ts` |
| `export function middleware` | Function not found | Rename to `export function proxy` |
| `headers()` without await | Type error | Use `await headers()` |
| `params` without await | Type error | Use `await params` |
| `searchParams` without await | Type error | Use `await searchParams` |
| Using edge runtime in proxy | Not supported | Proxy is nodejs only |

## Version Compatibility

| Next.js | File | Function | Async APIs |
|---------|------|----------|------------|
| 14.x | `middleware.ts` | `middleware` | Sync |
| 15.x | `middleware.ts` | `middleware` | **Async (await)** |
| 16.x | **`proxy.ts`** | **`proxy`** | **Async (await)** |

## Keep middleware.ts for Edge Runtime

If you need edge runtime, keep `middleware.ts`:

```typescript
// middleware.ts (edge runtime only)
export const config = {
  runtime: "edge",  // Only supported in middleware.ts
};

export function middleware(request: NextRequest) {
  // Edge-compatible code only
}
```
