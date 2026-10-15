# Themes

A theme = colours, fonts, logo and contact details, injected as CSS variables over the style's layout.

## Where the theme comes from (first match wins)
1. `pitch-profile/theme.json`: hand-tuned theme for your company (optional).
2. Generated from `pitch-profile/company.yaml → brand`:
   `accent`, `accent_2`, `background`, `heading_font`, `body_font` (Google Fonts names) or `fonts_css` (local fonts), `corner_radius`, `heading_weight`.
   The generator keeps the deck dark and **lightens your accent just enough to pass WCAG AA** as small text.
3. `themes/default.json`: neutral fallback (dark + soft blue).

Logo, product logos and contact always come from the profile (`company.yaml`, `catalog.yaml`).

## One deck = one brand
- Every deck renders in your company theme. Products appear as **logo badges** (`offer.product`, `cards[].product`, `solutions[].brand`) in your colours.
- Pure single-product pitch: add `pitch-profile/themes/<offer-id>.json` and set deck-data `"theme": "<offer-id>"`. The cover and close then show "A <Company> company".

## Theme file
```json
{
  "name": "acme", "label": "Acme",
  "fonts": ["https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"],
  "vars": { "--accent", "--accent-rgb", "--accent-2", "--accent-ink", "--glow-a-rgb", "--glow-b-rgb", "--num-solid",
            "--bg", "--bg-2", "--text", "--body", "--muted", "--grid", "--line", "--good", "--warn", "--bad",
            "--radius-card", "--radius-pill", "--head", "--sans", "--head-weight", "--head-track",
            "--eyebrow-font", "--eyebrow-track", "--g-font", "--g-style", "--g-weight", "--g-track", "--photo-grade" }
}
```
`--accent-rgb` is a space-separated triplet (`"124 156 255"`). `--good/--warn/--bad` colour the score bars; keep them distinct from `--accent`. `profile_check.py` checks text colours against WCAG AA.
