# EXPERIENCE.md — User Experience Plan

> **LOCKED PLANNING ARTIFACT.** The external dev tool reads this document but must
> not edit it. All UX changes go through the bmad-ux skill and are recorded in
> `decision-log.md`.

**Project:** {{PROJECT_NAME}}
**Track:** {{TRACK}}
**Date:** {{DATE}}
**Version:** {{VERSION}}

---

## Overview

{{PROJECT_UX_SUMMARY}}

**Personas covered:** {{PERSONAS}}
**Platform targets:** {{PLATFORMS}}
**Design system reference:** `bmad-output/DESIGN.md`

---

## User Journeys

> One section per major journey. Journeys map end-to-end goals, not individual screens.
> Screens are detailed in the Screen Inventory below.

---

### Journey: {{JOURNEY_1_NAME}}

**Goal:** {{JOURNEY_1_GOAL}}
**Primary persona:** {{JOURNEY_1_PERSONA}}
**Estimated time:** {{JOURNEY_1_TIME}}
**Entry points:**
- {{ENTRY_1}}
- {{ENTRY_2}}

**Success criteria:** {{JOURNEY_1_SUCCESS}}

#### Happy Path

```
[{{STEP_1}}]
      |
      v
[{{STEP_2}}]
      |
      v
[{{STEP_3}}]
      |
      v
[{{END_STATE}}]
```

#### Decision Points & Alternative Paths

| Trigger | Display | Recovery |
|---------|---------|---------|
| {{DECISION_TRIGGER_1}} | {{DISPLAY_1}} | {{RECOVERY_1}} |
| {{DECISION_TRIGGER_2}} | {{DISPLAY_2}} | {{RECOVERY_2}} |

#### Drop-off Risk Notes

{{JOURNEY_1_DROPOFF_NOTES}}

---

### Journey: {{JOURNEY_2_NAME}}

> Repeat the structure above for each major journey.

---

## Screen / State Inventory

> One section per screen or major view. Each screen must specify ALL named states.
> ASCII wireframes are strongly encouraged for complex layouts.

---

### Screen: {{SCREEN_1_NAME}}

**Purpose:** {{SCREEN_1_PURPOSE}}

**Entry from:** {{SCREEN_1_ENTRY}}

**Exits to:** {{SCREEN_1_EXITS}}

#### Layout Wireframe (mobile-first)

```
{{SCREEN_1_WIREFRAME_MOBILE}}
```

Tablet / Desktop variations (describe differences only):
{{SCREEN_1_RESPONSIVE_NOTES}}

#### Component Hierarchy

1. {{COMPONENT_1}}
2. {{COMPONENT_2}}
3. {{COMPONENT_3}}

#### Named States

**Default state**

{{SCREEN_1_DEFAULT_STATE}}

---

**Loading state**

- Trigger: {{LOADING_TRIGGER}}
- Display: {{LOADING_DISPLAY}}
- `aria-live="polite"` region active.
- Expected duration: {{LOADING_DURATION}}

---

**Empty state**

- Trigger: {{EMPTY_TRIGGER}}
- Display: {{EMPTY_DISPLAY}}
- Call-to-action: {{EMPTY_CTA}}

---

**Error state**

- Trigger: {{ERROR_TRIGGER}}
- Display: {{ERROR_DISPLAY}}
- Recovery action: {{ERROR_RECOVERY}}
- `role="alert"` active.

---

**Success state**

- Trigger: {{SUCCESS_TRIGGER}}
- Display: {{SUCCESS_DISPLAY}}
- Next step: {{SUCCESS_NEXT}}
- Announced via `aria-live` or `role="status"`.

---

**Disabled state** *(if applicable)*

- Condition: {{DISABLED_CONDITION}}
- Display: {{DISABLED_DISPLAY}}
- Explanation shown to user: {{DISABLED_EXPLANATION}}

---

#### Interactions & Animations

| Interaction | Behavior | Timing | `prefers-reduced-motion` |
|-------------|----------|--------|--------------------------|
| {{INTERACTION_1}} | {{BEHAVIOR_1}} | {{TIMING_1}} | {{REDUCED_MOTION_1}} |
| {{INTERACTION_2}} | {{BEHAVIOR_2}} | {{TIMING_2}} | {{REDUCED_MOTION_2}} |

---

#### Accessibility Annotations

- Heading level: {{HEADING_LEVEL}}
- Landmark role: {{LANDMARK_ROLE}}
- Focus management: {{FOCUS_MANAGEMENT}}
- Screen reader notes: {{SR_NOTES}}
- Keyboard shortcuts (if any): {{KEYBOARD_SHORTCUTS}}

---

### Screen: {{SCREEN_2_NAME}}

> Repeat the structure above for each screen.

---

## Error & Edge Case Catalogue

> Consolidate all error conditions across journeys and screens.

### Error: {{ERROR_1_NAME}}

**Trigger:** {{ERROR_1_TRIGGER}}

**Affected journeys / screens:** {{ERROR_1_SCOPE}}

**Display:**
- Visual: {{ERROR_1_VISUAL}}
- Copy: {{ERROR_1_COPY}}
- Icon: {{ERROR_1_ICON}}

**Recovery path:** {{ERROR_1_RECOVERY}}

**Accessibility:** `role="alert"` / `aria-describedby` on affected input.

---

### Edge Case: {{EDGE_1_NAME}}

**Scenario:** {{EDGE_1_SCENARIO}}

**Behavior:** {{EDGE_1_BEHAVIOR}}

---

## Interaction & Animation Spec

> Reference `DESIGN.md` for design tokens. Specify timing per interaction here.

| Element | Animation | Duration | Easing | Reduced-motion fallback |
|---------|-----------|----------|--------|------------------------|
| Page transition | Fade in | 200ms | ease-out | Instant (no animation) |
| Modal open | Scale + fade | 150ms | ease-out | Instant |
| Toast/notification | Slide in from top | 300ms | ease-out | Instant |
| Button loading | Spinner spin | 800ms loop | linear | Static spinner |
| {{CUSTOM_1}} | {{ANIM_1}} | {{DUR_1}} | {{EASE_1}} | {{REDUCED_1}} |

---

## Dev Handoff Notes

> Planning guidance for the external dev tool. Read-only — do not edit during implementation.

**Implementation priority by journey:**

1. {{PRIORITY_JOURNEY_1}} — critical path
2. {{PRIORITY_JOURNEY_2}}
3. {{PRIORITY_JOURNEY_N}}

**Assets required before dev start:**

- [ ] Logo SVG
- [ ] Icon set ({{ICON_SET}})
- [ ] Hero / feature images ({{IMAGE_SPEC}})
- [ ] Final copy for all screens (headlines, body, CTAs, error messages)

**Key implementation requirements:**

- Mobile-first CSS (min-width media queries).
- Semantic HTML5 landmark structure per every screen.
- Form validation: on-blur (not on every keystroke).
- All error messages via `aria-describedby`; focus moves to first error on submit.
- Loading states on every async action; disable interactive elements during load.
- `prefers-reduced-motion` media query respected for all animations.
- WCAG 2.1 AA minimum — see `DESIGN.md §3` for the full accessibility contract.

**Open questions for product / stakeholders:**

1. {{OPEN_QUESTION_1}}
2. {{OPEN_QUESTION_2}}

---

*Part of the BMAD Planning & Orchestrator plugin. Produced by the `bmad-ux` skill.*
