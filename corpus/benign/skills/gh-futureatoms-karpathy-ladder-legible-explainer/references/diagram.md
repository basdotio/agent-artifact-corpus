# Tier 2: diagrams

Use a diagram when the reader must see a shape: an order of steps, who talks
to whom, what contains what, which state follows which. A diagram that only
restates a list in boxes adds nothing; use a list instead.

## Pick the diagram kind

| The content is | Draw | Layout |
|---|---|---|
| Messages between parties over time (OAuth, TCP handshake, an API call chain) | Sequence diagram | One vertical lifeline for each party, time runs down, numbered arrows |
| Steps with decisions (a deploy pipeline, a support triage) | Flowchart | Top to bottom or left to right, diamonds only for real decisions |
| States and the events that move between them (a TCP connection, an order) | State diagram | States as boxes, events as arrow labels, start and end marks |
| Parts inside parts (a system, a document, a team) | Tree or nested boxes | Root at the top, siblings aligned |
| Data moving through components (a request through a CDN, a cache, an origin) | Data-flow or architecture | Components in columns by tier, arrows labelled with what moves |

## Deliverable

One `.html` file that holds the diagram as inline SVG, in the drawing-sheet
visual language: copy `assets/spec-sheet-template.html`, keep its font links,
`<style>` block, frame and title block, and delete the demo panels. The
diagram comes first and gets the full width: one `span-12` panel at the top,
with the numbered steps, tables and notes in panels below it. For a working
diagram (kept open while the user debugs or builds), use `<div class="frame
plain">` to drop the zone margins, so every pixel goes to the diagram; keep
the zone frame for a reference sheet. A working diagram that the user keeps
open must show the whole flow on one 1080p screen: tighten the row spacing,
or add a compact toggle that keeps every step and its key values. A visible
marker for each step (which steps show in the browser's DevTools and which
only in server logs) helps the user debug. A working diagram is for the screen:
write "Screen" in the title block's Sheet field and ship no PDF unless the user
asks to print it; `check_page.py` warns about print pages that do not matter
here. Fill the title block as in
`references/spec-sheet.md` step 5 (title, source, "Facts as of", language,
sheet number) and set `<title>` to the same title. A standalone `.svg` is fine
when the user asks for one, but then the fonts fall back to the system stack.

Hand-draw the SVG. Do not load Mermaid, D3 or any script from a CDN: the page
must work from `file://` with Google Fonts as its only request. When the user
says they will edit the diagram later, offer an Excalidraw scene through the
`excalidraw-diagrams` skill as well.

## SVG rules

- Use a `viewBox` and `width="100%"`; set no fixed pixel height. Draw at the size it will show on a desktop panel (about 900 to 1300 units wide), so 1 unit is about 1 px and 13-unit text reads at 13 px.
- Text at 13 units or more for labels and 12 for parameter lines, as rendered at desktop width: `var(--sans)` for labels, `var(--mono)` for code, headers and field names. A diagram read from a second monitor needs 14 or more.
- Show the values the user tracks on the arrows in the default view (for an auth flow: state, code_challenge, code_verifier, the token). Do not hide them behind a toggle or a click.
- Colours from the sheet tokens through CSS classes inside the SVG, so dark mode still works: ink for structure, blue for the normal path and annotations, red only for an error path or a "do not" item.
- Arrowheads: one `<marker>` whose path uses `fill="context-stroke"`, so each arrowhead takes the colour of its own line. (A marker filled with `currentColor` takes the colour of the SVG, not of the line, and gives black heads on blue lines.)
- Straight or orthogonal lines; no curves unless the curve carries meaning.
- Number the steps of a sequence or flow (1, 2, 3 in small circles or as a prefix in the label) and use the same numbers in the steps list beside the diagram.
- Label every arrow with what moves or what happens, in STE: "Sends code_challenge" says what the step does. Names of fields, headers and parameters stay as they are, in mono.
- Keep 24 or more units between parallel arrows and between a label and the next line. No label crosses a line. No two labels touch.
- Give the SVG `role="img"` and a `<title>` that says what the diagram shows.

## Phone width

An SVG scales down with its panel. A wide sequence diagram at 390 px becomes
unreadable text. Choose one:

- wrap the SVG in `<div class="table-wrap">` and give the SVG a `min-width` (for example 760 px) so it scrolls sideways inside the panel and the page does not, and add a mono caption "Scroll sideways to see all parties", or
- draw a second, vertical version for small screens and switch between them with a media query.

The numbered steps list beside the diagram carries the meaning on any screen
and for a screen reader.

## Sequence diagram pattern

```html
<svg viewBox="0 0 1000 560" width="100%" role="img" aria-labelledby="seq-t" class="diagram">
  <title id="seq-t">Authorization code flow with PKCE</title>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="context-stroke"/>
    </marker>
  </defs>
  <!-- parties: header box + dashed lifeline -->
  <g class="party">
    <rect x="40" y="20" width="180" height="40"/>
    <text x="130" y="45" text-anchor="middle">Browser</text>
    <line x1="130" y1="60" x2="130" y2="540" class="lifeline"/>
  </g>
  <!-- one message: numbered, labelled arrow -->
  <g class="msg">
    <line x1="130" y1="110" x2="480" y2="110" marker-end="url(#arrow)"/>
    <text x="140" y="102"><tspan class="n">1</tspan> Sends code_challenge</text>
  </g>
  <g class="msg bad">
    <line x1="480" y1="160" x2="130" y2="160" marker-end="url(#arrow)"/>
    <text x="140" y="152"><tspan class="n">2</tspan> Returns an error when the state does not agree</text>
  </g>
</svg>
```

```css
.diagram { font: 13px var(--sans); }
.diagram rect { fill: var(--paper); stroke: var(--ink); stroke-width: 1.5; }
.diagram text { fill: var(--ink); }
.diagram .lifeline { stroke: var(--muted); stroke-dasharray: 4 4; }
.diagram .msg line { stroke: var(--blue); stroke-width: 1.5; }
.diagram .msg.bad line { stroke: var(--red); }
.diagram .n { font-weight: 600; fill: var(--blue); }
.diagram .bad .n { fill: var(--red); }
```

For a flowchart or a state diagram, use the same pieces: boxes as `rect`
with the panel stroke, a decision as a `polygon` diamond, start and end as a
filled and a ringed `circle`, and labelled arrows with the same marker.

## Check

Run both checkers (`references/spec-sheet.md`, "Final check"). `check_page.py`
fails on SVG labels that overlap each other or leave the SVG, and
`ste_lint.py` reads the SVG `<text>` elements. Then read the desktop
screenshot at full size: every arrow points the right way, the numbers run in
order, every arrowhead has the colour of its line, and no label touches a
line.
