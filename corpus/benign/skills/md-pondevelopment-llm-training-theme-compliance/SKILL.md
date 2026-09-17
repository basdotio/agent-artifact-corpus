---
name: theme-compliance
description: Audit and fix theme compliance issues in HTML and JS files — raw Tailwind color utilities, hardcoded hex/RGB values, inline styles, and incorrect getCssVar usage. Use this when asked to "audit colors", "check theme compliance", "fix raw Tailwind", "fix hardcoded colors", or when lint:js-colors reports violations.
---

# Theme Compliance Audit & Fix

## Goal

Ensure all papers, questions, and site-wide HTML/JS files use the semantic design system tokens (CSS custom properties, panel/chip/toggle classes) instead of raw Tailwind color utilities or hardcoded hex/RGB/HSL values. This enables consistent dark-mode support and theme switching.

## When to use

- After creating or editing a paper/question with colored UI (bars, charts, badges, conditional styling)
- When `npm run lint:js-colors` reports violations
- When performing a bulk housekeeping pass
- When a visual regression appears in dark mode

## Quick check

```bash
# Run the JS color linter to find violations
npm run lint:js-colors

# Run full lint (includes HTML, CSS, JS colors, and repo validation)
npm run lint
```

## The two violation categories

### 1. HTML: Raw Tailwind color utilities and hardcoded colors

**Problem:** Classes like `bg-indigo-50`, `border-blue-200`, `text-red-600` or inline `style="color: #ef4444"` break theme switching.

**Solution:** Replace with semantic theme classes:

| Instead of | Use |
|-----------|-----|
| `bg-indigo-50`, `bg-blue-50` | `panel panel-info` or `bg-surface-*` tokens |
| `bg-green-50`, `bg-emerald-50` | `panel panel-success` or `bg-success-*` tokens |
| `bg-yellow-50`, `bg-amber-50` | `panel panel-warning` or `bg-warning-*` tokens |
| `bg-red-50`, `bg-rose-50` | `panel panel-danger` or use `--tone-rose-*` |
| `border-blue-200` | `border-info` or `border-accent` |
| `text-indigo-700` | `text-accent-strong` |
| `text-emerald-600` | `text-success` |
| Inline `style="color: #xxx"` | Semantic class or JS `getCssVar()` |

**Audit command:**
```bash
# The HTML linter catches <style> blocks and inline styles in fragments
npm run lint:html
```

### 2. JS: Hardcoded hex colors in interactive scripts

**Problem:** Lines like `element.style.backgroundColor = '#10b981'` or `fill: '#6366f1'` ignore the active theme.

**Solution:** Use the `getCssVar` helper with a hardcoded fallback:

```javascript
const getCssVar = (name, fallback) => {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
};

// Usage
element.style.backgroundColor = getCssVar('--tone-emerald-strong', '#10b981');
```

**Audit command:**
```bash
npm run lint:js-colors
```

**Auto-fix command (use with care):**
```bash
node scripts/fix-js-colors.js           # Apply fixes
node scripts/fix-js-colors.js --dry-run # Preview only
```

## Common token mappings

| Hex value | CSS token | Semantic meaning |
|-----------|-----------|-----------------|
| `#10b981`, `#22c55e`, `#059669` | `--tone-emerald-strong` | Success/positive |
| `#34d399` | `--tone-emerald-border` | Success border |
| `#ecfdf5`, `#d1fae5` | `--tone-emerald-bg` | Success background |
| `#6366f1`, `#4f46e5` | `--color-accent-strong` | Primary accent |
| `#eef2ff`, `#e0e7ff` | `--color-accent-bg` | Accent background |
| `#ef4444`, `#dc2626` | `--tone-rose-strong` | Danger/negative |
| `#fef2f2`, `#fee2e2` | `--tone-rose-bg` | Danger background |
| `#f59e0b`, `#d97706` | `--tone-amber-strong` | Warning |
| `#fffbeb`, `#fef3c7` | `--tone-amber-bg` | Warning background |
| `#e5e7eb`, `#d1d5db` | `--color-border` | Neutral border |
| `#f3f4f6`, `#f9fafb` | `--color-surface-alt` | Neutral surface |
| `#1f2937`, `#111827` | `--color-text-primary` | Primary text |
| `#6b7280`, `#9ca3af` | `--color-text-secondary` | Secondary text |

To discover more tokens, inspect `css/theme.css` for `--tone-*`, `--color-*` custom property definitions.

## getCssVar critical rules

1. **Define at IIFE top scope**, after `'use strict'`, never inside `init()`. Sibling functions like `updateUI()`, `renderChart()` need access. Defining inside `init()` causes `ReferenceError`.

2. **Always provide a fallback** — the second argument is a literal color value that works if the CSS variable is missing:
   ```javascript
   getCssVar('--tone-emerald-strong', '#10b981')  // ✅
   getCssVar('--tone-emerald-strong')              // ❌ no fallback
   ```

3. **SVG template literals** — wrap in `${}` interpolation AND quote the attribute:
   ```javascript
   // ✅ Correct
   `stroke="${getCssVar('--color-border', '#e5e7eb')}"`

   // ❌ Wrong — raw function call, no interpolation
   `stroke=getCssVar('--color-border', '#e5e7eb')`
   ```

4. **Never use raw `var()` in JS-generated inline styles:**
   ```javascript
   // ❌ Unreliable cross-browser
   element.style.color = 'var(--tone-emerald-strong)';

   // ✅ Resolves the value first
   element.style.color = getCssVar('--tone-emerald-strong', '#10b981');
   ```

## Full audit workflow

1. **Run linters:**
   ```bash
   npm run lint:js-colors   # JS violations
   npm run lint:html         # HTML violations
   ```

2. **Review violations** — the JS linter outputs file paths and line numbers.

3. **Apply fixes:**
   - For JS: use `node scripts/fix-js-colors.js` for bulk fixes, or manual edits for complex cases.
   - For HTML: manually replace Tailwind classes with semantic tokens (no auto-fixer).

4. **Verify:**
   ```bash
   npm test                  # Full lint + E2E
   ```

5. **Visual smoke test** — check both light and dark mode in the browser, especially charts, bars, and conditional coloring.

## Checklist items (from PAPER_CHECKLIST.md / QUESTION_CHECKLIST.md)

- [ ] `getCssVar` helper (if used) defined at **IIFE top scope**, not inside `init()`
- [ ] No raw Tailwind color utilities in HTML — use semantic theme classes
- [ ] No hardcoded colors in JS — use `getCssVar('--token', '#fallback')`
- [ ] No `<style>` blocks or inline `style=""` in HTML fragments
- [ ] Dark mode renders correctly (no invisible text, no clashing backgrounds)
