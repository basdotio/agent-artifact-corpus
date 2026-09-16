---
name: database-management
description: When you need to modify the database schema, run migrations, or deploy Supabase changes. Use this for all SQL and Supabase-related tasks.
---

# Database Management (Supabase)

## 1. Core Workflow

- **Environment:** We use Supabase (PostgreSQL + Auth).
- **Local Config:** `supabase/config.toml` manages local settings.
- **Env Vars:** Ensure `.env.local` is populated with valid Supabase credentials.

## 2. Key Commands

- **Check Migrations:** `npm run db:migrate:check`
  - Dry-runs pending remote migrations. Run this before any live migration.
- **Push Migrations:** `npm run db:migrate` or `npm run db:push`
  - Applies pending migration files only.
  - It does not reset data, seed sandbox media, deploy functions, or push local Supabase config.
- **Repair Existing Baseline History:** `npm run db:migrate:repair-history:check`, then `npm run db:migrate:repair-history`
  - For existing production/shared databases whose schema already exists but whose Supabase migration ledger is missing old baseline versions.
  - Marks historical baseline migrations as applied without running their SQL.
- **Link Database:** `npm run db:link`
  - Links the local development environment to the remote Supabase project.
- **Generate Types:** `npm run db:types`
  - Generates TypeScript definitions from the database schema. **Run this after every schema change.**
- **Deploy:** `npm run deploy:supabase`
  - Deploys migrations and config (often used in CI/CD).

## 3. Schema Management

- **Migrations:** SQL migrations are located in `libs/db/src/supabase/migrations`.
- **Production Rule:** Always create a new append-only migration for production/shared database changes. Do not rewrite, squash, reorder, delete, or recycle existing migrations once they may have been applied to a real database.
- **Data Safety:** Never run or recommend `db:reset`, `sandbox:reset`, `db:push:sandbox`, or `db:migrate:fresh` against a production/shared database containing orders, users, payments, or customer data.
- **Fresh Databases Only:** `npm run db:migrate:fresh` is only for a brand-new empty database.
- **No Local Docker:** There is no local Supabase Docker instance. The user will usually push DB migrations manually via `npm run db:migrate`. Do not attempt to run mutating DB commands yourself unless explicitly asked and the target is confirmed.
- **Validation:** Always verify schema changes are syntactically correct SQL before leaving them for the user to push.

## 4. Troubleshooting

- **CSP/Connection Issues:** If the build fails to connect to Supabase, check the Content Security Policy (CSP) headers in `next.config.js` or `middleware.ts`.
- **Url Sync:** Ensure `NEXT_PUBLIC_URL` matches your `site_url` in Supabase config to prevent redirect issues with auth.
