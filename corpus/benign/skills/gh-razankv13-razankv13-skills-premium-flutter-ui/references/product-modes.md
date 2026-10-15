# Product Modes

Use this reference when the user has not specified persona, scope, or output depth.

## Contents

- Persona Defaults
- Task Size Defaults
- Visual Direction Presets
- Onboarding And First Run
- Revision Mode
- Output Contract
- Non-Goals

## Persona Defaults

### Indie Developer

Prioritize speed and coherent defaults.

Include:

- Opinionated mobile pattern.
- Tokenized theme starter only as deep as needed.
- Reusable components for repeated controls.
- Realistic copy and states.
- One focused test or validation command.

Skip:

- Team governance docs.
- Multiple design-system variants.
- Heavy review artifacts unless requested.

### Startup Team

Prioritize consistency, reviewability, and narrow diffs.

Include:

- Existing repo conventions and design sources.
- Component/state variants that future screens can reuse.
- Accessibility and localization notes.
- Focused tests and screenshot/golden guidance when visual changes are material.
- Clear rationale for decisions that product/design reviewers will inspect.

Skip:

- Broad redesigns outside the requested flow.
- New packages without repeated need.

### Designer-Engineer

Prioritize token fidelity and critique quality.

Include:

- Explicit hierarchy, type, color, motion, spacing, and state decisions.
- Token mapping and component API shape.
- Before/after critique points when refactoring.
- Edge cases: long copy, RTL risk, text scale, dark mode, reduced motion.

Skip:

- Boilerplate app scaffolding unless asked.

## Task Size Defaults

### Small Fix

Examples: button state, card polish, spacing issue, contrast issue.

Deliver:

- Minimal code or review finding.
- One validation check if logic or layout can regress.
- No new abstraction unless the same problem repeats.

### Single Screen

Deliver:

- Screen-level layout and hierarchy.
- Existing tokens/components reused.
- Loading, empty, error, disabled, and success states when data/actions exist.
- Focused widget/golden/screenshot validation where appropriate.

### Multi-Screen Flow

Deliver:

- Shared flow shell, navigation behavior, and state ownership.
- Reusable controls for repeated actions.
- Consistent transition and feedback patterns.
- Localization and accessibility coverage for the journey.
- One important flow test when feasible.

### Design System Starter

Deliver:

- Theme, tokens, core component wrappers, and usage examples.
- Light/dark modes.
- Component states.
- Validation and adoption notes.

Do not scaffold auth, billing, analytics, or CI unless the user asks.

## Visual Direction Presets

When the user wants a vibe but no exact spec, propose one direction and name its tradeoffs instead of stacking trends. Useful starting points:

- **Editorial**: strong type hierarchy, generous whitespace, restrained color.
- **Fintech Trust**: sober surfaces, one accent family, tabular numerals, no marketing chrome.
- **SaaS Utility**: dense but scannable, clear states, low decoration.
- **Soft Consumer**: warm tinted neutrals, friendly shapes, gentle motion.

Translate the chosen direction into Flutter tokens and components using `craft-rubric.md` Visual Direction.

## Onboarding And First Run

Onboarding flow behavior — skip paths, value-before-signup, contextual permissions, step count — is `mobile-ux` territory; consult that skill's playbooks for the flow shape. This skill implements the screens that flow specifies. Screen-level notes:

- Prefer one contextual coach-mark pattern over six tutorial screens.
- Set emotional tone with copy/illustration on trust-heavy products.

## Revision Mode

When revising existing UI, identify the layer being changed:

- Copy.
- Layout.
- Hierarchy.
- Type.
- Color.
- Motion.
- States.
- Accessibility.
- Performance.

Change that layer only. Avoid rewriting a whole screen because one layer is weak.

## Output Contract

For implementation, the Completion Bar in SKILL.md is the contract; additionally name the files changed.

For review and audit, the format is SKILL.md Review Order (P0/P1/P2 findings with evidence and a minimal fix). Add open questions only when they block a correct fix.

## Non-Goals

Do not include these unless explicitly requested:

- Web or desktop Flutter UI.
- Marketplace or subscription pricing strategy.
- Full app starter kit.
- Figma import/export workflow.
- New design tool dependencies.
- Multiple brand variants.
- White-label or agency packaging.
