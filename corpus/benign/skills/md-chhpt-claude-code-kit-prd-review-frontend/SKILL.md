---
name: prd-review-frontend
description: Review a PRD from a senior frontend engineer perspective and output actionable issues, risks, clarifying questions, and acceptance criteria for web/mobile-web products.
---

# PRD Review (Frontend)

## Overview

把 PRD 当成“要交付的产品合同”来评审：先补齐信息，再用高级前端工程师视角检查可实现性、边界条件、数据/接口契约、质量属性，并给出可执行的改动建议与验收标准。

## Output Rules

- Use `assets/prd-review-report-template.md` as the final structure (Markdown).
- Keep output language consistent with the PRD unless the user requests otherwise.
- When information is missing, prioritize **Blocking Questions** and list explicit assumptions in the report.
- Use consistent severity + ownership; see `references/review-heuristics.md` for the rubric.

## Workflow

### Step 0: Gather Inputs (if missing, ask first)

Ask for the minimum missing context, then proceed:
- PRD content (doc link/path or pasted text) + target platform(s) (Web/H5/Hybrid)
- Existing stack & constraints (framework, routing, state, SSR/CSR, design system)
- Release constraints (timeline, phased rollout, feature flag/A-B)
- External dependencies (backend, design, data/analytics, auth/permissions)

If PRD is obviously incomplete, output:
1) “Blocking Questions” first (must answer before implementation)
2) A “Draft Review” that flags assumptions explicitly

### Step 1: Establish Shared Understanding
- Summarize: problem, goals, non-goals, user segments, success metrics
- Extract scope: key user stories, out-of-scope, constraints, dependencies
- Identify “unknowns” that could flip the solution (auth model, data freshness, etc.)

### Step 2: Review User Journeys & UI States
- For each flow: entry → happy path → edge cases → exit
- Enumerate states: loading, empty, error, partial success, retry, offline (if relevant)
- Validate responsiveness, keyboard support, focus order, a11y semantics
- Confirm copy, i18n, timezones, units, number/date formats

### Step 3: Validate Data / API / Contract
- Define UI data needs: fields, paging/sorting/filtering, search, permissions
- Check API contract clarity: request/response examples, errors, idempotency, rate limits
- Identify “contract gaps”: enums, nullability, pagination shape, time semantics
- Propose backend changes or a BFF/adapter if needed

### Step 4: Non-Functional Review (Frontend)
- Performance: critical path, bundle size, image strategy, rendering hotspots, budgets
- Reliability: retries/backoff, optimistic updates, cache invalidation, consistency UX
- Security & privacy: authz, PII, token storage, XSS/CSRF, logging redaction
- Observability: Sentry-like errors, web vitals, custom metrics, dashboards/alerts

### Step 5: Implementation Shape (lightweight)
- Component & page decomposition; state ownership; routing; forms; error boundaries
- Reuse design system; identify new components; interaction specs for designers
- Dependency plan: what must land first (API, design, data events)
- Release plan: feature flags, migrations, staged rollout, rollback

### Step 6: Output a Review Report
Use the template in `assets/prd-review-report-template.md`. Keep it actionable:
- Severity tags: `P0 Blocker`, `P1 Major`, `P2 Minor`, `P3 Nit`
- Each issue includes: What’s missing/wrong → Why it matters → Suggestion → Owner
- Finish with: “Assumptions made” + “Next step checklist”

## References

Load as needed:
- `references/review-heuristics.md`: checklist + common PRD gaps and questions

## Assets

Use directly:
- `assets/prd-review-report-template.md`: Markdown review report template
