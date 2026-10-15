# Brand logos (integration chips, logo arcs, "works with", marquees)

*Why:* A chip that says "Figma" next to a purple square with an "F" is an obvious placeholder; it makes the whole page look like a mock. Real logos are what make integration sections believable.

Rules:
- If an existing brand is named and gets an icon, that icon is the brand's real logo. Never an initial in a colored box, a generic glyph, or an emoji.
- Prefer full-color official marks on chips; use monochrome (white/ink) only when the section is deliberately grayscale (logo strips).
- If no real logo is available, drop the icon and show only the name. Don't invent one.
- On a small square slot (chips, arcs) use the symbol-only mark, not the wordmark. Full wordmarks (e.g. Iconify `logos:hubspot`, `logos:zendesk`) get squeezed into ~22px and become unreadable specks; use the `-icon` variant (`logos:zendesk-icon`) or Simple Icons (`hubspot`) instead. Look at the rendered result, since some sets only ship the wordmark.
- Download the SVGs into the project (e.g. `public/logos/figma.svg`) instead of hotlinking in production; inline them or use `<img>` with explicit width/height so layout doesn't shift.

Sources, in order of preference (verify the file actually loads, since brands come and go from these sets):
1. Iconify full-color logos: `https://api.iconify.design/logos:figma.svg` (also `logos:slack-icon`, `logos:github-icon`, `logos:notion-icon`, `logos:google-gmail`, `logos:zendesk-icon`, ...). Search names at icon-sets.iconify.design/logos.
2. Simple Icons (single color, any hex): `https://cdn.simpleicons.org/figma/F24E1E` or `https://cdn.jsdelivr.net/npm/simple-icons/icons/figma.svg`. Some brands were removed at the owner's request, so a 404 means try source 1.
3. The brand's own press/brand kit page, when the two above lack it.

```html
<span class="chip"><img src="/logos/figma.svg" alt="" width="20" height="20"> Figma</span>
```
```css
.chip{display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border-radius:999px;background:#fff;color:#111;font-weight:500}
.chip img{display:block;object-fit:contain}
/* grayscale strip: real logos, desaturated until hover */
.logo img{filter:grayscale(1);opacity:.55;transition:filter .3s,opacity .3s}.logo:hover img{filter:none;opacity:1}
```
