---
name: gromit-decompose
description: Use when decomposing implementation plans into bd beads. Reads plans, extracts tasks, and outputs JSON array of bead definitions following strict sizing rules. Non-interactive, produces machine-readable output only.
version: 1.0.0
---

# Gromit Decompose Skill

Transforms implementation plans into structured bead definitions for automated creation via `bd create`. This is a non-interactive skill that reads plans and outputs **JSON only** — no markdown, no conversation, no explanations.

## When to Use This Skill

Use this skill when:
- You have an implementation plan that needs to be broken into beads
- You're ready to create work items from a completed plan
- You need to map logical tasks to executable beads following sizing rules

## Methodology

This skill follows a strict non-interactive process:

### 1. Read the Plan

When the skill starts:
- Read the plan file from `.gromit/plans/<name>.md`
- Extract the plan frontmatter (especially `id` and `source_spec`)
- Read the Implementation Tasks section
- Understand task dependencies and files affected

**DO NOT** output any text at this stage. Work silently.

### 2. Apply Bead Sizing Rules

Each task in the plan must be mapped to 1-3 beads following these **strict sizing rules**:

**Bead Sizing Rules:**
- **One deliverable behavior per bead** — A single observable change that a caller or user could verify. Not "one file" or "one concern," but one unit of working functionality
- **1-3 acceptance criteria** — Concrete, testable criteria only; split if more than 3
- **Soft file limit of 4-5** — If touching 6+ files across unrelated packages, consider splitting. But touching interface.go, impl.go, mock_test.go, and impl_test.go for one method addition is fine — that's one change, not four
- **Self-contained** — Understandable without reading other beads
- **No ambiguity** — Claude implements without making design decisions
- **Clear definition of done** — Each criterion has an obvious pass/fail test

**Grouping Rules (Never Split These):**
- **Interface + implementation + mock updates** — In Go, changing an interface requires updating all implementations and mocks to compile. This is one change, not three beads
- **Implementation + its tests** — Claude writes tests alongside implementation. Under ATDD, they're explicitly the same workflow. Never create a separate "write tests for X" bead
- **Companion methods in the same package** — Methods that follow the same pattern in the same file (e.g., `ReadyWithLabel` and `ListWithLabel`) are one bead. If you'd copy-paste-modify to create the second, they belong together
- **Command flags + the wiring that makes them work** — A CLI flag that does nothing isn't a deliverable. The flag, its plumbing through to the runner, and its effect are one bead
- **Template + its registration** — Adding a template file and registering it in the renderer are one action, not two

**Splitting Logic:**
- If a task has 4+ acceptance criteria → split into multiple beads with 1-3 criteria each
- If a task touches 6+ files across unrelated packages → split by package boundary
- If two parts of a task are independently useful and don't need each other to compile → they can be separate beads
- If a task requires design decisions that would benefit from being settled first (e.g., define the data model, then build the API) → split at the decision boundary
- Never split natural units like Interface + implementation + mock, implementation + tests, companion methods, command flags+wiring, or template+registration

**DO NOT** create beads that are too small (e.g., single-line changes) unless they're genuinely independent concerns.

### 3. Map Tasks to Beads

For each task in the plan:

1. **Assess complexity**: Count files, count acceptance criteria, identify concerns
2. **Decide split strategy**: If the task exceeds sizing rules, determine how to split
3. **Create bead definitions**: Generate 1-3 beads per task with proper metadata

**Bead Definition Fields:**
- `title`: Clear, concise title (imperative form: "Add X", "Implement Y", "Fix Z")
- `description`: 2-4 sentences describing what needs to be done, including files to touch
- `priority`: `P1` (use plan's default priority — P1 for most features)
- `acceptance_criteria`: Array of 1-3 concrete, testable criteria
- `covers_tasks`: Array of 1-based plan task numbers this bead covers (must reference `### Task N:` headings from the plan)
- `depends_on_index`: Array of zero-based indices of beads this depends on (or empty array if no dependencies)
- `estimated_files`: Integer estimate of how many files this bead will touch

**Title Guidelines:**
- Start with a verb: "Add", "Implement", "Create", "Update", "Fix", "Refactor"
- Be specific: "Add JWT token validation" not "Add auth"
- Keep it under 60 characters
- Reflect the bead's single concern

**Description Guidelines:**
- First sentence: What to do
- Second sentence: Which files to modify/create
- Optional third sentence: Key implementation notes
- Reference specific functions, types, or APIs if helpful
- Ensure the described scope aligns with a realistic `estimated_files` value
- DO NOT include rationale or background — keep it action-oriented

**Acceptance Criteria Guidelines:**
- Use observable, testable language
- Start with a verb: "Returns", "Validates", "Creates", "Updates", "Throws"
- Be concrete: "Validates JWT signature using RS256" not "Handles tokens correctly"
- Avoid vague terms: "properly", "correctly", "as expected"

**Dependency Mapping:**
- Beads are ordered in the output array
- `depends_on_index` references the array index (0-based) of prerequisite beads
- If task A depends on task B, and B maps to beads [0, 1], A's beads should depend on [0, 1]
- If splitting a task, later parts of the same task should depend on earlier parts

### 4. Output JSON Only

Output a JSON array of bead definitions. **DO NOT** output any markdown, explanations, or conversational text.

**Output Format:**
```json
[
  {
    "title": "Create user model with profile fields",
    "description": "Define User struct in internal/models/user.go with fields for name, email, avatar_url, and bio. Include JSON tags for API serialization.",
    "priority": "P1",
    "acceptance_criteria": [
      "User struct defined with name, email, avatar_url, and bio fields",
      "Fields have appropriate JSON tags for serialization",
      "Struct includes validation tags for required fields"
    ],
    "covers_tasks": [1],
    "depends_on_index": [],
    "estimated_files": 2
  },
  {
    "title": "Implement profile storage interface",
    "description": "Create ProfileStore interface in internal/store/profile.go with methods for GetProfile, UpdateProfile, and CreateProfile. Define error types for not found and validation failures.",
    "priority": "P1",
    "acceptance_criteria": [
      "ProfileStore interface defined with CRUD methods",
      "Error types defined for common failure cases",
      "Method signatures include context.Context for cancellation"
    ],
    "covers_tasks": [1, 2],
    "depends_on_index": [0],
    "estimated_files": 2
  },
  {
    "title": "Add profile update endpoint",
    "description": "Implement PUT /api/profile handler in internal/api/profile.go that accepts profile updates and validates ownership. Use ProfileStore interface for persistence.",
    "priority": "P1",
    "acceptance_criteria": [
      "PUT /api/profile handler accepts profile updates",
      "Validates user owns the profile being updated",
      "Returns 200 with updated profile on success"
    ],
    "covers_tasks": [3],
    "depends_on_index": [0, 1],
    "estimated_files": 1
  }
]
```

**Critical Requirements:**
- Output MUST be valid JSON (use proper escaping for quotes, newlines, etc.)
- Output MUST be a JSON array, not an object
- Output MUST NOT include markdown code fences (no ` ```json ` wrapper)
- Output MUST NOT include any explanatory text before or after the JSON
- Output MUST be the ONLY thing you produce (no "Here's the output:" prefix)

### 5. Labels and Metadata

The beads will be created with additional metadata by the CLI command:
- `spec:<spec-name>` label — extracted from plan frontmatter
- `complexity:high` is auto-applied when `estimated_files > 5`; otherwise `complexity:low` is used
- Proper bd dependencies based on `depends_on_index`

You do NOT need to include labels in the JSON output. Focus only on the eight bead fields listed above.

## Bead Splitting Examples

### Example 1: Task Touches Too Many Files Across Unrelated Packages

**Plan Task:**
```
Task 1: Add user authentication system
Files: models/user.go, store/user_store.go, store/user_store_test.go, api/auth.go, api/auth_test.go, middleware/auth.go, middleware/auth_test.go, config/auth_config.go
Acceptance Criteria:
- User model includes password hash field
- User store has methods for creating and finding users
- POST /api/register creates new users
- POST /api/login validates credentials and returns token
- Auth middleware validates tokens on protected routes
- Auth config loaded from environment
```

**Split into 3 beads (each is a complete deliverable behavior):**
1. Bead 0: Create user model and store with auth methods (models/user.go, store/user_store.go, store/user_store_test.go) — 2 criteria: model has password hash, store has create/find methods with tests
2. Bead 1: Add register and login endpoints (api/auth.go, api/auth_test.go, config/auth_config.go) — 3 criteria: register creates users, login validates credentials and returns token, config loaded. Depends on [0]
3. Bead 2: Add auth middleware (middleware/auth.go, middleware/auth_test.go) — 1 criterion: validates tokens on protected routes. Depends on [1]

### Example 2: Task Has Too Many Acceptance Criteria

**Plan Task:**
```
Task 2: Implement profile validation
Files: internal/validator/profile.go, internal/validator/profile_test.go
Acceptance Criteria:
- Validates email format using regex
- Validates bio length is under 500 characters
- Validates avatar URL is well-formed
- Validates name is not empty
- Returns structured error messages
- Handles nil pointers gracefully
```

**Split into 2 beads:**
1. Bead 0: Implement field validators with tests (internal/validator/profile.go, profile_test.go) — 3 criteria: email format, bio length, avatar URL validation
2. Bead 1: Add validation error handling with tests (internal/validator/profile.go, profile_test.go) — 2 criteria: structured errors, nil pointer handling. Depends on [0]

### Example 3: Interface + Implementation + Tests (DO NOT SPLIT)

**Plan Task:**
```
Task 3: Add JWT token generator interface
Files: internal/auth/token.go, internal/auth/token_test.go, internal/auth/mocks/mock_token.go
Acceptance Criteria:
- TokenGenerator interface defined with Generate and Validate methods
- JWT implementation generates tokens with user ID and expiration
- JWT implementation signs tokens with RS256 algorithm
- Unit tests cover token generation and validation
```

**One bead (natural unit):**
1. Bead 0: Add TokenGenerator interface with JWT implementation (internal/auth/token.go, token_test.go, mocks/mock_token.go) — All 4 criteria. This is interface+implementation+mock+tests for one feature, so it stays together.

## Key Principles

1. **Non-interactive** — No conversation, no questions, no explanations
2. **JSON only** — Output must be valid JSON, nothing else
3. **Strict sizing** — Enforce 1-3 criteria per bead, soft limit of 4-5 files (split at 6+ across unrelated packages)
4. **Self-contained beads** — Each bead is understandable on its own
5. **Concrete criteria** — Every acceptance criterion must be testable
6. **Dependency integrity** — Preserve task dependencies when splitting

## Common Mistakes to Avoid

1. **Outputting markdown**: DO NOT wrap JSON in code fences or add explanatory text
2. **Too many criteria**: If you're creating a bead with 4+ criteria, you need to split it
3. **Too many files**: If a bead touches 6+ files across unrelated packages, it's too large (but interface+impl+mock+test for one feature is fine)
4. **Vague criteria**: "Works correctly" is not testable; "Returns 404 when user not found" is
5. **Missing dependencies**: If bead B uses types from bead A, B must depend on A
6. **Breaking atomicity**: Each bead should be independently committable
7. **Splitting natural units**: Never split interface+implementation+mock, implementation+tests, companion methods, flags+wiring, or template+registration

## Model and Complexity

This skill uses **haiku** for cost-effective, fast processing. The task is well-defined and mechanical — no complex decisions required. The plan has already been reviewed and approved by a human, so decompose is purely execution.

## Integration with Gromit Pipeline

This skill is the **Decompose** stage in Gromit's four-stage pipeline:
1. **Capture** (`gromit add`) - Raw ideas → backlog entries
2. **Refine** (`gromit refine`) - Backlog items or ad-hoc ideas → specs
3. **Plan** (`gromit plan`) - Specs → implementation plans
4. **Decompose** (`gromit decompose`) - Plans → bd beads (THIS SKILL)

The JSON you produce is consumed by the CLI, which creates beads via `bd create` and adds labels.
