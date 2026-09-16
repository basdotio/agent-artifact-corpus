# Better Auth - Advanced Authentication Made Simple

Better Auth is a modern, framework-agnostic authentication library that simplifies complex auth patterns while maintaining security and flexibility.

## Why Better Auth?

✅ **All authentication methods built-in** (JWT, sessions, cookies, OAuth)
✅ **Multi-provider support** (Google, GitHub, Microsoft, Discord, etc.)
✅ **Email verification** included
✅ **MFA/2FA support** built-in
✅ **Permission management** out of the box
✅ **Minimal configuration** needed
✅ **Type-safe** across frontend and backend
✅ **RBAC support** with advanced features

## Setup

### Installation

```bash
npm install better-auth
npm install next-auth  # For Next.js integration
npm install prisma @prisma/client
```

### Initialize Prisma

```bash
npx prisma init
```

### .env Configuration

```bash
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/authdb"

# Better Auth
BETTER_AUTH_SECRET="your-secret-key"
BETTER_AUTH_URL="http://localhost:3000"

# OAuth Providers
GOOGLE_CLIENT_ID="xxx"
GOOGLE_CLIENT_SECRET="xxx"
GITHUB_CLIENT_ID="xxx"
GITHUB_CLIENT_SECRET="xxx"
```

## Complete Setup

### Prisma Schema

```prisma
// prisma/schema.prisma
datasource db {
    provider = "postgresql"
    url      = env("DATABASE_URL")
}

generator client {
    provider = "prisma-client-js"
}

model User {
    id            String    @id @default(cuid())
    name          String?
    email         String    @unique
    emailVerified Boolean   @default(false)
    image         String?
    password      String?
    role          String    @default("user")
    
    // Relations
    sessions      Session[]
    accounts      Account[]
    
    createdAt     DateTime  @default(now())
    updatedAt     DateTime  @updatedAt
}

model Session {
    id        String   @id @default(cuid())
    sessionToken String @unique
    userId    String
    user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
    expires   DateTime
    createdAt DateTime @default(now())
    updatedAt DateTime @updatedAt
}

model Account {
    id                 String  @id @default(cuid())
    userId             String
    type               String
    provider           String
    providerAccountId  String
    refresh_token      String?
    access_token       String?
    expires_at         Int?
    token_type         String?
    scope              String?
    id_token           String?
    session_state      String?
    
    user User @relation(fields: [userId], references: [id], onDelete: Cascade)
    
    @@unique([provider, providerAccountId])
}

model VerificationToken {
    id         String   @id @default(cuid())
    email      String   @unique
    token      String   @unique
    expires    DateTime
    createdAt  DateTime @default(now())
}
```

### Better Auth Configuration

```typescript
// lib/auth.ts
import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { PrismaClient } from "@prisma/client";
import { nextCookies } from "better-auth/next-js";

const prisma = new PrismaClient();

export const auth = betterAuth({
    database: prismaAdapter(prisma),
    secret: process.env.BETTER_AUTH_SECRET,
    appName: "My Auth App",
    basePath: "/api/auth",
    
    // Session configuration
    session: {
        cookieOptions: {
            httpOnly: true,
            secure: process.env.NODE_ENV === "production",
            sameSite: "strict",
            maxAge: 7 * 24 * 60 * 60 // 7 days
        }
    },
    
    // User configuration
    user: {
        additionalFields: {
            role: {
                type: "string",
                default: "user"
            }
        }
    },
    
    // Email verification
    emailVerification: {
        sendVerificationEmail: async ({ user, url }) => {
            await sendEmail({
                to: user.email,
                subject: "Verify your email",
                html: `<a href="${url}">Verify email</a>`
            });
        }
    },
    
    // OAuth providers
    socialProviders: {
        google: {
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET
        },
        github: {
            clientId: process.env.GITHUB_CLIENT_ID,
            clientSecret: process.env.GITHUB_CLIENT_SECRET
        },
        discord: {
            clientId: process.env.DISCORD_CLIENT_ID,
            clientSecret: process.env.DISCORD_CLIENT_SECRET
        }
    },
    
    // Additional options
    plugins: [
        nextCookies() // For Next.js cookie handling
    ]
});

export type Session = typeof auth.$Infer.Session;
```

## API Routes

### auth/register

```typescript
// app/api/auth/register/route.ts
import { auth } from "@/lib/auth";

export const POST = auth.handler;
```

### auth/login

```typescript
// app/api/auth/login/route.ts
import { auth } from "@/lib/auth";

export const POST = auth.handler;
```

### auth/signout

```typescript
// app/api/auth/signout/route.ts
import { auth } from "@/lib/auth";

export const POST = auth.handler;
```

## Client-Side Usage

### useSession Hook

```typescript
// components/UserProfile.tsx
"use client";

import { useSession } from "better-auth/client";

export function UserProfile() {
    const { data: session, isPending } = useSession();
    
    if (isPending) return <div>Loading...</div>;
    
    if (!session) return <div>Not logged in</div>;
    
    return (
        <div>
            <h1>Welcome {session.user.name}</h1>
            <img src={session.user.image} alt="Profile" />
        </div>
    );
}
```

### Sign In with OAuth

```typescript
// components/LoginButton.tsx
"use client";

import { signIn } from "better-auth/client";

export function LoginButton() {
    return (
        <div>
            <button onClick={() => signIn.social({ provider: "google" })}>
                Login with Google
            </button>
            
            <button onClick={() => signIn.social({ provider: "github" })}>
                Login with GitHub
            </button>
            
            <button onClick={() => signIn.social({ provider: "discord" })}>
                Login with Discord
            </button>
        </div>
    );
}
```

### Sign In with Email/Password

```typescript
// app/login/page.tsx
"use client";

import { signIn } from "better-auth/client";
import { useState } from "react";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    
    async function handleLogin(e: React.FormEvent) {
        e.preventDefault();
        
        try {
            const result = await signIn.email({
                email,
                password,
                callbackURL: "/dashboard"
            });
            
            if (!result.ok) {
                setError(result.error?.message || "Login failed");
            }
        } catch (err) {
            setError("An error occurred");
        }
    }
    
    return (
        <form onSubmit={handleLogin}>
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
            
            <button type="submit">Login</button>
            
            {error && <div>{error}</div>}
        </form>
    );
}
```

## Email Verification

### Send Verification Email

```typescript
// lib/email.ts
import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

export async function sendVerificationEmail(email: string, url: string) {
    await resend.emails.send({
        from: "noreply@myapp.com",
        to: email,
        subject: "Verify your email",
        html: `
            <h1>Verify Your Email</h1>
            <p>Click the link below to verify your email:</p>
            <a href="${url}">Verify Email</a>
        `
    });
}
```

## Role-Based Access Control (RBAC)

### Middleware

```typescript
// middleware.ts
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

export async function middleware(request: NextRequest) {
    const session = await auth.api.getSession({
        headers: request.headers
    });
    
    // Check role for protected routes
    if (request.nextUrl.pathname.startsWith("/admin")) {
        if (!session || session.user.role !== "admin") {
            return NextResponse.redirect(new URL("/", request.url));
        }
    }
    
    return NextResponse.next();
}

export const config = {
    matcher: ["/admin/:path*", "/dashboard/:path*"]
};
```

### Component with Role Check

```typescript
// components/AdminPanel.tsx
"use client";

import { useSession } from "better-auth/client";

export function AdminPanel() {
    const { data: session } = useSession();
    
    if (!session || session.user.role !== "admin") {
        return <div>Access Denied</div>;
    }
    
    return <div>Admin Panel</div>;
}
```

## Multi-Factor Authentication (MFA)

### Enable TOTP

```typescript
// pages/security.tsx
import { auth } from "@/lib/auth";

export async function enableTOTP(userId: string) {
    const secret = auth.generateTOTPSecret();
    
    // Save secret to database
    await db.user.update({
        where: { id: userId },
        data: { totpSecret: secret }
    });
    
    return secret;
}
```

## Custom Callbacks

### Email Change Notification

```typescript
export const auth = betterAuth({
    // ... other config
    
    callbacks: {
        async onUserCreated({ user }) {
            // Send welcome email
            await sendEmail({
                to: user.email,
                subject: "Welcome!",
                html: "Welcome to our app!"
            });
        },
        
        async onSessionCreated({ user, session }) {
            // Log login event
            await db.loginLog.create({
                data: {
                    userId: user.id,
                    timestamp: new Date()
                }
            });
        }
    }
});
```

## Advanced Features

### Custom User Fields

```typescript
export const auth = betterAuth({
    user: {
        additionalFields: {
            role: { type: "string", default: "user" },
            department: { type: "string" },
            twoFactorEnabled: { type: "boolean", default: false }
        }
    }
});
```

### Password Reset Flow

```typescript
// lib/password-reset.ts
import { auth } from "@/lib/auth";

export async function sendPasswordResetEmail(email: string) {
    const user = await db.user.findUnique({ where: { email } });
    
    if (!user) {
        // Security: don't reveal if user exists
        return;
    }
    
    const resetToken = await auth.generateToken();
    
    await db.passwordReset.create({
        data: {
            userId: user.id,
            token: resetToken,
            expires: new Date(Date.now() + 1 * 60 * 60 * 1000) // 1 hour
        }
    });
    
    const resetUrl = `${process.env.BETTER_AUTH_URL}/reset-password?token=${resetToken}`;
    
    await sendEmail({
        to: email,
        subject: "Reset your password",
        html: `<a href="${resetUrl}">Reset Password</a>`
    });
}
```

## Database Migrations

```bash
# Generate Prisma migrations
npx prisma migrate dev --name init

# Deploy migrations
npx prisma migrate deploy
```

## Security Best Practices with Better Auth

✅ **Always use HTTPS** - Set secure cookie flag
✅ **Validate email** - Use emailVerification
✅ **Rate limit** - Use middleware to limit login attempts
✅ **Secure secrets** - Store in environment variables
✅ **Regular updates** - Keep Better Auth updated
✅ **Monitor sessions** - Log and track active sessions
✅ **Implement MFA** - For sensitive operations
✅ **Audit logging** - Track all auth events

## TypeScript Types

```typescript
// types/auth.ts
import { Session } from "better-auth";

declare module "better-auth" {
    interface Session {
        user: {
            id: string;
            email: string;
            name?: string;
            image?: string;
            role: "user" | "admin" | "moderator";
            emailVerified: boolean;
        };
    }
}
```

Better Auth handles most authentication complexity, allowing you to focus on building features rather than security infrastructure.