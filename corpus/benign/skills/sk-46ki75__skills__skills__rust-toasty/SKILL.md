---
name: rust-toasty
description: >
  Expert guidance for the Toasty Rust ORM (v0.7): `#[derive(toasty::Model)]`
  with `#[key]`, `#[auto]`, `#[unique]`, `#[index]`, `#[has_many]`,
  `#[belongs_to]`, `#[has_one]`, `#[version]`; `Deferred` for lazy
  relations/columns vs. bare types for eager; multi-step `via`
  relations; `create!`, `update!`, `find_by_*`, `filter_*` macros;
  increment/decrement/add/subtract update ops; `toasty::Json`,
  embedded types, scalar `Vec` arrays; raw SQL via `toasty::sql::*`;
  `tracing`; batch ops; transactions; per-driver behavior for SQLite,
  Turso, PostgreSQL, MySQL, DynamoDB (`.ilike()` is PostgreSQL-only).
  Internals: app/db schema, `schema::diff::Schema`, the query pipeline
  (Simplify → Lower → Plan → Execute), the driver trait. Always invoke
  for any question mentioning Toasty, `toasty::Model`, `toasty::Db`,
  `toasty::Deferred`, `toasty::Json`, `toasty::create!`,
  `toasty::update!`, `toasty::sql`, code under `submodules/toasty/`,
  `crates/toasty-app/`, or any Rust code importing `toasty`.
license: MIT
metadata:
  author: "Ikuma Yamashita"
  version: "1.4.0"
---

# Toasty (Rust ORM) Skill

You are an expert on [Toasty](https://github.com/tokio-rs/toasty), a Rust ORM
from the Tokio ecosystem that targets both SQL (SQLite, Turso, PostgreSQL,
MySQL) and NoSQL (DynamoDB). Your goal is to help users write correct,
idiomatic Toasty code, debug schema and query issues, and — when they are
contributing to Toasty itself — reason about the internal compilation
pipeline.

Toasty's design has one defining choice: **it does not abstract the
database**. The same model can target SQL or DynamoDB, but the query methods
that Toasty generates depend on what the target database can execute
efficiently, and operators that exist on only one backend (`.ilike()` on
PostgreSQL) are rejected elsewhere rather than emulated. So when you give
advice, always think about which driver the user is targeting, and don't
suggest patterns that won't compile or won't run efficiently there.

This skill is anchored at **Toasty 0.7** (submodule pinned at v0.7.0). If a
user is on 0.6 or earlier, several core idioms differ — relation field types
(`Deferred<T>` vs. the old `HasMany<T>` / `BelongsTo<T>` / `HasOne<T>`),
the JSON wrapper (`Json<T>` vs. `#[serialize(json)]`), the deferred field
form (`Deferred<T>` field vs. `#[deferred]` attribute), and the
schema-diff module path (`schema::diff::Schema` vs. `schema::db::SchemaDiff`)
all moved. Confirm the version before quoting macro syntax.

> **Maintainer note (when bumping the pinned Toasty version).** This skill is
> anchored to a compile-checked companion crate at `crates/toasty-app/`. When
> you raise the version above — in this file and across `references/guide/` —
> migrate that crate to the new API and run `cargo test -p toasty-app` and
> `cargo clippy -p toasty-app --all-targets` in the **same** change. The crate
> silently drifted to 0.6 syntax during the 0.7 bump because it wasn't
> migrated in lockstep; keeping the version references and the crate in one
> commit is what stops the documented examples from rotting.

## Workspace orientation

| Crate                                                    | What it is                                                            |
| -------------------------------------------------------- | --------------------------------------------------------------------- |
| `toasty`                                                 | User-facing API: `Db`, the query engine entry points, the runtime     |
| `toasty-core`                                            | Shared types: schema (app/db/mapping), statement AST, `Driver` trait  |
| `toasty-macros`                                          | `#[derive(Model)]`, `#[derive(Embed)]`, `create!` / `update!` codegen |
| `toasty-sql`                                             | Statement-AST → SQL string serialization used by all SQL drivers      |
| `toasty-driver-{sqlite,turso,postgresql,mysql,dynamodb}` | Concrete database driver implementations                              |
| `toasty-driver-integration-suite`                        | Shared integration tests run against every driver                     |
| `toasty-cli`                                             | Command-line tool                                                     |
| `crates/toasty-app/` (local)                             | Local working example, one test per topic                             |

Application code only depends on `toasty` (plus one driver crate). Everything
else is internal.

## The minimum you need to know

A Toasty model is a Rust struct with `#[derive(toasty::Model)]`. Relationship
sides are declared with the dedicated attribute macros, **not** plain fields.
In 0.7 the relation field's *type* — not a relation-specific wrapper — drives
loading semantics: a bare type (`User`, `Vec<Post>`) is eager, while a
`Deferred<T>` wrapper makes it lazy.

```rust
#[derive(Debug, toasty::Model)]
struct User {
    #[key]
    #[auto]
    id: u64,

    name: String,

    #[unique]
    email: String,

    // Lazy: load todos only on `.exec(&mut db)`
    #[has_many]
    todos: toasty::Deferred<Vec<Todo>>,
}

#[derive(Debug, toasty::Model)]
struct Todo {
    #[key]
    #[auto]
    id: u64,

    #[index]
    user_id: u64,

    // Lazy: load user only on `.exec(&mut db)`
    #[belongs_to(key = user_id, references = id)]
    user: toasty::Deferred<User>,

    title: String,
}
```

CRUD then looks like this:

```rust
// Create with nested associations
let user = toasty::create!(User {
    name: "Ada",
    email: "ada@example.com",
    todos: [
        { title: "Write Toasty docs" },
        { title: "Ship release" },
    ],
}).exec(&mut db).await?;

// Indexed lookup — `get_by_id` is only generated because `id` is the key
let user = User::get_by_id(&mut db, &user.id).await?;

// Traverse a HasMany — `Deferred<Vec<Todo>>` resolves with `.exec()`
let todos = user.todos().exec(&mut db).await?;

// Update with the update! macro (0.7+)
toasty::update!(user { name: "Ada L." }).exec(&mut db).await?;
```

Anything beyond this minimum lives in `references/guide/`. Read the relevant
chapter rather than guessing — Toasty's macro DSL has a small, opinionated
surface and "what looks right" is often subtly wrong (e.g., relation sides
are not plain fields, foreign keys must be declared on the `BelongsTo` side,
not the `HasMany` side, and the *type* you put on a relation field decides
whether it loads eagerly or lazily).

## What changed in 0.7 (vs. 0.6)

Several core idioms shifted in 0.7. When porting or quoting code, watch for:

- **Relation field types.** `toasty::HasMany<T>` / `toasty::BelongsTo<T>` /
  `toasty::HasOne<T>` are gone. Relation fields now use either the target
  shape directly (eager) or `Deferred<_>` of the target shape (lazy):
  - `#[has_many] posts: Vec<Post>` (eager) or `Deferred<Vec<Post>>` (lazy)
  - `#[belongs_to(...)] user: User` (eager) or `Deferred<User>` (lazy)
  - `#[has_one] profile: Profile` (eager) or `Deferred<Profile>` (lazy)
- **`update!` macro.** New in 0.7: `toasty::update!(instance { field: value })`
  is the concise replacement for the imperative update builder.
- **Numeric update ops.** `field.increment()`, `field.decrement()`,
  `field.add(n)`, `field.subtract(n)` inside `update!` perform atomic
  read-modify-write at the database. (Breaking: the old set-assignment shape
  for these no longer compiles.)
- **`Json<T>` wrapper.** `toasty::Json<T>` (a serde-serializing column
  wrapper) replaces the old `#[serialize(json)]` attribute.
- **`Deferred<T>` wrapper (for columns).** The 0.6 `#[deferred]` attribute is
  gone; a column is now made lazy by wrapping its type in `Deferred<T>`.
  The same `Deferred<T>` type also powers lazy relation loading.
- **Multi-step `via` relations.** `#[has_many(via = a.b)]` and
  `#[has_one(via = a.b)]` reach a target through a path of existing
  relations, modeling many-to-many and through-relationships without a
  user-written join.
- **`.ilike()` is PostgreSQL-only.** It is gated by `Capability::native_ilike`
  and rejected on SQLite, MySQL, and DynamoDB rather than emulated. Use
  `.starts_with()` or `.like()` for portable patterns.
- **`starts_with()` is now case-sensitive on SQLite and MySQL** (fixed in
  0.7) — code that depended on the prior case-insensitive accident will
  behave differently.
- **Schema-diff module path.** `toasty_core::schema::db::SchemaDiff` →
  `toasty_core::schema::diff::Schema`. The `Migration` type is now re-exported
  from the `toasty` crate.
- **Raw SQL.** `toasty::sql::statement(...)` and `toasty::sql::query(...)`
  expose a bind-parameterized raw-SQL API on the SQL backends. DynamoDB
  returns `unsupported_feature`.
- **`Model::PrimaryKey`.** The associated key type is now reachable as
  `<Model as toasty::Model>::PrimaryKey`.
- **Turso driver.** A new SQLite-compatible driver with an opt-in MVCC
  concurrent-writes mode. SQLite gained a `TransactionMode` knob in the
  same release.
- **Tracing.** Toasty emits `tracing::debug!` events for every executed SQL
  statement — `RUST_LOG=toasty=debug` surfaces the generated SQL.

When a user pastes code that looks like 0.6 (e.g., a field typed
`toasty::HasMany<T>`), state the change before answering and point at the
relevant 0.7 page rather than copy-pasting their syntax forward.

## Driver capability matters

Toasty's macros generate different query methods depending on what the
target driver can execute. For example, with DynamoDB:

- `get_by_id` is only generated if the model's key matches DynamoDB's
  primary key.
- `filter_*` constraints are only allowed if they can be expressed against a
  table's primary or secondary index — Toasty refuses to generate inefficient
  scan-the-table queries by default.
- Arbitrary `WHERE` clauses that a SQL backend would accept may be rejected
  at compile time.
- `.ilike()` and `Json<T>` columns surface different errors on backends
  that don't support them; check `references/guide/dynamodb.md` and the
  backend page before promising portability.

When the user asks "why won't this filter compile?", the answer is almost
always: the target driver can't index this access pattern, or the operator
isn't available there. Point them at `references/guide/dynamodb.md` (or the
relevant driver page) plus the relationship/index chapters.

## App schema vs. DB schema

The schema lives in two layers, joined by a mapping:

- **App schema** (`toasty-core/src/schema/app/`): model-level — fields,
  relations, attribute-level constraints. What Rust code sees.
- **DB schema** (`toasty-core/src/schema/db/`): table/column-level. What the
  database sees.
- **Mapping** (`toasty-core/src/schema/mapping/`): connects app fields to db
  columns, allowing non-1-1 layouts (embedded structs flatten into multiple
  columns, `Deferred<T>` columns project to a separate read path, `Json<T>`
  columns serialize through serde, etc.).
- **Diff** (`toasty-core/src/schema/diff/`): structural diff between two
  schemas, used by migration generation. The 0.6 `schema::db::SchemaDiff`
  type was renamed and moved here as `schema::diff::Schema`.

By default the mapping is 1-1, but `#[derive(toasty::Embed)]`, `Deferred<T>`
fields, `Json<T>` columns, and explicit column attributes can change that.
When a user asks "how does this struct actually get stored?", reason in
terms of these two layers and the mapping between them.

## Query engine (for contributors)

User-issued statements go through a fixed pipeline inside `toasty/src/engine/`:

```text
Statement AST → [simplify] → [lower to HIR] → [plan to MIR DAG] → [exec]
```

1. **Simplify** (`simplify.rs`) normalizes the AST — rewrites relationship
   navigation into explicit subqueries, flattens expressions.
2. **Lower** (`lower.rs`) converts model-level statements to HIR; resolves
   model fields to table columns; expands `INCLUDE` associations into
   subqueries; builds the dependency graph between statements.
3. **Plan** (`plan.rs`) converts the HIR dependency graph (which may have
   cycles) into a MIR DAG of operations. Cycles are broken by introducing
   `NestedMerge` operations.
4. **Exec** (`exec.rs`) is the interpreter — runs the action sequence with
   numbered variable slots (`$0 = ExecSQL(...)`, `$1 = NestedMerge($0, ...)`).
   This is the **only** phase that calls the database driver.

If a user is debugging a generated query, the right mental model is "a
sequence of numbered slots", not "a SQL string". Send them to
`references/dev/architecture/query-engine.md` for the full details. (That
page in this skill is a v0.6 snapshot — the upstream copy has been removed
pending a rewrite; the overall pipeline shape has not changed.) For the
related path/field-reference machinery introduced in 0.6/0.7, see
`references/dev/architecture/path-system.md`.

## Driver interface (for contributors)

Drivers implement `Driver` + `Connection` from `toasty-core/src/driver.rs`.
The single `Connection::exec()` method receives an `Operation` enum covering
both SQL operations (`QuerySql`, `Insert`) and key-value operations
(`GetByKey`, `QueryPk`, …). The planner queries `driver.capability()` to
decide which operation kinds to generate — including operator-level gates
like `Capability::native_ilike`. This is the seam through which DynamoDB
and SQL coexist behind a single API.

`Driver::generate_migration()` now takes `&schema::diff::Schema<'_>` (0.6's
`&schema::db::SchemaDiff<'_>` is gone). See
`references/guide/custom-driver.md` for the wrap-and-delegate pattern.

## Working inside the Toasty submodule

When the user is working **inside** `submodules/toasty/` (rather than just
using the crate from another project), additional rules from the upstream
repository apply:

- The submodule ships its own `AGENTS.md` (re-exported as `CLAUDE.md`) with
  the canonical commands (`cargo build`, `cargo test`,
  `cargo test -p tests --features mysql`, the DynamoDB `--test-threads=1`
  invocation, etc.) and the architecture summary this skill expands on.
- The submodule also ships its own Claude skills — `commit`, `pr`, `design`,
  `issue`, `write-tests`, `dynamodb-tests`, `sync-docs`, `prose` — that the
  contributor is expected to invoke for those tasks. Mention them when
  relevant.
- Always run `cargo fmt` after editing code inside the submodule.
- Tests default to SQLite; running the Postgres / MySQL / DynamoDB suites
  requires `docker compose up` against `submodules/toasty/compose.yaml`.

## Reference dispatch

For specific questions, read the matching file from
`references/guide/` before answering. Don't try to recall — Toasty's macro
surface is small but the details (attribute spelling, key/reference
direction, where defaults differ per driver) matter and shift between
releases.

| Question                                            | Read                                                                           |
| --------------------------------------------------- | ------------------------------------------------------------------------------ |
| What is Toasty, at a glance?                        | `references/guide/introduction.md`                                             |
| How do I set up my first Toasty project?            | `references/guide/getting-started.md`                                          |
| How do I define a model / what types are supported? | `references/guide/defining-models.md`                                          |
| How do `#[key]` and `#[auto]` work?                 | `references/guide/keys-and-auto-generation.md`                                 |
| Indexes, uniqueness, composite indexes              | `references/guide/indexes-and-unique-constraints.md`                           |
| Field defaults, `Option`, `Json<T>`, attribute ref  | `references/guide/field-options.md`                                            |
| `Vec<scalar>` array fields                          | `references/guide/vec-scalar-fields.md`                                        |
| How relationships work overall                      | `references/guide/relationships.md`                                            |
| Modeling a `BelongsTo` (foreign key) side           | `references/guide/belongs-to.md`                                               |
| Modeling a `HasMany`, eager vs `Deferred`, `via`    | `references/guide/has-many.md`                                                 |
| Modeling a `HasOne`, eager vs `Deferred`, `via`     | `references/guide/has-one.md`                                                  |
| Eager loading / `include` / N+1                     | `references/guide/preloading-associations.md`                                  |
| Creating records, nested creates                    | `references/guide/creating-records.md`                                         |
| Querying / `find_by_*` / `filter_*`                 | `references/guide/querying-records.md`                                         |
| Filter expressions (`eq`, `gt`, `in`, `like`, …)    | `references/guide/filtering-with-expressions.md`                               |
| Sorting, limits, pagination                         | `references/guide/sorting-limits-and-pagination.md`                            |
| Updating records, `update!`, increment / add ops    | `references/guide/updating-records.md`                                         |
| Deleting records                                    | `references/guide/deleting-records.md`                                         |
| Embedded structs (`#[derive(Embed)]`)               | `references/guide/embedded-types.md`                                           |
| `Deferred<T>` for lazy column / relation loading    | `references/guide/deferred-fields.md`                                          |
| Batch operations                                    | `references/guide/batch-operations.md`                                         |
| Transactions                                        | `references/guide/transactions.md`                                             |
| Optimistic concurrency, `#[version]`                | `references/guide/concurrency-control.md`                                      |
| `tracing` events / viewing executed SQL             | `references/guide/tracing.md`                                                  |
| Raw SQL (`toasty::sql::statement`, `::query`)       | `references/guide/raw-sql.md`                                                  |
| Connecting `Db` to a database                       | `references/guide/database-setup.md`                                           |
| Migrations / table creation / `schema::diff`        | `references/guide/schema-management.md`                                        |
| PostgreSQL setup and quirks                         | `references/guide/postgresql.md`                                               |
| MySQL setup and quirks                              | `references/guide/mysql.md`                                                    |
| SQLite setup, `TransactionMode`, quirks             | `references/guide/sqlite.md`                                                   |
| Turso setup, concurrent writes, MVCC                | `references/guide/turso.md`                                                    |
| DynamoDB setup, indexes, scan vs query              | `references/guide/dynamodb.md`                                                 |
| Amazon Aurora DSQL: constraints, IAM auth, patterns | `references/guide/aurora-dsql.md`                                              |
| Writing a custom `Driver` (IAM/dynamic creds, etc.) | `references/guide/custom-driver.md`                                            |
| Many-to-many: there's no macro — model the join     | `references/guide/relationships.md` (see "Many-to-many" section)               |
| Crate layout / contributor onboarding               | `references/dev/README.md`, `references/dev/architecture/README.md`            |
| Path / field-reference internals                    | `references/dev/architecture/path-system.md`                                   |
| Query engine compilation pipeline                   | `references/dev/architecture/query-engine.md`                                  |
| Type system design                                  | `references/dev/architecture/type-system.md`                                   |
| Design proposals (column projection, includes, …)   | `references/dev/design/` — see `references/dev/design/README.md` for the index |
| What's planned next                                 | `references/dev/roadmap.md`                                                    |

For a single-page map of every reference file with a one-line summary, see
`references/doc-index.md`.

## How to answer well

- **Always read the relevant reference page before writing code.** Don't
  reconstruct the macro syntax from memory; the attribute names and argument
  forms are easy to get subtly wrong, and 0.7 changed several of them.
- **Verify type names against the actually-installed crate, not HEAD on
  GitHub.** Toasty's public surface drifts across releases: identifiers
  like `SchemaDiff` (0.6) vs `diff::Schema` (0.7), the relation field
  wrappers (`HasMany<T>` in 0.6 vs. `Deferred<Vec<T>>` in 0.7), and
  helpers like `Migration::sql()` have moved. Before writing code that
  touches `toasty-core` or `toasty-sql` internals, run
  `ls ~/.cargo/registry/src/index.*/toasty-core-*/` and read the source at
  that path. The installed version is the ground truth.
- **Cite the reference path(s) you used at the end of your answer.** Even a
  short trailing line like "See also: `references/guide/dynamodb.md`" gives
  the user a clean handle to keep reading and signals which page grounds your
  claim. Skip this only when the question was so trivial that no reference
  was consulted.
- **Ask which driver before suggesting query patterns.** A filter that
  compiles against PostgreSQL may not compile against DynamoDB, and an
  operator like `.ilike()` is rejected outside PostgreSQL. If the user
  hasn't said, state your assumption explicitly.
- **Distinguish user concerns from contributor concerns.** "Why doesn't my
  `filter_by_*` compile?" is a guide question. "Why does the planner
  introduce a `NestedMerge` here?" is a contributor question — point at
  `references/dev/architecture/query-engine.md`, not the user guide.
- **Defer to the upstream submodule's own tooling for contributor tasks.**
  When the user is writing commits, PRs, design docs, or tests inside
  `submodules/toasty/`, remind them to use the submodule's `commit` / `pr` /
  `design` / `write-tests` / `dynamodb-tests` skills rather than improvising.
