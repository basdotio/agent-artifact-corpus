---
name: better-auth
description: Integrate better-auth into Next.js 16 apps. Use for email/password, social OAuth, magic links, passkeys, 2FA setup. Covers database adapters (Prisma/Drizzle), session management, and route protection.
---

# better-auth Integration

## Next.js 16 Breaking Changes

| Change | Before | After |
|--------|--------|-------|
| Route protection file | `middleware.ts` | **`proxy.ts`** |
| Function export | `export function middleware` | **`export function proxy`** |
| `headers()` | Sync | **Async (await)** |
| `cookies()` | Sync | **Async (await)** |
| `params` | Object | **Promise (await)** |
| `searchParams` | Object | **Promise (await)** |
| Edge runtime in proxy | Supported | **NOT supported** |

```bash
# Migration codemod
npx @next/codemod@latest middleware-to-proxy .
```

## What Matters Here

- **Secret must be 32+ chars** - Weak secrets = broken auth
- **Database schema must match your plugins** - CLI generates it: `npx @better-auth/cli generate`
- **Session cookies require headers** - Server-side: `auth.api.getSession({ headers: await headers() })`
- **Email functions are YOUR responsibility** - better-auth calls them, you implement sending

## Required Clarifications

Before implementing, clarify:

1. **Which auth methods?** (email/password, social, magic link, passkey)
2. **Which database adapter?** (Prisma, Drizzle, or built-in Kysely)
3. **Which social providers?** (Google, GitHub, Discord, etc.)
4. **Need 2FA?** (TOTP authenticator apps)
5. **Email provider?** (Resend, SendGrid, Nodemailer, etc.)

## Fastest Correct Path

```
1. Install: npm install better-auth
2. Create lib/auth.ts (server config)
3. Create lib/auth-client.ts (client config)
4. Create app/api/auth/[...all]/route.ts
5. Run: npx @better-auth/cli generate
6. Run: npx prisma db push (or drizzle equivalent)
7. Add proxy.ts for route protection (Next.js 16)
8. Build your custom UI forms
```

## What Can Go Wrong

| Problem | Cause | Fix |
|---------|-------|-----|
| "Invalid secret" | AUTH_SECRET < 32 chars | Generate: `openssl rand -base64 32` |
| Session always null | Missing headers in getSession | Pass `headers: await headers()` |
| DB errors on auth | Schema mismatch | Re-run `npx @better-auth/cli generate` |
| OAuth callback fails | Wrong redirectURI | Must match provider console exactly |
| `headers()` type error | Not awaited | Use `await headers()` in Next.js 16 |
| `params` type error | Not awaited | Use `await params` in Next.js 16 |
| Proxy not working | Wrong filename/export | Use `proxy.ts` with `export function proxy` |

## How Do I Know I'm Done?

- [ ] `AUTH_SECRET` is 32+ chars in `.env.local`
- [ ] `AUTH_URL` matches your domain (http://localhost:3000 for dev)
- [ ] Database tables created (user, session, account, verification)
- [ ] `/api/auth/session` returns session data when logged in
- [ ] Protected routes redirect to login when unauthenticated
- [ ] Email verification works (if enabled)
- [ ] Social login redirects correctly (if enabled)

## Must Follow

- Store ALL secrets in environment variables
- Use `auth.api.getSession()` server-side, NOT client methods
- Always run CLI generate after adding plugins
- Enable email verification for production
- Use HTTPS in production (required for secure cookies)
- Use `proxy.ts` for route protection in Next.js 16

## Must Avoid

- Hardcoding secrets in source code
- Using edge runtime in `proxy.ts` (not supported)
- Skipping email verification in production
- Calling `authClient.getSession()` in server components
- Manual schema creation (use CLI instead)
- Forgetting `await` on `headers()`, `params`, `searchParams`

## Reference Files

| File | When to Read |
|------|--------------|
| [01-installation-and-setup.md](./references/01-installation-and-setup.md) | Starting fresh |
| [02-nextjs-integration.md](./references/02-nextjs-integration.md) | API routes, proxy.ts |
| [03-database-adapters.md](./references/03-database-adapters.md) | Prisma/Drizzle setup |
| [04-auth-methods-email-password.md](./references/04-auth-methods-email-password.md) | Email/password auth |
| [05-auth-methods-social-logins.md](./references/05-auth-methods-social-logins.md) | OAuth providers |
| [06-auth-methods-magic-links.md](./references/06-auth-methods-magic-links.md) | Passwordless email |
| [07-auth-methods-passkeys.md](./references/07-auth-methods-passkeys.md) | WebAuthn/passkeys |
| [08-advanced-2fa.md](./references/08-advanced-2fa.md) | Two-factor auth |
| [09-session-management.md](./references/09-session-management.md) | Server/client sessions |
| [10-feature-password-reset.md](./references/10-feature-password-reset.md) | Password reset flow |
| [11-integration-email-service.md](./references/11-integration-email-service.md) | Email sending setup |

## Official Documentation

| Resource | URL |
|----------|-----|
| Official Docs | https://www.better-auth.com/docs |
| Installation | https://www.better-auth.com/docs/installation |
| Next.js Guide | https://www.better-auth.com/docs/integrations/next |
| Database | https://www.better-auth.com/docs/concepts/database |
| Plugins | https://www.better-auth.com/docs/plugins |

## Quick Start Commands

```bash
# Install
npm install better-auth

# Generate schema (after configuring auth.ts)
npx @better-auth/cli generate

# Push to database (Prisma)
npx prisma db push

# Push to database (Drizzle)
npx drizzle-kit generate && npx drizzle-kit migrate

# Migrate middleware to proxy (Next.js 16)
npx @next/codemod@latest middleware-to-proxy .
```
