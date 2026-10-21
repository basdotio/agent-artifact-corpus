# Diagram catalog

Syntax: one line, `@@name field | field | key=value`. Fields are positional, options are `key=value`. Lists inside a field use `,` (or `;` where noted). Every diagram accepts `cap=…` for a caption. Colours come from the course accent plus a fixed 4-colour categorical set, so all diagrams in a document match.

If a diagram you need is not here, write inline SVG directly in content.md (raw HTML is allowed). Match the look: `font-family="Inter"`, stroke-width 1.5, accent colour for primary shapes, `#6b7280` for secondary text, wrap in `<figure class="dg">…<figcaption>…</figcaption></figure>`.

| Name | Shows | Example |
|---|---|---|
| `flow` / `steps` | a process, pipeline, chain of consequences | `@@flow Aksiomi \| Logično sklepanje \| Izreki \| Novi rezultati` |
| `truth` | truth table with the decisive row highlighted | `@@truth A; B; A ⇒ B \| 0,0,1 \| 0,1,1 \| 1,0,0 \| 1,1,1 \| hl=2 \| cap=Neresnična samo pri A=1, B=0` |
| `ladder` | precedence, ranking, hierarchy of operators | `@@ladder ¬:negacija \| ∧:konjunkcija \| ∨:disjunkcija \| left=najvišja prednost \| right=najnižja` |
| `venn2` | set operations (any subset of panels) | `@@venn2 inter:Presek \| union:Unija \| diff:Razlika \| comp:Komplement \| subset:Podmnožica \| disjoint:Disjunktni \| symdiff:Simetrična razlika` |
| `venn3` | three sets with concrete elements per region | `@@venn3 A=2,3,c \| AB=a,b \| ABC=1 \| BC=4 \| C=d \| names=A,B,C` |
| `numline` | intervals, bounds, solution sets on ℝ | `@@numline -4..5 \| (-2,3]:A \| [2,3):B \| mark=-2:inf A \| shade=-4..-2:spodnje meje` |
| `intervals` | the interval notations side by side | `@@intervals [a,b] \| (a,b) \| [a,b) \| (a,b] \| note=poln krog = krajišče je v množici` |
| `nested` | nested sets / containment hierarchy (outer → inner; fields split by `;`) | `@@nested ℝ; realna števila; zaprta za: + − · ÷; √2, π \| ℚ; racionalna; …; ½ \| ℤ; cela; …; −1, 0 \| ℕ; naravna; …; 1, 2` |
| `dominoes` | induction: base case and the n → n+1 step | `@@dominoes base=1. baza \| step=2. korak: P(n) ⇒ P(n+1) \| labels=n₀,n₀+1,…,n,n+1,…` |
| `depend` | "for every x there is a y" vs "one y for all x" | `@@depend ∀x ∃y : x² = y \| ∃y ∀x : x² = y \| each=vsak x dobi svoj y — resnična \| one=en y za vse x — neresnična` |
| `timeline` | chronology, history of a field | `@@timeline 1806:De Morgan \| 1815:Boole \| 1845:Cantor \| 1872:Russell` |
| `tree` | taxonomy, decomposition, decision tree | `@@tree Števila > Realna, Kompleksna ; Realna > Racionalna, Iracionalna ; Racionalna > Cela` |
| `space` | student workspace (height in cm) | `@@space 5` |

## Details

**truth** — header fields separated by `;`, one row per `|` field, values separated by `,`. The last column is styled as the result. `hl=` takes a 0-based row index (or several: `hl=1,2`).

**numline** — first field is `lo..hi`. Interval fields: `[a,b]`, `(a,b)`, `[a,b)`, `(a,b]` optionally `:Label`; stacked on separate rows in order. `mark=x:text` draws a dashed guide at x with text above. `shade=a..b:text` adds a tinted band below the axis (use for "lower bounds", "solution set"). Use `-inf`/`inf` for unbounded ends.

**venn2** — panels in the order given; up to 3 per row. `names=A,B` renames the sets in the formulas.

**venn3** — regions: `A`, `B`, `C` (only), `AB`, `AC`, `BC` (pairwise), `ABC` (all three). Empty regions are simply omitted.

**nested** — each set is `symbol; name; top-right note; bottom-right examples`. Outer first. Keep to 3–5 levels.

**tree** — one field, rules separated by `;`, `parent > child, child`. Keep labels short (≤ 16 characters) — boxes are fixed width.

**space** — a dot grid (5 mm) with a faint "work space" label in the document language. Choose height by effort: 2.5–3 cm (one line), 4–5 cm (short derivation/table), 6–7 cm (proof, case analysis, truth table).

## Picking a diagram

Ask what the *structure* of the concept is:

- cases / combinations → `truth` (or a table)
- order / priority → `ladder`
- membership / overlap → `venn2`, `venn3`
- position on a line, bounds, intervals → `numline`, `intervals`
- containment hierarchy → `nested`; branching hierarchy → `tree`
- process / derivation chain → `flow`
- time → `timeline`
- recurrence / induction → `dominoes`
- "depends on" between quantified variables → `depend`

No structure → no diagram.
