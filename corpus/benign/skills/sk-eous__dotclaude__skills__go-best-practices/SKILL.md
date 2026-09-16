---
name: go-best-practices
description: Go development best practices, patterns, and conventions. Use when writing Go code, reviewing .go files, discussing goroutines, channels, error handling, or Go project structure. Triggers on mentions of Go, Golang, goroutines, channels, defer, interfaces, go mod.
---

# Go Best Practices

## Project Structure

```
project/
├── cmd/
│   └── myapp/
│       └── main.go
├── internal/
│   ├── handler/
│   ├── service/
│   └── repository/
├── pkg/
│   └── shared/
├── go.mod
└── go.sum
```

## Error Handling

### Always Check Errors
```go
// Bad
result, _ := doSomething()

// Good
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doSomething failed: %w", err)
}
```

### Wrap Errors with Context
```go
func fetchUser(id string) (*User, error) {
    user, err := db.Query(id)
    if err != nil {
        return nil, fmt.Errorf("fetch user %s: %w", id, err)
    }
    return user, nil
}
```

### Sentinel Errors
```go
var (
    ErrNotFound     = errors.New("not found")
    ErrUnauthorized = errors.New("unauthorized")
)

// Check with errors.Is
if errors.Is(err, ErrNotFound) {
    return http.StatusNotFound
}
```

### Custom Error Types
```go
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("%s: %s", e.Field, e.Message)
}

// Check with errors.As
var validErr *ValidationError
if errors.As(err, &validErr) {
    log.Printf("validation failed on %s", validErr.Field)
}
```

## Concurrency

### Goroutines with WaitGroups
```go
var wg sync.WaitGroup
for _, item := range items {
    wg.Add(1)
    go func(item Item) {
        defer wg.Done()
        process(item)
    }(item)
}
wg.Wait()
```

### Channels
```go
// Buffered channel for bounded work
jobs := make(chan Job, 100)

// Signal-only channel
done := make(chan struct{})

// Close to broadcast
close(done)
```

### Context for Cancellation
```go
func fetchData(ctx context.Context, url string) error {
    req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
    if err != nil {
        return err
    }

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()

    return nil
}
```

### Worker Pools
```go
func worker(id int, jobs <-chan Job, results chan<- Result) {
    for job := range jobs {
        results <- process(job)
    }
}

func main() {
    jobs := make(chan Job, 100)
    results := make(chan Result, 100)

    // Start workers
    for w := 0; w < 3; w++ {
        go worker(w, jobs, results)
    }

    // Send jobs
    for _, job := range allJobs {
        jobs <- job
    }
    close(jobs)
}
```

## Interfaces

### Small Interfaces
```go
// Good - single method
type Reader interface {
    Read(p []byte) (n int, err error)
}

// Accept interfaces, return structs
func Process(r Reader) (*Result, error) {
    // ...
}
```

### Interface Composition
```go
type ReadWriter interface {
    Reader
    Writer
}
```

## Testing

### Table-Driven Tests
```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 2, 3, 5},
        {"negative", -1, -2, -3},
        {"zero", 0, 0, 0},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Add(tt.a, tt.b)
            if got != tt.expected {
                t.Errorf("Add(%d, %d) = %d; want %d", tt.a, tt.b, got, tt.expected)
            }
        })
    }
}
```

### Test Helpers
```go
func setupTestDB(t *testing.T) *DB {
    t.Helper()
    db, err := NewDB(":memory:")
    if err != nil {
        t.Fatalf("setup db: %v", err)
    }
    t.Cleanup(func() { db.Close() })
    return db
}
```

## Resource Management

### Defer for Cleanup
```go
func readFile(path string) ([]byte, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, err
    }
    defer f.Close()

    return io.ReadAll(f)
}
```

### Mutex Patterns
```go
type SafeCounter struct {
    mu    sync.RWMutex
    value int
}

func (c *SafeCounter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value++
}

func (c *SafeCounter) Value() int {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return c.value
}
```

## Naming Conventions

- **Packages**: short, lowercase, no underscores (`http`, `json`)
- **Exported**: `PascalCase` (`NewServer`, `UserID`)
- **Unexported**: `camelCase` (`userID`, `conn`)
- **Acronyms**: consistent case (`URL`, `userID`)
- **Getters**: no `Get` prefix (`user.Name()` not `user.GetName()`)

## Common Patterns

### Functional Options
```go
type Server struct {
    port    int
    timeout time.Duration
}

type Option func(*Server)

func WithPort(p int) Option {
    return func(s *Server) { s.port = p }
}

func NewServer(opts ...Option) *Server {
    s := &Server{port: 8080, timeout: 30 * time.Second}
    for _, opt := range opts {
        opt(s)
    }
    return s
}
```

### Constructor Pattern
```go
func NewUser(name string) (*User, error) {
    if name == "" {
        return nil, errors.New("name required")
    }
    return &User{Name: name, CreatedAt: time.Now()}, nil
}
```

## Anti-Patterns to Avoid

- Naked returns in long functions
- Ignoring errors with `_`
- Passing large structs by value
- Using `init()` for complex logic
- Global mutable state
- Goroutine leaks (always ensure cleanup)
