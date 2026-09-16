# Toasty Developer Documentation

Documentation for contributors working on Toasty itself. For user-facing
documentation, see the [Toasty Guide](../guide/).

Start with [`CONTRIBUTING.md`](../../CONTRIBUTING.md) — it describes how
to propose changes and land PRs.

Docs built from the latest commit on `main`:

- [Nightly user guide](https://tokio-rs.github.io/toasty/nightly/guide/)
- [Nightly API docs](https://tokio-rs.github.io/toasty/nightly/api/)

## Architecture

High-level documentation of how Toasty is put together.

- [Architecture Overview](./architecture/README.md)
- [Path System](./architecture/path-system.md) — field references, typed/untyped layers, variant paths
- [Query Engine](./architecture/query-engine.md) — kept as a v0.6 snapshot; the upstream page has been removed pending a rewrite
- [Type System](./architecture/type-system.md) — kept as a v0.6 snapshot; the upstream page has been removed pending a rewrite

## Design Documents

Guide-level design documents for specific features. Use
[`_template.md`](./design/_template.md) when starting a new one.

- [Design Overview](./design/README.md)
- [Per-Call Column Projection](./design/column-projection.md)
- [Document and Collection Fields](./design/document-fields.md)
- [Include Filters](./design/include-filters.md)
- [Lower-Then-Simplify](./design/lower-then-simplify.md)
- [Retry-Safe Transparent Recovery](./design/retry-safe-recovery.md)
- [Static Assertions for `create!` Required Fields](./design/static-assertions-create-macro.md)
- [Static SQL Values](./design/static-sql-values.md)
- [`update!` Macro](./design/update-macro.md)

## Roadmap

- [Roadmap](./roadmap.md) — planned work and feature gaps

## Project

- [Commit Guidelines](./COMMITS.md)
- [GitHub Labels](./labels.md)
