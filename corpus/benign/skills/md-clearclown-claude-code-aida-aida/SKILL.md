---
name: aida
description: |
  AIDA - Multi-agent project generation with auto-init and full pipeline execution.
  Generate a complete project using multi-agent orchestration with TDD and quality gates.
  Enforces strict quality requirements via Stop Hooks (ralph-loop style).
tools: Read, Write, Edit, Bash, Glob, Grep, Task
hooks:
  Stop:
    - hooks:
        - type: command
          command: "$CLAUDE_PROJECT_DIR/hooks/stop/quality-gate-enforcer.sh"
          timeout: 300
  SubagentStop:
    - hooks:
        - type: command
          command: "$CLAUDE_PROJECT_DIR/hooks/stop/subagent-validator.sh"
          timeout: 120
---

# AIDA

Generate a complete project using multi-agent orchestration with TDD and quality gates.

## Usage

```
/aida "Create a Twitter clone with Go backend and React frontend"
```

---

## MANDATORY EXECUTION PROTOCOL

**You MUST follow this protocol exactly. Do NOT deviate.**

This command combines `/aida:init` + `/aida:start` + quality verification.

---

## What This Command Does

1. **Auto-Init**: Creates output directories and validates environment
2. **Session Start**: Initializes session state with full tracking
3. **Spec Generation**: Launches Leader-Spec for phases 1-4 via Task tool
4. **Implementation**: Launches Leader-Impl for TDD implementation via Task tool
5. **Quality Gates**: Verifies all 18 quality gates pass (enforced by Stop Hook)
6. **Completion**: Reports final project location with verification

---

## STRICT MODE (DEFAULT)

AIDA operates in **strict mode** by default:

### Enforcement via Stop Hook

When AIDA attempts to complete, the Stop Hook intercepts and:
1. Runs `./scripts/quality-gates.sh` automatically
2. **Blocks exit** if any gate fails (exit code 2)
3. Forces iteration until ALL requirements are met
4. **Allows exit** only when ALL gates pass (exit code 0)

### Quality Requirements (MANDATORY)

| Requirement | Minimum | Enforced By |
|-------------|---------|-------------|
| Backend Tests | **80+** | Stop Hook |
| Frontend Tests | **100+** | Stop Hook |
| E2E Tests | **20+** (actual execution) | Stop Hook + Gate 19 |
| Backend Coverage | **75%+** | Stop Hook |
| Frontend Coverage | **70%+** | Stop Hook |
| Docker | Build/Run/Health/E2E | Quality Gates |
| TDD Evidence | **10+ files** | Gate 20 |

### Completion Condition

**"DONE" can ONLY be output when:**
- All **20** quality gates PASS (including Gate 19: E2E, Gate 20: TDD Evidence)
- Stop Hook returns exit code 0
- `quality_gates_passed: true` in session.json
- **E2E tests actually executed** against running Docker containers
- **TDD evidence recorded** with RED-GREEN-REFACTOR cycle

### Gate 19: E2E Test Execution

Gate 19 は Docker が起動中に Playwright E2E テストを実際に実行:

```
Gate 6: Docker Run → Gate 7: Health Check → Gate 19: E2E Execution → Cleanup
```

**E2Eテストファイルの存在だけでは不十分。実際に実行してPASSする必要がある。**

### Gate 20: TDD Evidence Verification

Gate 20 はTDDサイクル（RED-GREEN-REFACTOR）の証拠を検証:

```bash
# TDDサイクルを記録
./scripts/tdd-logger.sh start <feature>
./scripts/tdd-logger.sh red <test-file>
./scripts/tdd-logger.sh green <test-file>
./scripts/tdd-logger.sh refactor "<changes>"
./scripts/tdd-logger.sh complete
```

**証拠は `.aida/tdd-evidence/` に保存。10+ ファイル必須。**

**No exceptions. No shortcuts. No manual overrides.**

---

## Step 1: Auto-Initialize

Create all required directories:
```bash
mkdir -p .aida/state .aida/checkpoints .aida/artifacts/requirements .aida/artifacts/designs .aida/tasks .aida/results .aida/specs .aida/errors .aida/tdd-evidence
```

Derive project name from user request:
- Convert to kebab-case
- Maximum 20 characters
- Examples:
  - "Create a Twitter clone" → `twitter-clone`
  - "Build todo app with auth" → `todo-app`
  - "Simple notes application" → `notes-app`

---

## Step 2: Create Session

Create `.aida/state/session.json`:
```json
{
  "session_id": "<UUID>",
  "started_at": "<ISO8601>",
  "mode": "aida",
  "current_phase": "SPEC_PHASE",
  "phase": 1,
  "phase_name": "extraction",
  "user_request": "$ARGUMENTS",
  "project_name": "<derived>",
  "phase_history": [
    {"phase": "INITIALIZING", "entered_at": "<ISO8601>", "exited_at": "<ISO8601>"}
  ],
  "leaders": {
    "spec": "pending",
    "impl": "pending"
  },
  "active_agents": [],
  "completed_tasks": [],
  "pending_tasks": ["spec-requirements", "spec-design", "spec-tasks", "impl-backend", "impl-frontend", "impl-docker", "quality-gates"]
}
```

Create `.aida/kanban.md`:
```markdown
# Project Kanban - {{PROJECT_NAME}}

## Current Status: SPEC_PHASE (Phase 1)

## Spec Phase
- [ ] Phase 1: Extraction & Architecture
- [ ] Phase 2: Structure & Schema
- [ ] Phase 3: Alignment
- [ ] Phase 4: Verification

## Impl Phase
- [ ] Backend Implementation (TDD)
- [ ] Frontend Implementation (TDD)
- [ ] Docker Setup

## Quality Gates (ALL 19 MUST PASS)
- [ ] Gate 1: Backend Build
- [ ] Gate 2: Backend Tests
- [ ] Gate 3: Frontend Build
- [ ] Gate 4: Frontend Tests
- [ ] Gate 5: Docker Build
- [ ] Gate 6: Docker Run
- [ ] Gate 7: Health Check
- [ ] Gate 19: E2E Test Execution (Playwright)
```

---

## Step 3: Launch Leader-Spec (Phases 1-4)

<MANDATORY_ACTION id="launch-leader-spec">

**YOU MUST INVOKE THE TASK TOOL NOW.**

Do NOT just describe the Task tool call - actually execute it.

Use these exact parameters:

| Parameter | Value |
|-----------|-------|
| description | "Leader-Spec: Specification Phases 1-4" |
| subagent_type | "general-purpose" |
| model | "sonnet" |
| run_in_background | false |
| prompt | See below |

**Task Prompt:**

```
You are AIDA Leader-Spec agent.

## CRITICAL INSTRUCTION
Read and follow the full instructions in: agents/leader-spec.md

## Current Session
- Session ID: {{SESSION_ID}}
- Project: {{PROJECT_NAME}}
- User Request: {{USER_REQUEST}}
- Working Directory: {{CWD}}

## Your Mission

Execute Phases 1-4 of the AIDA pipeline:

### Phase 1: Extraction & Architecture
1. Analyze user requirements thoroughly
2. Extract core features and constraints
3. Design high-level architecture
4. Write .aida/artifacts/requirements/extraction.md

### Phase 2: Structure
1. Define directory structure
2. Create data schemas
3. Define API contracts
4. Write .aida/artifacts/designs/structure.md

### Phase 3: Alignment
1. Verify requirements consistency
2. Check for conflicts or gaps
3. Write .aida/artifacts/alignment.md

### Phase 4: Verification & Output
1. Review all specs for completeness
2. Write final specifications:
   - .aida/specs/{{PROJECT}}-requirements.md (comprehensive, min 500 bytes)
   - .aida/specs/{{PROJECT}}-design.md (technical design, min 500 bytes)
   - .aida/specs/{{PROJECT}}-tasks.md (implementation tasks)

## Player Delegation
For parallel tasks, spawn player subagents using Task tool:
- subagent_type: "general-purpose"
- model: "haiku"
- Read agents/player.md for player protocol

## Completion Checklist
Before completing, verify:
- [ ] .aida/specs/{{PROJECT}}-requirements.md exists (min 500 bytes)
- [ ] .aida/specs/{{PROJECT}}-design.md exists (min 500 bytes)
- [ ] .aida/specs/{{PROJECT}}-tasks.md exists

## Completion Report
Write to .aida/results/spec-complete.json:
{
  "task_id": "spec-{{PROJECT}}",
  "status": "completed",
  "completed_at": "ISO8601",
  "outputs": {
    "requirements": ".aida/specs/{{PROJECT}}-requirements.md",
    "design": ".aida/specs/{{PROJECT}}-design.md",
    "tasks": ".aida/specs/{{PROJECT}}-tasks.md"
  },
  "summary": "Specification phases 1-4 complete"
}

Update .aida/state/session.json with:
- current_phase: "IMPL_PHASE"
- phase: 5
- leaders.spec: "completed"
```

</MANDATORY_ACTION>

**STOP: Do NOT proceed to Step 4 until Task tool has been invoked and Leader-Spec completes.**

---

## Step 4: Validate Specs

After Leader-Spec completes, validate:

```bash
./scripts/validate-outputs.sh {{PROJECT}} spec
```

**If validation fails:**
1. Report which files are missing
2. Re-spawn Leader-Spec to complete
3. Do NOT proceed until specs are valid

**If validation passes:**
- Continue to Step 5

---

## Step 5: Launch Leader-Impl (Phase 5)

<MANDATORY_ACTION id="launch-leader-impl">

**YOU MUST INVOKE THE TASK TOOL NOW.**

Do NOT just describe the Task tool call - actually execute it.

Use these exact parameters:

| Parameter | Value |
|-----------|-------|
| description | "Leader-Impl: TDD Implementation Phase" |
| subagent_type | "general-purpose" |
| model | "sonnet" |
| run_in_background | false |
| prompt | See below |

**Task Prompt:**

```
You are AIDA Leader-Impl agent.

## CRITICAL INSTRUCTION
Read and follow the full instructions in: agents/leader-impl.md

## Current Session
- Session ID: {{SESSION_ID}}
- Project: {{PROJECT_NAME}}
- Working Directory: {{CWD}}

## Specifications (MUST READ)
- .aida/specs/{{PROJECT}}-requirements.md
- .aida/specs/{{PROJECT}}-design.md
- .aida/specs/{{PROJECT}}-tasks.md

## TDD Protocol (MANDATORY)
Every implementation MUST follow:
1. RED: Write failing test FIRST
2. GREEN: Minimal code to pass test
3. REFACTOR: Clean up while tests pass

NO code without tests. NO tests without running them.

## Player Delegation (MANDATORY - ALL THREE PLAYERS)

### Backend Player
- subagent_type: "general-purpose"
- model: "haiku"
- Must produce: backend/ (in project directory)
- Must have: minimum 5 test files (*_test.go)
- All tests MUST pass

### Frontend Player (MANDATORY - SEPARATE)
- subagent_type: "general-purpose"
- model: "haiku"
- Must initialize with: npm create vite@latest frontend -- --template react-ts
- Must produce: frontend/ (in project directory)
- Must have: minimum 3 test files (*.test.tsx)
- All tests MUST pass

### Docker Player
- subagent_type: "general-purpose"
- model: "haiku"
- Must produce: docker-compose.yml, Dockerfiles
- Use Podman-compatible image paths: docker.io/library/...

## Quality Gates (ALL MUST PASS)
After all players complete, run:
./scripts/quality-gates.sh {{PROJECT}}

Gates:
1. Backend Build: go build ./...
2. Backend Tests: go test ./...
3. Frontend Build: npm run build
4. Frontend Tests: npm test -- --run
5. Docker Build: docker compose build
6. Docker Run: docker compose up -d
7. Health Check: curl localhost:8080/health

## Completion Checklist
Before completing:
- [ ] Backend directory has working Go code
- [ ] Backend has minimum 5 test files
- [ ] Frontend directory has working React code (NOT EMPTY)
- [ ] Frontend has minimum 3 test files
- [ ] Docker compose works
- [ ] ALL quality gates pass

## Completion Report
Write to .aida/results/impl-complete.json:
{
  "task_id": "impl-{{PROJECT}}",
  "status": "completed",
  "completed_at": "ISO8601",
  "project_path": "./",
  "quality_gates": {
    "backend_build": true,
    "backend_tests": true,
    "frontend_build": true,
    "frontend_tests": true,
    "docker_build": true,
    "docker_run": true,
    "health_check": true,
    "all_passed": true
  },
  "verification": {
    "backend": {"test_count": N, "test_output": "..."},
    "frontend": {"test_count": N, "test_output": "..."}
  },
  "summary": "Implementation complete, all quality gates passed"
}

Update .aida/state/session.json:
- current_phase: "COMPLETED"
- leaders.impl: "completed"
```

</MANDATORY_ACTION>

**STOP: Wait for Task tool completion before proceeding.**

---

## Step 6: Run Quality Gates

After Leader-Impl completes, run full verification:

```bash
./scripts/quality-gates.sh {{PROJECT}}
```

**All 7 gates MUST pass:**
1. Backend Build
2. Backend Tests
3. Frontend Build
4. Frontend Tests
5. Docker Build
6. Docker Run
7. Health Check

**If any gate fails:**
1. Identify the failure
2. Fix or re-spawn appropriate player
3. Re-run gates until all pass

---

## Step 7: Report Completion

After all quality gates pass:

Update `.aida/kanban.md`:
```markdown
# Project Kanban - {{PROJECT_NAME}}

## Status: COMPLETED

## Spec Phase - COMPLETE
- [x] Phase 1: Extraction & Architecture
- [x] Phase 2: Structure & Schema
- [x] Phase 3: Alignment
- [x] Phase 4: Verification

## Impl Phase - COMPLETE
- [x] Backend Implementation (TDD)
- [x] Frontend Implementation (TDD)
- [x] Docker Setup

## Quality Gates - ALL PASSED
- [x] Gate 1: Backend Build
- [x] Gate 2: Backend Tests
- [x] Gate 3: Frontend Build
- [x] Gate 4: Frontend Tests
- [x] Gate 5: Docker Build
- [x] Gate 6: Docker Run
- [x] Gate 7: Health Check
- [x] Gate 19: E2E Test Execution (Playwright)
```

**Final Output:**

```
AIDA Complete

Session: {{SESSION_ID}}
Project: {{PROJECT_NAME}}
Duration: {{DURATION}}

Generated Artifacts:
- Specs: .aida/specs/{{PROJECT}}-*.md
- Project: ./

Quality Gates: 7/7 PASSED
- Backend Build: PASS
- Backend Tests: PASS
- Frontend Build: PASS
- Frontend Tests: PASS
- Docker Build: PASS
- Docker Run: PASS
- Health Check: PASS

TDD Verification:
- Backend: {{N}} test files, all passing
- Frontend: {{N}} test files, all passing

To run the project:
  docker compose up -d
  open http://localhost:5173

To verify quality gates again:
  ./scripts/quality-gates.sh
```

---

## Multi-Agent Architecture

```
/aida "Create X"
    |
    +-- Step 1: Auto-Initialize (directories)
    |
    +-- Step 2: Create Session (session.json, kanban.md)
    |
    +-- Step 3: Task tool (sonnet) --> [Leader-Spec]
    |                                      |
    |                                      +-- Task tool (haiku) --> [Player]
    |                                      +-- Task tool (haiku) --> [Player]
    |                                      |
    |                                      +--> .aida/specs/
    |
    +-- Step 4: Validate Specs (validate-outputs.sh)
    |
    +-- Step 5: Task tool (sonnet) --> [Leader-Impl]
    |                                      |
    |                                      +-- Task tool (haiku) --> [Backend Player]
    |                                      +-- Task tool (haiku) --> [Frontend Player]
    |                                      +-- Task tool (haiku) --> [Docker Player]
    |                                      |
    |                                      +--> ./
    |
    +-- Step 6: Quality Gates (quality-gates.sh)
    |       |
    |       +-- 7 mandatory gates
    |
    +-- Step 7: Report Completion
```

---

## CRITICAL REQUIREMENTS

1. **Task tool MUST be invoked** - Leaders run as subagents via Task tool
2. **Wait for completion** - `run_in_background: false` ensures sequential execution
3. **Verify outputs exist** - Check spec files were actually created
4. **All quality gates MUST pass** - No success without 7/7
5. **TDD mandatory** - No code without tests
6. **Frontend SEPARATE** - Must spawn dedicated Frontend Player
7. **Model selection** - Leaders: `sonnet`, Players: `haiku`

---

## Status Check

To check progress during or after execution:
```
/aida:status
```

---

## Validation Commands

```bash
# Validate spec outputs
./scripts/validate-outputs.sh {{PROJECT}} spec

# Validate impl outputs
./scripts/validate-outputs.sh {{PROJECT}} impl

# Verify TDD compliance
./scripts/verify-tdd.sh {{PROJECT}} all

# Run all quality gates
./scripts/quality-gates.sh {{PROJECT}}
```

---

## Related Commands

| Command | Description |
|---------|-------------|
| `/aida:init` | Initialize directories only |
| `/aida:start` | Start spec phase only |
| `/aida:work` | Continue current phase |
| `/aida:status` | Check current status |
| `/aida:pipeline` | Full automation (same as /aida) |
| `/aida:resume` | **Continue from last session state** |
| `/aida:fix <project>` | **Fix existing project to meet all quality gates** |
