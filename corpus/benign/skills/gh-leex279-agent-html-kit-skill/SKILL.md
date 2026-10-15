---
name: html-kit
description: Write HTML documents (reports, architecture diagrams, plans, triage boards) with agent-html-kit components instead of hand-written CSS and SVG, at close to markdown token cost. Use when the user wants a document they will open in the browser, or asks for HTML output, a visual report, a diagram or an interactive board.
---

# agent-html-kit

The kit (`kit/kit.js`) holds all the design. You only write content, so an HTML file
costs about as many tokens as markdown. If the folder you write into has no `kit/kit.js`,
copy the `kit/` folder from this skill's directory next to the documents first; every
document loads it with one line.

## Writing an HTML document

Start the file with exactly this line, then write only content:
<!doctype html><meta charset="utf-8"><script src="kit/kit.js" defer></script>

Never write <style>, other <script> tags, style attributes, CSS or SVG. The kit draws everything.
Plain <h2> <h3> <p> <ul> <ol> <li> <b> <code> <a> are styled. In any text: **bold**, `code`,
status pills [done] [progress] [blocked] [todo] [warn], and IDs like ABC-123 are formatted.

<rk-header title="..." sub="..."></rk-header>           page hero
<rk-stats>                                              one stat per line: value | label | note
23 | PRs merged | +5 vs last week                       (note starting + is green, ! is red)
</rk-stats>
<rk-chart type="bar|line|hbar" title="..." unit="ms">   one point per line: Label: number (0 or more)
Mon: 3
</rk-chart>
<rk-table>                                              first line is the header, cells split by |
ID | Item | Status
CHK-1 | Apple Pay | [done]
</rk-table>
<rk-callout kind="risk|warn|note|ok" title="...">text</rk-callout>
<rk-diagram title="...">                                one edge per line: A -> B: label
Browser [user] -> API: HTTPS                            node kinds: [user] [svc] [db] [queue] [cache] [ext]
</rk-diagram>
<rk-steps>                                              numbered steps, one per line: Title | detail
Parse input | reject bad rows
</rk-steps>
<rk-board title="..." columns="Now,Next,Later,Cut">     drag-and-drop board with markdown export
ID | title | column (optional, items start in Inbox)
</rk-board>
<rk-cols><div>...</div><div>...</div></rk-cols>         side-by-side columns

## Or write markdown and render it

When the reader is another agent or a repo, write markdown. To give a human the same
rendered page, use these extensions and run `node kit/md2html.js file.md`:

Write GitHub-flavored Markdown, no raw HTML. Our renderer adds:
- The first "# Title" becomes the page hero.
- A line "stats: value label | value label | ..." becomes stat cards.
- Status pills anywhere, including table cells: [done] [progress] [blocked] [todo] [warn].
- IDs like ABC-123 become chips.
- Blockquotes starting "Risk:", "Warning:", "Note:" or "OK:" become colored callouts.
- Fenced blocks by language:
  chart    optional header lines "title: ...", "type: bar|line|hbar", "unit: ms", then "Label: number" lines
  diagram  optional "title: ...", then one edge per line "A -> B: label";
           node kinds [user] [svc] [db] [queue] [cache] [ext], e.g. "Browser [user] -> API: HTTPS"
  steps    numbered steps, one per line "Title | detail"
  board    "title: ...", "columns: Now,Next,Later,Cut", then "ID | title | column" lines;
           renders a drag-and-drop board with markdown export (items without a column start in Inbox)

## Rules

- Use only the data you were given. The kit computes summaries (status bar, chart
  average, peak bar) itself; do not write them out.
- If you need something the kit does not have, write plain HTML for that one part
  and keep the rest in components.
