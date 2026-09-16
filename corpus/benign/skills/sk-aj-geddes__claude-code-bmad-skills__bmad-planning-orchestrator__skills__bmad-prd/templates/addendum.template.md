# PRD Addendum — {{PROJECT_NAME}}

**Companion to:** `prd.md`
**Version:** {{VERSION}}
**Date:** {{DATE}}

> Overflow and working notes that would bloat the PRD. Nothing here is the source of truth for *what* to build — that stays in `prd.md`. This file holds detail, deferred items, open questions, and supporting research. Decisions belong in `decision-log.md`, not here.

---

## Open Questions

| # | Question | Owner | Needed By | Status |
|---|----------|-------|-----------|--------|
| Q1 | {{QUESTION_1}} | {{OWNER_1}} | {{DUE_1}} | open |
| Q2 | {{QUESTION_2}} | {{OWNER_2}} | {{DUE_2}} | open |

---

## Deferred Requirements (parked, not cut)

> Candidate FRs/NFRs not promoted into this release. Keep the wording so they can be lifted into `prd.md` later without rework.

- **{{DEFERRED_1_ID}}:** {{DEFERRED_1_DESCRIPTION}} — *reason deferred:* {{DEFERRED_1_REASON}}
- **{{DEFERRED_2_ID}}:** {{DEFERRED_2_DESCRIPTION}} — *reason deferred:* {{DEFERRED_2_REASON}}

---

## Detailed Acceptance Criteria Overflow

> When an FR/NFR needs more than the 3-5 criteria the PRD shows, the full set goes here, keyed by requirement ID.

### {{REQ_ID}}
- {{EXTRA_AC_1}}
- {{EXTRA_AC_2}}

---

## Prioritization Working Notes

> RICE inputs/outputs, scoring rationale, and any sensitivity notes that informed the MoSCoW buckets in the PRD. (Run `prioritize.py` to regenerate.)

| Feature | Reach | Impact | Confidence | Effort | RICE | → MoSCoW |
|---------|-------|--------|------------|--------|------|----------|
| {{FEAT_1}} | {{R1}} | {{I1}} | {{C1}} | {{E1}} | {{RICE_1}} | {{BUCKET_1}} |
| {{FEAT_2}} | {{R2}} | {{I2}} | {{C2}} | {{E2}} | {{RICE_2}} | {{BUCKET_2}} |

---

## Supporting Research / References

- {{RESEARCH_NOTE_1}}
- {{REFERENCE_1}}

---

## Glossary

| Term | Definition |
|------|------------|
| {{TERM_1}} | {{DEFINITION_1}} |
| {{TERM_2}} | {{DEFINITION_2}} |
