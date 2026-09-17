---
name: better-auth
description: Comprehensive authentication skill for Better Auth with TypeScript, Next.js 16, and JWT tokens. Use when implementing authentication systems with Better Auth, setting up Next.js App Router integration, or configuring JWT token authentication.
---

# Better Auth Authentication Skill

This skill provides comprehensive knowledge for implementing authentication systems using Better Auth with TypeScript, Next.js 16, and JWT tokens.

## Overview

Better Auth is a framework-agnostic authentication and authorization library for TypeScript that provides enterprise-grade features through a flexible plugin architecture. It handles everything from basic email/password authentication to advanced features like JWT tokens, OAuth, and session management.

## Core Setup

### Backend Configuration

```typescript
import { betterAuth } from "better-auth";
import { jwt } from "better-auth/plugins";

export const auth = betterAuth({
  database: {
    provider: "postgresql", // or your preferred database
    url: process.env.DATABASE_URL!,
  },
  secret: process.env.BETTER_AUTH_SECRET!,
  plugins: [
    jwt({
      algorithm: "HS256",
      expiresIn: "7d",
      issuer: "https://example.com",
      audience: ["https://api.example.com"],
    }),
  ],
  emailAndPassword: {
    enabled: true,
  },
  emailVerification: {
    enabled: true,
  },
});
```

### Next.js Integration

Create `lib/auth.ts`:

```typescript
import { auth } from "./auth";

// Export for use throughout the application
export { auth };
```

## Next.js 16 App Router Integration

### Server Component Authentication

```typescript
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

export default async function ProtectedPage() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    redirect("/sign-in");
  }

  return (
    <div>
      <h1>Protected Content</h1>
      <p>Welcome, {session.user.name}!</p>
    </div>
  );
}
```

### Middleware for Route Protection

```typescript
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

export async function middleware(request: NextRequest) {
  const session = await auth.api.getSession({
    headers: await headers()
  });

  if (!session && request.nextUrl.pathname.startsWith("/dashboard")) {
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"],
};
```

## JWT Token Implementation

### Server-Side JWT Configuration

```typescript
import { betterAuth } from "better-auth";
import { jwt } from "better-auth/plugins";

export const auth = betterAuth({
  plugins: [
    jwt({
      algorithm: "HS256",
      expiresIn: "7d",
      issuer: "https://example.com",
      audience: ["https://api.example.com"],
    }),
  ],
});
```

### Client-Side JWT Usage

```typescript
import { createAuthClient } from "better-auth/client";
import { jwtClient } from "better-auth/client/plugins";

const authClient = createAuthClient({
  plugins: [jwtClient()],
});

// Generate JWT
const { data } = await authClient.jwt.generate();

console.log("JWT:", data.token);

// Decode JWT
const decoded = await authClient.jwt.decode({
  token: data.token,
});

console.log("JWT payload:", decoded);
```

## Bearer Token Authentication

### Server Configuration

```typescript
import { betterAuth } from "better-auth";
import { bearer } from "better-auth/plugins";

export const auth = betterAuth({
  plugins: [
    bearer({
      expiresIn: 60 * 60 * 24 * 7, // 7 days
    }),
  ],
});
```

### Client Usage

```typescript
import { bearerClient } from "better-auth/client/plugins";

const authClient = createAuthClient({
  plugins: [bearerClient()],
});

// Generate Bearer Token
const { data } = await authClient.bearer.generate();

console.log("Access token:", data.accessToken);

// Use Bearer Token in API Calls
fetch("/api/protected", {
  headers: {
    Authorization: `Bearer ${data.accessToken}`,
  },
});
```

## API Route Protection

### Protected API Route

```typescript
import { auth } from "@/lib/auth";
import { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const session = await auth.api.getSession({
    headers: {
      authorization: req.headers.authorization,
    },
  });

  if (!session) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  // Process protected route
  res.status(200).json({ message: "Access granted", user: session.user });
}
```

## Email and Password Authentication

```typescript
import { betterAuth } from 'better-auth';

export const auth = betterAuth({
  database: {
    provider: "postgresql",
    url: process.env.DATABASE_URL!,
  },
  secret: process.env.BETTER_AUTH_SECRET!,
  emailVerification: {
    sendEmailVerification: async (user) => {
      // Implement your email verification logic here
    }
  },
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false, // Set to true if email verification is required
  }
});
```

## Client-Side Integration

### Creating Auth Client

```typescript
import { createAuthClient } from "better-auth/client";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000",
  fetchOptions: {
    credentials: "include",
  },
});
```

### Using in Client Components

```typescript
"use client";

import { useState } from "react";
import { authClient } from "@/lib/auth-client";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await authClient.signIn.email({
        email,
        password,
        callbackURL: "/dashboard",
      });
      if (response.error) {
        console.error(response.error);
      }
    } catch (error) {
      console.error("Sign in error:", error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
      />
      <button type="submit">Sign In</button>
    </form>
  );
}
```

## Environment Variables

```env
DATABASE_URL=your_database_connection_string
BETTER_AUTH_SECRET=your_secret_key
NEXT_PUBLIC_BASE_URL=http://localhost:3000
```

## Best Practices

1. Always use environment variables for secrets
2. Validate sessions server-side for protected content
3. Use Next.js middleware for route-level protection
4. Implement proper error handling
5. Configure JWT expiration based on security requirements
6. Use HTTPS in production
7. Regularly rotate secrets