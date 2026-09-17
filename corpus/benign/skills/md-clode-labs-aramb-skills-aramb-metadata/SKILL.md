---
name: aramb-metadata
description: Generate or update aramb.toml configuration file by analyzing docker-compose files or codebase. Use this skill when you need to create project metadata, service configurations, or environment setup for aramb-orchestrated projects.
category: development
tags: [metadata, configuration, docker, devops, analysis, toml]
license: MIT
---

# Aramb Metadata Generator

Analyze project structure and generate aramb.toml configuration with service definitions only. Uses APPLICATION_ID from environment variable.

## Inputs

- `requirements`: What metadata to generate or update
- `project_path`: Root directory to analyze (defaults to current directory)
- `validation_criteria`: Self-validation criteria (critical, expected, nice_to_have)

## Prerequisites

**CRITICAL**: APPLICATION_ID environment variable MUST be set:

```bash
if [ -z "$APPLICATION_ID" ]; then
  echo "ERROR: APPLICATION_ID environment variable not set"
  echo "Set it with: export APPLICATION_ID=your-app-id"
  exit 1
fi
```

## CRITICAL RULE: Build Service Separation

**When backend code needs to be built, you MUST create TWO services:**

### 1. Build Service (type="build") - Backend Only
- **Settings**: `repoUrl`, `buildPath`, `targetBranches`, `installationId = "123456789"` (dummy value)
- **Outputs**: `outputs.IMAGE_URL` (Docker images)
- **Excludes**: `image`, `cmd`, `commandPort`, `publicNet`, vars, secrets

### 2. Runtime Service (type="backend")
- **Settings**: `image` = `${buildServiceId.outputs.IMAGE_URL}`
- **Settings**: `cmd`, `commandPort`, `publicNet`
- **Includes**: vars, secrets as needed
- **Excludes**: `repoUrl`, `buildPath`, `targetBranches`, `installationId`

### Exceptions
- **Databases** (postgres, redis, mongodb) use `image` directly without build service
- **Pre-built containers** use `image` directly without build service
- **Frontend services** are created as single services (type="frontend") with static build configuration, NO separate build service

## Task Chat Communication

Send progress updates to the task chat so users can follow along. Use `TaskUserResponse` MCP tool for key milestones:

**When to send updates:**
- **Starting**: What you're analyzing
- **Key milestones**: Services discovered, configuration generated
- **Completion**: Summary of services created in aramb.toml

**Example:**
```
TaskUserResponse(message="🔍 Analyzing project structure. Found docker-compose.yml, scanning for services...")
```

```
TaskUserResponse(message="📋 Discovered 4 services: postgres-db, backend-build, backend-api, frontend-web. Generating aramb.toml...")
```

```
TaskUserResponse(message="✅ Generated aramb.toml with 4 services. Backend uses build service (101) → runtime (102). Ready for deployment.")
```

Keep messages concise. Focus on what was discovered and created.

## Workflow

### 0. Validate APPLICATION_ID (CRITICAL FIRST STEP)

```bash
if [ -z "$APPLICATION_ID" ]; then
  echo "ERROR: APPLICATION_ID environment variable not set"
  echo "Set it with: export APPLICATION_ID=your-app-id"
  exit 1
fi

echo "Using APPLICATION_ID: $APPLICATION_ID"
```

### 1. Discover Services

**Docker Compose Analysis**:
- Search for docker-compose.yml, docker-compose.yaml, compose.yml
- Extract services, ports, environment variables, volumes, dependencies
- Identify database images (postgres:15, redis:7, mongo:6)

**Codebase Analysis** (ALWAYS required):
- **Environment files**: .env, .env.example, .env.production
- **Config files**: config.js, settings.py, application.yml, config.toml
- **Package files**: package.json, go.mod, requirements.txt, Cargo.toml
- **Source code**: Search for `process.env`, `os.Getenv()`, `os.environ`
- **Framework detection**: Express, FastAPI, Gin, Django, React, Vue, Angular, Next.js
- **Build files**: Dockerfile, Makefile, build scripts

### 2. Map Service Types

| Detected Pattern | Services to Create | Output |
|-----------------|-------------------|--------|
| Backend framework (Express, FastAPI, Gin, Django, etc.) | Build service (type="build")<br>Backend service (type="backend") | `outputs.IMAGE_URL` |
| Frontend framework (React, Vue, Angular, Next.js, etc.) | Single frontend service (type="frontend") | N/A |
| Microservice with Dockerfile | Build service (type="build")<br>Backend/template service | `outputs.IMAGE_URL` |
| Aramb agent code | Build service (type="build")<br>Aramb-agent service (type="aramb-agent") | `outputs.IMAGE_URL` |
| Database (postgres, redis, mongodb) | Single service with `image` field | N/A |
| Pre-built container | Single service with `image` field | N/A |

**Rules**:
- **Backend code to build**: TWO services (build + runtime)
- **Frontend code**: Single service (type="frontend") with static build configuration
- **Databases**: Single service with `image` only
- **Pre-built containers**: Single service with `image` only
- **Build service ID < Runtime service ID** (sequential ordering for backends)
- **Build services**: Auto-generate `installationId = "123456789"` (dummy value)

### 3. Extract Configuration

**Vars (Non-sensitive)**:
- Database: POSTGRES_DB, POSTGRES_USER, DB_HOST, DB_PORT
- Application: PORT, NODE_ENV, ENVIRONMENT, DEBUG, API_URL
- Configuration: TIMEOUT, MAX_CONNECTIONS, feature flags

**Secrets (Sensitive - leave empty)**:
- Passwords: POSTGRES_PASSWORD, DB_PASSWORD, MYSQL_PASSWORD
- Tokens: API_KEY, AUTH_TOKEN, JWT_SECRET, SECRET_KEY
- Credentials: PRIVATE_KEY, OAUTH_CLIENT_SECRET, SESSION_SECRET

**Secret Detection Keywords** (case-insensitive):
- Classify as **secret**: PASSWORD, PASSWD, PWD, SECRET, TOKEN, API_KEY, PRIVATE, CREDENTIAL, JWT, OAUTH
- Classify as **var**: HOST, PORT, URL, ENDPOINT, DATABASE, DB_NAME, DB_USER, ENVIRONMENT, DEBUG

**Service References**:
- Vars: `${uniqueIdentifier.vars.KEY}`
- Secrets: `${uniqueIdentifier.secrets.KEY}`
- Build outputs: `${uniqueIdentifier.outputs.IMAGE_URL}` or `${uniqueIdentifier.outputs.PATH}`

### 4. Generate TOML Structure

**CRITICAL**: Only create services. Do NOT create project, application, or config_status sections.

**Build Services**: Always set `installationId = "123456789"` (dummy value for all build services)

**Vars and Secrets**: Create INDEPENDENT values for database credentials:
- Database names: Use project-specific names (e.g., "notesdb", "myapp_db")
- Usernames: Use default database usernames (e.g., "postgres", "root", "admin")
- Passwords: Leave as EMPTY strings (`value = ""`)
- Ports: Use standard ports (PostgreSQL: 5432, MySQL: 3306, Redis: 6379, MongoDB: 27017)
- Hosts: Use service names for container networking (e.g., "postgres", "redis", "mongodb")

**DO NOT** use placeholders or references for basic database configuration - create actual independent values

```toml
# Example: Database Service (pre-built image)
[[services]]
uniqueIdentifier = 100
name = "postgres-db"
type = "postgres"
description = "PostgreSQL database service for application data storage"
applicationID = "8ab0de2a-385c-42f8-8671-185b108802f6"  # Actual value from $APPLICATION_ID

[services.configuration.settings]
image = "postgres:15"
commandPort = 5432
publicNet = false

[[services.configuration.vars]]
key = "POSTGRES_DB"
value = "myapp"

[[services.configuration.vars]]
key = "POSTGRES_USER"
value = "postgres"

[[services.configuration.secrets]]
key = "POSTGRES_PASSWORD"
value = ""

# Example: Backend Build Service
[[services]]
uniqueIdentifier = 101
name = "backend-build"
type = "build"
description = "Build service for backend API Docker image"
applicationID = "8ab0de2a-385c-42f8-8671-185b108802f6"  # Actual value from $APPLICATION_ID

[services.configuration.settings]
repoUrl = "https://github.com/user/repo"
buildPath = "."
targetBranches = ["main"]
installationId = "123456789"  # Dummy value - auto-generated
# Outputs: outputs.IMAGE_URL

# Example: Backend Runtime Service
[[services]]
uniqueIdentifier = 102
name = "backend-api"
type = "backend"
description = "Backend API service handling business logic and data processing"
applicationID = "8ab0de2a-385c-42f8-8671-185b108802f6"  # Actual value from $APPLICATION_ID

[services.configuration.settings]
image = "${101.outputs.IMAGE_URL}"
cmd = "npm start"
commandPort = 8080
publicNet = true

[[services.configuration.vars]]
key = "PORT"
value = "8080"

[[services.configuration.vars]]
key = "DB_HOST"
value = "localhost"

[[services.configuration.secrets]]
key = "DATABASE_URL"
value = "postgres://${100.vars.POSTGRES_USER}:${100.secrets.POSTGRES_PASSWORD}@localhost:5432/${100.vars.POSTGRES_DB}"
# ↑ SECRET because it references ${100.secrets.POSTGRES_PASSWORD}

[[services.configuration.secrets]]
key = "JWT_SECRET"
value = ""

# Example: Frontend Service (Single Service - No Build Service)
[[services]]
uniqueIdentifier = 103
name = "frontend-web"
type = "frontend"
description = "Frontend web application serving static files to users"
applicationID = "8ab0de2a-385c-42f8-8671-185b108802f6"  # Actual value from $APPLICATION_ID

[services.configuration.settings]
staticPath = "./frontend/dist"  # Local build output directory
cmd = "npx http-server"
commandPort = 8080
publicNet = true

[[services.configuration.vars]]
key = "API_URL"
value = "http://localhost:8080"
```

**IMPORTANT**:
- Do NOT create `[config_status]` section
- Use actual APPLICATION_ID value from environment variable
- Create independent database credentials (db names, usernames)
- Leave passwords as empty strings

### 5. Update Existing TOML

If aramb.toml exists:
- Read existing configuration
- Merge new services (avoid duplicates)
- Preserve existing uniqueIdentifiers
- Do NOT create or update config_status section

## Constraints

### uniqueIdentifiers
- **Services**: 100, 101, 102, ... (sequential, no gaps, no duplicates)
- **Build service ID < Runtime service ID**

### APPLICATION_ID
- **MUST** be set in environment variable
- **MUST** exit with error if not found
- **MUST** use actual APPLICATION_ID value in all services (NOT placeholder)
- **Example**: `applicationID = "8ab0de2a-385c-42f8-8671-185b108802f6"` (actual value from $APPLICATION_ID)

### Service Description
- **MUST** include `description` field for ALL services
- **MUST** be clear and concise (1-2 sentences)
- **MUST** describe the service's purpose and role in the application
- Examples:
  - Database: "PostgreSQL database service for application data storage"
  - Backend: "Backend API service handling business logic and data processing"
  - Frontend: "Frontend web application serving static files to users"
  - Build: "Build service for backend API Docker image"

### Service Types
- Supported: aramb-agent, backend, build, frontend, mongodb, onboarding, postgres, redis, template
- **Build service**: Always type="build"
- **Runtime service**: backend, frontend, aramb-agent, onboarding, template
- **Database**: postgres, redis, mongodb

### Settings Validation

**Build Service (type="build")** - Backend Only:
- **MUST have**: `description` (clear, concise service purpose)
- **MUST have**: `repoUrl`, `buildPath`, `targetBranches`, `installationId = "123456789"` (auto-generated dummy value)
- **MUST NOT have**: `image`, `cmd`, `commandPort`, `publicNet`, vars, secrets

**Backend Runtime Service (type="backend")**:
- **MUST have**: `description` (clear, concise service purpose)
- **MUST have**: `image` (reference to build output, e.g., `${101.outputs.IMAGE_URL}`)
- **MUST have**: `cmd`, `commandPort`
- **MUST NOT have**: `repoUrl`, `buildPath`, `targetBranches`, `installationId`
- **MUST have**: Corresponding build service with lower uniqueIdentifier

**Frontend Service (type="frontend")** - Single Service:
- **MUST have**: `description` (clear, concise service purpose)
- **MUST have**: `staticPath` (local path to build output, e.g., "./frontend/dist")
- **MUST have**: `cmd`, `commandPort`
- **MUST NOT have**: `repoUrl`, `buildPath`, `targetBranches`, `installationId`, `image`
- **NO build service required** - frontend builds happen locally

**Database Service (postgres, redis, mongodb)**:
- **MUST have**: `description` (clear, concise service purpose)
- **MUST have**: `image` (direct, e.g., "postgres:15")
- **MUST NOT have**: `repoUrl`, `buildPath`, `targetBranches`, `installationId`

**Pre-built Container Service**:
- **MUST have**: `description` (clear, concise service purpose)
- **MUST have**: `image` (direct, e.g., "myorg/app:latest")
- **MUST NOT have**: `repoUrl`, `buildPath`, `targetBranches`, `installationId`

**NEVER**: Both `image` (direct) and `repoUrl` in same service

### Vars & Secrets

**CRITICAL CONSTRAINT**: Secrets can ONLY be referenced in secrets, vars can be referenced anywhere

**Rules**:
1. **If a value references another service's SECRET** → it MUST be a SECRET
2. **If a value references only VARS** → it CAN be a VAR or SECRET
3. **If a value has NO references** → it CAN be a VAR or SECRET

**Example (CORRECT)**:
```toml
# Service 100: Database
[[services.configuration.secrets]]
key = "POSTGRES_PASSWORD"
value = ""

# Service 102: Backend
[[services.configuration.secrets]]  # ← SECRET because it references a secret
key = "DATABASE_URL"
value = "postgres://${100.vars.POSTGRES_USER}:${100.secrets.POSTGRES_PASSWORD}@postgres:5432/${100.vars.POSTGRES_DB}"
```

**Example (INCORRECT)**:
```toml
# Service 102: Backend
[[services.configuration.vars]]  # ✗ WRONG! References a secret but defined as var
key = "DATABASE_URL"
value = "postgres://...${100.secrets.POSTGRES_PASSWORD}..."  # ✗ Secret reference in var!
```

**Guidelines**:
- Extract from codebase analysis (env files, config files, source code)
- Never hardcode sensitive values
- Leave secrets with empty values (`""`)
- Use service references to avoid duplication
- **If referencing secrets → use secrets section**
- **If referencing only vars → use vars section**
- Services ordered by dependency (higher IDs depend on lower IDs)

## Self-Validation

**Critical checks** (MUST pass):
1. APPLICATION_ID environment variable is set
2. TOML syntax is valid
3. Structure complete: Only services (100+), NO project, application, or config_status sections
4. Service types valid: aramb-agent, backend, build, frontend, mongodb, onboarding, postgres, redis, template
5. uniqueIdentifiers sequential: 100, 101, 102, ...
6. Required fields present (service: name, type, description, applicationID)
7. All services MUST have `description` field with clear, concise text (1-2 sentences)
8. All services use actual APPLICATION_ID value from environment variable (NOT placeholder)
9. Database vars have independent values: database names, usernames, ports, hosts
10. Passwords and secrets are empty strings (`value = ""`)
9. Build service pattern followed for backends:
   - Build services (type="build") have `repoUrl`, no `cmd`
   - Backend runtime services reference build outputs, no `repoUrl`
   - Build service ID < Backend runtime service ID
10. Frontend services (type="frontend"):
   - Have `staticPath` pointing to local build directory
   - NO separate build service required
   - Have `cmd` and `commandPort`
11. Database services have `image`, no `repoUrl`
12. Vars and secrets extracted from codebase (not empty)
13. Service references valid (`${N.vars.KEY}` points to existing service)
14. Secrets empty or use references (never hardcoded)
15. **CRITICAL**: Values referencing secrets MUST be in secrets section (NOT vars)
16. **CRITICAL**: If `${N.secrets.KEY}` appears in value → must be a secret, not a var

## Error Handling

- No services detected → Create minimal template with database and backend services
- Unknown service type → Use "template" as default
- Circular dependencies → Log warning, break cycle
- Docker-compose parsing fails → Fall back to codebase analysis
- APPLICATION_ID not set → EXIT with error immediately

## Output

Return JSON summary:
```json
{
  "file_created": "aramb.toml",
  "application_id": "8ab0de2a-385c-42f8-8671-185b108802f6",
  "structure": {
    "services": 4
  },
  "services_detected": [
    {"uniqueIdentifier": 100, "name": "postgres-db", "type": "postgres", "description": "PostgreSQL database service for application data storage", "applicationID": "8ab0de2a-385c-42f8-8671-185b108802f6"},
    {"uniqueIdentifier": 101, "name": "backend-build", "type": "build", "description": "Build service for backend API Docker image", "applicationID": "8ab0de2a-385c-42f8-8671-185b108802f6"},
    {"uniqueIdentifier": 102, "name": "backend-api", "type": "backend", "description": "Backend API service handling business logic and data processing", "applicationID": "8ab0de2a-385c-42f8-8671-185b108802f6"},
    {"uniqueIdentifier": 103, "name": "frontend-web", "type": "frontend", "description": "Frontend web application serving static files to users", "applicationID": "8ab0de2a-385c-42f8-8671-185b108802f6"}
  ],
  "build_outputs": {
    "101": "outputs.IMAGE_URL → service 102"
  },
  "frontend_static_builds": {
    "103": "staticPath: ./frontend/dist (local build)"
  },
  "vars_created": {
    "100": ["POSTGRES_DB=notesdb", "POSTGRES_USER=postgres"],
    "102": ["PORT=8080", "DB_HOST=localhost"],
    "103": ["API_URL=http://localhost:8080"]
  },
  "secrets_created": {
    "100": ["POSTGRES_PASSWORD=\"\""],
    "102": ["DATABASE_URL=postgresql://...", "JWT_SECRET=\"\""]
  },
  "reference_constraints_applied": [
    "DATABASE_URL placed in secrets (references POSTGRES_PASSWORD secret)",
    "All secret references only in secrets section",
    "Var references allowed in both vars and secrets"
  ],
  "service_references": [
    "102 → 100 (DB vars/secrets)",
    "102 → 101 (IMAGE_URL)"
  ],
  "notes": [
    "All services use actual APPLICATION_ID from environment",
    "Database credentials created with independent values",
    "Passwords left empty for security",
    "Build service has dummy installationId=123456789"
  ],
  "validation_passed": true
}
```
