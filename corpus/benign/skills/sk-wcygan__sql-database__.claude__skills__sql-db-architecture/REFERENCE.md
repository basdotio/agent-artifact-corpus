# sql-database Architecture Reference

Detailed API signatures, implementation patterns, and design decisions for the toy relational database.

## Core Type System

### types/ - SQL Types and Values

```rust
#[derive(Clone, Debug, PartialEq)]
pub enum SqlType {
    Int,
    Text,
    Bool,
}

#[derive(Clone, Debug, PartialEq, Ord, PartialOrd, Eq)]
pub enum Value {
    Int(i64),
    Text(String),
    Bool(bool),
    Null, // Reserved for future; v1 avoids producing it
}

impl Value {
    pub fn as_bool(&self) -> Option<bool>;
    pub fn cmp_same_type(&self, other: &Value) -> Option<std::cmp::Ordering>;
}
```

**Design notes:**
- No implicit type widening
- WHERE comparisons require same-type values (v1)
- Null is defined but not produced in v1

### common/ - Shared Types

```rust
pub type ColumnId = u16;

#[derive(Clone, Debug)]
pub struct Row(pub Vec<Value>);

#[derive(Clone, Debug)]
pub struct RecordBatch {
    pub columns: Vec<String>,
    pub rows: Vec<Row>,
}

#[derive(thiserror::Error, Debug)]
pub enum DbError {
    #[error("parse: {0}")] Parser(String),
    #[error("plan: {0}")]  Planner(String),
    #[error("exec: {0}")]  Executor(String),
    #[error("catalog: {0}")] Catalog(String),
    #[error("storage: {0}")] Storage(String),
    #[error("wal: {0}")]     Wal(String),
    #[error(transparent)]    Io(#[from] std::io::Error),
}

pub type DbResult<T> = Result<T, DbError>;

pub struct Config {
    pub data_dir: PathBuf,
    pub page_size: usize,           // e.g., 4096
    pub buffer_pool_pages: usize,   // e.g., 256
    pub wal_enabled: bool,          // true in v1
}
```

## Expression System

### expr/ - Expression AST and Evaluation

```rust
pub enum BinaryOp {
    Eq, Ne, Lt, Le, Gt, Ge,  // Comparison
    And, Or,                  // Logical
}

pub enum UnaryOp {
    Not,
}

pub enum Expr {
    Literal(Value),
    Column(String),  // Resolved to ColumnId during planning
    Binary {
        left: Box<Expr>,
        op: BinaryOp,
        right: Box<Expr>,
    },
    Unary {
        op: UnaryOp,
        expr: Box<Expr>,
    },
}
```

**Evaluator pattern:**
```rust
impl Expr {
    pub fn eval(&self, row: &Row, schema: &TableSchema) -> DbResult<Value>;
}
```

## Storage Layer

### storage/ - Heap Table and Tuples

```rust
pub struct RecordId {
    pub page_id: PageId,
    pub slot: u16,
}

pub trait HeapTable {
    fn insert(&mut self, row: &Row) -> DbResult<RecordId>;
    fn get(&mut self, rid: RecordId) -> DbResult<Row>;
    fn update(&mut self, rid: RecordId, row: &Row) -> DbResult<()>;
    fn delete(&mut self, rid: RecordId) -> DbResult<()>;
}
```

**Implementation details:**
- Slotted page layout (fixed page_size from Config)
- Tuple serialization via `bincode`
- Custom row header + column offsets for variable-length data

### buffer/ - Buffer Pool (Page Cache)

```rust
pub struct PageId(pub u64);
pub struct TableId(pub u64);

pub trait Pager {
    fn fetch_page(&mut self, table: TableId, pid: PageId) -> DbResult<&mut [u8]>;
    fn allocate_page(&mut self, table: TableId) -> DbResult<PageId>;
    fn flush(&mut self) -> DbResult<()>;
}
```

**Implementation:**
- LRU eviction policy (`lru` + `hashbrown`)
- File segments per table
- Single-writer, no pin/unpin in v1
- Optional `memmap2` for memory-mapped files

### wal/ - Write-Ahead Log

```rust
#[derive(serde::Serialize, serde::Deserialize)]
pub enum WalRecord {
    Insert {
        table: TableId,
        row: Row,
        rid: RecordId,
    },
    Update {
        table: TableId,
        rid: RecordId,
        new_row: Row,
    },
    Delete {
        table: TableId,
        rid: RecordId,
    },
    CreateTable {
        name: String,
        schema: TableSchema,
        table: TableId,
    },
    DropTable {
        table: TableId,
    },
}
```

**Write protocol:**
1. Append `WalRecord` to log file
2. `fsync` WAL file
3. Apply operation to storage
4. Periodically checkpoint (flush dirty pages, truncate WAL)

**Recovery:**
- Read WAL from start
- Replay records in order
- Restore system state

**Design choice: redo-only**
- Simpler than undo/redo
- Stable across page format changes
- Single-writer means no torn state

## Metadata

### catalog/ - Schema and Metadata

```rust
pub struct Column {
    pub name: String,
    pub ty: SqlType,
}

pub struct TableSchema {
    pub columns: Vec<Column>,
    pub name_to_ordinal: HashMap<String, u16>,
}

pub enum IndexKind {
    BTree,
    Hash,
    Bitmap,
    Trie,
}

pub struct IndexMeta {
    pub name: String,
    pub columns: Vec<ColumnId>,  // Composite support later
    pub kind: IndexKind,
}

pub struct TableMeta {
    pub id: TableId,
    pub name: String,
    pub schema: TableSchema,
    pub indexes: Vec<IndexMeta>,
}
```

**Persistence:**
- JSON serialization (`serde_json`)
- Assign stable `TableId`, `IndexId`
- Track column order and types

## Query Planning

### planner/ - Logical and Physical Plans

**Logical operators:**
- `TableScan(table)`
- `Filter(expr)`
- `Project(cols)`
- `Insert(table, values)`
- `Update(table, assignments, predicate)`
- `Delete(table, predicate)`

**Physical operators:**
- `SeqScan(table)`
- `IndexScan(index, key|range)`
- `Filter(child, predicate)`
- `Project(child, columns)`
- Modify operators (Insert/Update/Delete)

**Planning rules (v1):**
1. **Predicate pushdown** - Move filters to scans
2. **Index selection** - Choose IndexScan when:
   - WHERE has simple predicate on indexed column
   - Equality → Hash or BTree
   - Range → BTree only
   - Boolean → Bitmap
3. **Cost model** - Trivial: prefer index if available and predicate matches

## Query Execution

### executor/ - Volcano Model

```rust
pub trait Exec {
    fn open(&mut self) -> DbResult<()>;
    fn next(&mut self) -> DbResult<Option<Row>>;
    fn close(&mut self) -> DbResult<()>;
}
```

**Concrete operators:**
- `SeqScanExec` - Full table scan via HeapTable
- `IndexScanExec` - Index lookup via Index trait
- `FilterExec` - Predicate evaluation (uses `Expr::eval`)
- `ProjectExec` - Column projection
- `InsertExec` - Writes to storage + WAL + indexes
- `UpdateExec` - Modifies via RecordId + maintains indexes
- `DeleteExec` - Removes via RecordId + updates indexes

**Pull-based iteration:**
```rust
exec.open()?;
while let Some(row) = exec.next()? {
    // Process row
}
exec.close()?;
```

## Indexes

### index/ - Multiple Index Types

```rust
pub trait Index {
    fn insert(&mut self, key: &Value, rid: RecordId) -> DbResult<()>;
    fn delete(&mut self, key: &Value, rid: RecordId) -> DbResult<()>;
    fn get_eq(&self, key: &Value) -> DbResult<Vec<RecordId>>;
    fn get_range(&self, low: &Value, high: &Value) -> DbResult<Vec<RecordId>>;
}
```

**Implementations:**

1. **B+Tree** (`sled`-backed):
   - Supports equality and range queries
   - Key → RecordId mapping
   - Persistent via sled embedded database

2. **Hash** (`hashbrown::HashMap`):
   - Equality queries only
   - `HashMap<Value, Vec<RecordId>>`
   - Persistence added later

3. **Bitmap** (`roaring::RoaringBitmap`):
   - For low-cardinality boolean/enum columns
   - One bitmap per distinct value
   - Efficient for boolean predicates

4. **Trie** (`radix_trie`):
   - Prefix matching for `LIKE 'prefix%'`
   - Text column optimization

**Index maintenance:**
- Hooks in executor's Insert/Update/Delete operators
- Update all indexes on affected columns
- Transactional with WAL logging

## SQL Parsing

### parser/ - SQL to AST

**Approach:**
- Use `sqlparser-rs` for initial parsing
- Convert to sql-database-specific AST types
- Normalize identifiers (lowercase)
- Convert literals to `Value` enum

**Supported SQL (v1):**

**DDL:**
```sql
CREATE TABLE users (id INT, name TEXT, age INT);
DROP TABLE users;
CREATE INDEX idx_name ON table(column);
DROP INDEX idx_name;
```

**DML:**
```sql
INSERT INTO users VALUES (1, 'Will', 27);
SELECT id, name FROM users;
SELECT * FROM users WHERE age > 20;
UPDATE users SET age = 28 WHERE id = 1;
DELETE FROM users WHERE id = 1;
```

## Testing Strategy

### testsupport/ - Fixtures and Helpers

```rust
pub fn run_sql_script(script: &str) -> DbResult<String>;
```

**Usage pattern:**
```rust
#[test]
fn test_select_with_filter() {
    let output = run_sql_script(r#"
        CREATE TABLE t (id INT, name TEXT, age INT);
        INSERT INTO t VALUES (1, 'Alice', 30);
        INSERT INTO t VALUES (2, 'Bob', 25);
        SELECT * FROM t WHERE age > 26;
    "#).unwrap();

    insta::assert_snapshot!(output);
}
```

**Property tests** (`proptest`):
- Round-trip row serialization
- WAL replay consistency
- Index correctness

**Test organization:**
- Unit tests inline with implementation
- Integration tests in `tests/` directories
- Snapshot tests for query output verification

## Build and Development

**Standard commands:**
```bash
cargo check                        # Fast validation
cargo test                         # Run all tests
cargo fmt -- --check              # Verify formatting
cargo clippy --all-targets --all-features  # Lints
scripts/coverage.sh               # Generate coverage report
```

**Coverage output:**
- HTML: `target/llvm-cov/html/index.html`
- LCOV: `target/llvm-cov/lcov.info`

**Workspace dependencies:**
- All versions pinned in root `Cargo.toml` under `[workspace.dependencies]`
- Crates reference with `{ workspace = true }`
- Consistent versions across all members

## Dependencies by Crate

```toml
# common
thiserror, serde

# types
serde

# parser
sqlparser-rs, thiserror

# planner
hashbrown

# executor
tracing

# storage
bytes, bincode, serde, memmap2, fs2

# buffer
lru, hashbrown

# wal
serde, bincode, chrono

# catalog
serde, serde_json, uuid, ahash

# index
sled, hashbrown, roaring, radix_trie

# repl
rustyline, tabled, clap, tracing-subscriber

# testsupport
tempfile, insta, proptest
```

## Implementation Order

**Recommended build sequence:**

1. `common`, `types`, `expr` - Foundations
2. `parser` - SQL → AST
3. `catalog` - In-memory metadata + JSON persist
4. `buffer` + `storage` - Heap table + slotted pages
5. `wal` - Append + replay for Insert/Update/Delete
6. `planner` - Rule-based optimization
7. `index` - B+Tree via sled + DML hooks
8. `executor` - All Volcano operators
9. `repl` - SELECT rendering with tabled
10. `testsupport` - Script runner + snapshots

**Milestone:** After step 8, you have a working, crash-recoverable, indexed SQL engine.

## Architecture Principles

1. **Tiny interfaces** - Traits like `Exec`, `Index`, `HeapTable` have minimal methods
2. **Early returns** - Prefer `?` operator over nested error handling
3. **Plain data** - Avoid over-abstraction; use simple structs/enums
4. **Tracing** - Log major phases with `tracing` spans (query_id, plan, rows_out)
5. **Snapshot tests** - Use `insta` to verify optimizer behavior over time
6. **Clean boundaries** - Each crate has clear responsibility, minimal cross-dependencies

## Common Debugging Paths

**Query not using index:**
→ Check `planner/` index selection rules
→ Verify predicate matches index column
→ Ensure index kind supports operation (range vs equality)

**Storage corruption:**
→ Check WAL replay logic
→ Verify slotted page slot management
→ Test row serialization round-trip

**Performance issues:**
→ Profile buffer pool hit rate
→ Check if SeqScan used instead of IndexScan
→ Verify LRU eviction strategy

**Parse errors:**
→ Check `parser/` AST conversion
→ Verify SQL is in supported subset
→ Look for identifier normalization issues

---

This reference provides the detailed API contracts and implementation patterns. For high-level architecture and navigation strategies, see SKILL.md.
