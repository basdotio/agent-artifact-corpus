# Visual Treatment Map

For a visual learner, the format IS part of the teaching. **Pick a visual primitive deliberately
for each chunk of content — never default to a bullet list.** Bullets are where structure goes to
die; almost every bulleted list is secretly a table, a sequence, or a comparison.

Each concept should pair prose with **one** load-bearing visual (dual coding — words + picture beats
words alone). One precision visual + optional companion sketch per screen; more than that blows
working memory.

## The map

| If the content is… | …use this primitive | Kit class | Not this |
|---|---|---|---|
| a comparison across items/attributes | **data table** (`tabular-nums`, zebra; add `.data-table--sticky` only for long tables) | `.data-table` | bullets |
| a set of rules / structured facts | **data table** or labelled **cards** | `.data-table`, `.card` | bullets |
| a process / ordered steps | **pipeline / step cards** | `.pipeline` | numbered bullets |
| events over time | **timeline / horizontal rail** | `.timeline`, `.timeline__item` | paragraph chronology |
| before ↔ after, right ↔ wrong, either/or | **diff-panel** (two columns) | `.diff` `.diff__before/__after` | prose |
| a hierarchy / relationship / flow | **inline-SVG diagram** (simple, hand-authored) | (SVG) | ASCII art |
| a small tree / graph (3–6 nodes) | **inline-SVG tree helper** (hand-authored) | `.svg-tree`, `.svg-tree__edge`, `.svg-tree__node` | auto-layout |
| a code-like snippet where lines matter | **annotated code block** | `.code-annot`, `.code-annot__line--hi`, `.code-annot__note` | prose walkthrough |
| a small caveat beside a sentence | **sidenote / margin note** | `.sidenote` | parenthetical clutter |
| any visual that needs a durable label/source | **figure + caption** | `.figure`, `.figure__cap` | unlabeled image |
| alternate views of the same idea | **tabs** (JS-on collapses, JS-off prints/reads all) | `.tabs` | separate repeated sections |
| a single striking quantity | **KPI card** (oversized serif numeral) | `.kpi` | inline text |
| growth / trend / proportion | **inline-SVG chart** framed in a window | `.window` + SVG | a described number |
| a caveat, gotcha, or key rule | **callout** (semantic left-border) | `.callout--warn/rule/info` | bold prose |
| a term ↔ definition pair to memorise | **flashcard** | `.flip` | glossary dump |
| a snippet to analyse | **worked example** (faded) | `.worked` | "walk through" prose |

## Rules of thumb
- **Diagram discipline:** inline SVG is for *simple, explanatory* pictures (a curve, a tree of 3–6
  nodes, a boxes-and-arrows flow). Do **not** hand-compute graph auto-layout. If a lesson truly needs
  real graph/plot layout, that is an opt-in vendored-library escape hatch — not the default path.
- **Tree helper pattern:** keep node coordinates hand-authored and obvious. Use `.svg-tree__edge`
  for relationships and `.svg-tree__node` / `.svg-tree__node--accent` for nodes. Always include
  `role="img"` plus an `aria-label`.
  ```html
  <svg class="svg-tree" viewBox="0 0 320 160" role="img" aria-label="Topic splits into two branches.">
    <path class="svg-tree__edge" d="M160 42V78M160 78H90M160 78H230"/>
    <rect class="svg-tree__node svg-tree__node--accent" x="110" y="18" width="100" height="36" rx="10"/>
    <text x="160" y="36">Topic</text>
    <rect class="svg-tree__node" x="40" y="96" width="100" height="36" rx="10"/>
    <text x="90" y="114">Branch A</text>
    <rect class="svg-tree__node" x="180" y="96" width="100" height="36" rx="10"/>
    <text x="230" y="114">Branch B</text>
  </svg>
  ```
- **Window-chrome framing** (`.window`) is for *one* hero visual per lesson (a chart, a diagram).
  Neutral grey dots, used once — it reads as "figure in a textbook," not "I am a Mac app."
- **Asymmetry beats a 3-up grid.** Prefer a prose-left / visual-right split (`.split` in the example)
  over three identical centered cards.
- When you catch yourself writing `<ul>`, stop and ask which row of the table above it really is.
