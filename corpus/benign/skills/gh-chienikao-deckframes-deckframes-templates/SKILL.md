---
name: deckframes-templates
description: >
  Build a deckframes deck on a user-supplied corporate or school PowerPoint template (.pptx/.potx):
  inspect its slide layouts, map them to roles (cover, section, content, two-content, title-only,
  closing) in config.json, and build with --template. Use when the user must use their
  organisation's master slides.
---

# .pptx templates

Template mode fills the template's own placeholders, so it keeps the organisation's master
exactly — but it has **no outline slide, sub-TOC or nav bar**, and infographic blocks degrade to
bullets/tables. Tell the user this trade-off before choosing it over a canvas theme.

## Register a template

```bash
mkdir -p templates/<name>
cp <their-file>.pptx templates/<name>/template.pptx
deckframes template inspect templates/<name>/template.pptx --write-config templates/<name>/config.json
```

`inspect` lists every layout with its placeholders and an auto-detected role mapping (layout names
in English and Chinese are recognised). Verify the mapping in `config.json`:

| Role | Used for | Needs |
|---|---|---|
| `cover` | cover | title + subtitle |
| `agenda` | table of contents | title + body |
| `section` | chapter divider | title (+ body for number/subtitle) |
| `content` | normal slide | title + one body |
| `two_content` | text + visual | title + two bodies |
| `title_only` | visual-only slide | title |
| `closing` | closing | title |

```json
{
  "file": "template.pptx",
  "layouts": { "cover": "Title Slide", "content": "Title and Content" },
  "sizes": { "title": null, "body_max": 24, "body_min": 14, "split_below": 16 },
  "text_ratio": 0.45,
  "section_label": "{n:02d}",
  "theme": { "fonts": { "ea": "Microsoft JhengHei" } }
}
```

`sizes.title: null` keeps the template's title size. Only override fonts in `theme` (e.g. a CJK
font the template lacks) — never the template's colours. Existing slides in the template are
removed at build time; masters and layouts are kept.

Build with `deckframes build --template <name>` (looked up in `./templates/`, then
`~/.deckframes/templates/`), or set `template: <name>` in the front matter / `deckframes init --template`.
Preview once and fix any wrong role in `layouts`.
