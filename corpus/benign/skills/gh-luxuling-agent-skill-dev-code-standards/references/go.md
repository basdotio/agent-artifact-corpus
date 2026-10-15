# Go

These rules add to the general ones in `SKILL.md`. Where the two conflict, as they do on file names, test location, and comments, this file wins for Go code.

## Errors

Go returns errors instead of throwing, so "throw, and catch at the boundary" becomes "return, and handle at the boundary". Every layer that adds information wraps the error with `%w` and returns it. The boundary (HTTP handler, `main`, job runner) is the only place that turns an error into a response, a log line, or an exit code.

```go
func (s *UserService) Get(ctx context.Context, id string) (model.User, error) {
	user, err := s.store.FindUser(ctx, id)
	if err != nil {
		return model.User{}, fmt.Errorf("get user %s: %w", id, err)
	}

	return user, nil
}
```

Never check an error only to log it and carry on, and never swallow one with `_`. If the project already has its own error types or a central error handler, use those instead of inventing new ones.

## Panic

Do not panic in handler, service, repository, or library code. Panic or `log.Fatal` only during startup in `main` or `init`, and use `Must*` helpers such as `regexp.MustCompile` only for package-level values.

## Comments

Give each exported identifier a one-line doc comment that starts with its name. Unexported code follows the general rule: no comments except markers and the rare line explaining why.

```go
// UserService reads and updates users.
type UserService struct {
	store userStore
}
```

## Services and dependencies

Services, repositories, and handlers are structs that hold their dependencies, built with a `New` constructor and wired together in `main`. Behavior lives in methods on the pointer.

```go
type UserService struct {
	store userStore
}

// NewUserService returns a UserService backed by store.
func NewUserService(store userStore) *UserService {
	return &UserService{store: store}
}
```

## Interfaces

Accept interfaces, return structs. Declare a small interface in the package that uses it, not next to the implementation, and only when there is a second implementation or a test fake that needs it. Do not create an interface for every struct.

```go
type userStore interface {
	FindUser(ctx context.Context, id string) (model.User, error)
}
```

## Validation

Validate request bodies at the handler with `go-playground/validator` struct tags. Decode, validate once, and pass the typed value inward. Services and repositories do not validate again.

```go
type createUserRequest struct {
	Name  string `json:"name" validate:"required"`
	Email string `json:"email" validate:"required,email"`
}

func (h *UserHandler) Create(w http.ResponseWriter, r *http.Request) {
	var req createUserRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}

	if err := h.validate.Struct(req); err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}

	user, err := h.users.Create(r.Context(), req.Name, req.Email)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJSON(w, http.StatusCreated, user)
}
```

## Blank lines

An `if err != nil` check belongs to the call above it, so keep the two together and put the blank line after the check, as in the examples above.

## Default libraries

Reach for these first, and do not add another dependency for a job one of them already does:

- **chi** for HTTP routing.
- **go-playground/validator** for validating input.
- **pgx** with **sqlc** for Postgres. Write the SQL and let sqlc generate typed query code. No ORM, and never edit generated code by hand.

For anything else, use what the project already has. If the project has nothing for the job, ask before adding a dependency.

## Naming and layout

- Name files in snake_case: `user_profile.go`, `format_date.go`. This replaces the kebab-case rule for Go.
- Organize by layer under `internal/`, with one entry point per binary under `cmd/`:

```
cmd/
  api/
    main.go
internal/
  handler/
    user.go
  service/
    user.go
    user_test.go
  repository/
    user.go
  model/
    user.go
```

## Testing

- Tests live beside the code they test: `internal/service/user.go` is tested by `internal/service/user_test.go`. This replaces the top-level `tests/` rule for Go.
- Use the standard `testing` package only, with no assertion library. Write table-driven tests: a slice of cases run through `t.Run`.

```go
func TestCalculateTotal(t *testing.T) {
	tests := []struct {
		name  string
		items []model.LineItem
		want  int64
	}{
		{name: "empty", items: nil, want: 0},
		{name: "two items", items: []model.LineItem{{Price: 250, Qty: 2}, {Price: 100, Qty: 1}}, want: 600},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := CalculateTotal(tt.items)

			if got != tt.want {
				t.Errorf("CalculateTotal() = %d, want %d", got, tt.want)
			}
		})
	}
}
```

- Run `go test ./...` before reporting the work as done, and say what the result was.

## Formatting and linting

Always run `gofmt` (or `goimports`) and `go vet` before finishing, even when the project has no config for them. Run `golangci-lint` only when the project has a config for it.
