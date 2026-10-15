# Template — choosing and configuring a .pptx template

The builder knows nothing about any template. Everything lives in `manual.json` → `"template"`. The deck is
built from the template file itself (masters, layouts, theme, logo art come along); the template's own sample
slides are dropped at the end.

No template of your own? Use the bundled `templates/plain.pptx` (white, 16:9, no branding) or `templates/dark.pptx`
(the same, dark background, light text) — regenerate them with `scripts/make_plain_template.py [--theme dark]`.
Their configs are the first two worked examples below.

## 1. Inspect before you configure

```bash
$PY $S/scripts/inspect_template.py <template.pptx> [--suggest] [--render <dir>]
```

Prints slide size, theme colours per master, every master's layouts (placeholder idx/type/box in inches) and
every sample slide (its layout, placeholders, shapes, text). `--render <dir>` also exports `<dir>/template.pdf`
(Keynote on macOS, PowerPoint on Windows, else LibreOffice) — **look at it**: the logo, rules and footer are often
drawn on the layout, not as placeholders, and only a render shows where they sit.

`--suggest` prints a `"template"` block to paste into `manual.json` — a starting point measured from the file:

- `cover` = the first layout with a centred title, or a title + subtitle; `divider` = title + one body;
  `content` = title only. A layout name that repeats across masters is given as `{"slide": n}` when a sample
  slide uses it, else as `{"layout", "master"}`.
- `area` = `[title's left edge (to 0.1"), title bottom + 0.2", slide width − 2 × margin, down to 0.3" above the
  lowest layout-drawn shape on the content layout, or 0.5" above the slide bottom]`, to 0.05".
- `colors` only when the theme background (`lt1`) is dark — then the dark worked config below; a light theme
  keeps the builder defaults.

It cannot see art drawn on sample slides or a logo that is a placeholder, so build once with it and look
(§10) before trusting `area`.

## 2. Pick cover / divider / content layouts

Each of `cover`, `divider`, `content` takes one of:

| Form | When |
|---|---|
| `{"layout": "<name>", "master": <i>}` | layout names are unique within that master (`master` defaults to 0) |
| `{"slide": <n>}` | use sample slide n's layout (1-based) — required when names repeat across masters |

- **cover:** the title page. If its layout has no title (idx 0) **and** subtitle (idx 1) placeholder, the
  builder draws text boxes at `cover.title_box` / `cover.subtitle_box` (`[x, y, w, h]` inches).
  `cover.title_left` moves both placeholders' left edge (e.g. to clear logo art on the left).
- **divider:** agenda + chapter dividers. Uses title idx 0 + body idx 1 when present, else text boxes
  (title in the content title box; list inside `area`).
- **content:** every task and table slide. Uses title placeholder idx 0 unless `title_box` is set.
- Anything drawn **on the sample slide** (not its layout) is lost when sample slides are dropped. If the
  render shows a band or logo on the sample but the inspect output lists no such shape on the layout, check.

## 3. Content area

`"area": [x, y, w, h]` in inches = the rectangle below the title and above the footer/logo. Steps, tip slot,
screenshot and tables all live inside it.

- `y` just below the title (or the template's rule under it); `y + h` above the footer/logo.
- The tip box occupies a fixed slot at the bottom-left: top at `y + h − 1.3"`, 3.95" wide, 1.05" tall.
  If the template has a logo bottom-left, end `area` above it.
- Screenshot goes right of the steps column, cropped to 16:9 around its marks.
- Table `widths` in `intro`/`reference` should sum to ≤ `w`.

## 4. Title placement

- `"title_box": [x, y, w, h]` forces the heading (kicker + title) into a text box instead of the title
  placeholder. Needed when the content layout has no title placeholder, or its placeholder overlaps a logo.
- Without either, the builder falls back to `[area.x, 0.3, area.w, 1.2]`, bottom-anchored.

## 5. Footer

`"footer": {"slide": <n>, "placeholders": [<idx>, …]}` copies those placeholders from sample slide n onto
every new slide. Use it when the footer copy ("Confidential", page label) lives on a sample slide.
Omit it when the layout already draws the footer. Copied shapes get fresh ids (a duplicate id crashed Keynote).

## 6. Colours

Hex without `#`. Keys and what they paint:

| Key | Paints | Default (light) |
|---|---|---|
| `accent` | kicker text, callout boxes, numbered badges, tip outline + label, TOC numbers | `E5484D` |
| `on_accent` | digits in badges, table header text, badge outline | `FFFFFF` |
| `text` | slide titles, step text, `**bold**` runs | `1F2328` |
| `muted` | subtitles, non-bold tip/step text | `4A4F57` |
| `tip_fill` | tip box fill | `FDECEC` |
| `table_head` / `table_row` / `table_ink` | table header fill / body fill / body text | `E5484D` / `F4F5F7` / `1F2328` |
| `pic_line` | thin frame around each screenshot | `C8CCD2` |

- Defaults suit a **light** template. A **dark** template must override at least `text`, `muted`, `tip_fill`,
  `pic_line` — dark text on a dark slide validates fine and is invisible (only visual QA catches it).
- `accent` must stand out against the screenshots: if the app's own buttons share the accent colour, callouts
  blend in. Pick a contrasting accent and check a busy shot.

## 7. Fonts and labels

- `"font"` (Latin, default `Arial`) and `"script_font"` (complex-script `<a:cs>` face, default none).
- Set `script_font` for scripts the Latin font lacks. Thai: `"Tahoma"` — Arial and most brand faces have no Thai
  glyphs; Tahoma ships with Office on Windows and macOS, so the PPTX stays editable everywhere.
- `"tip_label"` (default `"Tip: "`) prefixes every tip box — e.g. `"เคล็ดลับ: "` for a Thai manual.

## 8. Worked configs

### Plain light (bundled `templates/plain.pptx`, 13.33" × 7.5")

```json
"template": {
  "path": "<skill dir>/templates/plain.pptx",
  "cover":   { "layout": "Title Slide" },
  "divider": { "layout": "Title and Content" },
  "content": { "layout": "Title Only" },
  "area": [0.6, 1.75, 12.1, 4.9]
}
```

Colour defaults apply. A relative `path` is resolved against the workspace.

### Plain dark (bundled `templates/dark.pptx`, 13.33" × 7.5", background `1B1F24`)

Same layouts as plain; only the colours change. `inspect_template.py --suggest` prints exactly this `colors`
block for any template whose theme background is dark (`build_manual.DARK_COLORS`). `accent`, `on_accent` and
`table_head` keep their defaults — red on the dark grey reads fine.

```json
"template": {
  "path": "<skill dir>/templates/dark.pptx",
  "cover":   { "layout": "Title Slide" },
  "divider": { "layout": "Title and Content" },
  "content": { "layout": "Title Only" },
  "area": [0.6, 1.75, 12.1, 4.9],
  "colors": {
    "text": "E8EAED", "muted": "B0B6BE", "tip_fill": "2A3038",
    "table_row": "262B32", "table_ink": "E8EAED", "pic_line": "5A6068"
  }
}
```

### A dark branded template (13.33" × 7.5", logo art on the cover's left, footer on a sample slide)

What `inspect_template.py` + the render typically show: a cover layout with full-bleed art, a separate
"section" layout for dividers, a "Title Only" content layout, and the footer copy as placeholders 11/12 on a
sample slide rather than on the layout.

```json
"template": {
  "path": "~/Templates/brand-dark.pptx",
  "cover":   { "layout": "Title Slide with Background", "title_left": 3.3 },
  "divider": { "layout": "Section Title" },
  "content": { "layout": "Title Only" },
  "footer":  { "slide": 5, "placeholders": [11, 12] },
  "area": [0.35, 1.95, 12.65, 4.8],
  "colors": {
    "accent": "FF3C63", "on_accent": "FFFFFF", "text": "FFFFFF", "muted": "E6C0C0",
    "tip_fill": "4A164E", "table_head": "FF3C63", "table_row": "F3E6EE", "table_ink": "3A1040",
    "pic_line": "5B3A66"
  }
}
```

### A light corporate template with repeated layout names (14.70" × 8.27", 3 masters)

- Layout names repeat ("Title Slide" twice in two masters) → pick by sample slide.
- The cover sample slide uses a layout with **no placeholders**; its title and subtitle are plain text boxes →
  `cover.title_box` / `subtitle_box` needed.
- The content sample's layout draws the logo top-left, a coloured rule at ~1.2" and a footer at ~7.5"; it has only
  a slide-number placeholder → `title_box` needed, no `footer`.

```json
"template": {
  "path": "~/Templates/corporate-light.pptx",
  "cover":   { "slide": 1, "title_box": [0.73, 2.6, 13.0, 0.9], "subtitle_box": [0.73, 3.6, 13.0, 0.6] },
  "divider": { "slide": 3 },
  "content": { "slide": 2 },
  "title_box": [1.55, 0.2, 12.7, 0.95],
  "area": [0.45, 1.45, 13.8, 6.0],
  "colors": {
    "accent": "4E7A00", "on_accent": "FFFFFF", "text": "262626", "muted": "4A4A4A",
    "tip_fill": "EEF7D9", "table_head": "4E7A00", "table_row": "F4F4F4", "table_ink": "262626",
    "pic_line": "C8C8C8"
  }
}
```

What the render showed for that kind of template:
- cover: the coloured band is on the layout, so it survives; title/subtitle boxes above clear the logo.
- content + divider: titles drawn in `title_box`, right of the logo, above the rule; tip slot clears the footer.
- a divider on a blank layout gets a plain-text list (no template styling) — readable, not designed.
- if most screens of the app are the accent's colour, switch `accent` to a contrasting one (e.g. red `E30613`).

## 9. Big templates

A branded template can be tens of MB (embedded media on unused layouts). Before keeping it next to the manual
sources, slim it: `$PY $S/scripts/slim_template.py <template.pptx> <ws>/manual.json <ws>/../templates/slim.pptx`
keeps only the layouts and sample slides `manual.json` refers to and rewrites `template.path`.

## 10. Check it

```bash
$PY $S/scripts/manual.py <ws>/manual.json --role <code> --pdf
pdftoppm -r 60 -png <ws>/out/<out_name>-<edition>.pdf <ws>/qa-tpl/s      # or render.applescript / render.ps1 … png (qa.md §1)
```

Look at cover, TOC, one divider, one task slide, one table slide. Adjust `area`, `title_box`, colours; rebuild.
Only then run the full visual QA loop (qa.md).

Templates without a notes master: python-pptx adds one on the first speaker note; the builder also lists it in
the presentation so Keynote accepts the file (Keynote rejects the whole deck as "invalid format" otherwise).
