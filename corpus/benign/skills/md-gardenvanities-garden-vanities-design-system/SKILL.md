---
name: design-system
description: Operational guide for applying the Garden Vanities design system in implementation tasks
---

# Design System Skill

Use this skill whenever a task touches UI, layout, styles, tokens, or interaction states.

## Canonical Sources

1. Primary source of truth: `.agents/design-system.md`
2. Project context: `.agents/context.md`
3. Implementation layer: `src/styles/tokens/` and `src/styles/utilities.css`

If any source conflicts, follow `.agents/design-system.md`.

## Required Workflow

### 1) Classify the task scope

- `token-level` (new/changed tokens)
- `component-level` (UI component behavior/appearance)
- `layout-level` (grid, spacing, rhythm)
- `interaction-level` (states, focus, motion)

### 2) Apply system constraints

- Use semantic tokens, not raw values.
- Prefer semantic layout wrappers/props (`Section[density]`, `Container[gutter]`, `Grid[gap]`) for structural rhythm.
- Preserve light matrix with dark parity.
- Keep Layered Dark Editorial (LDE) coherence: subtle layered surfaces, restrained accent, modular composition.
- Respect max depth levels (`0..3` only).
- Keep motion within allowed durations/easing.
- Keep spacing/radius/shadow within system scales.

### 3) Validate mandatory interaction rules

For every interactive element, ensure:

1. default
2. hover (desktop)
3. focus-visible
4. active
5. disabled (if applicable)

### 4) Block forbidden patterns

- Hardcoded colors in components.
- Arbitrary spacing/radius values unless tokenized (`var(...)`) or tokenized structural `calc(...)`.
- Decorative animation.
- New visual variants without semantic reason.
- Truncation of critical/reading content.
- Any UI exception outside system rules.
- Visual drift from LDE baseline (neon accents, heavy blur/glow, decorative gradients in reading surfaces).

### 5) Report decisions in output

When finishing, include:

- Section `Applied rules` with the exact system constraints used.
- Section `Residual debt` with any mismatch that could not be resolved in this task.

For UI-related tasks, these two sections are mandatory.

### 6) Run spacing policy check (when touching layout/tokens)

- Run `bun run check:spacing` after spacing/layout/token changes.
- Treat only new violations as blockers (baseline entries are migration debt).

## Token Change Policy

Only add a new token when:

- there is a real semantic gap
- no equivalent token exists
- reuse is expected in multiple contexts
- it works in both light and dark
- usage is documented

If those conditions are not met, reuse existing tokens.
