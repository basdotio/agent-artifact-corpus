---
name: architecture-doc
description: Produce the customer-facing technical documentation set for a product the customer self-hosts - an Architecture and Requirements document plus its Deployment Guide sibling - in the mono house theme (near-black chrome, Inter, tables at 8.9pt, full-width Figma diagrams). Encodes the six-section skeleton enterprise infra teams expect, the monochrome preset, the four topology diagram archetypes (trust-zone bands, HA tier rows, enrolment patterns, access matrix), the Figma-to-assets export pipeline, and the fact-check pass that catches sizing and quorum errors before they ship. Use whenever the user wants an architecture design document, a solution architecture, a deployment guide, a "tài liệu kiến trúc / tài liệu triển khai gửi khách", or asks for "tài liệu kiến trúc gửi khách". Composes figma-topology (diagrams) + doc-builder (render).
---

# architecture-doc - the house technical reference

Builds the document an enterprise customer reads *before* they deploy your product on
their own infrastructure: what it is, how it is built, what they must provision, and
how they stand it up. Reference shape: a self-hosted mesh control plane (Architecture and Requirements plus
a Deployment Guide), about 11 pages.

This is not a proposal (a proposal is a different deliverable and not covered here) and not a runbook you follow with a
terminal open (that is the Deployment Guide sibling, section 8 below). It is the
document the customer's architecture team, security team and procurement team all read.

## Golden rules

1. **Three readers, one document.** Every section must serve at least one of: the infra
   engineer who provisions hosts, the security architect who approves the exposure, the
   procurement analyst who prices the BOM. A section serving none of them is filler.
2. **Diagrams carry the load, prose connects them.** Draw in Figma with `figma-topology`
   plus the archetypes in `references/diagram-patterns.md`. Never restate a diagram in
   a paragraph, and never draw ascii.
3. **Colour means something or it is absent.** The document chrome is monochrome
   (`--accent "#182329"`). Colour appears only inside diagrams, where the category
   palette is semantic. Blue chrome next to a blue DATABASE tile is a bug.
4. **Every number on a diagram must exist in a source you checked.** Ports, container
   counts, image tags, subnet ranges. Read the compose file or the runbook. See the
   fact-check pass, section 6 - it exists because the reference document shipped three
   real errors before it was run.
5. **Render through `doc-builder`.** Never hand-write HTML. Paste the house style block
   (section 4) into the markdown so the theme travels with the file.

## 1. Decide which document you are writing

| Document | Answers | Reader opens it |
|---|---|---|
| Architecture and Requirements | What is it, how is it built, what do I provision | Before buying / before sizing |
| Deployment Guide | How do I stand it up, step by step | With a terminal open |

Write the Architecture doc first - the Deployment Guide inherits its component table,
port table and domain table verbatim. Two documents, one set of facts.

Name them plainly: `<Product> - Architecture and Requirements`, `<Product> - Deployment
Guide`. No version number in the title (semver does not belong to prose; it goes in the
meta line as `v1.0 | <date>`). No "Architecture Design Document" unless the customer's
procurement template mandates that exact string - it describes only the first third of
the content.

## 2. The six-section skeleton

This is the shape enterprise infra teams expect. Keep the numbering; they cross-refer to
it in review meetings.

```
1. System Architecture
   1.1 System Overview          two paragraphs, no more
   1.2 <Product> Architecture   the full topology diagram + component table
   1.3 Technology Stack         one small table per layer
   1.4 Deployment Model         form (Compose/Helm/...) + runtime modes
2. Network Diagram
   2.1 Single-instance Model    the trust-zone blueprint
   2.2 High-availability Model  the tier-row blueprint
3. Hardware Requirements
   3.1 Single-instance Model    Recommended AND Minimum columns
   3.2 High-availability Model  same, plus a node total
4. Standard Software List       version, licence, replaceable, notes
5. Deployment and Verification
   5.1 Deployment Steps         four numbered steps, pointing at the Guide for detail
   5.2 Verification             what "it worked" looks like, in two stages
6. Use Cases                    two reference scenarios, each with a diagram
```

Section notes that matter:

- **1.1 is two paragraphs.** Paragraph one: what problem the category solves, in plain
  words. Paragraph two: what this product specifically does about it. No history, no
  market framing.
- **2 is called "Network Diagram"** because that is the standard section name in
  Vietnamese enterprise architecture documents. Earn the name: the diagrams must carry
  zones, ports and traffic paths, not just boxes. If the customer template does not
  mandate it, "Deployment Topology" is more accurate - offer the swap, do not assume it.
- **3 always ships two columns**, Recommended and Minimum. A single column reads as
  either padded (if you list production numbers) or negligent (if you list the floor).
  State plainly that Minimum is lab-grade with no headroom.
- **4 drops any column that is uniformly the same value.** An "Open source: Y/Y/Y/Y"
  column is noise - say it once in the intro line instead.
- **6 exists to make the abstract concrete.** Two scenarios, no more.

## 3. Voice

Plain, short, unhedged. The reference document's opening is the calibration:

> A traditional network trusts whatever is already inside it. Zero Trust does not: every
> peer authenticates, and every path between two peers is allowed or denied explicitly.

Rules that produce that:

- **One idea per sentence.** If a sentence has a colon *and* a semicolon, split it.
- **Name the limitation.** "Minimum leaves no headroom for relay traffic, audit growth,
  or an upgrade running alongside the current version" beats "Minimum is 2 vCPU".
- **No restating.** If it is in the table, the ports strip, or the diagram, it does not
  also get a paragraph. The single most common failure mode is a closing sentence that
  re-lists the table above it.
- **Technical English stays technical.** Never simplify `ip_forward=1`, `SNI`, `quorum`,
  `h2c`. The reader knows these words; softening them wastes their time.
- **Say what a component is not**, when it is easy to get wrong. "It is not itself an
  identity provider." "This is not a permission error page - the port does not respond."

`doc-builder`'s sanitizer strips em dashes, smart quotes, arrows and emoji on every
build, so write with plain hyphens and straight quotes and let it normalise the rest.

## 4. The house preset

Paste this block into the markdown, directly under the H1. Pandoc passes raw HTML
through, so the theme travels with the source file and survives a re-render by anyone.

```html
<style>
.doc { --fig-bleed: 17.5mm; --fig-max-h: 160mm; }
.doc-body table { font-size: 8.9pt; }
.doc-body thead th { font-size: 7.8pt; padding: 9px 10px; letter-spacing: 0.4px; }
.doc-body tbody td { padding: 8px 10px; line-height: 1.45; }
.doc-body table code { font-size: 8.2pt; padding: 1px 5px; }
.doc-body figure img { border: 0; box-shadow: none; }
/* monochrome chrome: colour is reserved for the diagrams, where it carries meaning */
/* The child combinator is not a style choice. `build_doc.py`'s sanitizer strips
   a space that sits before punctuation, so `.masthead .eyebrow` reaches the
   browser as `.masthead.eyebrow`, matches nothing, and the eyebrow silently
   keeps `var(--accent)`. `>` survives the pass and says the same thing. */
.masthead > .eyebrow { color: #6B7B7E; }
.masthead > .brand { color: #182329; }
.doc-body li::marker { color: #8A9899; }
.doc-body code { background: #EDF2F2; color: #182329; }
.doc-body a { color: #182329; border-bottom-color: #C9D2D3; }
</style>
```

Two of those lines are load-bearing, not taste:

- **The figure variables**, with `--wide-figures` on the build. doc-builder's print CSS
  caps figures at `max-width: 80%; max-height: 100mm`, which renders a dense topology
  illegibly small in the PDF. `--wide-figures` lets each diagram bleed past the text
  column out to the paper margin instead - 193mm wide rather than 158mm - and
  `--fig-bleed` / `--fig-max-h` size that bleed. See section 4.1 for why this also
  decides how the document paginates.
- **The table sizes.** A five- or six-column table at the 9.8pt default wraps every cell
  in an 880px card. 8.9pt with tighter padding fits them.

One trap that costs a render each time it is met: **Chrome will not resolve a
`url(#id)` gradient reference inside an SVG loaded as a CSS background** in this
print path, and base64 does not change it - the shape comes out in the browser's
fallback grey with no error anywhere. Anything reaching the page as a background
image needs flat fills. A gradient that does not resolve is not a gradient.

Tonal ladder, darkest to lightest: `#182329` (brand, masthead rule, table header rule,
headings) -> `#36474D` (body) -> `#6B7B7E` (eyebrow, subtitle, meta, table cells) ->
`#8A9899` (list markers, section numbers in the contents).

### Build commands

```bash
# path relative to this skill directory; works for plugin and copy installs
B=../doc-builder/scripts/build_doc.py

# branded delivery copy
python3 $B <DOC>.md \
  --brand "<PRODUCT>" --eyebrow "Technical Documentation" \
  --subtitle "<one line: what is inside beyond the title>" \
  --meta "<VENDOR> | v1.0 | YYYY-MM-DD" \
  --accent "#182329" --wide-figures --pdf

# unbranded copy, when the customer will re-badge it
python3 $B <DOC>.md --eyebrow "" --meta "<VENDOR> | v1.0 | YYYY-MM-DD" \
  --accent "#182329" --wide-figures --out <DOC>-plain.html --pdf
```

The masthead has three slots - brand, eyebrow, title - so do not repeat the document
type across two of them. Eyebrow carries the type; the title carries the subject.

### 4.1 The pagination pass (run it before you ship the PDF)

A diagram block is about 165mm tall on a 269mm A4 text height, and it cannot be split.
Whenever less than that is left on the page it jumps to the next one and strands a
half-empty sheet behind it - the single thing that makes an otherwise clean document
look unfinished. Three things control it, in order of leverage:

1. **Let long tables split.** doc-builder's print CSS breaks tables across sheets and
   repeats the header row. A table that jumps whole costs as much white space as a
   diagram does, and this fixes it for free.
2. **Keep diagrams wide.** A wider diagram is a taller diagram, so it fills more of the
   sheet it lands on. Shrinking diagrams to make them "fit" does not work - to fit into
   the ~80mm typically left on a page a diagram has to drop to about half width, which is
   unreadable, and the white space simply moves elsewhere. Total slack is fixed by the
   page count; all you are doing is choosing where it lands.
3. **Tune the one diagram that just misses.** A diagram that overshoots the foot of its
   page by 10mm costs a two-thirds-empty sheet. Cap that one by file name, and pass the
   value per build so the branded and unbranded copies - whose mastheads differ in
   height, which shifts everything after them - can each get their own:

   ```html
   .doc-body figure img[src$="topology-overview.png"] { max-height: var(--lead-fig-h, 132mm); }
   ```
   ```bash
   python3 $B ... --wide-figures --var lead-fig-h=150mm
   ```

   `<div class="pagebreak"></div>` in the markdown forces a break where nothing else
   will do. Use it last: it only adds white space, it never removes any.

Measure, do not eyeball. Render each page and find the last row of ink on it:

```bash
pdftoppm -png -r 55 <DOC>.pdf /tmp/pg
# then per page: bottom gap = (page height - last inked row) as a fraction of 297mm
```

Under ~55mm reads as a normal paragraph break. Around 90mm reads as a section break and
is acceptable right before a diagram. Over 120mm is the defect you are hunting. Expect to
land 2-3 pages in the 90mm band on a diagram-heavy document; that is the floor for A4.

## 5. Diagrams

Load `figma-topology` for the visual language (tokens, helpers, icon library), then
`references/diagram-patterns.md` in this skill for the four archetypes this document
type needs and the helper extensions they require (dashed sub-zones, footer summary
bars, colour chips, elbow connectors, per-component icon mapping).

Pipeline, per diagram:

1. Build the frame with `use_figma` (load the `figma-use` skill first - it is mandatory).
2. `get_screenshot` on the frame id, eyeball it, fix collisions.
3. `curl` the returned URL into `assets/<name>.png`.
4. Reference it in the markdown as `![caption](assets/<name>.png)`; the alt text renders
   as the centred caption.

Keep every frame the same width (1400 is the house size) so the images render at one
scale down the document. Height varies with content; that is fine.

## 6. The fact-check pass (do not skip)

Diagrams are believed. A wrong number in a diagram becomes a wrong purchase order. The
reference document's predecessor shipped all three of these:

- **Counted things.** Does the diagram show the same *number* of databases, nodes,
  containers as the component table? The reference diagram drew one PostgreSQL where the
  product ships two.
- **Quorum and pair counts.** Anything doing leader election needs an odd number. The old
  HA diagram drew a single etcd - a customer building from it gets a cluster that cannot
  elect.
- **Ports and domains belong on the diagram**, not only in a table three sections away.
  The network team reads the picture, not the prose.
- **Version strings.** Empty version cells and floating tags (`latest`) in a software
  list read as unfinished. State the tag as actually deployed *and* recommend pinning.
- **Cross-document drift.** The same component described two ways in two documents. Grep
  the component names across every `.md` in the folder before rendering.

Ground every number in a file you opened - the compose file, the runbook, the `.env`
reference. If you cannot ground it, write the qualifier ("at time of writing", "or
newer") rather than inventing a number.

## 7. Verification before delivery

- [ ] Read the rendered PDF page by page (the Read tool takes `pages`). Do not ship a
      PDF you have only rendered.
- [ ] Every diagram spans the full text column and its smallest label is legible.
- [ ] No table cell wraps to more than two lines.
- [ ] `grep -c $'[--‘’“”→•]'` on the HTML returns 0.
- [ ] Component names identical across every document in the set.
- [ ] No colour in the chrome; colour only inside diagram frames.
- [ ] Title has no version number; meta line has the version and the date.

## 8. The Deployment Guide sibling

Same theme, same style block, same accent - so the pair reads as one set. Different
shape: numbered procedure, one heading per step, a `**Verify:**` line closing each step
so the reader knows whether to continue. It inherits the component, port and domain
tables from the Architecture document verbatim; when one changes, change both and
re-render both.

## Reference files

- `references/document-structure.md` - the six sections expanded, with the reference document
  as a worked example of what belongs in each.
- `references/diagram-patterns.md` - the four archetypes, their layout grids, and the
  helper functions figma-topology does not ship.
