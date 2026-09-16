# Writing a Custom Driver

Toasty's stock drivers (`toasty-driver-{sqlite,postgresql,mysql,dynamodb}`) cover
the common cases, but the `Driver` trait is public and you are free to
implement your own — either from scratch or by wrapping a stock driver. Common
reasons to need one:

- **Dynamic credentials** — IAM-issued tokens that rotate (Amazon Aurora DSQL,
  RDS IAM auth, GCP Cloud SQL IAM auth). Stock drivers bake the password into
  the URL at construction time, so the credential cannot be refreshed.
- **Custom auth plumbing** — Kerberos / GSSAPI, mutual TLS with rotating
  client certs, SSO-issued short-lived passwords.
- **Custom test harness** — record-and-replay of operations, fault injection,
  query allow-lists.
- **Custom logging or retry policies** beyond what the stock drivers provide.

This page covers the wrap-and-delegate pattern, which is the right answer in
almost all cases. Writing a fully-fresh driver is an order of magnitude more
work (you would also need to re-implement `toasty-sql` serialization, OID
caching, prepared-statement caching, etc.) and is only worth it if you are
targeting a database with no PostgreSQL / MySQL wire-protocol compatibility.

## The `Driver` trait surface

Live source: `toasty-core/src/driver.rs`. The shape an implementer needs to
satisfy (paraphrased):

```rust,ignore
#[async_trait]
pub trait Driver: Debug + Send + Sync + 'static {
    fn url(&self) -> Cow<'_, str>;
    fn capability(&self) -> &'static Capability;
    async fn connect(&self) -> Result<Box<dyn Connection>>;
    fn max_connections(&self) -> Option<usize> { None }
    fn generate_migration(&self, diff: &schema::diff::Schema<'_>) -> Migration;
    async fn reset_db(&self) -> Result<()>;
}
```

In Toasty 0.7, the schema-diff types live under
`toasty_core::schema::diff::*` — `diff::Schema` replaces what 0.6 called
`schema::db::SchemaDiff`. The example below still uses the 0.6 path;
update both the trait signature and the `generate_migration`
implementation to the new path when targeting 0.7.

Of these, `connect()` is the only method you typically need to override when
wrapping a stock driver. Everything else can be delegated to a "template"
instance of the wrapped driver.

`Capability` for the stock drivers is exposed as a `pub const`
(`Capability::POSTGRESQL`, `Capability::MYSQL`, `Capability::SQLITE`,
`Capability::DYNAMODB`) — you can return one of them directly, or build your
own if your wrapper genuinely changes what the planner can emit.

`reset_db` is a dev/test convenience that drops and recreates the database.
For backends without `CREATE DATABASE` / `DROP DATABASE` permission (DSQL,
many managed Postgres tiers) it cannot be implemented honestly — return an
error rather than silently doing nothing.

## Wrapping `PostgreSQL` to inject rotating credentials

This is the canonical pattern. `toasty_driver_postgresql::PostgreSQL::new(url)`
parses the URL once and stores a `tokio_postgres::Config` with the password
baked in. There is no callback hook on the driver, the builder, or the
pool to refresh that password. The trick: build a *fresh* `PostgreSQL`
inside `Driver::connect()` each time the pool asks for a new connection.

Existing connections in the pool keep working — authentication happens once
at TLS handshake, so a connection's token validity doesn't matter after the
handshake. Only *new* connects need a freshly-minted token.

### Sketch

```rust,ignore
use std::borrow::Cow;
use std::sync::Arc;
use async_trait::async_trait;
use toasty_core::Result;
use toasty_core::driver::{Capability, Connection, Driver};
use toasty_driver_postgresql::PostgreSQL;

pub struct DynamicCredsDriver {
    hostname: String,
    user: String,
    dbname: String,
    creds_provider: Arc<MyCredsProvider>, // your code
    /// A `PostgreSQL` built once with a placeholder password — used only
    /// for the non-`connect` `Driver` methods (`capability`,
    /// `generate_migration`). Its baked-in password is never used for a
    /// real connection.
    template: Arc<PostgreSQL>,
}

#[async_trait]
impl Driver for DynamicCredsDriver {
    fn url(&self) -> Cow<'_, str> {
        Cow::Owned(format!("custom://{}/{}", self.hostname, self.dbname))
    }

    fn capability(&self) -> &'static Capability {
        self.template.capability()
    }

    async fn connect(&self) -> Result<Box<dyn Connection>> {
        let password = self.creds_provider.mint().await?;
        let encoded: String =
            url::form_urlencoded::byte_serialize(password.as_bytes()).collect();
        let url = format!(
            "postgresql://{u}:{p}@{h}/{d}?sslmode=verify-full",
            u = self.user, p = encoded, h = self.hostname, d = self.dbname,
        );
        let pg = PostgreSQL::new(url)?;
        pg.connect().await
    }

    fn generate_migration(
        &self,
        diff: &toasty_core::schema::diff::Schema<'_>,
    ) -> toasty_core::schema::db::Migration {
        self.template.generate_migration(diff)
    }

    async fn reset_db(&self) -> Result<()> {
        Err(/* not supported */)
    }
}
```

Two details worth lingering on:

**Percent-encode the password.** IAM-issued tokens routinely contain `=`,
`&`, `?`, `%`, `+` — characters that break URL parsing in the password
slot. Always `url::form_urlencoded::byte_serialize`, even if today's tokens
happen to be safe.

**Use a template, not `Default`.** `PostgreSQL` cannot be constructed
without parsing a URL, so build one with a placeholder password at startup
and keep an `Arc<PostgreSQL>` to delegate the non-`connect` `Driver`
methods to. Its baked-in password is never used because no real `.connect()`
goes through it.

## Wiring the driver into `Db`

```rust,ignore
let driver = DynamicCredsDriver::new(...).await?;
let db = toasty::Db::builder()
    .models(toasty::models!(crate::*))
    .build(driver)
    .await?;
```

`Db::builder().build(impl Driver)` is the entry point for custom drivers
(versus `.connect(url)` which dispatches based on URL scheme). See
`references/guide/database-setup.md` for the rest of the builder surface.

## Error wrapping: the `!Sized` trap

`toasty_core::Error::driver_operation_failed` takes
`impl std::error::Error + Send + Sync + 'static`. This bound implicitly
requires `Sized`. Several common error types from external crates do **not**
satisfy it directly:

- `Box<dyn std::error::Error + Send + Sync>` — what most AWS SDK fallible
  calls return as `BoxError`.
- `anyhow::Error` — does not implement `std::error::Error`.

Both compile-fail with the cryptic message *"the size for values of type
`dyn std::error::Error + Send + Sync` cannot be known at compilation time"*.
Fix it with a one-line newtype:

```rust,ignore
#[derive(Debug)]
struct DriverError(String);

impl std::fmt::Display for DriverError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}
impl std::error::Error for DriverError {}

fn wrap<E: std::fmt::Display>(e: E) -> toasty_core::Error {
    toasty_core::Error::driver_operation_failed(DriverError(e.to_string()))
}
```

## Connection pool interaction

The pool calls `Driver::connect()` whenever it needs a fresh slot — on
startup (to validate the builder), on cache miss when no idle connection is
available, and after a `connection_lost` eviction. It does **not** call it
to renew an existing connection. Implications:

- A token-rotating driver is automatically correct: every pool slot is born
  with a fresh token.
- A connection that outlives its token's TTL still works — only the next
  *new* connect needs a fresh token.
- If you enable `pool_pre_ping(true)` or aggressive
  `pool_health_check_interval`, you'll mint more tokens. Token minting
  is cheap (no network — pure HMAC), but the AWS credentials provider
  may itself be cached or rate-limited; tune accordingly.

For pool knobs and recovery semantics, see
`references/guide/database-setup.md#connection-pool`.

## Verifying your driver against the installed crate version

The `Driver` trait shape **has changed between Toasty releases**. The
agent-investigation common mistake is to read HEAD on GitHub and write code
that doesn't compile against the version on crates.io. Before implementing,
verify the trait surface against the actually-installed source:

```bash
ls ~/.cargo/registry/src/index.*/toasty-core-*/src/driver.rs
```

Read that file, not the GitHub `main` branch. The schema-diff types in
particular have moved across point releases (`schema::db::SchemaDiff` in
0.6 → `schema::diff::Schema` in 0.7), and `Migration` exposure was
reorganized in the same window — the installed source is the truth.

## See also

- `references/guide/database-setup.md` — connection pool, `Db::builder`
- `references/guide/aurora-dsql.md` — full worked example: DSQL via
  IAM-token rotation, plus DSQL-specific DDL constraints
- `references/dev/architecture/query-engine.md` — what `Operation`s the
  planner will hand to your `Connection::exec()` if you implement that too
