# Snapshot Refs

Load this file when you need to reason about ref validity, annotated
screenshots, or efficient extraction patterns.

## Default Loop

1. `agent-browser open <url>`
2. `agent-browser snapshot -i`
3. Interact using refs like `@e1`
4. Verify the result
5. Re-snapshot when the page or DOM meaningfully changed

## When Refs Become Stale

Assume refs may be invalid after:

- clicking a link that navigates
- submitting a form
- opening or closing a modal or drawer
- expanding accordions or menus that rerender content
- switching tabs
- reloading the page
- client-side route changes in SPAs

If unsure, take a fresh `snapshot -i`.

## When Refs Usually Stay Good

Refs are often still usable after:

- reading values with `get`
- short waits without DOM changes
- scrolling the same page
- clicking controls that do not rerender the target region

Even then, verify with a quick follow-up snapshot if the page is highly dynamic.

## Annotated Screenshots

Use:

```bash
agent-browser screenshot --annotate
```

This gives a visual map where label `[N]` corresponds to ref `@eN`.

Prefer it when:

- the page has icon-only buttons
- accessibility names are poor
- layout position matters
- canvas or chart regions are involved

Annotated screenshots help with discovery, but text snapshots remain cheaper for
most structural work.

## Efficient Link Harvesting

When the task is "visit several links from this page," avoid clicking through
and navigating back repeatedly.

For a few known refs, read URLs directly:

```bash
agent-browser get attr @e4 href
agent-browser get attr @e7 href
```

For bulk extraction, use `eval` only when necessary and keep the result narrow:

```bash
agent-browser eval 'Array.from(document.querySelectorAll("a")).slice(0, 20).map(a => a.href)'
```

Then open the harvested targets directly in their own step or session.

## JSON Output

If later tooling needs machine-readable output, prefer JSON-capable inspection
surfaces such as:

- `agent-browser snapshot -i --json`
- `agent-browser get text @e1 --json`

Use plain-text snapshots when a human-readable view is faster to interpret.
