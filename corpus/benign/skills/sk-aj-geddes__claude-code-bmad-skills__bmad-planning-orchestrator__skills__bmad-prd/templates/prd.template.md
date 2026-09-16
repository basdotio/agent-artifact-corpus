# Product Requirements Document (PRD)

**Project Name:** {{PROJECT_NAME}}
**Version:** {{VERSION}}
**Date:** {{DATE}}
**Author:** {{AUTHOR}} (PM)
**Status:** {{STATUS}}
**Track:** {{TRACK}}  <!-- Quick Flow | BMad Method | Enterprise -->

> Source of truth for *what* and *why*. It does not prescribe *how* (that is the architecture skill).
> Overflow / deferred detail lives in `addendum.md`. Decisions are logged in `decision-log.md`.

---

## Executive Summary

**Problem Statement:** {{PROBLEM_STATEMENT}}

**Proposed Solution:** {{SOLUTION_OVERVIEW}}

**Business Value:** {{BUSINESS_VALUE}}

**Target Outcome:** {{TARGET_OUTCOME}}

---

## Project Overview

### Background
{{BACKGROUND}}

### Current State → Desired State
- **Current:** {{CURRENT_STATE}}
- **Desired:** {{DESIRED_STATE}}

### Stakeholders
| Stakeholder | Role | Interest | Influence |
|-------------|------|----------|-----------|
| {{STAKEHOLDER_1}} | {{ROLE_1}} | {{INTEREST_1}} | {{INFLUENCE_1}} |
| {{STAKEHOLDER_2}} | {{ROLE_2}} | {{INTEREST_2}} | {{INFLUENCE_2}} |

---

## Goals and Objectives

### Business Goals
1. {{BUSINESS_GOAL_1}}
2. {{BUSINESS_GOAL_2}}

### User Goals
1. {{USER_GOAL_1}}
2. {{USER_GOAL_2}}

---

## Functional Requirements

> Format: `FR-###: <PRIORITY> — <capability>`. One capability each, with 3-5 testable acceptance criteria. Describe WHAT, not HOW. IDs are immutable; never renumber — append new ones.

### FR-001: {{FR_1_TITLE}} — [MUST | SHOULD | COULD | WON'T]
**Description:** {{FR_1_DESCRIPTION}}
**Acceptance Criteria:**
- {{FR_1_AC_1}}
- {{FR_1_AC_2}}
- {{FR_1_AC_3}}
**Related Epic:** {{FR_1_EPIC}}

---

### FR-002: {{FR_2_TITLE}} — [MUST | SHOULD | COULD | WON'T]
**Description:** {{FR_2_DESCRIPTION}}
**Acceptance Criteria:**
- {{FR_2_AC_1}}
- {{FR_2_AC_2}}
**Related Epic:** {{FR_2_EPIC}}

---

### FR-003: {{FR_3_TITLE}} — [MUST | SHOULD | COULD | WON'T]
**Description:** {{FR_3_DESCRIPTION}}
**Acceptance Criteria:**
- {{FR_3_AC_1}}
- {{FR_3_AC_2}}
**Related Epic:** {{FR_3_EPIC}}

---

_Continue with additional functional requirements as needed..._

---

## Non-Functional Requirements

> Every NFR must be measurable, with a stated measurement method. Categories: Performance, Security, Scalability, Reliability, Usability, Maintainability (+ Compliance / Operability for Enterprise track).

### NFR-001: {{NFR_1_TITLE}} — [MUST | SHOULD | COULD] (Performance)
**Description:** {{NFR_1_DESCRIPTION}}
**Acceptance / Threshold:** {{NFR_1_THRESHOLD}}
**Measurement Method:** {{NFR_1_MEASUREMENT}}

### NFR-002: {{NFR_2_TITLE}} — [MUST | SHOULD | COULD] (Security)
**Description:** {{NFR_2_DESCRIPTION}}
**Acceptance / Threshold:** {{NFR_2_THRESHOLD}}
**Measurement Method:** {{NFR_2_MEASUREMENT}}

### NFR-003: {{NFR_3_TITLE}} — [MUST | SHOULD | COULD] (Scalability / Reliability)
**Description:** {{NFR_3_DESCRIPTION}}
**Acceptance / Threshold:** {{NFR_3_THRESHOLD}}
**Measurement Method:** {{NFR_3_MEASUREMENT}}

<!-- Enterprise track: add NFRs for Compliance and Operability/DevOps here. -->

_Continue with additional non-functional requirements as needed..._

---

## Epics and User Stories (Outline)

> This is an OUTLINE. Detailed, ready-for-dev story files ({epic}.{story}.{slug}.story.md) are compiled later by the sprint/story skills, which cite this section. Do NOT add story points, velocity, or estimates here — delivery is count-based.

### EPIC-001: {{EPIC_1_NAME}}
**Business Value:** {{EPIC_1_VALUE}}
**User Segments:** {{EPIC_1_SEGMENTS}}
**Related Requirements:** {{EPIC_1_REQS}}

**User Stories (sketch):**
- **STORY-001:** As a {{USER_TYPE}}, I want {{CAPABILITY}}, so that {{BENEFIT}}.
  - Given {{CONTEXT}}, when {{ACTION}}, then {{OUTCOME}}.
- **STORY-002:** As a {{USER_TYPE}}, I want {{CAPABILITY}}, so that {{BENEFIT}}.
  - Given {{CONTEXT}}, when {{ACTION}}, then {{OUTCOME}}.

---

### EPIC-002: {{EPIC_2_NAME}}
**Business Value:** {{EPIC_2_VALUE}}
**User Segments:** {{EPIC_2_SEGMENTS}}
**Related Requirements:** {{EPIC_2_REQS}}

**User Stories (sketch):**
- **STORY-003:** As a {{USER_TYPE}}, I want {{CAPABILITY}}, so that {{BENEFIT}}.

_Continue with additional epics as needed..._

---

## Prioritization Summary (MoSCoW)

| Priority | Requirements | Rationale |
|----------|--------------|-----------|
| Must | {{MUST_LIST}} | {{MUST_RATIONALE}} |
| Should | {{SHOULD_LIST}} | {{SHOULD_RATIONALE}} |
| Could | {{COULD_LIST}} | {{COULD_RATIONALE}} |
| Won't (this release) | {{WONT_LIST}} | {{WONT_RATIONALE}} |

<!-- If RICE was used to settle ordering, note the ranked output and link the decision-log entry. -->

---

## Success Metrics

| Metric | Baseline | Target | Measurement Method | Frequency |
|--------|----------|--------|--------------------|-----------|
| {{METRIC_1}} | {{BASELINE_1}} | {{TARGET_1}} | {{METHOD_1}} | {{FREQUENCY_1}} |
| {{METRIC_2}} | {{BASELINE_2}} | {{TARGET_2}} | {{METHOD_2}} | {{FREQUENCY_2}} |

---

## Assumptions and Dependencies

### Assumptions
1. {{ASSUMPTION_1}}
2. {{ASSUMPTION_2}}

### Dependencies
| Dependency | Type | Owner | Status | Risk | Mitigation |
|------------|------|-------|--------|------|------------|
| {{DEP_1}} | {{TYPE_1}} | {{OWNER_1}} | {{STATUS_1}} | {{RISK_1}} | {{MITIGATION_1}} |

---

## Constraints

- **Technical:** {{TECH_CONSTRAINTS}}
- **Business:** {{BUSINESS_CONSTRAINTS}}
- **Timeline:** {{TIMELINE_CONSTRAINTS}}

---

## Out of Scope

| Excluded | Reason | Revisit? |
|----------|--------|----------|
| {{OUT_OF_SCOPE_1}} | {{REASON_1}} | {{REVISIT_1}} |
| {{OUT_OF_SCOPE_2}} | {{REASON_2}} | {{REVISIT_2}} |

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation | Owner |
|------|--------|-------------|------------|-------|
| {{RISK_1}} | {{IMPACT_1}} | {{PROB_1}} | {{MITIGATION_STRATEGY_1}} | {{OWNER_1}} |

---

## Traceability Matrix

> Every requirement traces up to a goal and down to an epic/story. Orphans (either direction) are defects.

| Requirement | Business Goal | Epic | User Story | Status |
|-------------|---------------|------|------------|--------|
| FR-001 | {{GOAL_A}} | EPIC-001 | STORY-001 | {{STATUS}} |
| FR-002 | {{GOAL_A}} | EPIC-001 | STORY-002 | {{STATUS}} |
| NFR-001 | {{GOAL_C}} | (cross-cutting) | — | {{STATUS}} |

---

## Handoff

- **To Architecture:** {{ARCH_HANDOFF_NOTES}}
- **To Sprint/Story Planning:** epics outline above is the source for story compilation.
- **Open questions / overflow:** see `addendum.md`.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| {{VERSION}} | {{DATE}} | {{AUTHOR}} | Initial draft |
