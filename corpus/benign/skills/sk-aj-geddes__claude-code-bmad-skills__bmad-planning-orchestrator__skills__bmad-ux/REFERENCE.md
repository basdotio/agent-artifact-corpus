# BMAD UX — Reference Material

Extended reference for the `bmad-ux` skill. Keep the SKILL.md under ~5K tokens;
reach for this file when you need the full pattern library, breakpoint detail, or
component state matrix.

---

## Design Pattern Library

### Color System Patterns

**Monochromatic** — one hue at multiple lightness values. Simple, cohesive, easy to
keep WCAG-compliant. Best for utility-focused products.

**Complementary** — two hues opposite on the color wheel (e.g., blue + orange).
High visual impact. Use the secondary sparingly (CTAs, highlights). Contrast-check
every combination.

**Triadic / Split-Complementary** — three evenly-spaced hues. Rich; complex to
manage. Limit to illustration / data visualization, not UI chrome.

**Semantic color independence rule** — success/warning/error/info colors must convey
meaning through shape and label in addition to color (WCAG 1.4.1 — Use of Color).

### Typography Pattern Principles

- **Vertical rhythm** — all spacing is a multiple of the 8px base unit. Odd spacing
  values (e.g., 10px, 14px) break rhythm and indicate a token error.
- **Line-length** — body text: 60–80 characters. Headings: 40–60 characters. Enforce
  via `max-width` on the text container, not the element itself.
- **Heading hierarchy** — H1 is a page-level landmark; only one per page. H2 sections
  the page; H3 subsections an H2 block. Never skip levels (H1 → H3).
- **Font loading** — specify `font-display: swap` in the Dev Notes of any story that
  loads a web font.

### Spacing & Layout Patterns

**8px grid** — every margin, padding, gap, and size value must be divisible by 4 (half
step) or 8 (full step). Document exceptions in `decision-log.md`.

**Container nesting** — maximum two levels of horizontal padding (page container +
component padding). Deeper nesting collapses content on mobile.

**Sticky / fixed elements** — must not cover interactive content. Reserve a
`--height-header` token (e.g., 56px mobile / 64px desktop) and use it as
`scroll-margin-top` on all anchor targets.

### Animation & Motion Patterns

| Category | Duration | Easing | Notes |
|----------|----------|--------|-------|
| Micro (icon, badge) | 100–150ms | ease-out | Nearly instant |
| Element enter / exit | 150–250ms | ease-out / ease-in | Fade, slide, scale |
| Page transition | 200–300ms | ease-in-out | Fade preferred |
| Loader / spinner | 800ms loop | linear | Must respect `prefers-reduced-motion` |
| Complex sequence | 300–500ms | custom cubic-bezier | Avoid for core flows |

`prefers-reduced-motion: reduce` behavior:
- Disable all decorative animations.
- Keep meaningful transitions (modal open) as instant visibility change.
- Spinners: show static version; do not spin.

---

## Full Breakpoint Reference

| Name | Min-width | Max-width | Columns | Container max | Padding |
|------|-----------|-----------|---------|---------------|---------|
| Mobile | 320px | 767px | 1 | 100% | 16px |
| Tablet | 768px | 1023px | 2 | 100% | 24px |
| Desktop | 1024px | 1439px | 3–4 | 1200px | 32px |
| Desktop XL | 1440px | — | 4–6 | 1440px | 32px |

### Touch vs. Pointer targets

| Breakpoint | Input type | Min target size | Min spacing |
|------------|------------|-----------------|-------------|
| Mobile | Touch | 44×44px | 8px |
| Tablet | Touch + mouse | 44×44px | 8px |
| Desktop | Mouse | 40×40px | 4px |

### Typography scale (per breakpoint)

See `responsive-breakpoints.sh` for the machine-readable version.
Run: `bash "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/responsive-breakpoints.sh"`

| Role | 320px | 768px | 1024px | 1440px |
|------|-------|-------|--------|--------|
| H1 | 28px | 36px | 48px | 56px |
| H2 | 24px | 28px | 36px | 40px |
| H3 | 20px | 22px | 24px | 28px |
| H4 | 18px | 18px | 20px | 22px |
| Body | 16px | 16px | 18px | 18px |
| Small | 14px | 14px | 16px | 16px |

---

## Component State Matrix

Every interactive component must have every state below defined in DESIGN.md.
Mark N/A only when a state is genuinely impossible for that component.

| Component | Default | Hover | Focus | Active | Disabled | Loading | Error | Success | Empty |
|-----------|---------|-------|-------|--------|----------|---------|-------|---------|-------|
| Button (primary) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| Button (secondary) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| Button (destructive) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| Text input | ✓ | — | ✓ | — | ✓ | — | ✓ | ✓ | — |
| Select | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — |
| Checkbox | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — |
| Radio | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — |
| Card | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | — | — |
| Modal / dialog | ✓ (open) | — | ✓ | — | — | ✓ | ✓ | ✓ | — |
| Nav item | ✓ | ✓ | ✓ | ✓ (current) | — | — | — | — | — |
| Toast / banner | ✓ | — | ✓ | — | — | — | ✓ | ✓ | — |
| Data table | ✓ | ✓ (row) | ✓ | — | — | ✓ | ✓ | — | ✓ |
| List view | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | — | ✓ |

### Accessibility annotations per component

| Component | Required ARIA | Focus behavior | Screen reader note |
|-----------|---------------|----------------|-------------------|
| Button | `aria-disabled`, `aria-busy` (loading) | Receives focus; Enter/Space activates | Announce state changes |
| Text input | `aria-describedby` (error/helper), `aria-invalid` | Tab in; Enter submits form | Error announced via `role="alert"` |
| Select | `aria-expanded`, `aria-controls` (listbox) | Tab in; arrow keys navigate options | Selected option announced |
| Modal | `role="dialog"`, `aria-modal`, `aria-labelledby` | Focus moves to modal on open; trapped | Dismiss with Escape |
| Nav | `aria-label="Main navigation"`, `aria-current="page"` | Tab through items; Enter activates | Current page announced |
| Toast | `role="alert"` (error) or `role="status"` (info) | Non-focusable; auto-dismiss | Announced immediately |
| Loading | `aria-live="polite"`, `aria-label="Loading..."` | Non-focusable | Announced when content loads |
| Empty state | — | CTA button receives focus | CTA must describe the action |

---

## WCAG 2.1 AA Quick Reference

Full interactive checklist:
```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/wcag-checklist.sh"
```

Color pair verification:
```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/contrast-check.py" #foreground #background
```

### Key thresholds

| Criterion | Threshold | Notes |
|-----------|-----------|-------|
| Normal text contrast (1.4.3) | ≥ 4.5:1 | Text < 18px (or bold < 14px) |
| Large text contrast (1.4.3) | ≥ 3:1 | Text ≥ 18px (or bold ≥ 14px) |
| UI component contrast (1.4.11) | ≥ 3:1 | Borders, icons, focus rings |
| Touch target size (2.5.5 advisory) | ≥ 44×44px | Mobile and tablet |
| Reflow (1.4.10) | No H-scroll at 320px | Must plan for this explicitly |
| Text resize (1.4.4) | 200% without loss | Avoid fixed heights on text containers |
| Focus visible (2.4.7) | 2px solid outline minimum | Never `outline: none` unresolved |

### Common planning failures to avoid

- Specifying a color pair without verifying contrast — always run `contrast-check.py`.
- Specifying hover-only interactions (not keyboard-reachable).
- Designing empty states or error states as "TBD" — they must be fully specified in
  EXPERIENCE.md before stories are created.
- Missing focus-trap spec on modals.
- Animations without a `prefers-reduced-motion` fallback.

---

## Decision Log Entries — Template

When updating DESIGN.md or EXPERIENCE.md, append an entry to `decision-log.md`:

```markdown
### [YYYY-MM-DD] UX Decision: <short title>

**Context:** <what situation prompted the change>
**Decision:** <what was changed and why>
**Alternatives considered:** <other options and why they were rejected>
**Impact:** <which screens / components are affected>
**Author:** bmad-ux skill
```

---

*Part of the BMAD Planning & Orchestrator plugin. Extended reference for the `bmad-ux` skill.*
