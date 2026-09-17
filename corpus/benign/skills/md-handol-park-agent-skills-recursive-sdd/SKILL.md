---
name: recursive-sdd
description: "Enhanced Spec-Driven Development (SDD) framework with recursive decomposition for large-scale features. Use when a feature is too large for a single spec (multi-service features, 5+ atomic components, complex dependency graphs, or features spanning multiple domains). Provides structured workflow: Blueprint (product discovery) to Parent Spec (orchestrator with decomposition map) to Atomic Specs (standard SPEC-XXX.md). Includes tools for dependency validation, visualization, progress tracking, and integration test generation."
---

# Recursive SDD Framework

Enhanced Spec-Driven Development with recursive decomposition for handling large-scale features that cannot fit in a single spec.

## When to Use This Skill

Use this skill when a feature is **too large for a single spec**:

- **Multi-service features**: Spans multiple services/domains (e.g., "Add real-time collaboration with WebRTC, presence tracking, and conflict resolution")
- **Complex component features**: Requires 5+ interdependent atomic components (e.g., "Complete authentication system with OAuth, 2FA, session management")
- **Dependency-heavy features**: Has complex dependency graphs where sequencing is critical (e.g., "Migration from monolith to microservices for payment processing")
- **General rule**: Any feature that can't be clearly specified in one atomic spec

## Framework Overview

The Recursive SDD Framework extends the standard SDD workflow with three phases:

```
Phase A: Blueprint (Product Discovery)
   └─> Define domains, interfaces, contracts

Phase B: Parent Spec (Orchestrator)
   └─> Decomposition map, dependency graph, build order

Phase C: Recursive Implementation
   └─> Each atomic spec follows standard SDD loop (Spec → Tests → Code → Verify)
```

## Phase A: Create the Blueprint

The Blueprint is a **structural document** that defines boundaries without implementation details.

### Create Blueprint

```bash
node scripts/init-blueprint.js "Feature Name"
```

### Fill in Blueprint Sections

1. **Executive Summary**: What is this feature? Why does it need decomposition?

2. **System of Systems**: High-level domains this feature touches
   - Define responsibility, technologies, current state for each domain

3. **Interface Contracts**: APIs/Events between domains (enables parallel development)
   - Define type (REST API, GraphQL, Event Bus, WebSocket, gRPC)
   - Document purpose and key endpoints/events

4. **Non-Functional Requirements**: Performance, security, reliability, observability

5. **Risks and Constraints**: Technical risks, resource constraints, dependencies

### Get Approval

Mark Blueprint as `[APPROVED]` before proceeding to Phase B.

## Phase B: Create the Parent Spec

The Parent Spec is an **orchestrator document** that maps the decomposition.

### Create Parent Spec

```bash
node scripts/init-parent-spec.js "Feature Name"
```

Auto-generates PARENT-SPEC-XXX number and creates template.

### Fill in Decomposition Map

1. **Atomic Specs Table**: List all atomic components

| Spec ID  | Title             | Description                 | Status  | Dependencies       |
| -------- | ----------------- | --------------------------- | ------- | ------------------ |
| SPEC-010 | WebSocket Handler | Real-time message transport | PENDING | -                  |
| SPEC-011 | Presence Tracker  | User online/offline state   | PENDING | SPEC-010           |
| SPEC-012 | Conflict Resolver | Merge concurrent edits      | PENDING | SPEC-010, SPEC-011 |

**Status values**: PENDING → DRAFT → APPROVED → IMPLEMENTED → INTEGRATED

2. **Dependency Graph**: Visual representation (Mermaid)
   - Auto-generated with: `node scripts/visualize-dependencies.js PARENT-SPEC-XXX`

3. **Build Order**: Phases based on dependency graph
   - Auto-calculated with: `node scripts/validate-dependencies.js PARENT-SPEC-XXX`

4. **Integration Points**: How components integrate
   - Define integration type, test scenarios, acceptance criteria

5. **Integration Testing Strategy**: E2E test plan
   - Auto-generate template: `node scripts/generate-integration-tests.js PARENT-SPEC-XXX`

## Phase C: Implement Atomic Specs

Each atomic spec follows the standard SDD loop.

### Create Atomic Spec

```bash
node scripts/init-atomic-spec.js "Component Name" --parent PARENT-SPEC-001
```

Creates a standard `SPEC-XXX.md` file following the existing SDD template.

### Standard SDD Loop for Each Atomic Spec

1. **Define**: Fill in requirements, design, implementation plan
2. **Approve**: Get approval, mark `[APPROVED]`
3. **Test**: Write tests (must fail initially)
4. **Implement**: Write the code
5. **Verify**: Tests pass, mark `[IMPLEMENTED]`
6. **Integrate**: Passes integration tests, mark `[INTEGRATED]`

## Tools

### Dependency Validation

Check for circular dependencies and validate build order:

```bash
node scripts/validate-dependencies.js PARENT-SPEC-001
```

**Output:**

- ❌ Circular dependencies (with cycle paths)
- ❌ Missing dependencies
- ✅ Valid dependency graph
- 📋 Suggested build order (phases that can be built in parallel)

### Dependency Visualization

Generate or update Mermaid diagram:

```bash
node scripts/visualize-dependencies.js PARENT-SPEC-001
```

**Options:**

- Default: Updates the Mermaid block in the parent spec
- `--output diagram.md`: Writes to separate file

**Features:**

- Color-coded by status (IMPLEMENTED=green, APPROVED=blue, DRAFT=yellow)
- Shows dependency arrows
- Auto-generates node IDs

### Progress Tracking

Track completion of all atomic specs:

```bash
node scripts/track-progress.js PARENT-SPEC-001
```

**Output:**

- 📊 Overall progress bar
- Status breakdown (PENDING, DRAFT, APPROVED, IMPLEMENTED, INTEGRATED)
- ⚠️ Mismatches between table status and actual file status
- 📋 Next actions (specs ready to create, approve, implement, or integrate)

### Integration Test Generation

Auto-generate integration test templates from integration points:

```bash
node scripts/generate-integration-tests.js PARENT-SPEC-001
```

**Generates:**

- Python test file with pytest fixtures
- Test cases for each integration point
- E2E flow test
- Error propagation test
- Performance under load test

## Workflow Summary

### Starting a Large Feature

1. Create Blueprint: `node scripts/init-blueprint.js "Feature Name"`
2. Fill in domains, contracts, NFRs
3. Get Blueprint approved
4. Create Parent Spec: `node scripts/init-parent-spec.js "Feature Name"`
5. Define decomposition map, dependencies
6. Validate dependencies: `node scripts/validate-dependencies.js PARENT-SPEC-XXX`
7. Visualize graph: `node scripts/visualize-dependencies.js PARENT-SPEC-XXX`
8. Generate integration tests: `node scripts/generate-integration-tests.js PARENT-SPEC-XXX`

### Implementing Atomic Components

For each atomic spec (following build order):

1. Create spec: `node scripts/init-atomic-spec.js "Component" --parent PARENT-SPEC-XXX`
2. Follow standard SDD loop (Spec → Approve → Tests → Code → Verify)
3. Update parent spec table with status
4. Track progress: `node scripts/track-progress.js PARENT-SPEC-XXX`

### Integration Phase

1. All atomic specs marked `[IMPLEMENTED]`
2. Run integration tests (auto-generated template)
3. Fix integration issues
4. Mark specs as `[INTEGRATED]` when tests pass
5. Feature complete!

## Integration with Existing Workflow

This skill **extends** the existing SDD workflow (WORKFLOW.md):

- **Blueprint** and **Parent Spec**: New document types for large features
- **Atomic Specs**: Standard `SPEC-XXX.md` format (no changes to existing workflow)
- **Tests**: Follow existing TDD approach (tests before code)
- **Verification**: Standard `make test`, `make format`, `make lint`

**File locations:**

- All specs (Blueprint, Parent, Atomic) → `workspace/specs/`
- Integration tests → `workspace/tests/integration/`

## Best Practices

1. **Keep atomic specs small**: Each should be independently testable and deployable
2. **Define interfaces early**: Enables parallel development of atomic components
3. **Validate dependencies often**: Catch circular dependencies early
4. **Update parent spec status**: Keep decomposition table in sync with actual progress
5. **Test integration continuously**: Don't wait until all components are done
6. **Use build order**: Implement in dependency order to avoid blockers

## Example: Real-time Collaboration Feature

**Blueprint** defines:

- Domains: WebSocket layer, Presence service, Conflict resolution, UI components
- Contracts: WebSocket events, Presence API, Conflict resolution API

**Parent Spec** decomposes to:

- SPEC-010: WebSocket Handler (no deps)
- SPEC-011: Presence Tracker (depends on SPEC-010)
- SPEC-012: Conflict Resolver (depends on SPEC-010)
- SPEC-013: UI Integration (depends on SPEC-011, SPEC-012)

**Build order**:

1. Phase 1: SPEC-010 (can start immediately)
2. Phase 2: SPEC-011, SPEC-012 (parallel after Phase 1)
3. Phase 3: SPEC-013 (after Phase 2)

**Integration tests** verify:

- WebSocket + Presence integration
- WebSocket + Conflict resolution integration
- Full E2E flow: User edit → WebSocket → Presence update → Conflict check → UI update
