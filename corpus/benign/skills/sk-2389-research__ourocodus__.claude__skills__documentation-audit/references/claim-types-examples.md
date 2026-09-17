# Claim Types and Verification Examples

This reference guide provides detailed examples of each claim type with recommended verification strategies.

---

## 1. Behavioral Claims

Claims about what the code does at runtime - its behavior, logic, and control flow.

### Examples

**Simple behavior**:
> "The `Retry` function attempts the operation up to 3 times before returning an error."

**Verification**:
- Use `mcp__serena__find_symbol` to locate the `Retry` function
- Read the implementation to verify the retry count
- Confidence: `certain` (if logic is clear) or `high` (if complex)

**Complex behavior**:
> "Sessions progress through states: CREATED → SPAWNING → ACTIVE → TERMINATING → CLEANED"

**Verification**:
- Use `mcp__serena__search_for_pattern` to find state transition code
- Use `mcp__zen__analyze` for complex state machine verification
- Check for all mentioned transitions
- Confidence: `high` to `very_high` (state machines can be complex)

**Error handling**:
> "If the session already exists, `Create()` returns `ErrSessionExists`"

**Verification**:
- Use `mcp__serena__find_symbol` to locate the `Create` method
- Read error handling logic
- Verify the specific error type returned
- Confidence: `certain` (straightforward error check)

**Timing/retry behavior**:
> "The service retries with exponential backoff, starting at 100ms and doubling each time"

**Verification**:
- Use symbolic analysis to find retry logic
- Use `mcp__zen__debug` if the retry logic is spread across multiple components
- Check initial delay and backoff multiplier
- Confidence: `high` (requires careful reading of timing logic)

---

## 2. Structural Claims

Claims about code organization, types, interfaces, and relationships.

### Examples

**Type existence**:
> "The `Manager` type provides session lifecycle management"

**Verification**:
- Use `mcp__serena__find_symbol` with `name_path="Manager"` to verify existence
- Check the type definition and exported methods
- Confidence: `certain` (simple existence check)

**Interface implementation**:
> "Manager implements the `SessionProvider` interface"

**Verification**:
- Use `mcp__serena__find_symbol` to find both Manager and SessionProvider
- Compare method signatures
- Confidence: `certain` (structural verification)

**Package structure**:
> "The relay package is organized into `session`, `protocol`, and `websocket` subpackages"

**Verification**:
- Use `Glob` with pattern `pkg/relay/*/` to list subpackages
- Compare against claim
- Confidence: `certain` (directory listing)

**Dependency relationship**:
> "The session manager depends on the protocol handler for message routing"

**Verification**:
- Use `mcp__serena__find_referencing_symbols` to verify dependencies
- Check import statements and type references
- Confidence: `high` to `very_high`

---

## 3. API Claims

Claims about public APIs, endpoints, request/response formats, and protocols.

### Examples

**REST endpoint**:
> "POST /api/sessions creates a new session and returns JSON with `session_id` and `status`"

**Verification**:
- Check for OpenAPI spec (canonical source) using `Glob` pattern `**/openapi.{yaml,json}`
- If no spec, use `mcp__serena__search_for_pattern` to find the route handler
- Verify response structure
- Confidence: `certain` (if spec exists) or `high` (if verified from code)

**WebSocket protocol**:
> "Messages use JSON-RPC 2.0 format with `method`, `params`, and `id` fields"

**Verification**:
- Check for protocol definition files (protobuf, GraphQL) using `Glob`
- If none, use symbolic analysis to find message serialization code
- Confidence: `very_high` (if canonical source) or `high` (from code)

**GraphQL schema**:
> "The `User` type has fields `id: ID!`, `name: String!`, and `email: String`"

**Verification**:
- Look for `*.graphql` or `schema.graphql` files (canonical source)
- Verify exact field definitions
- Confidence: `certain` (schema files are canonical)

---

## 4. Configuration Claims

Claims about environment variables, config files, defaults, and settings.

### Examples

**Environment variable**:
> "Use `OUROCODUS_ACP_BINARY` to specify a custom ACP binary path. Defaults to `acp`."

**Verification**:
- Use `mcp__serena__search_for_pattern` with pattern `OUROCODUS_ACP_BINARY` to find usage
- Check the default value in code
- Confidence: `certain` (simple constant check)

**Config file format**:
> "The config file uses YAML format with top-level keys: `server`, `database`, and `logging`"

**Verification**:
- Look for config schema files or parsing code
- Use `mcp__serena__find_symbol` to find config struct definition
- Verify field names match documented keys
- Confidence: `high` to `very_high`

**Default values**:
> "Default timeout is 30 seconds"

**Verification**:
- Use `mcp__serena__search_for_pattern` with "30" or "timeout" to find the constant
- Verify the exact default value
- Confidence: `certain` (constant verification)

**Feature flags**:
> "Set `ENABLE_EXPERIMENTAL_FEATURES=true` to enable beta functionality"

**Verification**:
- Search for the flag name in code
- Check if it's actually used to gate features
- **Note**: Mark as contextual - behavior changes based on flag
- Confidence: `high`

---

## 5. Usage Claims

Claims about how to use the code - commands, examples, workflows.

### Examples

**CLI command**:
> "Run `make build` to compile the project"

**Verification**:
- Read the Makefile to verify the `build` target exists
- Check what it actually does
- Optionally: Run the command to verify it works (if safe)
- Confidence: `certain` (if Makefile is authoritative) or `very_high` (if tested)

**Function usage**:
> "Call `manager.Create(ctx, role)` to create a new session"

**Verification**:
- Use `mcp__serena__find_symbol` to find the `Create` method
- Verify the signature matches (context, role parameters)
- Check the return values mentioned
- Confidence: `certain` (signature verification)

**Workflow example**:
> "First call `Initialize()`, then `Start()`, and finally `Cleanup()` when done"

**Verification**:
- Use symbolic analysis to find all three methods
- Look for usage examples in tests or documentation
- Check if there are ordering constraints in code
- Use `mcp__zen__analyze` for complex workflow verification
- Confidence: `high` to `very_high`

**Test command**:
> "Run `mise run smoke` to execute smoke tests"

**Verification**:
- Check `.mise.toml` for the `smoke` task definition
- Verify what it actually runs
- Confidence: `certain` (config file is canonical)

---

## Verification Method Selection Guide

### Use Canonical Sources (Highest Confidence)

- OpenAPI/Swagger specs for REST APIs
- Protobuf definitions for gRPC
- GraphQL schema files
- Database schema files
- Config schemas (JSON Schema, etc.)
- Makefile/mise.toml for command definitions

**Tools**: `Glob` to find, `Read` to verify

### Use Symbolic Analysis (High Confidence)

- Structural claims (types, interfaces, packages)
- Simple behavioral claims (error returns, method signatures)
- Configuration constants
- Direct dependencies

**Tools**: `mcp__serena__find_symbol`, `mcp__serena__find_referencing_symbols`, `mcp__serena__search_for_pattern`

### Use Deep Investigation (Medium to High Confidence)

- Complex behavioral claims (state machines, retry logic)
- Multi-component interactions
- Implicit contracts and protocols
- Performance characteristics

**Tools**: `mcp__zen__analyze`, `mcp__zen__debug`, `mcp__zen__thinkdeep`

---

## Special Cases

### Multiple Versions

When documentation mentions version-specific behavior:

> "In v2.0+, the API returns 201 Created. In v1.x, it returns 200 OK."

**Verification**:
- Note the version context
- Verify current version behavior
- Mark as contextual if multiple versions are supported
- Confidence: `high` (with version noted)

### Planned Features

When documentation describes future functionality:

> "In the next release, we will support batch operations"

**Action**:
- Add disclaimer banner: "⚠️ Planned Feature - Not Yet Implemented"
- Mark `verification: not_applicable`
- Do not attempt to verify in code
- Confidence: N/A

### External Dependencies

Claims about external services or libraries:

> "The GitHub API returns user data in JSON format"

**Verification**:
- Check if there's a local OpenAPI spec or client library
- Otherwise, mark for user review (external behavior can change)
- Confidence: `medium` (if no canonical source available)

### Runtime-Only Behavior

Claims that require execution to verify:

> "The service handles 10,000 requests per second"

**Action**:
- Mark for manual testing or benchmarking
- Do not attempt to verify through static analysis
- Confidence: `low` to `medium` (cannot verify statically)
