---
name: design_patterns-hamster_style
description: Use when writing or modifying Go code in the dodder repository - enforces project-specific naming, formatting, and structural conventions that differ from standard Go style
---

# Dodder Go Style Guide

## Overview

Dodder's Go codebase has distinctive conventions that diverge from standard Go style. This skill is a reference for agents writing or reviewing Go code in dodder. Violations of these conventions create inconsistency that is worse than the "wrong" style itself.

**Formatting tools:** `goimports` + `gofumpt` (run via `just codemod-go-fmt`). These handle indentation (tabs), trailing commas, and import sorting automatically. This skill covers the conventions that formatters cannot enforce.

## Naming

### Packages and directories: `snake_case`

Dodder uses underscores in package names, not the single-word Go convention.

```
blob_store_id        # YES
blobstoreid          # NO
blob-store-id        # NO
```

Prefixes group related packages: `env_`, `collections_`, `command_components_`.

### Files: `snake_case`, entry point is `main.go`

Every package uses `main.go` as the primary file containing core types and constructors (NOT `package main`). Other files are named by concern: `errors.go`, `reader.go`, `writer.go`, `{typename}.go`.

Build variants use suffixes: `main_debug.go`, `repool_release.go`.

### Constructors: `Make`, not `New`

```go
pool.Make(nil, reset)             // YES - Make prefix
MakeResetter[K, V]()              // YES
ids.MakeObjectId(left, right)     // YES
pool.New(nil, reset)              // NO - avoid New
```

`New` exists in ~25 places (legacy, forked stdlib code, or IO constructors like `NewReader`/`NewWriter`). For new code, always use `Make`.

`Must` prefix for panic-on-error variants: `MustObjectId()`, `MustTypeStruct()`.

### Method receivers: full type name, not single letter

```go
func (genre *Genre) Set(v string) error        // YES - full name
func (transacted *Transacted) GetSku() *SKU     // YES
func (blobStore *blobStoreV1) ReadOne() error   // YES
func (g *Genre) Set(v string) error             // NO - single letter
func (t *Transacted) GetSku() *SKU              // NO
```

The receiver name matches the type name in camelCase. For single-word types, use the word lowercase (`genre`, `pool`, `heap`). For compound types, use the full compound (`blobStore`, `matchBuilder`, `compressionType`).

Exceptions: `a`/`b` for comparison methods, `dst`/`src` for copy operations.

### Getters/setters: `Get`/`Set` prefix

```go
func (t *Transacted) GetSku() *SKU              // YES - Get prefix
func (t *Transacted) SetTai(tai Tai)             // YES - Set prefix
func (t *Transacted) Sku() *SKU                  // NO - bare accessor
```

Boolean checkers use `Is` prefix: `IsEmpty()`, `IsConfig()`, `IsErrNotFound()`.

### Generic type parameters: `SCREAMING_SNAKE_CASE`

```go
type pool[SWIMMER any, SWIMMER_PTR interfaces.Ptr[SWIMMER]] struct {}
func MakeResetter[KEY any, VALUE any]() Resetter[KEY, VALUE]
type Seq[ELEMENT any] = iter.Seq[ELEMENT]
```

Common names: `ELEMENT`, `SWIMMER`, `SWIMMER_PTR`, `BLOB`, `BLOB_PTR`, `KEY`, `VALUE`, `SELF`, `ID`, `ID_PTR`, `OUT`.

### Interfaces

No blanket `-er` suffix. Suffix conventions by role:

| Suffix | Meaning | Example |
|--------|---------|---------|
| `Getter` | Read access | `GenreGetter`, `TransactedGetter` |
| `Setter` | Write access | `ConfigDryRunSetter` |
| `Mutable` | Read+write variant of immutable interface | `IdMutable`, `SetMutable`, `CollectionMutable` |
| `Factory` | Creates instances | `BlobReaderFactory`, `ObjectWriterFactory` |
| `Ptr` | Pointer-constrained generic | `PoolPtr`, `ResetablePtr`, `ValuePtr` |
| `Like` | Resembles but isn't exactly X | `ExternalLike` |
| `-er` | Standard Go trait (sparingly) | `Stringer`, `Lenner`, `Lessor`, `Equaler`, `Resetter` |

Domain-noun interfaces have no suffix: `BlobReader`, `BlobStore`, `Config`, `Env`, `Genre`.

### Constants and enums

Exported: `PascalCase`. Unexported: `camelCase` or `snake_case` (for bit flags).

```go
// Exported ordinal enum
const (
    Unknown = Genre(iota)
    Blob
    Type
    Tag
)

// Unexported bit flags (snake_case)
const (
    unknown        = byte(iota)
    blob           = byte(1 << iota)
    tipe                                  // "type" is a keyword, use "tipe"
    tag
)
```

String-typed constants for versioned identifiers: `TypeInventoryListV2 = "!inventory_list-v2"` with `VCurrent` alias pointing to latest.

### Keyword avoidance

`tipe` replaces `type` as a variable/constant name (206 occurrences across 46 files).

### Test variables

- `sut` for "system under test"
- `ex` for expected value, `ac` for actual value
- Tests wrap `*testing.T` with `ui.T{T: t1}` for enhanced assertions

## Structural Conventions

### Import grouping: two groups

1. Standard library
2. Everything else (project-internal and third-party mixed, sorted alphabetically)

```go
import (
    "fmt"
    "io"
    "os"

    "code.linenisgreat.com/dodder/go/lib/_/interfaces"
    "code.linenisgreat.com/dodder/go/lib/alfa/errors"
    "golang.org/x/xerrors"
)
```

Named imports use mixed case to avoid conflicts: `ConTeXT "context"`.

### Type declarations: grouped `type ( ... )` blocks

Related types, interfaces, and aliases are declared together in parenthesized blocks, not individually.

### Interface compliance assertions

```go
var _ interfaces.PoolPtr[string, *string] = pool[string, *string]{}
var _ interfaces.CommandComponentWriter = (*CompressionType)(nil)
```

### Unexported struct + exported interface

The dominant pattern: public API is an interface, private struct is the implementation.

```go
type Env interface { ... }        // exported interface
type env struct { ... }           // unexported implementation
```

### Type aliases for re-export

```go
type Tag = Id
type ObjectId = objectId3
type ExternalObjectId = domain_interfaces.ExternalObjectId
```

### Build tags

Four categories: `debug`/`!debug`, `test`, `test && debug`, `next`/`!next`.

Tests run with: `go test -v -tags test,debug ./...`

## Code Patterns

### Error handling: `errors.Wrap(err)`, always

```go
if err = someOperation(); err != nil {
    err = errors.Wrap(err)
    return result, err
}
```

Never use standard `errors` or `fmt.Errorf` for wrapping. Import `alfa/errors` exclusively. Wrapping `io.EOF` panics by design.

Use `errors.Wrapf(err, "context: %s", val)` for context. Use `errors.ErrorWithStackf(...)` for new errors with stack traces.

### Named return values: always

```go
func Make(config Config) (env Env, err error) {  // YES
func Make(config Config) (Env, error) {            // NO - unnamed returns
```

### Deferred error aggregation

```go
defer errors.DeferredCloser(&err, file)
defer errors.Deferred(&err, file.Sync)
defer errors.DeferredCloseAndRename(&err, tmpFile, oldPath, newPath)
```

### Pool borrowing: `GetWithRepool`

```go
element, repool := pool.GetWithRepool()
defer repool()
```

Never discard repool without `//repool:owned` annotation.

### `sku.Transacted`: never dereference

Use `ResetWith` for value copies, `CloneTransacted` for persistent copies. See main CLAUDE.md for full patterns.

### Switch: `default` first when it's an error/panic

```go
switch id := id.(type) {
default:
    panic(fmt.Sprintf("not a type: %T", id))

case SeqId:
    tipe = id.ToType()
}
```

This pattern places the error/panic `default` as the first case for immediate visibility. Used consistently in type switches and value switches where the default is exceptional.

### Resetter pattern (singleton, field-by-field)

```go
type tagResetter struct{}

func (tagResetter) Reset(tag *TagStruct) {
    tag.value = ""
    tag.virtual = false
}

func (tagResetter) ResetWith(dst, src *TagStruct) {
    dst.value = src.value
    dst.virtual = src.virtual
}

var TagResetter = sTagResetter   // exported singleton
```

### Immutable options via value-receiver `With*` methods

```go
func (options Options) WithPrintTai(v bool) Options {
    options.PrintTai = v
    return options
}
```

Value receiver creates a copy; returns modified copy. No mutation.

### Bare blocks for lexical scoping

Curly braces without a control structure limit variable scope:

```go
func (equaler equaler) Equals(a, b Metadata) bool {
    {
        a := a.(*metadata)
        b := b.(*metadata)
        // a, b shadow only within this block
    }
}
```

### ASCII art section dividers

Figlet-style `//` banners separate major sections within long files:

```go
//   __  __           _
//  |  \/  |_   _ ___| |_
//  | |\/| | | | / __| __|
//  | |  | | |_| \__ \ |_
//  |_|  |_|\__,_|___/\__|
//
```

### Blank lines within switches

Each case block is separated by a blank line from the next.

### Per-package `CLAUDE.md`

Every leaf package has its own `CLAUDE.md` describing purpose and key types. When creating a new package, include one.

## Quick Reference

| Convention | Dodder Style | Standard Go |
|---|---|---|
| Package names | `snake_case` | `singleword` |
| Constructors | `Make` prefix | `New` prefix |
| Receivers | Full type name | Single letter |
| Getters | `Get` prefix | Bare name |
| Generic params | `SCREAMING_SNAKE` | `T`, `K`, `V` |
| Import groups | 2 (stdlib / everything else) | 3 (stdlib / external / internal) |
| Error wrapping | `alfa/errors.Wrap` | `fmt.Errorf("%w")` |
| Entry file | `main.go` per package | `{package}.go` |
| Options pattern | Value-receiver `With*` | Functional options |
| Keyword "type" | `tipe` | n/a |
