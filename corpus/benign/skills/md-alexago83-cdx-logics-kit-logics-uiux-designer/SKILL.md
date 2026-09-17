---
name: logics-uiux-designer
description: Product UI/UX design assistant for this repo. Use when Codex should propose UI/UX improvements, redesign flows/screens, define a lightweight design system (tokens/components/states), and produce actionable handoff artifacts (specs, backlog items, tasks) aligned with the `logics/*` workflow.
---

# Product UI/UX workflow

## Inputs to request (ask if missing)

- Platform (web/mobile/desktop), target device sizes, and constraints (tech, time, brand).
- The user goal (job-to-be-done) and primary success metric.
- Current UX issues (screenshots, video, repro steps, analytics, support tickets).
- Existing design system/tokens/components (if any).

## Outputs to produce

- A concise UI/UX proposal in `logics/specs/` (use the template in `assets/templates/uiux_proposal.md`).
- One backlog item with clear acceptance criteria.
- One or more tasks with a concrete plan + validation commands.

## Create a UI/UX proposal doc

Use the generator script (creates a `spec_XXX_*.md` in `logics/specs/` using the UI/UX proposal template):

```bash
python logics/skills/logics-uiux-designer/scripts/logics_uiux.py new --title "Redesign offline recap modal"
```

## Procedure

1. Audit current UX
   - List top issues (severity, frequency, impact).
   - Identify where users get stuck (friction, cognitive load, errors).
2. Define the target experience
   - Goals, non-goals, and success metrics.
   - Proposed user flow(s) and information architecture.
3. Design the solution
   - Screen-by-screen changes (layout, hierarchy, states).
   - Component inventory (new vs reuse), and state matrix (loading/empty/error/disabled).
   - Content/microcopy guidelines (labels, errors, confirmations).
4. Quality checks
   - Accessibility: focus order, keyboard nav, contrast, touch targets.
   - Responsiveness: small/medium/large layouts.
5. Handoff into Logics
   - Create/promote docs using `logics-flow-manager`.
   - Convert acceptance criteria into a concrete validation plan (see `logics-acceptance-to-tests`).
