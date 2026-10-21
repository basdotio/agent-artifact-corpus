# Tier 3: the spec-sheet page

A spec sheet is one dense page that shows a subject from several sides at
once, laid out like an engineering drawing: a frame with zone references
(1 to 8 across, A to D down), lettered panels, and a title block at the bottom
right. The reader scans it, finds the panel they need, and reads only that.
`assets/spec-sheet-template.html` is a working example with every component.

## Contents

- Workflow
- Plan the panels
- Panel catalogue
- Layout
- Visual language
- House design rules
- Sheets that explain a document
- Final check

## Workflow

1. **Collect the facts.** Verify them first, from the source the user gave, the repository, or a current primary source. Write down what each panel will claim and where the claim comes from.
2. **Plan the panels** (next section). Write the plan as a short list: letter, title, the question it answers, component, span.
3. **Copy the template** to the output path. Keep the font links, the whole `<style>` block, the icon sprite, the frame and the `<script>` at the end (it makes annotated lines safe at every width). Delete every demo panel and all demo text (HTTP caching).
4. **Build the panels** from the catalogue. Write all prose in STE (`references/ste-writing.md`).
5. **Fill the title block**: Title (also the page `<title>`), the main source or standard, owner, scope, "Facts as of" with the date you checked the facts, revision, source location, "Sheet 1 of 1". Add a "Language: 80% ASD-STE100" cell only when the user asked for STE. Use fields that are true for the subject; rename keys if you must, but keep "Facts as of".
6. **Check** with both scripts and read the screenshots (end of this file).

## Plan the panels

Use one panel for each real question the reader has about the subject,
usually 3 to 8. A narrow subject can be 1 or 2 panels plus the title block.
If you find fewer than 3 questions, ask yourself if a diagram (tier 2) is the
better answer. Never invent a panel to fill the grid: padding is where
unchecked facts get in. Good questions, by kind:

- What are its parts, and how do they fit together? (structure tree)
- What does one real example look like, piece by piece? (annotated line)
- Which options are allowed, and which are not? (status table)
- What does each term or option mean, and what do people get wrong? (dictionary table)
- What are the limits, sizes or thresholds? (gauges)
- How did it change over time, or what are the phases? (timeline)
- What must I do, step by step? (procedure)
- What must I always or never do? (rule list)
- What could go wrong? (risk table with severity chips, WARNING and CAUTION callouts)

Order the panels in reading order: A at the top left, then across the row,
then the next row. Panel A answers the user's question when the question has
a short answer (a verdict, a recommendation, "the main difference is ..."):
it is the first thing read on a desktop and the first panel on a phone. The
most important explanatory panel comes next and gets the largest span. Each panel has a meta label at the top right that names its
source or its kind ("RFC 9111 section 5.2", "annotated examples", "plan.md
section 4", "assessment, not in the source").

## Panel catalogue

All class names are in the template's `<style>` block.

| Component | Markup | Use it for |
|---|---|---|
| Panel | `section.panel.span-N` > `.panel-head` (`.panel-id`, `h2.panel-title`, `.panel-meta`) + `.panel-body` + optional `hr.hair.flush` and `.panel-note` | Every panel. The note holds a definition or a short remark. |
| Structure tree | `.tree` > `.tree-root`, `.tree-stem`, `.tree-branches[style="--n:K"]` > `.tree-branch` > `.tree-node` + `ul.tree-list` (`.k` key, `small` remark) | Parts of a system, sections of a document, a hierarchy of 2 to 4 branches. |
| Callout | `.callout`, optional `small`; `.callout.warning` (red outline and tint), `.callout.caution` (ink outline) | One fact the reader must not miss. A WARNING or CAUTION callout starts with a `.sev` chip, then the command, then the risk. |
| Severity chip | `span.sev.warning`, `.sev.caution`, `.sev.note` | Risk tables and callouts. |
| Annotated line | `.ann-block` > `.sub` + optional `.ann-wrap` > `.measure` + `.ann-line`. Each annotated piece is `span.seg` > `.t` (the annotated text: a `code` or a `span`) + `span.ann-label` (options `.lane-2`, `.start`, `.end`); `.seg.bad` for a wrong part; separators between segments get `.sep` | A header, a command, a config line or a sentence, explained piece by piece. `.measure` above it gives a length ("13 words, limit 20"). |
| Status table | `table.sheet-table` inside `.table-wrap`; status cells `.status.ok` / `.status.no` with the `#i-ok` / `#i-no` icons; `.d` for a second line in a cell | Allowed and not allowed, supported and not supported, pass and fail. |
| Dictionary table | Same table with `.stack-sm` and `data-label="<column>"` on every `td`, so rows become cards on a phone; columns such as Term, Status, Meaning, Example, Do not write (red cells with `.red`) | Terms, options or words with meaning and misuse. Use `.stack-sm` for any table of 3 or more columns. |
| Gauges | `.gauges` > `.gauge[style="--value:V; --max:M"]` (`.gauge-head` with `.v`, `.gauge-track` > `.gauge-fill`, `.gauge-ticks`), `.gauge.bad` for a value over its limit | Limits, sizes, thresholds, a worked calculation. Give gauges that share a scale the same ticks. |
| Procedure | `ol.procedure` > `li`, introduced by a `.sub` line ending in a colon | Steps in order, one instruction in each step. |
| Rule list | `ul.rules` | Short imperative rules, one in each item. |
| Timeline | `ol.timeline[style="--n:K"]` > `li` (`.year`, `.node`, `.what`) | History, phases, a rollout plan. Keep each caption under about 8 words. |
| Title block | `.titleblock` > `.tb.tb-title` (with the page `h1`) and `.tb` cells (`.k`, `.v`); `.tb-wide` for a long value, `.tb-3` + `.tb-1` for a long value next to a short one | Always, at the bottom right (last item of the last row). |

**Annotated lines at every width.** The script at the end of the template
looks at each `.ann-line` after the fonts load, on resize and before print.
When the segments wrap onto a second line, a label leaves its panel, or labels
collide, it switches that line to legend mode: numbered brackets on the line
and the labels as a numbered list under it. So you do not need to measure; you
do need to keep the script, the `.seg > .t` markup, and short labels (about 6
words). A full sentence anatomy reads best in a `span-7` or wider panel, where
it stays inline at desktop width.

You can add a component that the subject needs (a small inline SVG diagram in
a panel, a matrix, a before-and-after pair). Build it from the same tokens,
1 px and 1.5 px ink lines, and the same type scale.

## Layout

- The panel grid has 12 columns. Use `span-3` to `span-12`. Each row should add up to 12.
- To put two items in one column (the template stacks History on the title block), wrap them in `div.stack.span-N`. Keep the title block in the last item of the grid.
- At 1180 px and below, `span-3` to `span-5` become half width and wider spans become full width; the grid fills gaps (`row dense`) and the last stack stays at the right. At 760 px and below every panel is full width. Check the 1024 and 800 px results in the report, not only the desktop screenshot.
- Balance each row: panels in a row stretch to the same height, so a panel with little content leaves dead space (`check_page.py` fails a panel at 1440 px with more than about a quarter empty). Change spans, move a component, or merge two small panels. Add content only when it answers a real question. Widen a table column rather than let short cells wrap onto two lines.
- Print: the template prints the whole sheet on one landscape page with its line work. Before printing, its script tries several layout widths and keeps the zoom that fills the page, so keep the script. `check_page.py` writes two PDFs and reports the type size of each: `print.pdf` on A4 (fits any printer; body type about 5.5 pt) and `print-a3.pdf` on A3 (body type about 8 pt, readable on a wall). When the user will pin or print the sheet, ship both and say which is which. Do not cut content to fit a page: if the A3 sheet needs more than one page, split the subject into "Sheet 1 of 2" and "Sheet 2 of 2". Lay the sheet out in the paper's shape: landscape, about 1.4 times as wide as it is tall (the A-series ratio), so the print fills the page. A near-square sheet prints with a quarter of the page blank and smaller type. Keep every panel the user's reference or request asks for (for example a History panel); never drop one to gain print size, ship the A3 PDF instead.

## Visual language

Keep the template's tokens and type. Do not invent new colours.

- Paper `--paper`, ink `--ink`, secondary ink `--ink-2`, `--muted` for labels, `--hair` for light rules, `--tint` and `--zebra` for fills.
- `--blue` for approved, normal, explanatory annotation. `--red` only for "not approved", errors, risks and wrong examples.
- IBM Plex Sans Condensed for text and titles, IBM Plex Mono for codes, field names, axis numbers and meta labels.
- Lines are 1 px (rules, connectors) or 1.5 px (panel and box borders). No shadows, no rounded corners except timeline nodes, no gradients.

## House design rules

These are the skill's house design rules (opinionated defaults; edit them to taste). `check_page.py` enforces the ones a script can see.

- No one-sided accent marks: no coloured `border-left` or `border-right` strips, no single coloured edge on a card, no pseudo-element bars, no inset edge shadows. Highlight with a tint fill, a full four-sided outline, or a chip.
- Text uses the full width it has. No `max-width` on text, no `text-wrap: balance` or `pretty`, no `<br>` to lay out running text.
- Body paragraphs are justified with `hyphens: auto` and `lang="en"` on `<html>`; below 680 px they are left-aligned.
- No em dashes and no emoji. Icons are inline Material SVG paths.
- Self-contained: inline CSS and JS, images as data URIs, Google Fonts as the only network request.

## Sheets that explain a document

When the user gives you a document to understand (an agent's plan, a design
doc, a diff, a long answer), the sheet maps that document, and a separate
panel gives your assessment. The sheet is shorter than the document: a
reader with no time for the source has no time for a longer review.
`check_page.py` prints the visible word count; keep it under the source's
word count. Typical
panels:

- Bottom line (panel A): your verdict on the user's decision in one sentence, the conditions, and a sentence the user can say at their meeting
- What it proposes (tree of the parts or phases)
- Decisions it makes (status table: decision, what it says, section)
- Numbers it depends on (gauges or a table, each with its section)
- Order of work (timeline of phases, with each exit criterion)
- Risks (table with severity; mark which risks the document names and which you add)
- What to check before you approve (procedure in STE)
- Title block with the document name and its date or version

Every fact names its section of the source in a column or in the meta label.
When the source does not say something that matters, write "Not stated in the
source" in that cell. Quote the source's own words only inside
`data-ste="ignore"`.

**Check the document against itself before you build.** A faithful map of a
flawed plan reads like an approval. Ask:

- Does each mechanism meet the goal it claims? (A guarantee that one step quietly breaks.)
- Do the numbers agree across sections? (A retention time against a deduplication window; a limit against a peak rate.)
- Does each failure path keep the promise the document makes? (What happens on a crash, a retry, a replay, a full disk.)
- What happens on the first start, a restart and a rebuild? (An initial snapshot or backfill, a consumer that restarts from the beginning, a cache that starts empty.)
- Is every step that one section depends on in the order of work?
- Is every open question tied to a gate or an owner?

Put each mismatch in the assessment panel, with both section references, in
STE, and with a WARNING or CAUTION chip when it can lose data or cause an
outage.

## Final check

```bash
python3 <skill-dir>/scripts/check_page.py <page.html> --out <scratch-dir>/<page>-check
python3 <skill-dir>/scripts/ste_lint.py <page.html> --mode 80    # or strict
```

Fix every error. Then read the tiles that `check_page.py` lists (2x phone
tiles, and desktop tiles for a tall page) and the desktop screenshot at full
size, and check:

- every panel has its letter, title and meta label, and letters run in reading order;
- annotation brackets sit under the part they explain, inline or in legend mode;
- no heading or paragraph wraps while space remains on its line;
- no large empty area inside a panel (the report warns about dead space);
- the title block is complete, with "Facts as of", and at the bottom right;
- the print report says 1 A4 page.
