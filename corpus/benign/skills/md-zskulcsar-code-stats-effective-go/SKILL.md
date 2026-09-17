---
name: effective-go
description: Apply Go idioms from “Effective Go” when writing, reviewing, or refactoring Go code so results remain idiomatic, maintainable, and performant.
---

# Effective Go – Practical Go Coding Standards

## Purpose

Translate the guidance from the official “Effective Go” document into a field-ready checklist. Use this skill whenever you touch Go code so the result reads like idiomatic Go, not a translation from another language.

**Core Principle:** Let Go’s design lead the implementation—favor simplicity, explicit error handling, and tooling-enforced consistency.

---

## TOP 10 CRITICAL RULES

### 1. Let `gofmt` Decide Layout 🔧

```go
// ✅ GOOD: Trust gofmt for alignment.
type Config struct {
    timeout time.Duration
    retries int
}

// ❌ BAD: Manual spacing fights the formatter.
type Config struct {
    timeout    time.Duration  // extra spaces vanish after gofmt
    retries    int
}
```

Always run `gofmt` or `go fmt ./...` before committing. If the formatted output looks awkward, restructure the code rather than overriding the tool. See `./docs/FORMATTING.md` for details.

### 2. Name Things the Go Way 🏷️

```go
// ✅ GOOD
package cache

type Store struct{}
func (s *Store) Put(key string, value any) {}

// ❌ BAD
package cache_manager // underscores and verbose names

type CacheStore struct{} // stutters with package name
func (s *CacheStore) SetValue(...) {}
```

Packages stay lower-case without underscores, exported identifiers use MixedCaps, and getters drop the `Get` prefix. More patterns live in `./docs/NAMING.md`.

### 3. Handle Errors Explicitly ⚠️

```go
// ✅ GOOD
resp, err := client.Do(req)
if err != nil {
    return fmt.Errorf("fetch config: %w", err)
}

// ❌ BAD
resp, _ := client.Do(req) // ignores failure paths
```

Return errors, check them immediately, and wrap with context when propagating. Panics are for truly exceptional states. Review `./docs/ERRORS.md` for nuanced cases.

### 4. Embrace Go Control Flow 🔄

```go
// ✅ GOOD: Range loop with short-lived variable.
for i, user := range users {
    if err := user.Validate(); err != nil {
        return fmt.Errorf("user %d invalid: %w", i, err)
    }
}

// ❌ BAD: Manual index loop without need.
for i := 0; i < len(users); i++ {
    user := users[i]
    ...
}
```

Prefer `range`, use `if` initializers, and rely on switch semantics instead of fallthrough-heavy chains. See `./docs/CONTROL_FLOW.md`.

### 5. Design for Concurrency & Zero Values 🚦

```go
// ✅ GOOD: Capture loop variable, use zero-value sync primitives.
type Worker struct {
    mu sync.Mutex        // zero value is ready to use
    ch chan Job          // initialized in Start
}

func (w *Worker) Start(ctx context.Context, jobs []Job) {
    w.ch = make(chan Job)
    go func() {
        defer close(w.ch)
        for _, job := range jobs {
            job := job // capture for goroutine safety
            select {
            case <-ctx.Done():
                return
            case w.ch <- job:
            }
        }
    }()
}

// ❌ BAD: Shares loop variable and relies on nil mutex/channel states.
type UnsafeWorker struct {
    mu *sync.Mutex
    ch chan Job
}

func (w *UnsafeWorker) Start(jobs []Job) {
    go func() {
        for _, job := range jobs {
            go func() { w.ch <- job }() // job shared across iterations
        }
    }()
}
```

Design concurrent code so goroutines own the data they work on, channels are closed by senders, loop variables are captured locally, and zero values of structs (e.g., `sync.Mutex`, slices, maps) are immediately usable. Additional pipeline patterns live in `./docs/CONCURRENCY.md`.

### 6. Prefer Interfaces at Boundaries, Concrete Types Inside 🔄

```go
// ✅ GOOD: Accept interface, return concrete.
func NewLogger(w io.Writer) *Logger {
    return &Logger{w: w}
}

// ❌ BAD: Exposes interface wrapper needlessly.
func NewLogger(w io.Writer) io.Writer {
    return &logWrapper{w: w}
}
```

Accept interfaces when dependencies vary, return concrete types to preserve functionality and simplify testing. Keep interfaces small—one or two methods is ideal. See `./docs/NAMING.md` and `./docs/CONTROL_FLOW.md` for more nuance.

### 7. Use `defer` for Cleanup, But Not Inside Hot Loops ♻️

```go
// ✅ GOOD: defer close near acquisition.
f, err := os.Open(path)
if err != nil {
    return nil, err
}
defer f.Close()

// ❌ BAD: defer inside tight loop—each iteration stacks another defer.
for _, file := range files {
    f, _ := os.Open(file)
    defer f.Close()
}
```

Defer simplifies cleanup, but repeated defers in frequently executed loops can increase allocations and delay resource release. Instead, close explicitly inside the loop when needed. Consult `./docs/CONTROL_FLOW.md` for defer patterns.

### 8. Make Zero Values Useful 🎯

```go
// ✅ GOOD: Ready-to-use after var declaration.
type Buffer struct {
    bytes.Buffer
    limit int
}

// ❌ BAD: Requires mandatory initialization.
type Buffer struct {
    data []byte
    init bool
}
```

Structures should work immediately after declaration. Avoid mandatory constructor flags; rely on slices, maps, and sync primitives that behave with zero values. Additional patterns live in `./docs/DATA_STRUCTURES.md`.

### 9. Minimize Package-Level State 🧭

```go
// ✅ GOOD: Explicit dependency injection.
type Service struct {
    client *http.Client
}

// ❌ BAD: Hidden globals impede testing.
var defaultClient = &http.Client{}

func Fetch(url string) ([]byte, error) {
    return defaultClient.Get(url)
}
```

Prefer dependency injection over package-level variables. If a global is unavoidable, guard access with synchronization and document its use carefully.

### 10. Coordinate Cancellation with Context ⏹️

```go
// ✅ GOOD
req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
// operations observe ctx.Done()

// ❌ BAD
req, err := http.NewRequest(http.MethodGet, url, nil)
// ignores caller cancellation, leaks goroutines
```

Contexts propagate cancellation, deadlines, and tracing. Accept `context.Context` as the first parameter where operations may block or spawn goroutines. See `./docs/CONCURRENCY.md` for pipeline patterns.

```go
// ✅ GOOD: Goroutine uses local copy and context cancellation.
for _, job := range jobs {
    job := job
    go func() {
        select {
        case <-ctx.Done():
            return
        case workCh <- job.Process():
        }
    }()
}

// ❌ BAD: Captures loop variable, leaks goroutines.
for _, job := range jobs {
    go func() {
        workCh <- job.Process() // 'job' shared across iterations
    }()
}
```

Launch goroutines intentionally, copy loop variables inside, guard shared maps with synchronization, and ensure the zero value of a type is useful. Check `./docs/CONCURRENCY.md` and `./docs/DATA_STRUCTURES.md`.

---

## Key Practices

### Formatting
Run `gofmt` as your law of the land. Align imports into standard, third-party, and internal groups. Avoid manual alignment that will be removed by the formatter.

### Naming
Prefer short, descriptive names that avoid stutter. Interfaces describe behavior (`io.Reader`), structs are nouns (`http.Server`), and exported functions start with the package name when read aloud (`http.ListenAndServe`).

### Functions & Methods
- Return multiple values to communicate success, data, and error without side channels.
- Keep named return parameters short-lived; only use them when they improve clarity.
- Use pointer receivers when methods mutate the receiver or when copying would be expensive.

### Data Handling
- Prefer slices over arrays; append returns the updated slice.
- Initialize maps with `make` before assignment.
- Design constructors that return ready-to-use values, but rely on zero values when possible.

### Documentation
- Every exported identifier needs a doc comment whose first sentence starts with the identifier name.
- Provide a package comment that explains the package’s purpose and entry points.
- Keep doc comments factual and concise; they double as the synopsis shown by `go doc`.

### Initialization Discipline
- Keep `init` functions short—initialize package-level state or register handlers only.
- Avoid launching goroutines or performing network calls in `init`; prefer explicit setup functions.
- Document any non-trivial side effects so importers are not surprised.

### Interfaces
- Keep them small; one or two methods typically suffice.
- Accept interfaces, return concrete types to reduce API surface and maintain control.
- Use type assertions and type switches thoughtfully; avoid `interface{}` unless a true abstraction.

### Blank Identifier
- Use `_` intentionally to ignore values (e.g., `_ = err` during temporary scaffolding) or to enforce interface compliance.
- Avoid leaving `_` placeholders behind—replace with meaningful usage or remove the binding once done.
- Employ `_` in import statements only for side effects (`import _ "net/http/pprof"`) when those effects are required and documented.

### Composite Literals
- Use composite literals to initialize structs, slices, and maps in a single expression.
- Name fields in struct literals when clarity matters, especially for exported fields.
- Prefer literal initialization over a series of assignments to highlight intended state.

---

## Good vs. Bad Patterns

**Good – Zero value usable**
```go
type Counter struct {
    mu sync.Mutex
    n  int
}

func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.n++
}
```
No constructor needed; the zero value works immediately.

**Bad – Requires mandatory constructor**
```go
type Counter struct {
    mu *sync.Mutex
    n  int
}

func NewCounter() *Counter {
    return &Counter{mu: &sync.Mutex{}}
}
```
Forgetting to call `NewCounter` leads to nil dereference. Prefer value fields.

**Good – Clear error propagation**
```go
func Load(path string) ([]byte, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("load %q: %w", path, err)
    }
    return data, nil
}
```

**Bad – Panic for expected failure**
```go
func Load(path string) []byte {
    data, err := os.ReadFile(path)
    if err != nil {
        panic(err) // aborts the program on normal error
    }
    return data
}
```

**Good – Table-driven test for inputs**
```go
func TestParseDuration(t *testing.T) {
    cases := []struct {
        input string
        want  time.Duration
        err   bool
    }{
        {"1s", time.Second, false},
        {"500ms", 500 * time.Millisecond, false},
        {"garbage", 0, true},
    }
    for _, tc := range cases {
        t.Run(tc.input, func(t *testing.T) {
            got, err := parseDuration(tc.input)
            if tc.err {
                require.Error(t, err)
                return
            }
            require.NoError(t, err)
            require.Equal(t, tc.want, got)
        })
    }
}
```

**Bad – Repetitive tests without tables**
```go
func TestParseDurationSeconds(t *testing.T) {
    got, err := parseDuration("1s")
    if err != nil || got != time.Second {
        t.Fatalf("want 1s, got %v (err=%v)", got, err)
    }
}

func TestParseDurationMilliseconds(t *testing.T) {
    got, err := parseDuration("500ms")
    if err != nil || got != 500*time.Millisecond {
        t.Fatalf("want 500ms, got %v (err=%v)", got, err)
    }
}
```

---

## Workflow Checklist

1. **Format** – Run `gofmt` / `goimports`.
2. **Name** – Verify packages and identifiers follow Go conventions (`./docs/NAMING.md`).
3. **Control Flow** – Prefer `range`, `switch`, and `if` initializers where idiomatic (`./docs/CONTROL_FLOW.md`).
4. **Data** – Use slices, maps, and zero-value friendly structs (`./docs/DATA_STRUCTURES.md`).
5. **Errors** – Return and wrap errors; avoid panic (`./docs/ERRORS.md`).
6. **Concurrency** – Launch goroutines safely, close channels properly (`./docs/CONCURRENCY.md`).
7. **Docs** – Add Go-style doc comments that begin with the identifier name.

---

## References

- `./docs/FORMATTING.md` – gofmt rules and import organization.
- `./docs/NAMING.md` – naming conventions and stutter avoidance.
- `./docs/CONTROL_FLOW.md` – idiomatic `if`, `for`, `switch`, and defer usage.
- `./docs/DATA_STRUCTURES.md` – slices, maps, allocation, zero values.
- `./docs/CONCURRENCY.md` – goroutines, channels, select, pipelines.
- `./docs/ERRORS.md` – error handling, panic/recover boundaries.
- `./docs/QUICK_REFERENCE.md` – rapid reminders for common tasks.

---

## Quick Checklist

- [ ] `gofmt` run (no manual alignment).
- [ ] Package and identifiers follow Go naming rules.
- [ ] Errors are checked, wrapped, and propagated.
- [ ] Zero values usable; constructors optional.
- [ ] Goroutines and channels respect context and closure.
- [ ] Doc comments exist for exported APIs and start with the identifier name.
- [ ] `init` functions are minimal; table-driven tests cover edge cases; blank identifiers only where intentional.
