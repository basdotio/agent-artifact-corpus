---
name: multi-brand-theming
description: Multi-brand and theming: derive palettes from base, palette overrides, data-theme, white-label UI using UDS tokens.
version: 0.6.0
triggers:
  - multi-brand
  - white label
  - theming
  - brand override
  - custom palette
  - theme variant
  - white-label ui
  - multiple themes
  - brand palette
  - custom theme
  - custom colors
  - my brand colors
  - generate palette
  - palette from hex
  - use my colors
  - brand hex colors
  - palette from user input
  - customize colors
  - my company colors
---

# Multi-Brand Theming — UDS Skill

Use this skill when the user needs **multi-brand**, **white-label**, **custom theming**, or **custom colors** on top of the Universal Design System. UDS has 9 structural palettes and a **palette generator**: you can provide your own colors (e.g. hex values) and UDS generates a full palette (primary, secondary, accents, neutrals, WCAG-aware) and merges it into the token set.

## When to Use

- User wants to **customize colors** or use **their own brand colors** (hex input → generated palette).
- User wants multiple brands or products with different look-and-feel but shared components.
- User needs a custom palette (e.g. company brand colors) that fits the UDS token model.
- User is deciding between one design system with brand layers vs separate systems.
- User wants to switch themes at runtime via `data-theme`.

## Token Architecture

- **Foundation (locked):** Typography scale (Inter body), spacing (4px base, 12-step scale), motion durations/easing, z-index, opacity. Same for every palette.
- **Palette (vary):** Color (brand, text, background, border, status), shadow (elevation), border-radius (shape), display font (h1–h3). Each palette defines these in `tokens/design-tokens.json` under `theme.<palette>` and optionally `theme.<palette>.dark` for dark mode.

One surface = one palette. Do not mix palette token sets on the same page.

## Applying a Palette

- **HTML:** Set `data-theme` on the root (or app wrapper): `<html lang="en" data-theme="minimal-saas">`. For dark mode, add a class (e.g. `docs-dark`) and define overrides under `[data-theme="X"].docs-dark` in CSS.
- **Runtime switch:** `document.documentElement.setAttribute('data-theme', 'corporate');` — use the palette slug (e.g. `corporate`, `gradient-startup`, `ai-futuristic`).
- **Scoped:** You can set `data-theme` on a subtree (e.g. `<div data-theme="apple-minimal">`) so one page has different sections with different palettes; use sparingly for consistency.

## Built-in Palettes (9)

| Palette | Identity | Best for |
|---------|----------|----------|
| minimal-saas | Balanced, neutral | Product UI, SaaS apps |
| gradient-startup | High-energy gradients | Marketing, landing pages |
| ai-futuristic | Sharp, dark-native | Dev tools, AI products |
| corporate | Conservative, squared | Enterprise, regulated |
| apple-minimal | Smooth, refined | Premium consumer |
| illustration | Friendly, rounded | Education, creative |
| dashboard | Compact, data-dense | Analytics, admin panels |
| bold-lifestyle | Brutalist, 0px radius | Fashion, media |
| minimal-corporate | Subtle, understated | Professional services |

## Customize Colors: Palette Generated from User Input

UDS can **generate a full palette from user-provided colors** (e.g. one or more hex codes). The palette engine derives primary, secondary, accent, neutrals, and ensures WCAG contrast guidance. Output is merged into `tokens/design-tokens.json` and `tokens/figma-tokens.json` so you use it like any built-in palette via `data-theme="<name>"`.

## Creating a Custom Palette

Use the palette CLI to derive a new palette from **your** brand colors (user input); it merges into `tokens/design-tokens.json` and `tokens/figma-tokens.json`:

```bash
# One primary color (secondary/accent derived)
python src/scripts/palette.py create --name my-brand --colors "#3B82F6"

# Multiple colors, round shape
python src/scripts/palette.py create --name duo-tone --colors "#E8590C,#7048E8" --shape round

# List built-in and custom palettes
python src/scripts/palette.py list

# Preview color harmony before creating
python src/scripts/palette.py preview --colors "#3B82F6"
```

Custom palettes live under `tokens/custom/` and are merged into the main token files. After creation, use `data-theme="my-brand"` (or the name you gave). Ensure WCAG contrast: run `npm run audit` after adding or changing palette colors.

## One System vs Separate Systems

- **One system with brand layers (recommended):** One codebase, one component set, multiple palettes. Each product or brand picks a palette (built-in or custom). Single docs, single dependency, easier upgrades.
- **Separate systems:** Only if brands need completely different components, workflows, or release cycles. Heavier to maintain; consider first whether custom palettes + same components suffice.

## MCP

If available, `get_palette` returns the full token set for any palette (light/dark). Use it to show users exact values for a chosen theme or to compare palettes.

## Quick Reference

| Task | Command or action |
|------|--------------------|
| Apply palette | `data-theme="<palette-slug>"` on html or container |
| Create custom palette | `python src/scripts/palette.py create --name <name> --colors "#hex" [--shape round\|square\|balanced]` |
| List palettes | `python src/scripts/palette.py list` |
| Dark mode | Same palette; overrides under `[data-theme="X"].docs-dark` (or your dark class) |
| Source of truth | `tokens/design-tokens.json` — palette overrides under `theme.<palette>` |
