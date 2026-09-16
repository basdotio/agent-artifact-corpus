# Database Adapters

## What Matters

- Use CLI to generate schema: `npx @better-auth/cli generate`
- Never manually create tables - CLI ensures schema matches your plugins
- Re-run CLI after adding any plugin

## Prisma Setup

### 1. Install

```bash
npm install prisma @prisma/client -D
npm install @prisma/client
```

### 2. Initialize Prisma

```bash
npx prisma init
```

### 3. Configure datasource

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// Don't add models manually - CLI will generate them
```

### 4. Configure adapter in auth.ts

```typescript
import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

export const auth = betterAuth({
  database: prismaAdapter(prisma, {
    provider: "postgresql", // or "mysql", "sqlite"
  }),
  // ... other config
});
```

### 5. Generate schema and push

```bash
npx @better-auth/cli generate
npx prisma db push
```

## Drizzle Setup

### 1. Install

```bash
npm install drizzle-orm postgres
npm install drizzle-kit -D
```

### 2. Configure adapter

```typescript
import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

const client = postgres(process.env.DATABASE_URL!);
const db = drizzle(client, { schema });

export const auth = betterAuth({
  database: drizzleAdapter(db, {
    provider: "pg",
    schema: schema,
  }),
  // ... other config
});
```

### 3. Generate and migrate

```bash
npx @better-auth/cli generate
npx drizzle-kit generate
npx drizzle-kit migrate
```

## Core Tables Created

The CLI generates these tables:

| Table | Purpose |
|-------|---------|
| `user` | User accounts |
| `session` | Active sessions |
| `account` | OAuth provider links |
| `verification` | Email/password reset tokens |

Plugins add more tables (e.g., `twoFactor`, `passkey`).

## Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| Manual table creation | Schema mismatch errors | Always use CLI generate |
| Forgetting to regenerate | Missing plugin tables | Re-run CLI after adding plugins |
| Wrong provider string | Adapter errors | Prisma: "postgresql", Drizzle: "pg" |
