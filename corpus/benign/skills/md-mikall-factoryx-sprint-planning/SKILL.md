---
name: sprint-planning
description: Plans the next sprint with PM analysis, multi-agent technical table, and roadmap generation. Use to plan sprints, prioritize features, convene technical tables.
user-invocable: true
---

# Sprint Planning Workflow

Structured workflow to plan a sprint with PM input, multi-agent technical review, and final output.

## Trigger

Invoke with `/sprint-planning` when needed to:
- Plan the next sprint
- Prioritize candidate features
- Technical review of features
- Generate sprint roadmap

## Required Input

1. Target sprint number
2. `requirements/requirements-list.md`
3. `requirements/plan.md`
4. `analysis/HLA.md`
5. `analysis/principles.md`

## Workflow

### PHASE 0: Lessons Learned Review

**Before planning**, read `analysis/lessons-learned.md` to:
1. Check **What Didn't Work** — avoid repeating the same mistakes
2. Check **Improvement Actions** with status "Pending" — incorporate applicable actions into this sprint
3. Check **What Worked** — replicate successful approaches

Share relevant findings with the team during the Technical Table (Phase 2).

---

### PHASE 1: Analysis and Prioritization (Product Manager)

**Agent**: `product-manager`

1. Read `requirements/requirements-list.md`
2. Read `requirements/plan.md` (already planned/completed)
3. Identify candidate features for sprint N
4. Prioritize with criteria:
   - Business value (user impact)
   - Technical dependencies (what unblocks what)
   - Risk (address risks first)
   - Estimated effort (S/M/L)
5. Verify each feature has a success metric
6. **Waste filter**: verify no candidate feature introduces partially done work (incomplete from previous sprints), extra features not requested by the business, unnecessary relearning, avoidable handoffs between agents, predictable waiting on external dependencies, excessive task switching, or foreseeable defects from ambiguous specs

**Output**: Candidate feature list with priority and rationale

---

### PHASE 2: Multi-Agent Technical Table

**Participants**: All agents in sequence

#### 2.1 Solution Architect (`solution-architect`)
- Coherence with HLA and `analysis/principles.md`
- Architectural risks
- Are new ADRs needed?
- Impact on performance and scalability

#### 2.2 Spec Analyst (`spec-analyst`)
- Requirements clear and atomic?
- Ambiguities or missing requirements?
- Anti-patterns identified?
- **Cross-artifact coherence**: do selected features conflict with each other or with already-implemented features? Check for:
  - Shared data models that would be modified by multiple features simultaneously
  - Contradictory business rules across features
  - API contract conflicts (same endpoint modified by different features)
  - Terminology drift between requirements

#### 2.3 UX Designer (`ux-designer`) — if activated
- User flow complexity for new features
- Interaction pattern consistency with existing UI
- Accessibility implications
- States to define (empty, loading, error, success)
- UX risks (complex flows, unfamiliar patterns)

#### 2.4 Dev Teams (per team)
- **DB Team**: schema impacts, migrations, RLS
- **Backend Team**: API complexity, business logic
- **Frontend Team**: UI/UX complexity, components

#### 2.5 Senior Test Engineer (`senior-test-engineer`)

The Test Engineer evaluates each candidate feature and identifies **what must be tested** and **what tools are needed to test it**. Coverage must be complete for the type of system being built.

**Test coverage assessment** — for each feature, the tester identifies which categories apply:

| Category | When it applies | What to verify |
|----------|----------------|----------------|
| **Data** | DB exists | Schema, constraints, RLS, data integrity after CRUD, migrations |
| **Backend API** | Backend exists | Every endpoint against contracts, status codes, error handling, validation |
| **M2M integrations** | External services, webhooks, queues, scheduled jobs | Calls, responses, timeouts, retries, fallback behavior |
| **Human interfaces** | UI exists | E2E user journeys (Playwright), accessibility (WCAG 2.1 AA), UI states |
| **Business rules** | Always | Rule enforcement at system boundaries, edge cases, boundary values |
| **Performance** | NFRs exist | Response times, load behavior, concurrency, resource consumption |
| **Regression** | Always | Existing TCs impacted by changes |

**Test infrastructure request** (non-negotiable right — MUST be budgeted in the sprint):
- Stubs and simulators for external services
- Test APIs for data setup/teardown
- Advanced logging and diagnostic endpoints
- Fixture managers for test data
- Any custom tooling needed to test "at the terminals"

**Test tools as sprint tasks**: all infrastructure requested by the Test Engineer is included as development tasks in the sprint roadmap, with effort estimates and dependencies. A system that cannot be thoroughly tested cannot be released.

#### 2.6 Security & Privacy Auditor (`security-privacy-auditor`)
- New endpoints with sensitive data?
- RLS/auth impacts?
- Compliance check

**Output**:
- Approved features
- Features with reservations (and what's needed)
- Features to defer (and why)

---

### PHASE 3: Negotiation (if needed)

If critical blockers:
1. PM and Architect negotiate scope
2. Options: simplify, split, defer
3. Goal: achievable sprint, economical, without excessive debt

---

### PHASE 4: Sprint Roadmap Drafting

**Output**: `requirements/sprints/sprint-N-roadmap.md`

```markdown
# Sprint N - Roadmap

## Sprint Goal
[Clear sentence]

## Exit Criteria
- [ ] [testable criterion 1]
- [ ] [testable criterion 2]

## Included Features
| ID | Feature | Requirements | Team | Effort | Success Metric |
|----|---------|-------------|------|--------|---------------|

---

## DB Team Plan
### Tasks
| # | Task | Output | Effort | Dependencies |

## Backend Team Plan
### Tasks
| # | Task | Output | Effort | Dependencies |

## Frontend Team Plan
### Tasks
| # | Task | Output | Effort | Dependencies |

## QA Plan
### Test Strategy
### Test Infrastructure Requests
| Artifact | Type | Purpose | Effort |
### Priority Test Cases
| TC | Type | Priority | Requirement |

## Security & Privacy Plan
### Checklists to Pass

## UX Plan (if UX Designer activated)
### User Flows to Define/Update
### States Checklist (empty, loading, error, success)
### Accessibility Checks

## Sprint Risks
| # | Risk | Probability | Impact | Mitigation | Owner |

> Update `analysis/risk-register.md` with new risks identified during this sprint planning.

## Dependencies
[ASCII Diagram]

## Technical Table Notes
[Decisions, accepted trade-offs, risks]
```

---

## Final Checklist

- [ ] Features have traceable requirements
- [ ] Every team has tasks with defined outputs
- [ ] Testable exit criteria
- [ ] Dependencies mapped
- [ ] QA has test strategy
- [ ] Security/privacy review planned
- [ ] No unresolved critical blockers
- [ ] Architectural principles respected
- [ ] **Cross-artifact coherence**: selected features don't conflict with each other or existing functionality
- [ ] **Terminology consistent**: same concepts use same names across all sprint documents
- [ ] **Risk register updated**: new risks from technical table added to `analysis/risk-register.md`
- [ ] **UX review** (if activated): user flows validated, states defined, accessibility planned
