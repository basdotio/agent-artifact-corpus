---
name: database-schema
description: This skill should be used when modifying the database schema, running Prisma migrations, querying the database with Prisma ORM, or working with PostgreSQL in the ClaudeCode Sentiment Monitor project. Specifically trigger this skill for tasks involving schema changes, migrations, Prisma client operations, or database structure questions.
---

# Database Schema

## Overview

Guide for working with the PostgreSQL database and Prisma ORM in the ClaudeCode Sentiment Monitor project. Handle schema modifications, migrations, and database queries with project-specific patterns.

## When to Use This Skill

Use this skill when:
- Adding, modifying, or removing database tables or fields
- Running Prisma migrations or generating the Prisma client
- Writing database queries with Prisma ORM
- Understanding the current schema structure
- Troubleshooting database-related issues
- Setting up the database for the first time

## Critical Path Configuration

**This project uses a non-standard Prisma schema location:**

- Schema file: `app/app/prisma/schema.prisma`
- Generated client: `app/app/generated/prisma/`
- **Always** import from: `@/generated/prisma/client`
- **Never** import from: `@prisma/client`

All Prisma commands **must** include `--schema=app/prisma/schema.prisma` flag.

## Quick Start

### Helper Scripts

Use the bundled scripts for common operations:

```bash
# Run migrations (from project root)
.claude/skills/database-schema/scripts/prisma_migrate.sh dev --name add_new_field
.claude/skills/database-schema/scripts/prisma_migrate.sh deploy
.claude/skills/database-schema/scripts/prisma_migrate.sh status

# Generate Prisma client
.claude/skills/database-schema/scripts/prisma_generate.sh

# Open Prisma Studio (database GUI)
.claude/skills/database-schema/scripts/prisma_studio.sh
```

### Manual Commands

When not using scripts, always use the correct schema path:

```bash
cd app

# Create and apply migration
npx prisma migrate dev --name add_field --schema=app/prisma/schema.prisma

# Generate Prisma client
npx prisma generate --schema=app/prisma/schema.prisma

# Open database GUI
npx prisma studio --schema=app/prisma/schema.prisma

# Check migration status
npx prisma migrate status --schema=app/prisma/schema.prisma
```

## Schema Structure

Review `references/current-schema.md` for complete schema documentation including:
- All 4 tables (RawPost, RawComment, SentimentResult, DailyAggregate)
- Field definitions and types
- Relationships and cascade behaviors
- Indexes and constraints
- Common query patterns
- Migration history

## Working with the Schema

### Creating a Migration

**Step-by-step process:**

1. Edit the schema file: `app/app/prisma/schema.prisma`
2. Create migration using the script:
   ```bash
   .claude/skills/database-schema/scripts/prisma_migrate.sh dev --name descriptive_name
   ```
3. Generate Prisma client:
   ```bash
   .claude/skills/database-schema/scripts/prisma_generate.sh
   ```
4. Update TypeScript types in service layer if needed
5. Test locally before committing

**Migration naming conventions:**
- `add_field_name` - Adding a new field
- `create_table_name` - Creating a new table
- `add_index_field` - Adding an index
- `rename_old_to_new` - Renaming a field (may require manual SQL)

### Schema Best Practices

Follow these patterns when modifying the schema:

```prisma
model ExampleModel {
  // 1. Primary key first
  id String @id @default(cuid())

  // 2. Required fields
  requiredField String
  createdAt     DateTime @default(now())

  // 3. Optional fields
  optionalField String?
  updatedAt     DateTime @updatedAt

  // 4. Relations
  relatedModel RelatedModel? @relation(fields: [relatedModelId], references: [id])
  relatedModelId String?

  // 5. Indexes and constraints
  @@index([fieldName])
  @@unique([field1, field2])
  @@map("snake_case_table_name")
}
```

**Naming conventions:**
- Prisma models/fields: camelCase
- Database tables/columns: snake_case (use `@map`)
- Use `@@map("table_name")` for all models

### Common Prisma Patterns

#### Singleton Client
```typescript
// lib/prisma.ts (already exists)
import { PrismaClient } from "@/generated/prisma/client";

const prisma = new PrismaClient({
  log: process.env.NODE_ENV === "development"
    ? ["query", "error"]
    : ["error"],
});
```

#### Upsert Pattern (Idempotent Updates)
```typescript
// Update mutable fields on conflict
await prisma.rawPost.upsert({
  where: { id: post.id },
  create: {
    // All fields
    id: post.id,
    subreddit: post.subreddit,
    // ...
  },
  update: {
    // Only mutable fields
    score: post.score,
    numComments: post.numComments,
  },
});
```

#### Fetching with Relations
```typescript
// Avoid N+1 queries - use include
const posts = await prisma.rawPost.findMany({
  where: { subreddit: "ClaudeAI" },
  include: {
    sentiment: true,
    comments: true,
  },
  orderBy: { createdAt: "desc" },
  take: 50,
});
```

#### Transactions
```typescript
// Multi-step operations
await prisma.$transaction(async (tx) => {
  const post = await tx.rawPost.create({ data: { /* ... */ } });
  const sentiment = await tx.sentimentResult.create({ data: { /* ... */ } });
  const aggregate = await tx.dailyAggregate.upsert({ /* ... */ });
  return { post, sentiment, aggregate };
});
```

## Index Optimization

**Current indexes** (see `references/current-schema.md` for details):
- `raw_posts`: `[subreddit, createdAt]`, `[createdAt]`
- `raw_comments`: `[postId]`, `[subreddit, createdAt]`
- `sentiment_results`: `[itemType, analyzedAt]`, `[cacheKey]`
- `daily_aggregates`: `[subreddit, date]`, `[date]`

**When to add indexes:**
- Fields used in `where` clauses frequently
- Fields used in `orderBy`
- Foreign keys (Prisma doesn't auto-index)
- Composite unique constraints

**Adding an index:**
```prisma
model Example {
  field1 String
  field2 String

  @@index([field1, field2]) // Composite index
}
```

## Environment Setup

Required in `app/.env.local`:

```bash
DATABASE_URL="postgresql://user:password@host:port/database?schema=public"
```

## Database Maintenance

### View Database (Prisma Studio)
```bash
.claude/skills/database-schema/scripts/prisma_studio.sh
# Opens GUI at http://localhost:5555
```

### Reset Database (Development Only)
```bash
.claude/skills/database-schema/scripts/prisma_migrate.sh reset
# WARNING: Deletes all data and re-runs migrations
```

### Check Migration Status
```bash
.claude/skills/database-schema/scripts/prisma_migrate.sh status
```

## Common Pitfalls

Avoid these mistakes:

1. **Forgetting --schema flag** - Always use `--schema=app/prisma/schema.prisma`
2. **Wrong import path** - Use `@/generated/prisma/client`, not `@prisma/client`
3. **Multiple PrismaClient instances** - Always use singleton pattern
4. **Skipping client generation** - Run `prisma generate` after schema changes
5. **Editing migrations manually** - Let Prisma generate them
6. **Missing indexes** - Add for frequently queried fields
7. **Using deleteMany carelessly** - No undo, consider soft deletes
8. **Ignoring N+1 queries** - Use `include` for relations
9. **Running from wrong directory** - Scripts expect project root
10. **Not testing migrations locally** - Always test before deploying

## Resources

- **Prisma Docs**: https://www.prisma.io/docs
- **Schema Reference**: https://www.prisma.io/docs/reference/api-reference/prisma-schema-reference
- **Prisma Client API**: https://www.prisma.io/docs/reference/api-reference/prisma-client-reference
- **Current Schema**: See `references/current-schema.md` in this skill

## Examples

See existing implementations:
- `app/app/prisma/schema.prisma` - Complete schema
- `app/lib/prisma.ts` - Prisma client singleton
- `app/lib/services/*.service.ts` - Query patterns in services
