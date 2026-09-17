---
name: deep-analysis
description: Proactively investigates Go SSO codebase to understand authentication flows, trace gRPC request paths, analyze clean architecture patterns, and provide comprehensive backend code insights. Use when users ask about SSO implementation, service structure, database queries, or need to understand how authentication/authorization works.
allowed-tools: Task
---

# Deep Code Analysis for Go SSO Backend

This Skill provides comprehensive codebase investigation capabilities using the codebase-detective agent with semantic search and pattern matching, optimized for Go microservices architecture.

## When to use this Skill

Claude should invoke this Skill when:

- User asks "how does [authentication/authorization feature] work?"
- User wants to understand SSO service architecture or clean architecture layers
- User is debugging and needs to trace gRPC request flow
- User asks "where is [authentication logic/token validation/tenant isolation] implemented?"
- User needs to find all usages of a domain entity or usecase
- User wants to understand dependencies between layers (controller → usecase → repository)
- User mentions: "investigate", "analyze", "find", "trace", "understand", "how does SSO"
- User is exploring the SSO codebase structure
- User needs to understand complex multi-layer flows (e.g., login flow through all layers)
- User wants to understand database queries (sqlc), Redis operations, or gRPC contracts
- User asks about tenant isolation implementation
- User wants to trace how JWT tokens are generated/validated

## Instructions

### Phase 1: Determine Investigation Scope

Understand what the user wants to investigate:

1. **Specific Feature**: "How does user login with JWT work?"
2. **Find Implementation**: "Where is the tenant isolation logic?"
3. **Trace Flow**: "What happens when a gRPC login request comes in?"
4. **Debug Issue**: "Why is token refresh failing for some users?"
5. **Find Patterns**: "Where are all the database queries made?"
6. **Analyze Architecture**: "What's the structure of the clean architecture layers?"
7. **Security Investigation**: "How is tenant_id validated across all queries?"
8. **Database Flow**: "How does sqlc generate type-safe queries?"
9. **Session Management**: "How are sessions stored in Redis?"

### Phase 2: Invoke codebase-detective Agent

Use the Task tool to launch the codebase-detective agent with comprehensive instructions:

```
Use Task tool with:
- subagent_type: "codebase-detective"
- description: "Investigate [brief summary]"
- prompt: [Detailed investigation instructions]
```

**Prompt structure for codebase-detective agent**:

```markdown
# Code Investigation Task

## Investigation Target
[What needs to be investigated - be specific]

## Context
- Working Directory: [current working directory]
- Purpose: [debugging/learning/refactoring/etc]
- User's Question: [original user question]

## Investigation Steps

1. **Initial Search**:
   - Use semantic search (claude-context MCP) if available
   - Use gopls MCP for Go-specific symbol lookups if available
   - Otherwise use grep/ripgrep for patterns
   - Search project structure:
     - `/internal/controller/grpc/` - gRPC handlers
     - `/internal/usecase/` - Business logic layer
     - `/internal/domain/entity/` - Domain entities
     - `/internal/infrastructure/storage/` - Database layer (sqlc)
     - `/proto/` or `github.com/rshelekhov/sso-protos` - gRPC Protocol Buffer definitions

2. **Code Location**:
   - Find exact file paths and line numbers
   - Identify gRPC endpoint entry points
   - Trace through clean architecture layers (controller → usecase → repository)
   - Note related files and dependencies

3. **Code Flow Analysis**:
   - Trace gRPC request → controller → usecase → repository → database
   - Identify key functions and their roles in each layer
   - Map out service dependencies (PostgreSQL, Redis, MongoDB)
   - Note context propagation and error handling

4. **Pattern Recognition**:
   - Identify clean architecture patterns used
   - Note Uber Go Style Guide compliance
   - Find tenant isolation patterns
   - Identify sqlc query patterns
   - Find similar implementations for reference

## Deliverables

Provide a comprehensive report including:

1. **📍 Primary Locations**:
   - gRPC handler file with line numbers (internal/controller/grpc/)
   - Usecase implementation (internal/usecase/)
   - Repository/storage layer (internal/infrastructure/storage/)
   - Proto definitions (proto/ or github.com/rshelekhov/sso-protos)
   - Database queries (if using sqlc: queries/*.sql)

2. **🔍 Code Flow**:
   - gRPC request → controller handler → usecase → repository → database
   - How layers interact (dependency injection, interfaces)
   - Context propagation through layers
   - Error handling and wrapping patterns
   - Tenant isolation checkpoints

3. **🗺️ Architecture Map**:
   - Clean architecture layer diagram
   - Service dependencies (PostgreSQL, Redis, MongoDB)
   - gRPC service relationships
   - Dependency injection flow

4. **📝 Code Snippets**:
   - gRPC handler implementation
   - Usecase business logic
   - sqlc-generated repository methods
   - Key security checks (tenant isolation, auth validation)
   - Error handling patterns

5. **🚀 Navigation Guide**:
   - How to explore related endpoints
   - Related proto definitions to examine
   - Commands to test gRPC endpoints (grpcurl)
   - Database migration files to review
   - Related test files (*_test.go)

6. **💡 Insights**:
   - Why clean architecture is used
   - Tenant isolation strategy rationale
   - Security considerations in implementation
   - Performance implications (N+1 queries, caching)
   - Best practices observed (Uber Go Style Guide)

## Search Strategy

**With MCP Claude-Context Available**:
- Index the codebase if not already indexed
- Use semantic queries for concepts (e.g., "JWT token validation", "tenant isolation")
- Use natural language to find functionality

**With MCP gopls Available** (Go-specific):
- Use gopls for symbol lookups (functions, structs, interfaces)
- Find implementations of interfaces
- Locate all references to a function/type
- Navigate to definitions across packages

**Fallback (No MCP)**:
- Use ripgrep (rg) or grep for pattern matching
- Search Go files: `rg "pattern" --type go`
- Search file names: `find . -name "*auth*.go"`
- Trace imports manually: look for `import` statements
- Use git grep for repository-wide search
- Search proto files: `rg "service AuthService" --type proto`

## Output Format

Structure your findings clearly with:
- File paths using backticks: `internal/controller/grpc/auth.go:145`
- Go code blocks for snippets with proper syntax highlighting
- Clear headings and sections
- Clean architecture layer indicators (Controller → Usecase → Repository)
- Actionable next steps (grpcurl commands, test commands)
```

### Phase 3: Present Analysis Results

After the agent completes, present results to the user:

1. **Executive Summary** (2-3 sentences):
   - What was found
   - Where it's located
   - Key insight

2. **Detailed Findings**:
   - Primary file locations with line numbers
   - Code flow explanation
   - Architecture overview

3. **Visual Structure** (if complex):
   ```
   gRPC Endpoint: AuthService.Login (proto/auth/v1/auth.proto:23)
     ├── Controller: Login handler (internal/controller/grpc/auth.go:89)
     ├── Usecase: Authenticate (internal/usecase/auth/login.go:34)
     │   ├── Validate credentials (internal/usecase/auth/login.go:45)
     │   ├── Repository: GetUserByEmail (internal/infrastructure/storage/postgres/user.go:78)
     │   ├── Password verification (bcrypt)
     │   └── Generate JWT tokens (internal/usecase/auth/token.go:23)
     └── Response: AuthResponse with tokens
   ```

4. **Code Examples**:
   - Show key Go code snippets inline
   - Highlight tenant isolation patterns
   - Show error handling with context wrapping
   - Highlight important security checks

5. **Next Steps**:
   - Suggest follow-up investigations
   - Offer to dive deeper into specific parts
   - Provide grpcurl commands to test endpoints
   - Provide commands to run tests

### Phase 4: Offer Follow-up

Ask the user:
- "Would you like me to investigate any specific part in more detail?"
- "Do you want to see how [related feature] works?"
- "Should I trace [specific function] further?"

## Example Scenarios

### Example 1: Understanding Authentication Flow

```
User: "How does user login work in the SSO service?"

Skill invokes codebase-detective agent with:
"Investigate user authentication and login flow in Go SSO service:
1. Find gRPC Login endpoint in proto definitions
2. Trace controller handler for Login
3. Follow usecase authentication logic
4. Identify JWT token generation
5. Find session storage in Redis
6. Locate tenant isolation validation
7. Show error handling patterns"

Agent provides:
- proto/auth/v1/auth.proto:23 (Login RPC definition)
- internal/controller/grpc/auth.go:89-135 (Login handler)
- internal/usecase/auth/login.go:34-89 (authentication logic)
- internal/usecase/auth/token.go:23-67 (JWT generation)
- internal/infrastructure/storage/redis/session.go:45 (session storage)
- Flow: gRPC Request → Controller → Usecase → Repository (PostgreSQL) → JWT Gen → Redis Session
- Tenant isolation: Validated at controller:102, usecase:48, repository:89
```

### Example 2: Debugging Token Refresh Failure

```
User: "Token refresh is failing with 'invalid tenant' error"

Skill invokes codebase-detective agent with:
"Debug token refresh failure with tenant validation error:
1. Find RefreshToken gRPC endpoint
2. Trace refresh token validation logic
3. Check tenant_id extraction from token
4. Verify tenant isolation checks
5. Identify where 'invalid tenant' error originates
6. Check database query tenant_id filtering"

Agent provides:
- proto/auth/v1/auth.proto:34 (RefreshToken RPC)
- internal/controller/grpc/auth.go:187 (RefreshToken handler)
- internal/usecase/auth/refresh.go:45 (refresh logic)
- internal/usecase/auth/token.go:89 (tenant_id extraction from JWT claims)
- Issue: RefreshToken query missing tenant_id filter at repository:134
- Root cause: sqlc query in queries/refresh_token.sql missing WHERE tenant_id = $2
- Fix: Add tenant_id parameter to GetRefreshToken query
```

### Example 3: Finding All Database Queries

```
User: "Where are all the database queries for the user table?"

Skill invokes codebase-detective agent with:
"Find all database queries related to user table:
1. Search for user-related sqlc queries
2. Identify repository methods using these queries
3. List all SQL operations (SELECT, INSERT, UPDATE, DELETE)
4. Note tenant isolation in WHERE clauses
5. Find transaction usage patterns
6. Check for N+1 query issues"

Agent provides:
- queries/user.sql (sqlc query definitions):
  - GetUserByID:12 (SELECT with tenant_id filter)
  - GetUserByEmail:23 (SELECT with tenant_id filter)
  - CreateUser:34 (INSERT with tenant_id)
  - UpdateUser:45 (UPDATE with tenant_id WHERE clause)
  - DeleteUser:56 (soft delete, UPDATE is_deleted)
- internal/infrastructure/storage/postgres/user.go:
  - Repository implementation using sqlc-generated code
  - All queries properly filter by tenant_id
  - Transaction usage in CreateUserWithProfile:134
- Tenant isolation: All 5 queries include tenant_id validation
- Pattern: Prepared statements via sqlc (SQL injection safe)
```

## Success Criteria

The Skill is successful when:

1. ✅ User's question is comprehensively answered
2. ✅ Exact code locations provided with line numbers
3. ✅ Code relationships and flow clearly explained
4. ✅ User can navigate to code and understand it
5. ✅ Architecture patterns identified and explained
6. ✅ Follow-up questions anticipated

## Tips for Optimal Results

1. **Be Comprehensive**: Don't just find one file, map the entire flow through all layers
2. **Provide Context**: Explain why code is structured this way (clean architecture rationale)
3. **Show Examples**: Include actual Go code snippets
4. **Think Holistically**: Connect related pieces across layers and files
5. **Anticipate Questions**: Answer follow-up questions proactively
6. **Security Focus**: Always note tenant isolation and security patterns

## Integration with Other Tools

This Skill works well with:

- **MCP claude-context**: For semantic code search across Go codebase
- **MCP gopls**: For Go-specific symbol lookups, find implementations, references
- **Standard CLI tools**: grep, ripgrep, find, git
- **Go tools**:
  - `go list ./...` - List all packages
  - `go doc` - View package documentation
  - `grpcurl` - Test gRPC endpoints
- **Project-specific tools**:
  - `golangci-lint` - Code quality analysis
  - `sqlc` - View generated database code
  - Database migrations tools

## Notes

- The codebase-detective agent uses extended thinking for complex Go architecture analysis
- Semantic search (MCP claude-context) is preferred but not required
- gopls MCP provides Go-specific navigation capabilities when available
- Agent automatically falls back to grep/ripgrep/find if MCPs unavailable
- Results are actionable with file:line references
- Great for understanding clean architecture layers
- Helps trace multi-tenant authentication flows
- Identifies security patterns (tenant isolation, SQL injection prevention)
- Useful for onboarding to SSO service architecture
- Helps prevent incorrect assumptions about authentication/authorization flows

## SSO Project Structure Reference

For context, the Go SSO project follows clean architecture:

```
/internal/
├── controller/grpc/     - gRPC handlers (entry points)
├── usecase/            - Business logic layer
├── domain/
│   ├── entity/         - Domain entities
│   └── service/        - Domain services
├── infrastructure/
│   ├── storage/        - Database repositories (PostgreSQL, MongoDB)
│   └── service/        - External services (Redis)
└── config/             - Configuration management

/proto/                 - Protocol Buffer definitions (or sso-protos repo)
/queries/               - sqlc SQL query definitions
/migrations/            - Database migrations
/api_tests/            - Integration tests
```

**Key patterns to recognize:**
- Clean architecture: Controller → Usecase → Repository
- Dependency injection via interfaces
- sqlc for type-safe database queries
- gRPC for all service APIs
- Tenant isolation at every layer
- Context propagation through all layers
- Error wrapping with context: `fmt.Errorf("context: %w", err)`
