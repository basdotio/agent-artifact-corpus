# DESIGN.md — Visual System

> **LOCKED PLANNING ARTIFACT.** The external dev tool reads this document but must
> not edit it. All design changes go through the bmad-ux skill and are recorded in
> `decision-log.md`.

**Project:** {{PROJECT_NAME}}
**Track:** {{TRACK}}
**Date:** {{DATE}}
**Version:** {{VERSION}}

---

## 1. Design Tokens

### 1.1 Color Palette

> Replace placeholder values with project-specific colors after running contrast checks.
> Verify every text/background pair with:
> `python "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/contrast-check.py" #fg #bg`

**Primary**

| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary-50`  | `{{PRIMARY_50}}`  | Light tint backgrounds |
| `--color-primary-100` | `{{PRIMARY_100}}` | Hover backgrounds |
| `--color-primary-500` | `{{PRIMARY_500}}` | Base — buttons, links |
| `--color-primary-600` | `{{PRIMARY_600}}` | Hover state |
| `--color-primary-700` | `{{PRIMARY_700}}` | Active / pressed state |

**Secondary**

| Token | Value | Usage |
|-------|-------|-------|
| `--color-secondary-500` | `{{SECONDARY_500}}` | Accent elements |

**Semantic**

| Token | Value | Usage |
|-------|-------|-------|
| `--color-success` | `{{SUCCESS}}` | Success states, confirmations |
| `--color-warning` | `{{WARNING}}` | Warning banners |
| `--color-error`   | `{{ERROR}}`   | Error states, destructive |
| `--color-info`    | `{{INFO}}`    | Informational callouts |

**Neutral Scale**

| Token | Value | Usage |
|-------|-------|-------|
| `--color-neutral-50`  | `{{NEUTRAL_50}}`  | Page background |
| `--color-neutral-100` | `{{NEUTRAL_100}}` | Card / panel background |
| `--color-neutral-300` | `{{NEUTRAL_300}}` | Borders, dividers |
| `--color-neutral-500` | `{{NEUTRAL_500}}` | Placeholder, muted text |
| `--color-neutral-700` | `{{NEUTRAL_700}}` | Secondary body text |
| `--color-neutral-900` | `{{NEUTRAL_900}}` | Primary body text |

---

### 1.2 Typography

**Font Families**

| Role | Stack |
|------|-------|
| Sans-serif | `{{FONT_SANS}}` |
| Monospace  | `{{FONT_MONO}}` |

**Type Scale**

Scale from `responsive-breakpoints.sh`. Fill in project-confirmed values:

| Role | Mobile | Tablet | Desktop | Weight | Line-height |
|------|--------|--------|---------|--------|-------------|
| H1   | 28px   | 36px   | 48px    | 700    | 1.2         |
| H2   | 24px   | 28px   | 36px    | 700    | 1.25        |
| H3   | 20px   | 22px   | 24px    | 600    | 1.3         |
| H4   | 18px   | 18px   | 20px    | 600    | 1.4         |
| Body | 16px   | 16px   | 18px    | 400    | 1.5–1.6     |
| Small| 14px   | 14px   | 16px    | 400    | 1.5         |

---

### 1.3 Spacing Scale (8px grid)

| Token | Value | Common use |
|-------|-------|------------|
| `--space-1`  | 4px  | Inline gaps |
| `--space-2`  | 8px  | Tight internal padding |
| `--space-3`  | 12px | Form field gaps |
| `--space-4`  | 16px | Standard padding (mobile) |
| `--space-6`  | 24px | Standard padding (tablet) |
| `--space-8`  | 32px | Standard padding (desktop) |
| `--space-12` | 48px | Section margin (mobile) |
| `--space-16` | 64px | Section margin (desktop) |

---

### 1.4 Breakpoints

| Name       | Min-width | Max-width | Container max-width |
|------------|-----------|-----------|---------------------|
| Mobile     | 320px     | 767px     | 100% (16px padding) |
| Tablet     | 768px     | 1023px    | 100% (24px padding) |
| Desktop    | 1024px    | 1439px    | 1200px (32px padding)|
| Desktop XL | 1440px    | —         | 1440px              |

---

### 1.5 Elevation & Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-xs` | `0 1px 2px rgba(0,0,0,.05)`  | Subtle lift |
| `--shadow-sm` | `0 2px 4px rgba(0,0,0,.05)`  | Cards (default) |
| `--shadow-md` | `0 4px 8px rgba(0,0,0,.10)`  | Cards (hover) |
| `--shadow-lg` | `0 8px 16px rgba(0,0,0,.10)` | Dropdowns |
| `--shadow-xl` | `0 12px 24px rgba(0,0,0,.15)`| Modals |

---

### 1.6 Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm`   | 4px   | Inputs, small chips |
| `--radius-md`   | 8px   | Cards, buttons |
| `--radius-lg`   | 12px  | Panels, modals |
| `--radius-full` | 9999px| Pills, avatars |

---

## 2. Component Specifications

> For each component: visual defaults, all states, responsive behavior, accessibility.
> The external dev tool implements exactly what is specified here.

### 2.1 Button — Primary

**Visual**

| Property | Value |
|----------|-------|
| Background | `--color-primary-500` |
| Text       | White |
| Height     | 48px (mobile/tablet) · 40px (desktop) |
| Padding    | 16px 32px |
| Border-radius | `--radius-md` |
| Font       | 16px, weight 600 |
| Min-width  | 120px |

**States**

| State    | Visual change |
|----------|---------------|
| Default  | Primary-500 background |
| Hover    | Primary-600 background |
| Focus    | 2px solid outline, Primary-300, 2px offset |
| Active   | Primary-700 background |
| Disabled | 50% opacity, cursor not-allowed |
| Loading  | Spinner icon + "Loading..." text, disabled |

**Accessibility**

- Touch target min 44×44px.
- Clear focus ring (never removed, only styled).
- `aria-busy="true"` when loading; `aria-disabled="true"` when disabled.
- Never use `<div>` — use `<button>`.

---

### 2.2 Button — Secondary

> Shares size/radius with Primary. Contrast-check border against background.

| State | Visual |
|-------|--------|
| Default  | Transparent bg, Primary-500 border + text |
| Hover    | Primary-50 background |
| Focus    | Same ring as Primary |
| Active   | Primary-100 background |
| Disabled | 50% opacity |

---

### 2.3 Button — Destructive

> Used for delete, remove, cancel-with-consequence. Must be distinct from Primary.

| State | Visual |
|-------|--------|
| Default  | Error color background, white text |
| Hover    | Darker error shade |
| Focus    | Error-color focus ring |

---

### 2.4 Text Input

| Property | Value |
|----------|-------|
| Height   | 48px |
| Border   | 1px solid `--color-neutral-300` |
| Border-radius | `--radius-sm` |
| Padding  | 12px 16px |
| Font     | 16px (prevents iOS zoom) |

**States**

| State   | Border / Shadow |
|---------|-----------------|
| Default | Neutral-300 border |
| Focus   | Primary-500 border + 3px Primary-100 ring |
| Error   | Error-500 border + 3px Error-100 ring |
| Success | Success-500 border + check icon |
| Disabled| Neutral-100 bg, not-allowed cursor |

**Label / helper / error**

- Label: 14px medium, 8px margin-bottom. Required = asterisk (*).
- Helper: 14px Neutral-600, 4px margin-top.
- Error msg: 14px Error-600, error icon, `role="alert"`, `aria-describedby` on input.

---

### 2.5 Card

| Property | Value |
|----------|-------|
| Background | White |
| Border-radius | `--radius-md` |
| Padding  | 24px |
| Shadow   | `--shadow-sm` default, `--shadow-md` on hover |
| Image aspect | 16:9 |

**Structure:** [Image optional] → Title (H3) → Description (2-3 lines) → Action.

**Responsive:** 1 col (mobile) · 2 col (tablet) · 3-4 col (desktop).

---

### 2.6 Modal / Dialog

| Property | Value |
|----------|-------|
| Mobile  | Full screen or bottom-sheet |
| Tablet  | 80% width, centered |
| Desktop | Max 600px, centered, `--shadow-xl` |

**Accessibility contract:**

- `role="dialog"` + `aria-modal="true"` + `aria-labelledby`.
- Focus moves to modal on open.
- Focus trapped inside (Tab cycles within).
- Escape closes modal; focus returns to trigger.

---

### 2.7 Navigation

| Breakpoint | Pattern |
|------------|---------|
| Mobile     | Hamburger (>=) icon → full-screen overlay |
| Tablet     | Expanded horizontal or collapsible sidebar |
| Desktop    | Horizontal bar, optional dropdowns |

Keyboard: All nav items reachable via Tab / arrow keys. `aria-label="Main navigation"`.

---

### 2.8 Loading / Skeleton State

- Inline spinner: `aria-label="Loading..."` + `aria-live="polite"`.
- Skeleton screens: match layout shape; no real content until loaded.
- Full-page loader: `role="status"` + visible label.

---

### 2.9 Error Banner

- Full-width band, Error semantic color.
- Icon + title ("Something went wrong") + optional detail.
- Action button ("Retry" or "Dismiss").
- `role="alert"` — announced immediately by screen readers.

---

## 3. WCAG 2.1 AA Contract

> Run the full checklist:
> `bash "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/wcag-checklist.sh"`

This visual system commits to the following:

**Color contrast — verified pairs**

| Pair | Ratio | AA Normal | AA Large | Notes |
|------|-------|-----------|----------|-------|
| Body text on page bg       | {{RATIO_BODY}}   | [ ] | — | |
| Primary btn text on btn bg | {{RATIO_BTN}}    | [ ] | — | |
| Link text on page bg       | {{RATIO_LINK}}   | [ ] | — | |
| Placeholder on input bg    | {{RATIO_PLACEHOLDER}} | [ ] | — | 4.5:1 required |
| Error text on input bg     | {{RATIO_ERROR_TEXT}}  | [ ] | — | |

Verify each:
```
python "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/contrast-check.py" #fg #bg
```

**Keyboard & focus**

- All interactive elements reachable via Tab. Tab order follows reading order.
- Focus indicator: 2px solid outline, 2px offset. Never `outline: none` without a custom visible replacement.
- Skip-to-content link at top of every page.
- Modal/dialog focus trap active when open; Escape closes.

**Touch & sizing**

- Minimum touch target: 44×44px (mobile and tablet).
- Minimum target spacing: 8px.
- No horizontal scroll at 320px viewport width (WCAG 1.4.10).
- Text resizable to 200% without loss of functionality.

**Semantic structure (spec for dev)**

- One H1 per page. Heading hierarchy: H1 → H2 → H3 (no skips).
- Landmark regions: `<header>`, `<nav>`, `<main>`, `<footer>`.
- Lists use `<ul>` / `<ol>`. Tables have `<th scope>` + `<caption>`.
- Buttons for actions (`<button>`); links for navigation (`<a>`).
- All images: descriptive `alt` or `alt=""` for decorative.
- Form inputs: `<label for>` or `aria-label`. Error via `aria-describedby`.
- Dynamic content: `aria-live="polite"` for updates; `role="alert"` for errors.
- `prefers-reduced-motion`: disable or reduce animations where specified.

---

## 4. Design Decisions

> Record rationale here. Link to `decision-log.md` for full thread.

| Decision | Rationale | Alternatives considered |
|----------|-----------|------------------------|
| {{DECISION_1}} | {{RATIONALE_1}} | {{ALTERNATIVES_1}} |

---

*Part of the BMAD Planning & Orchestrator plugin. Produced by the `bmad-ux` skill.*
