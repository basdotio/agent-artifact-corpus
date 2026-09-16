---
name: bmad-ux
description: |
  Solutioning-phase UX planning skill (optional; activate when the project has a UI).
  Produces TWO planning documents: DESIGN.md (the visual system — design tokens, color
  palette, typography, spacing, component specs, WCAG 2.1 AA contract) and
  EXPERIENCE.md (user journeys, flow diagrams, screen states, error/empty/loading
  handling). Use when the user says "design the UX", "create UX planning docs",
  "define the design system", "map the user flows", "UX for this feature",
  "wireframe the flows", "what are the user journeys", "accessibility design",
  "WCAG compliance", "design tokens", "responsive design plan", "mobile-first design",
  or "create DESIGN.md / EXPERIENCE.md". Runs after architecture is drafted and before
  stories are created. Supports Create / Update / Validate intents.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, TodoWrite
---

# BMAD UX — Visual System & Experience Planning

Produces the two-document UX contract that downstream story authors and the external
dev tool rely on. This is a **planning** skill. It produces specifications, not code.

## What it produces

Under `bmad-output/` (or the folder in `config.yaml`):

```
bmad-output/
├── DESIGN.md         # Visual system: tokens, components, accessibility contract
└── EXPERIENCE.md     # Journeys, flows, states, error/empty/loading specs
```

Both documents are **locked planning artifacts**. The external dev tool may read them
but must not edit them. All design decisions should be recorded in `decision-log.md`.

## Three intents

- **Create** — generate both documents from scratch (most common).
- **Update** — revise specific sections when requirements change; append a dated entry
  to `decision-log.md` explaining what changed and why.
- **Validate** — audit existing documents for completeness and WCAG 2.1 AA gaps. Run
  the WCAG checklist; report findings but do not alter the project's code.

## Pre-flight reads

Before drafting, read (in order):

1. `bmad-output/config.yaml` — project name, track, output folder.
2. `bmad-output/project-context.md` — user personas, platform targets, constraints.
3. `bmad-output/prd.md` (if present) — feature list, user stories, acceptance criteria.
4. `bmad-output/architecture.md` (if present) — component boundaries, API contracts.

If any of these are missing, ask the user for the key inputs before proceeding.

## DESIGN.md — Visual System

Use `${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/templates/design.template.md`.

The document covers:

**1. Design Tokens**

Commit to concrete values. Placeholders are not acceptable for tokens.

- Color palette: primary, secondary, semantic (success / warning / error / info),
  neutral scale. All color pairs used for text must be WCAG 2.1 AA verified.
- Typography: font families, size scale (mobile → desktop), weight, line-height.
  Minimum 16px body on mobile (prevents iOS zoom). Base unit: 8px.
- Spacing scale (8px grid), border-radius set, shadow/elevation set.
- Breakpoints: 320px (mobile), 768px (tablet), 1024px (desktop), 1440px (desktop XL).

**2. Component Specs**

For each component: visual defaults, all interaction states (default / hover / focus /
active / disabled / loading / error / success), responsive behavior, and accessibility
annotations (ARIA roles, aria-label placement, focus-trap rules, min touch target
44×44px on mobile).

Core components to specify: buttons (primary / secondary / destructive), text inputs,
select / checkbox / radio, cards, modals, navigation (desktop + mobile hamburger),
loading/skeleton states, error banners.

**3. WCAG 2.1 AA Contract**

Enumerate the concrete accessibility requirements the visual system guarantees:

- Text contrast ≥ 4.5:1 (normal), ≥ 3:1 (large text ≥ 18px or bold ≥ 14px).
- UI component / graphic contrast ≥ 3:1.
- Visible focus indicator (2px solid outline minimum).
- All functionality reachable via keyboard.
- No horizontal scroll at 320px viewport width.
- Touch targets ≥ 44×44px with ≥ 8px spacing.

Run the checklist to produce the contract summary:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/wcag-checklist.sh"
```

Check specific color pairs with:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/contrast-check.py" #foreground #background
```

Verify responsive breakpoint rules:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/responsive-breakpoints.sh"
```

## EXPERIENCE.md — User Experience Plan

Use `${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/templates/experience.template.md`.

The document covers:

**1. User Journeys**

One section per major journey (onboarding, core workflow, settings, error recovery, etc.).
Each journey: goal, persona, entry points, happy-path flow diagram (ASCII or bullet
steps), estimated time, and drop-off risk notes.

**2. Screen / State Inventory**

For every screen or major view: purpose, layout wireframe (ASCII encouraged),
component hierarchy, and all named states:

- **Default** — normal first-load state.
- **Loading** — skeleton or spinner; `aria-live="polite"` announced.
- **Empty** — zero-data state with helpful call-to-action.
- **Error** — what went wrong + recovery action.
- **Success** — confirmation feedback.
- **Disabled** — why access is restricted.

**3. Decision Points & Alternative Paths**

For each journey, map the branch points (validation failure, auth required, network
error, timeout, etc.). Each branch: trigger, display, and recovery path.

**4. Interaction & Animation Notes**

Timing and easing for transitions. Respect `prefers-reduced-motion`. Note which
animations are decorative vs. meaningful.

## Subagent strategy

For projects with more than four major journeys, fan out parallel subagents:

| Agent | Task | Output file |
|-------|------|-------------|
| Agent 1 | Design tokens + color/contrast pairs → DESIGN.md §1 | `bmad-output/ux-tokens-draft.md` |
| Agent 2 | Core component specs → DESIGN.md §2 | `bmad-output/ux-components-draft.md` |
| Agent 3 | WCAG contract + a11y annotations | `bmad-output/ux-a11y-draft.md` |
| Agent N | One major user journey + screen states | `bmad-output/ux-journey-N-draft.md` |

Write shared context to `bmad-output/ux-shared-context.md` (personas, brand intent,
breakpoints) before launching agents. The main context assembles the drafts into the
two final documents and runs the WCAG checklist across all screens.

Example subagent prompt:

```
Task: Design the [journey name] user flow with full state coverage.
Context: Read bmad-output/ux-shared-context.md for personas, tokens, and component patterns.
Objective: Produce the [journey name] section of EXPERIENCE.md covering: entry points,
  happy-path flow diagram, all screen states (loading/empty/error/success), decision
  branch map, and accessibility annotations.
Output: Write to bmad-output/ux-journey-[name]-draft.md.
Constraints:
  - Follow design tokens from context (colors, spacing, typography).
  - WCAG 2.1 AA compliance: 4.5:1 contrast, keyboard accessible, 44px touch targets.
  - Design mobile-first (320px), then scale to tablet and desktop.
  - Specify all interaction states per component.
  - No application code — planning specifications only.
```

## Guardrails

- This skill produces planning documents. It never writes application code, CSS,
  component implementations, or test suites.
- If the project has no UI (API-only, CLI-only, background service), skip this skill
  entirely and note the decision in `decision-log.md`.
- Stop before "implement". Hand off to the story-creation skill once the two documents
  are approved.

See `REFERENCE.md` for design pattern library, full breakpoint reference, and
component state matrix.

> ---
> Part of the **BMAD Planning & Orchestrator** plugin — a Claude Code harness for the **BMAD Method** by the **BMAD Code Organization** (https://github.com/bmad-code-org/BMAD-METHOD). Implements the spirit of `bmad-ux-designer`. All methodology credit belongs to the BMAD Code Organization.
