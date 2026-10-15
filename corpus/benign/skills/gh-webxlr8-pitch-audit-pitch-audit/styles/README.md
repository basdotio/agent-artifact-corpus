# Deck styles

Each style is one folder under `styles/`. `render.py --style <folder>` picks it. Default: `style-1`.

| Style | Name | Look | Origin |
|---|---|---|---|
| `style-2` | Editorial | Light paper, Fraunces serif headlines, white cards, sparing accent, photo-led | Original |
| `style-1` | Neon Studio (default) | Dark canvas, faint grid, corner glows, heavy tight headlines, accent payoff line, glowing "hot" card | Original |

Styles hold **layout only**. Colours, fonts, logos and contact come from a brand **theme** (`../themes/`), injected as CSS variables. A style must never hard-code a colour or font. Use the variables listed in `../themes/README.md`.

## Contract every style must meet

A style folder contains:
- `style.md`: design rules in plain words.
- `style.json` (optional): `mode` (`dark` or `light`; light generates a paper theme with an accent darkened to pass WCAG AA), `head_font`, `head_weight`.
- `style.css`: all visual rules. Page size 1280×720 px.
- `layouts.py`: `render(deck, ctx) -> str` returning one HTML document. It may reuse another style's layouts (style-2 imports style-1's and only changes CSS).
- `assets/` (optional).

Rules: use only theme CSS variables; no CSS transforms for positioning; no gradient-clipped text; support every layout in `../references/deck-data-schema.md`. Unknown fields are ignored, never crash.

## Adding a new style
1. Copy `style-2/` (smallest example) to `style-3/` and change `style.css` / `style.json`.
2. Describe it in `style.md` and add a row to the table above.
3. `python3 examples/run_demo.py` with `"style": "style-3"` must pass all four build steps.
