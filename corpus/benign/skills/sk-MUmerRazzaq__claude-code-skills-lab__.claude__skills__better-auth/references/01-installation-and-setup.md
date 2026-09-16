# Installation & Core Setup

## What Matters

- One package: `better-auth` (includes all adapters and Next.js support)
- Two config files: `lib/auth.ts` (server) and `lib/auth-client.ts` (client)
- Secret must be 32+ characters

## Install

```bash
npm install better-auth
```

## Server Config: lib/auth.ts

```typescript
import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

export const auth = betterAuth({
  secret: process.env.AUTH_SECRET!, // 32+ chars, required
  baseURL: process.env.AUTH_URL,    // http://localhost:3000 for dev

  database: prismaAdapter(prisma, {
    provider: "postgresql",
  }),

  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
    requireEmailVerification: true, // Enable for production
  },

  // Email verification - YOU must implement sendEmail
  emailVerification: {
    sendVerificationEmail: async ({ user, url }) => {
      await sendEmail({
        to: user.email,
        subject: "Verify your email",
        html: `<a href="${url}">Verify Email</a>`,
      });
    },
  },
});

export type Session = typeof auth.$Infer.Session;
```

## Client Config: lib/auth-client.ts

```typescript
import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_AUTH_URL, // Optional, defaults to current origin
});
```

## Environment Variables

```bash
# .env.local
AUTH_SECRET="your-32-char-minimum-secret-here"  # Generate: openssl rand -base64 32
AUTH_URL="http://localhost:3000"
DATABASE_URL="postgresql://user:pass@localhost:5432/db"
```

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| AUTH_SECRET < 32 chars | "Invalid secret" error | Use `openssl rand -base64 32` |
| Missing AUTH_URL | OAuth callbacks fail | Set to your app's base URL |
| Importing from wrong path | Type errors | Server: `better-auth`, Client: `better-auth/react` |
