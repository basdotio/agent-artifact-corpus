# Session Management

## What Matters

- **Server-side**: Use `auth.api.getSession()` with headers
- **Client-side**: Use `authClient.useSession()` hook
- **Next.js 16**: `headers()`, `cookies()`, `params`, `searchParams` ALL require await

## Server-Side Session (Next.js 16)

### In Server Components

```typescript
import { auth } from "@/lib/auth";
import { headers } from "next/headers";

export default async function DashboardPage() {
  const session = await auth.api.getSession({
    headers: await headers(), // MUST await
  });

  if (!session) {
    return <p>Not authenticated</p>;
  }

  return (
    <div>
      <p>User: {session.user.name}</p>
      <p>Email: {session.user.email}</p>
    </div>
  );
}
```

### With Dynamic Route Params (Next.js 16)

```typescript
// app/users/[id]/page.tsx
import { auth } from "@/lib/auth";
import { headers } from "next/headers";

export default async function UserPage({
  params,
}: {
  params: Promise<{ id: string }>  // params is a Promise
}) {
  const { id } = await params;  // Must await

  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    return <p>Not authenticated</p>;
  }

  return <p>User {id}: {session.user.name}</p>;
}
```

### In Server Actions

```typescript
"use server";

import { auth } from "@/lib/auth";
import { headers } from "next/headers";

export async function protectedAction() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    throw new Error("Unauthorized");
  }

  return { userId: session.user.id };
}
```

### In API Routes

```typescript
// app/api/protected/route.ts
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { NextResponse } from "next/server";

export async function GET() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  return NextResponse.json({ user: session.user });
}
```

## Client-Side Session

### useSession Hook

```typescript
"use client";

import { authClient } from "@/lib/auth-client";

export function UserProfile() {
  const { data: session, isPending, error } = authClient.useSession();

  if (isPending) {
    return <p>Loading...</p>;
  }

  if (error) {
    return <p>Error: {error.message}</p>;
  }

  if (!session) {
    return <p>Not signed in</p>;
  }

  return (
    <div>
      <p>Welcome, {session.user.name}</p>
      <p>Email: {session.user.email}</p>
    </div>
  );
}
```

### Conditional Rendering

```typescript
"use client";

import { authClient } from "@/lib/auth-client";

export function AuthStatus() {
  const { data: session, isPending } = authClient.useSession();

  if (isPending) return null;

  return session ? (
    <button onClick={() => authClient.signOut()}>Sign Out</button>
  ) : (
    <a href="/signin">Sign In</a>
  );
}
```

## Session Type

```typescript
// lib/auth.ts
export type Session = typeof auth.$Infer.Session;

// In components
import type { Session } from "@/lib/auth";

function Component({ session }: { session: Session }) {
  // Type-safe session access
}
```

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| `getSession()` without headers | Always returns null | Pass `headers: await headers()` |
| `headers()` without await | Type error | Use `await headers()` |
| `params` without await | Type error | Use `await params` |
| `authClient.getSession()` in server | Wrong context | Use `auth.api.getSession()` |
| useSession in server component | Hook error | Only use in client components |
