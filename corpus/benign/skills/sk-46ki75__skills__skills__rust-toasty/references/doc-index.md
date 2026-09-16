# Toasty Documentation Index

One-line summary of every reference file shipped with the `rust-toasty`
skill. All paths are relative to `skills/rust-toasty/references/`. Source of
truth lives in `submodules/toasty/docs/` — these are curated copies, kept in
sync with the submodule revision pinned at the repo root (Toasty 0.7.0).

## User guide (`guide/`)

### Foundations

| Path | Topic |
| ---- | ----- |
| `guide/introduction.md` | What Toasty is, design goals, SQL + NoSQL story |
| `guide/getting-started.md` | First project: `Cargo.toml`, `Db::builder`, hello-toasty |
| `guide/defining-models.md` | `#[derive(toasty::Model)]`, supported field types, `Option<T>` |
| `guide/keys-and-auto-generation.md` | `#[key]`, `#[auto]`, composite keys, UUID vs auto-increment |

### CRUD

| Path | Topic |
| ---- | ----- |
| `guide/creating-records.md` | `toasty::create!`, nested creates, default values |
| `guide/querying-records.md` | `find_by_*`, `filter_*`, returning `Option` vs error |
| `guide/updating-records.md` | `toasty::update!`, partial updates, `increment` / `add` / `subtract` ops |
| `guide/deleting-records.md` | `delete()`, cascading semantics per driver |

### Schema features

| Path | Topic |
| ---- | ----- |
| `guide/indexes-and-unique-constraints.md` | `#[index]`, `#[unique]`, composite indexes |
| `guide/field-options.md` | All attributes, defaults, nullability, `toasty::Json<T>` wrapper |
| `guide/vec-scalar-fields.md` | `Vec<T>` for scalars — array on Postgres, JSON elsewhere, list on DynamoDB |

### Relationships

| Path | Topic |
| ---- | ----- |
| `guide/relationships.md` | Overview: relation kinds, ownership, key direction, eager vs `Deferred<T>` |
| `guide/belongs-to.md` | `#[belongs_to(key=…, references=…)]`, FK on the child side |
| `guide/has-many.md` | `#[has_many]`, eager `Vec<T>` vs lazy `Deferred<Vec<T>>`, multi-step `via` |
| `guide/has-one.md` | `#[has_one]`, when to use vs `BelongsTo`, multi-step `via` |
| `guide/preloading-associations.md` | Eager loading / `include`, avoiding N+1 |

### Advanced queries

| Path | Topic |
| ---- | ----- |
| `guide/filtering-with-expressions.md` | `eq`, `gt`, `in`, `like` / `ilike` / `starts_with`, boolean combinators |
| `guide/sorting-limits-and-pagination.md` | `order_by`, `limit`, cursor-style pagination |
| `guide/raw-sql.md` | `toasty::sql::statement` / `toasty::sql::query` for unsupported SQL features |

### Advanced features

| Path | Topic |
| ---- | ----- |
| `guide/embedded-types.md` | `#[derive(toasty::Embed)]`, flattening into parent columns |
| `guide/deferred-fields.md` | `Deferred<T>` wrapper for lazy column / relation loading |
| `guide/batch-operations.md` | Bulk inserts, batched lookups |
| `guide/transactions.md` | `db.transaction()`, isolation, driver differences |
| `guide/concurrency-control.md` | Optimistic concurrency, `#[version]` columns |
| `guide/tracing.md` | `tracing` events, viewing executed SQL via `RUST_LOG=toasty=debug` |

### Database admin

| Path | Topic |
| ---- | ----- |
| `guide/database-setup.md` | Connecting `Db` to a backend, connection strings, pool config |
| `guide/schema-management.md` | Creating tables, migrations, `schema::diff::Schema` |

### Database backends

| Path | Topic |
| ---- | ----- |
| `guide/postgresql.md` | PostgreSQL driver setup, type mappings, quirks, attribute→DDL cheat-sheet |
| `guide/mysql.md` | MySQL driver setup, type mappings, quirks |
| `guide/sqlite.md` | SQLite driver setup, `TransactionMode`, type mappings, quirks |
| `guide/turso.md` | Turso driver: SQLite-compatible engine with MVCC concurrent writes |
| `guide/dynamodb.md` | DynamoDB driver setup, primary key model, query vs scan |
| `guide/aurora-dsql.md` | Amazon Aurora DSQL: constraints, IAM auth, OCC retry, patterns |
| `guide/custom-driver.md` | Writing a custom `Driver` (IAM auth, dynamic creds, custom test harness) |

## Developer docs (`dev/`)

### Architecture

| Path | Topic |
| ---- | ----- |
| `dev/README.md` | Contributor onboarding, where things live |
| `dev/architecture/README.md` | High-level architecture overview, crate map |
| `dev/architecture/path-system.md` | Field references, typed/untyped layers, variant paths |
| `dev/architecture/query-engine.md` | v0.6 snapshot — full pipeline: AST → simplify → lower → plan → exec |
| `dev/architecture/type-system.md` | v0.6 snapshot — type system design, app/db schema mapping |

### Design proposals

| Path | Topic |
| ---- | ----- |
| `dev/design/README.md` | Index of active design proposals |
| `dev/design/_template.md` | Template for new proposals |
| `dev/design/column-projection.md` | Projecting a subset of columns |
| `dev/design/document-fields.md` | JSON / document column support |
| `dev/design/include-filters.md` | Filter expressions on `.include()` paths |
| `dev/design/lower-then-simplify.md` | Pipeline reorder: lower before simplify |
| `dev/design/retry-safe-recovery.md` | Transparent recovery from lost connections |
| `dev/design/static-assertions-create-macro.md` | Compile-time checks in `create!` |
| `dev/design/static-sql-values.md` | Reusable static SQL value literals |
| `dev/design/update-macro.md` | `toasty::update!` macro design |

### Roadmap

| Path | Topic |
| ---- | ----- |
| `dev/roadmap.md` | Prioritized planned features (composite keys, FK, migrations, JSON) |
