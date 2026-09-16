# Migration Principles

> Safe migration strategy for zero-downtime changes.

## Safe Migration Strategy

```
For zero-downtime changes:
│
├── Adding column
│   └── Add as nullable → backfill → add NOT NULL
│
├── Removing column
│   └── Stop using → deploy → remove column
│
├── Adding index
│   └── CREATE INDEX CONCURRENTLY (non-blocking)
│
└── Renaming column
    └── Add new → migrate data → deploy → drop old
```

## Migration Philosophy

- Never make breaking changes in one step
- Test migrations on data copy first
- Have rollback plan
- Run in transaction when possible
- For NextBlock production/shared databases, treat migrations as append-only:
  create a new migration file for each change and do not rewrite, squash,
  reorder, delete, or recycle existing migrations.
- Do not recommend reset/fresh/sandbox replay commands for any database that
  may contain orders, users, payments, or customer data.
- If Supabase reports old baseline migrations as pending on an existing
  database, repair the migration ledger instead of replaying baseline SQL:
  `npm run db:migrate:repair-history:check`, then
  `npm run db:migrate:repair-history`, then rerun
  `npm run db:migrate:check`.

## Serverless Databases

### Neon (Serverless PostgreSQL)

| Feature | Benefit |
|---------|---------|
| Scale to zero | Cost savings |
| Instant branching | Dev/preview |
| Full PostgreSQL | Compatibility |
| Autoscaling | Traffic handling |

### Turso (Edge SQLite)

| Feature | Benefit |
|---------|---------|
| Edge locations | Ultra-low latency |
| SQLite compatible | Simple |
| Generous free tier | Cost |
| Global distribution | Performance |
