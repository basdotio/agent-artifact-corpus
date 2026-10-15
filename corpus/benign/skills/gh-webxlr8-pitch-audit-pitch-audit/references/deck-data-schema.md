# deck-data.json: contract between Claude and the renderer

Claude writes `clients/<slug>/deck-data.json`. `scripts/render.py` turns it into the PDF using a style.
Every style supports every layout below. Text fields accept light markup:

- `*text*` → accent colour (once per headline: the part that stings or helps)
- `**text**` → bold
- `\n` → line break

Image paths are relative to the client folder (e.g. `screenshots/desktop-fold.png`).

## Top level
```json
{
  "title": "Acme Rentals: website review",
  "style": "style-1",
  "theme": null,                   // one deck = one brand: your company (pitch-profile). Set an offer id only for a pure single-product pitch with pitch-profile/themes/<id>.json
  "summary": { ... },              // optional; only rendered as a separate PDF with render.py --with-summary
  "file_name": "Acme-Rentals-Website-Review.pdf",
  "client": { "name": "Acme Rentals", "url": "https://acme.in", "logo": "images/prospect-logo.png", "logo_on_dark": "images/prospect-logo-on-dark.png" },
  "contact": null,                 // optional override; default = your contact from company.yaml
  "slides": [ ... ]
}
```

## Common slide fields
| Field | Use |
|---|---|
| `layout` | one of the layouts below (required) |
| `eyebrow` | small green caps label, e.g. `"02 · Performance"` |
| `title` | headline with `*green*` payoff |
| `body` | 1–2 sentence lead |
| `chips` | list of strings or `{ "text", "active": true, "severity": "critical|high" }` |
| `image` | `{ "src", "frame": "browser|phone|plain", "label": "acme.in" }` |
| `footnote` | small caption line |
| `glow` | `"strong"`, `"center"` or omit |
| `size` | headline class override: `h-xl`, `h-lg`, `h-md`, `h-sm` |
| `photo` | `{ "src": "images/cover.jpg", "mode": "full" \| "right", "pos": "center 40%", "dim": 0.35 }` full-bleed or right-half photo, auto-darkened, works on any layout |

## Layouts

**cover**: `eyebrow`, `title`, `subtitle`, `image` (desktop shot), `image_mobile` (path), `footer`.

**statement**: big headline + optional body/chips/`tiles: [{value,label}]` (+ `tile_cols`) + optional framed image or `photo`. `text_width` narrows the text column. `image_side`: `right` (default) / `left`. `live: true` adds the red LIVE badge.

**stats**: `title`, `body`, `group_label`, `stats: [{ "value": "100+", "label": "Brands served" }]` (max 4). `num_size` (default 112).

**scorecard**: `title`, `overall` (0-100), `grade`, `categories: [{ "label", "score" }]` (max 8), `footnote`.

**finding**: one problem per slide. `filmstrip: { frames: [{src, label}], highlight: <index>, caption }` shows the page-load frames from `prospect_assets.py` instead of an image. `image: { src, inset: true, size: "large", label, caption }` shows their own evidence screenshot at 600×440. `eyebrow`, `title`, `body`, `metric: { "value": "6.2s", "label": "to show main content on mobile" }`, `evidence: [..max 3]`, `impact` (business sentence), `chips`, `image`.

**process**: `title`, `steps: [{ "title", "body", "num", "icon" }]` (max 5, arrows between), `highlight` (index, default last), `footnote`.

**cards**: `title`, `body`, `cards: [{ "tag", "icon", "title", "body", "product" }]` (max 6), `columns`, `highlight`. `product` (an offer name from catalog.yaml, e.g. "Acme Rental Suite") shows a logo/name badge. Lays out automatically.

**solutions**: `title`, `items: [{ "brand": "<offer name>", "icon", "title", "body", "fixes": [..max 3], "outcome" }]` (max 4), `highlight`. Items whose `brand` names a catalog product show that product's logo as the badge (deck colours unchanged).

**tiers**: `title`, `tiers: [{ "num", "title", "body", "price", "theme" }]` (max 3), `highlight`, `footnote`.

**compare**: side-by-side table for packages or options. `title`, `columns: [{ "title", "sub" }]` (2–3), `highlight` (column index), `groups: [{ "label", "rows": [{ "label", "values": [true, false, "text"] }] }]` (about 12 rows max over all groups; `true` = check, `false` = dash, text shows as is), `footnote`.

**proof**: `title`, `body`, `stats: [{value,label}]` (max 4, optional), `clients: [names]` (max 14), `cases: [{ "client", "industry", "work", "result" }]` (max 3). Fill `result` only with a real, client-approved number.

**score_gaps**: `title`, `overall`, `categories` (8, mini bars), `gaps: [{icon, title, body}]` (3), `ring_caption`. Replaces separate impact + scorecard slides.

**offer**: the single recommendation. `product`: the offer name (a catalog product shows its logo). With `mockup: { url, title, user, caption, kpis:[{value,label}], rows:[{id,lane,status,tone: go|wait|done,eta}], alert:{title,body} }` + `modules: [..]` the right side becomes an HTML product mockup. `next`: one line of later offers. `eyebrow`, `product` (an offer name from catalog.yaml; products show their logo badge), `title`, `body`, `facts: [{value,label}]` (max 3), `includes: [..max 6]`, `includes_label`, `outcome`, `footnote`.

**center**: centred statement: `eyebrow`, `title`, `body`.

**contact**: `title` (default "Next step"), `body`, `first_step: { "title", "body", "label" }`, `cta`, `contact` overrides, `footer`, `proof: { stats:[{value,label}], clients:[..], label }` (bottom proof strip), `photo`.

**summary** (top-level block, not a slide), `eyebrow`, `title`, `overall`, `score_line`, `issues: [{title, body}]` (3), `recommendation: { product, title, body, points: [..max 4] }`, `first_step`.

## Icons available
globe, send, message, home, search, zap, check, chart, shield, phone, cpu, layers, cart, users, cloud, book, palette, truck, box, alert, bot, calendar
