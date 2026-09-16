# PRD Reference — FR/NFR Taxonomy, Quality Rules, Prioritization

Detailed reference for the `bmad-prd` skill. The SKILL.md keeps the workflow lean; this file holds the depth.

---

## 1. Functional Requirements (FR)

**Definition:** what the system *does* — user-facing capabilities and observable system behaviors. Describe WHAT and WHY, never HOW (no tech choices, no data structures, no algorithms — those belong to architecture).

**Format:**
```
FR-001: MUST — User can create an account with email and password
Acceptance Criteria:
- Email is validated against RFC 5322
- Password requires min 8 chars, mixed case, one digit
- Confirmation email is sent within 30s of submission
- Duplicate email is rejected with a specific error message
Related Epic: EPIC-001
```

**Rules:**
- One capability per FR. If you wrote "and", consider splitting.
- IDs are immutable once assigned. Append new ones (FR-014); never renumber.
- Every FR carries a MoSCoW priority and 3-5 acceptance criteria.
- Acceptance criteria are **testable** — phrased so a tester (human or external dev tool) can pass/fail them. Prefer Given/When/Then for behavioral ACs.

---

## 2. Non-Functional Requirements (NFR)

**Definition:** how *well* the system performs — quality attributes and constraints. Every NFR must be **measurable** with a stated measurement method.

| Category | Covers | Example metric |
|----------|--------|----------------|
| Performance | latency, throughput, resource use | p95 response < 200ms; 1k req/s sustained |
| Security | authn, authz, data protection, secrets | All PII encrypted at rest (AES-256); OWASP Top 10 mitigated |
| Scalability | concurrent load, data volume, growth | 10k concurrent sessions; linear to 1M rows |
| Reliability | uptime, fault tolerance, recovery | 99.9% monthly uptime; RTO < 1h |
| Usability | accessibility, UX standards | WCAG 2.1 AA; core task ≤ 3 clicks |
| Maintainability | modularity, documentation, observability | All public APIs documented; structured logs on every request |
| Compliance (Enterprise) | regulatory, legal, audit | GDPR data-subject deletion within 30 days |
| Operability/DevOps (Enterprise) | deployability, monitoring, rollback | Zero-downtime deploy; alert on p95 breach |

**Format:**
```
NFR-001: MUST — API endpoints respond within 200ms at the 95th percentile
Measurement: load test at expected peak, measure server-side p95
```

**Rules:**
- A number or a binary pass/fail, always. "Fast", "secure", "scalable" are not NFRs until quantified.
- NFRs are not afterthoughts; security and performance often gate the architecture.
- NFRs may map to no single epic — that's fine; they appear in the traceability matrix as cross-cutting.

---

## 3. Requirement-Quality Rules (the bar)

A requirement is **done** only if it is:

1. **Atomic** — one testable thing.
2. **Unambiguous** — no "etc.", no "and/or", no undefined adjectives.
3. **Measurable** — pass/fail is decidable. Replace vague terms:
   - "user-friendly" → specific task-time or click-count target
   - "fast" → a latency budget
   - "robust" → a named failure mode + expected behavior
   - "scalable" → a load number
4. **Traceable** — links up to a business goal and down to an epic/story.
5. **Prioritized** — carries a MoSCoW value.
6. **Implementation-free** — states the need, not the solution. ("Users can search orders" — not "add an Elasticsearch index".)
7. **Verifiable by acceptance criteria** — each FR has ACs; each NFR has a measurement method.

**Smell list (validator flags these):** missing IDs, missing priority, no acceptance criteria, "MUST" on everything (priority inflation), vague adjectives, requirements that prescribe technology.

---

## 4. MoSCoW

Best for time-boxed scope and MVP definition.

- **Must** — without it the release fails. Be ruthless: if >60% of FRs are Must, re-examine.
- **Should** — important, but a workaround exists; can slip a release.
- **Could** — desirable if capacity allows; first to be cut.
- **Won't** — explicitly out of scope *this release*. Keep visible to stop scope creep; revisit next cycle.

Log every non-obvious bucket placement in `decision-log.md`.

---

## 5. RICE

Best for ranking many features or settling contested priority. Output is a relative ranking, which you then fold into MoSCoW buckets.

**Formula:** `(Reach × Impact × Confidence) / Effort`

| Factor | Meaning | Scale |
|--------|---------|-------|
| Reach | users/events affected per period | raw count |
| Impact | value per user | 0.25 minimal, 0.5 low, 1 medium, 2 high, 3 massive |
| Confidence | certainty of the estimates | 0-100% |
| Effort | size of the work | person-months (a planning proxy only) |

Run `scripts/prioritize.py` (interactive or `-b CSV`). It sorts descending and can export a results CSV.

**Important — not estimation.** Effort here is a coarse prioritization input, not a delivery estimate. This plugin does NOT use story points, velocity, or burndown. Story sizing happens later in the sprint/story skills, using "small enough for one agent session (~2-8h)", and delivery is tracked **count-based** (stories remaining / completion rate).

---

## 6. Kano (optional lens)

Useful when reasoning about satisfaction rather than raw priority:
- **Basic** — expected; absence causes dissatisfaction (often Must).
- **Performance** — more is better; linear satisfaction.
- **Excitement** — unexpected delighters; exponential upside (often Could).

Kano informs MoSCoW; it does not replace it.

---

## 7. Epics & Stories (outline level)

The PRD produces an **outline**, not finished story files.

```
EPIC-001: User Authentication
Business Value: secure, personalized access
User Segments: all users
Related Requirements: FR-001, FR-002, FR-003
Stories (sketch):
- As a new user, I want to create an account so that I can access personalized features
- As a returning user, I want to log in securely so that I can reach my data
- As a user, I want to reset my password so that I can recover access
```

Detailed, ready-for-dev story files — the ~8K-token context objects with Tasks/Subtasks, Dev Notes (with source citations), Testing strategy, Dependency Maps, Owned File Scope, and an empty Dev Agent Record — are compiled later by the sprint/story skills, named `{epic}.{story}.{slug}.story.md`. The PRD just needs a clean epic/story outline and traceability so those skills have a source to cite.

---

## 8. Traceability Matrix

| Requirement | Business Goal | Epic | Story | Status |
|-------------|---------------|------|-------|--------|
| FR-001 | Goal A | EPIC-001 | STORY-001 | draft |
| NFR-001 | Goal C | (cross-cutting) | — | draft |

Every requirement must trace up to at least one goal. Orphan requirements (no goal) and orphan goals (no requirement) are both defects.
