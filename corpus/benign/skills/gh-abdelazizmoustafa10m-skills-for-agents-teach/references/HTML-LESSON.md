# HTML Lesson Contract

The normative spec for a `teach` lesson. A lesson is **one self-contained `.html` file** in
`./lessons/` that opens offline by double-click and prints legibly. This file is the rules;
[`../examples/0001-golden-example.html`](../examples/0001-golden-example.html) is the taste —
**open the example first, then match it.** Keep this contract in mind, not memorised: when in
doubt, imitate the example.

Companion refs: [VISUAL-TREATMENT-MAP.md](./VISUAL-TREATMENT-MAP.md) (which visual for which
content) · [INTERACTION-MENU.md](./INTERACTION-MENU.md) (the recall widgets + their markup).

---

## 1. Required skeleton
Every lesson MUST contain these landmarks (copy from the example):

```html
<!doctype html><html lang="…"><head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NN · <lesson title></title>
  <meta name="teach:lesson" content="NNNN">     <!-- zero-padded ordinal -->
  <meta name="teach:contract" content="v1">     <!-- contract version; do not change -->
  <style id="kit"> …inlined lesson-kit.css… </style>
  <style id="page"> …optional page-specific layout only… </style>
</head><body>
  <main class="lesson">
    <header class="lesson-head"> ordinal · <h1>title</h1> · mission tie-in </header>
    <p class="lede"> the single tangible win, up front </p>
    <!-- content sections: each = prose (≤65ch) + ONE deliberate visual (see treatment map) -->
    <div class="section-label">Recall …</div>
    <!-- ≥1 active-recall widget (REQUIRED) -->
    <footer class="cite"> primary source + "ask a follow-up" + anchors to sibling lessons </footer>
  </main>
  <script id="kit"> …inlined lesson-kit.js… </script>
</body></html>
```

**Hard requirements** (the validator enforces these):
- `<title>`, `<meta name="teach:lesson">`, `<meta name="teach:contract">` present.
- A `.lede` (one-sentence win) and a `.cite` footer with a **real primary source** (never invented).
- **≥1 recall widget** (`.quiz`, `.cloze`, `.flip`, `.worked`, `.sequence`, `.match`, or
  `.predict`). A lesson with no recall surface is a poster — *if you can't name what the learner is
  forced to produce, it isn't a lesson.*
- **No external network requests**: no CDN, no `<script src>`/`<link href>` to the web, no web-fonts,
  no `@import`. Diagrams are inline SVG. The one allowed outward link is the citation `<a href>`.
- **No unresolved `REPLACE` / `TODO` / `{{…}}` markers.**

---

## 2. Embedding the kit (why single-file / inline)
The shared design system lives in [`../assets/lesson-kit.css`](../assets/lesson-kit.css) and
[`../assets/lesson-kit.js`](../assets/lesson-kit.js) — the **authoring source of truth**. Each lesson
**inlines a copy** of both into `<style id="kit">` and `<script id="kit">`. Do **not** `<link>`/`<script src>`
them: inlining is what makes the lesson self-contained, offline, portable ("send/open/print this one
file"), and immune to broken links and version drift.

Produce the file by writing the lesson body with empty `id="kit"` tags, then inline the kit:
```bash
node scripts/inline-kit.mjs <lesson.html>
```
The script fills `<style id="kit"></style>` and `<script id="kit"></script>` from the shared assets.
Consistency across a course comes from every lesson being
generated from the **same kit**, not from a live link. When you genuinely improve the kit, bump nothing —
old frozen lessons keep working; new lessons pick up the change. Cross-lesson cosmetic drift within a
course is acceptable and fixed by regeneration.

*Optional "course mode"* (only once a workspace is well established and the user asks): link a shared
`./assets/lesson.css` to save bytes, accepting the coupling. Not the default.

---

## 3. Degradation + print contract
JS is **enhancement only** — the lesson must be fully readable and printable with scripting off.
Every interactive element MUST have the states below (the kit already implements them):

| Element | JS on | JS off | Print (`@media print`) |
|---|---|---|---|
| `.reveal` (`<details>`) | click to toggle | open, readable | **forced open** |
| `.quiz` (MCQ) | grades, shows `.quiz__why` | buttons inert, prompt readable | answer rationale shown |
| `.cloze` (fill-blank) | grades on blur | plain input, prompt readable | prints blank input |
| `.flip` (flashcard) | click crossfade | both faces stacked | both faces printed |
| `.worked` (faded steps) | reveal per step | all answers visible | all answers shown |
| `.sequence` (ordering) | JS injects up/down controls + check | static order readable | answer key shown |
| `.match` (pairs) | click A then B | static columns readable | answer key shown |
| `.predict` (predict output) | JS injects check + reveal | prompt/input readable | answer shown |
| `.self-rate` | emits rating event | inert buttons readable | hidden |
| `.tabs` | one panel shown | all panels visible, radios hidden | all panels printed |
| inline-SVG diagram | static | static | vector, crisp |

Dark mode is **CSS-only** (`prefers-color-scheme`) — no JS toggle in core. **Print forces
ink-on-white**: never let dark-mode colours bleed into print (the kit's `@media print` block
resets tokens to high-contrast — keep any page-specific colours token-based so they follow).

---

## 4. Design tokens (already in the kit — use them, don't hand-pick values)
Semantic OKLCH tokens with a `prefers-color-scheme: dark` override and a print reset. Use the
variables; never inline raw hex/px. Summary: warm paper `--bg` / warm near-black `--ink` (never
`#fff`/`#000`); one focal `--accent` (muted teal); sparse `--ok/--warn/--danger/--info` for
*signal only*; spacing `--sp-1..7` (4→48px); radii `--r-sm/--r/--r-lg`; type `--font-serif`
(reading), `--font-sans` (chrome), `--font-mono` (code/labels), 17px body / 1.6 / `--measure` 65ch;
motion `--dur-1..3` + one `--ease`. Components: `.card(--elevated/--recessed)`, `.window`,
`.callout--info/rule/warn/success`, `.kpi`, `.diff`, `.pipeline`, `.data-table`, `.section-label`,
`.timeline`, `.figure`, `.sidenote`, `.code-annot`, `.svg-tree`, `.tabs`.

---

## 5. Anti-slop checklist (top 8 — the rest is in the example)
These are not taste preferences; decorative noise measurably *lowers* learning transfer
(seductive-details effect). Ship none of:
1. **em-dashes as connectors** — rewrite the sentence.
2. **AI-purple / violet / baby-blue** accents — the kit's teal is the accent; don't add gradients.
3. **pure `#000` / `#fff`** — use `--ink` / `--bg`.
4. **decorative emoji in headings** — mono `.section-label` + dot instead.
5. **decorative visuals** — every diagram/table/card must encode the concept (dual coding), not fill space.
6. **fabricated numbers, logos, names, testimonials** — cite real sources only.
7. **non-`tabular-nums` figures in tables** — the kit handles it; keep numbers in `.data-table`/`.kpi`.
8. **motion-on-mount for static text** — only interactive tiles animate in; never `h1`/`p`.

---

## 6. Validate before delivery
Run `node scripts/validate-lesson.mjs ./lessons/NNNN-*.html` (or the golden example). It fails on:
missing landmarks, external network refs, unresolved markers, no recall widget, missing citation.
A lesson that doesn't pass is not finished. If possible, also open it for the user
(`open <file>` / `xdg-open <file>`), and eyeball it in both light and dark and in print preview.
