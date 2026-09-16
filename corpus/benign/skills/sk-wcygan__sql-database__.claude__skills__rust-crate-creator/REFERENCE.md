# Rust Crate Creator - Reference Guide

This document provides detailed reference material for creating new crates in the workspace.

## Workspace Dependency Management

### Core Principle

**All dependencies must be pinned at the workspace level, then referenced with `{ workspace = true }`.**

This ensures:
- Version consistency across all crates
- Single source of truth for dependency versions
- Easier updates (change once, applies everywhere)
- No version conflicts between workspace members

### Adding a New External Dependency

**Step 1:** Add to root `Cargo.toml`:
```toml
[workspace.dependencies]
new-dep = "1.2.3"
# or with features:
new-dep = { version = "1.2.3", features = ["feature1", "feature2"] }
```

**Step 2:** Reference in member crate:
```toml
[dependencies]
new-dep = { workspace = true }
```

### Adding a New Internal Dependency (Path Dependency)

**Step 1:** Add to workspace dependencies:
```toml
[workspace.dependencies]
my-new-crate = { path = "crates/my-new-crate" }
```

**Step 2:** Reference in other crates:
```toml
[dependencies]
my-new-crate = { workspace = true }
```

**Important:** Even path-only dependencies MUST use workspace references. This maintains consistency and allows for future feature flag management.

### Common Dependencies in This Workspace

**Serialization:**
- `serde` - Core serialization framework
- `serde_json` - JSON support
- `bincode` - Binary encoding (with `serde` feature)

**Data Structures:**
- `ahash` - Fast hashing
- `hashbrown` - High-performance HashMap (with `serde` feature)
- `uuid` - UUID generation (with `serde`, `v4` features)
- `bytes` - Byte buffer manipulation

**Error Handling:**
- `thiserror` - Derive macros for error types

**Testing:**
- `proptest` - Property-based testing
- `pretty_assertions` - Better assertion output
- `tempfile` - Temporary file/directory management

**Domain-Specific:**
- `sqlparser` - SQL parsing (Generic dialect)

**Internal:**
- `common` - Shared types, errors, utilities
- `types` - SQL value types and schemas
- `expr` - Expression evaluation

## Project Structure Standards

### Typical Crate Layout

```
crates/my-crate/
├── Cargo.toml              # Crate manifest (workspace deps only)
├── CLAUDE.md               # Integration guidelines for AI assistants
├── AGENTS.md               # Architecture guardrails
├── src/
│   ├── lib.rs             # Main entry point with module docs
│   ├── module1.rs         # Feature modules
│   ├── module2.rs
│   └── tests.rs           # Optional: centralized tests
└── tests/                  # Optional: integration tests
    └── integration.rs
```

### When to Use Each Testing Location

**In-module tests (`#[cfg(test)] mod tests`):**
- Unit tests for functions/types in the same file
- Testing private implementation details
- Fast, focused tests
- Example: `src/lib.rs` contains `mod tests` for functions in `lib.rs`

**Separate tests.rs:**
- When test code is substantial
- Shared test utilities
- Still has access to private items via `use super::*`
- Example: `crates/storage/src/tests.rs`

**Integration tests (`tests/` directory):**
- Testing public API only
- Cross-module integration
- Realistic usage scenarios
- Each file is a separate test binary

### File Naming Conventions

- **Modules:** `snake_case.rs` (e.g., `storage_backend.rs`)
- **Test files:** `tests.rs` or descriptive name (e.g., `heap_tests.rs`)
- **Integration tests:** Descriptive names (e.g., `catalog_persistence.rs`)

## Documentation Standards

### Module-Level Documentation

**Pattern 1: Educational focus (for library crates):**
```rust
//! Brief description of the crate's purpose.
//!
//! This crate provides X, Y, and Z for the SQL database.
//!
//! # Examples
//!
//! ```
//! use crate_name::TypeName;
//!
//! let value = TypeName::new();
//! value.operation();
//! ```
//!
//! # Architecture
//!
//! Key design decisions:
//! - Decision 1: rationale
//! - Decision 2: rationale
```

**Pattern 2: Service/implementation focus:**
```rust
//! Physical storage layer for heap tables.
//!
//! Provides fixed-size slotted pages, tuple encoding, and append-only heap files.
//! This is the only layer that directly interacts with the filesystem for table data.
```

### Type Documentation

**With examples:**
```rust
/// Identifier for a column within a table schema.
///
/// # Examples
///
/// ```
/// let id_col: ColumnId = 1;    // maps to "id"
/// let name_col: ColumnId = 2;  // maps to "name"
/// ```
pub type ColumnId = u64;
```

**For complex types:**
```rust
/// Persistent catalog storing table schemas and index metadata.
///
/// The catalog is the source of truth for all DDL operations. It:
/// - Assigns unique IDs to tables and indexes
/// - Validates identifier names
/// - Maintains lookup indexes for fast access
///
/// # Examples
///
/// ```
/// let mut catalog = Catalog::new();
/// let table_id = catalog.create_table("users", vec![
///     Column::new("id", SqlType::Integer),
///     Column::new("name", SqlType::Text),
/// ])?;
/// ```
///
/// # Serialization
///
/// Catalogs serialize to JSON via `save()` and load via `load()`.
pub struct Catalog { ... }
```

### Function Documentation

```rust
/// Creates a new table with the provided columns.
///
/// # Arguments
///
/// * `name` - Table name (must be lowercase, non-reserved)
/// * `columns` - Column definitions with names and types
///
/// # Returns
///
/// Returns the assigned `TableId` on success.
///
/// # Errors
///
/// Returns `DbError::Catalog` if:
/// - Table name is reserved or already exists
/// - Column names are invalid or duplicated
/// - Type validation fails
///
/// # Examples
///
/// ```
/// let table_id = catalog.create_table("users", vec![
///     Column::new("id", SqlType::Integer),
/// ])?;
/// ```
pub fn create_table(&mut self, name: &str, columns: Vec<Column>) -> DbResult<TableId> {
    // implementation
}
```

## Testing Patterns

### Unit Test Structure

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_descriptive_name() {
        // Arrange
        let input = setup_test_data();

        // Act
        let result = function_under_test(input);

        // Assert
        assert_eq!(result, expected);
    }

    #[test]
    fn test_error_condition() {
        let result = function_that_should_fail();

        assert!(result.is_err());
        // or more specific:
        assert!(matches!(result, Err(DbError::Catalog(_))));
    }
}
```

### Tempfile Pattern for Filesystem Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_file_persistence() {
        // Create temporary directory (automatically cleaned up)
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("test.db");

        // Write to file
        let mut storage = Storage::create(&file_path).unwrap();
        storage.write(data).unwrap();

        // Read back
        let loaded = Storage::open(&file_path).unwrap();
        assert_eq!(loaded.read(), expected);

        // Directory automatically deleted when `dir` drops
    }

    #[test]
    fn test_multiple_files() {
        let dir = tempdir().unwrap();

        // Create multiple test files in same directory
        let file1 = dir.path().join("data1.db");
        let file2 = dir.path().join("data2.db");

        // Use files...

        // All cleaned up automatically
    }
}
```

### Property-Based Testing

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn prop_roundtrip_preserves_data(data in any::<Vec<u8>>()) {
            let encoded = encode(&data);
            let decoded = decode(&encoded).unwrap();
            prop_assert_eq!(data, decoded);
        }

        #[test]
        fn prop_serialization_deterministic(value in 0..1000i32) {
            let bytes1 = serialize(value);
            let bytes2 = serialize(value);
            prop_assert_eq!(bytes1, bytes2);
        }

        #[test]
        fn prop_never_panics(input in ".*") {
            // Should not panic on any input
            let _ = parse(&input);
        }
    }
}
```

**Property test naming:** Prefix with `prop_` for clarity.

**Reproducing failures:** When proptest finds a failure, it outputs a seed:
```
Test failed: seed = [1, 2, 3, 4]
```

Reproduce with:
```rust
proptest! {
    #![proptest_config(ProptestConfig {
        rng_algorithm: RngAlgorithm::ChaCha,
        seed: [1, 2, 3, 4]  // from failure
    })]

    #[test]
    fn prop_test_name(...) { ... }
}
```

### Integration Test Example

```rust
// tests/catalog_integration.rs
use catalog::{Catalog, Column};
use common::DbError;
use types::SqlType;
use tempfile::tempdir;

#[test]
fn catalog_persistence_roundtrip() {
    let dir = tempdir().unwrap();
    let catalog_path = dir.path().join("catalog.json");

    // Create and populate catalog
    let mut catalog = Catalog::new();
    let table_id = catalog.create_table("users", vec![
        Column::new("id", SqlType::Integer),
        Column::new("name", SqlType::Text),
    ]).unwrap();

    // Save
    catalog.save(&catalog_path).unwrap();

    // Load fresh instance
    let loaded = Catalog::load(&catalog_path).unwrap();

    // Verify
    let table = loaded.table_by_id(table_id).unwrap();
    assert_eq!(table.name, "users");
    assert_eq!(table.columns().len(), 2);
}
```

## Common Error Handling Patterns

### Error Type Design

All errors use `common::DbError`:

```rust
pub enum DbError {
    Catalog(String),
    Parser(String),
    Storage(String),
    Io(std::io::Error),
    // ... other variants
}
```

**When to add a new variant:**
- New subsystem with distinct error conditions
- Clear categorization helps error handling
- Document in `common/src/lib.rs`

### Error Creation Patterns

```rust
// Format string for context
return Err(DbError::Catalog(format!("unknown table '{name}'")));

// Wrap IO errors
fs::read_to_string(path)
    .map_err(|e| DbError::Io(e))?;

// Or use From trait
fs::read_to_string(path)?;  // if From<io::Error> is implemented
```

### Error Propagation

```rust
pub fn operation() -> DbResult<T> {
    let step1 = substep_a()?;  // Propagate errors
    let step2 = substep_b(step1)?;
    Ok(step2)
}
```

## Serialization Patterns

### Bincode Configuration

The workspace uses `bincode 2.0.1` with a standardized configuration:

```rust
use bincode::config::{self, Config};
use bincode::serde::{decode_from_slice, encode_into_slice, encode_to_vec};

/// Returns the standard bincode configuration for this workspace.
///
/// Uses legacy format (little endian, fixed-width integers) for
/// compatibility across the database stack.
fn bincode_config() -> impl Config {
    config::legacy()
}

// Encoding to Vec
let bytes = encode_to_vec(&data, bincode_config())
    .map_err(|e| DbError::Storage(format!("encode failed: {e}")))?;

// Encoding into fixed buffer
let written = encode_into_slice(&data, &mut buffer, bincode_config())
    .map_err(|e| DbError::Storage(format!("encode failed: {e}")))?;

// Decoding
let (data, bytes_read) = decode_from_slice(&bytes, bincode_config())
    .map_err(|e| DbError::Storage(format!("decode failed: {e}")))?;
```

**Critical rules:**
- Always use `bincode::serde::*` (not the deprecated v1 API)
- Always use the same config (via `bincode_config()` helper)
- Handle errors by wrapping in appropriate `DbError` variant

### JSON Serialization (Catalog)

```rust
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct Catalog {
    tables: Vec<TableMeta>,

    // Skip runtime-only fields
    #[serde(skip)]
    #[serde(default)]
    table_name_index: HashMap<String, usize>,
}

impl Catalog {
    pub fn save(&self, path: &Path) -> DbResult<()> {
        let json = serde_json::to_string_pretty(self)
            .map_err(|e| DbError::Catalog(format!("serialize: {e}")))?;
        fs::write(path, json)?;
        Ok(())
    }

    pub fn load(path: &Path) -> DbResult<Self> {
        let json = fs::read_to_string(path)?;
        let mut catalog: Self = serde_json::from_str(&json)
            .map_err(|e| DbError::Catalog(format!("deserialize: {e}")))?;

        // Rebuild skipped indexes
        catalog.rebuild_indexes();
        Ok(catalog)
    }
}
```

## CLAUDE.md Template Variants

### For Data/Domain Crates (types, common)

Focus on:
- Educational value
- Reusability across workspace
- Clear type definitions
- Property-based testing

Example: `crates/types/CLAUDE.md`

### For Service Crates (storage, catalog)

Focus on:
- Integration contracts with other crates
- Persistence mechanisms
- API boundaries
- Extension points

Example: `crates/storage/CLAUDE.md`, `crates/catalog/CLAUDE.md`

### For Logic Crates (parser, expr)

Focus on:
- Input/output contracts
- Mapping between representations
- Supported feature subset
- Coordination with other layers

Example: `crates/parser/CLAUDE.md`

## AGENTS.md Best Practices

Purpose: Provide concise implementation guardrails for AI agents extending the crate.

**Key sections:**
1. **Purpose** - What the crate does (1-2 sentences per bullet)
2. **Architecture checkpoints** - Core patterns that must be preserved
3. **Workspace coordination** - Dependency and integration rules
4. **Extending the crate** - How to safely add features

Keep it under 50 lines. Reference detailed info in CLAUDE.md.

## Build and Validation Commands

### Per-Crate Commands

```bash
# Fast validation
cargo check -p crate-name

# Run tests
cargo test -p crate-name

# Formatting check
cargo fmt --package crate-name -- --check

# Apply formatting
cargo fmt --package crate-name

# Linting
cargo clippy -p crate-name --all-targets --all-features

# Coverage
scripts/coverage.sh -- --package crate-name
```

### Workspace-Wide Commands

```bash
# Check everything
cargo check

# Test everything
cargo test

# Format all
cargo fmt

# Lint all
cargo clippy --all-targets --all-features

# Full coverage
scripts/coverage.sh
```

### Pre-Commit Checklist

```bash
cargo fmt -- --check  # or cargo fmt to auto-fix
cargo clippy --all-targets --all-features
cargo test
```

## Common Pitfalls and Solutions

### Pitfall 1: Version Conflicts

**Problem:** Adding a dependency with a specific version in a member crate.

**Solution:** Always add to workspace dependencies first:

```toml
# DON'T DO THIS in member Cargo.toml:
[dependencies]
new-dep = "1.2.3"

# DO THIS instead:
# 1. Add to workspace root:
[workspace.dependencies]
new-dep = "1.2.3"

# 2. Reference in member:
[dependencies]
new-dep = { workspace = true }
```

### Pitfall 2: Inconsistent Error Types

**Problem:** Creating custom error types in each crate.

**Solution:** Extend `common::DbError` with new variants as needed.

### Pitfall 3: Mixing Bincode APIs

**Problem:** Using deprecated `bincode::serialize` or mixing configurations.

**Solution:** Always use `bincode::serde::*` with the shared config helper.

### Pitfall 4: Forgetting Test Cleanup

**Problem:** Tests leave files/directories in temp locations.

**Solution:** Use `tempfile::tempdir()` which auto-cleans on drop.

### Pitfall 5: Incomplete Documentation

**Problem:** Missing doc comments or examples.

**Solution:** Follow the documentation templates and run `cargo doc --open` to review.

## Next Steps After Creating a Crate

1. **Integration:** Update dependent crates to use the new crate
2. **Documentation:** Update root README if needed
3. **Testing:** Add integration tests that span multiple crates
4. **CI/CD:** Ensure new crate is covered by CI pipelines
5. **Coverage:** Run `scripts/coverage.sh` and review results
