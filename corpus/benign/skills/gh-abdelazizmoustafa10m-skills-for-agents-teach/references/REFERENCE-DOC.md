# Reference Document Contract

A reference document is a compressed lookup sheet in `./reference/*.html`. It is the layer the
learner keeps open or prints after a lesson. It is not a lesson: recall widgets are optional, but the
same offline, print, and accessibility rules apply.

Use a reference doc for syntax, formulas, algorithms, checklists, glossaries, poses, routines, or any
stable facts that will be reused across lessons.

## Required shape

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reference - short name</title>
<meta name="teach:contract" content="v1">
<meta name="teach:reference" content="short-slug">
<style id="kit"></style>
<style id="page"></style>
</head>
<body>
<main class="lesson">
  <header class="lesson-head">
    <span class="ordinal">Reference</span>
    <h1>Short reference name</h1>
    <p class="mission">What task this helps the learner do faster.</p>
  </header>

  <p class="lede">One sentence saying when to use this sheet.</p>

  <div class="section-label">Core table</div>
  <table class="data-table">
    <caption>What to scan for</caption>
    <thead><tr><th>Case</th><th>Use</th><th>Watch for</th></tr></thead>
    <tbody>
      <tr><td>Common case</td><td>Reusable move</td><td>Relevant caveat</td></tr>
    </tbody>
  </table>

  <div class="section-label">Decision rule</div>
  <div class="callout callout--rule">
    <span class="callout__k">Rule</span>
    The compact rule the learner should remember.
  </div>

  <footer class="cite">
    Primary sources: <a href="">add real source before publishing</a>.
    <br>Related lessons: <a href="#">lesson link</a>.
  </footer>
</main>
<script id="kit"></script>
</body>
</html>
```

## Rules

- Inline `assets/lesson-kit.css` and `assets/lesson-kit.js`; do not link CDNs, fonts, scripts, or
  images from the network. The citation link is the only outward link.
- Keep page-specific CSS in `<style id="page">`, token-based, and minimal. Prefer kit components.
- Print must work on paper: no dark-mode-only colors, hidden answers, sticky headers, or JS-required
  content.
- Use semantic HTML. Give every inline SVG `role="img"` plus an `aria-label` or `<title>`; give every
  informative image alt text.
- Cite real primary sources. Do not ship empty links, invented sources, or unresolved drafting text.
