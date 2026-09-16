# Command Guide

Load this file when you need exact `agent-browser` command families or a
concise reminder of the highest-signal flags.

## Discovery First

- `agent-browser open <url>`
  - Opens the page and already waits for the initial page load.
- `agent-browser snapshot -i`
  - Default inspection step. Returns interactive refs like `@e1`.
- `agent-browser screenshot --annotate`
  - Best when you need a visual map from `[N]` labels to refs like `@eN`.

## Interact With Refs

- `agent-browser click @e1`
- `agent-browser fill @e2 "text"`
- `agent-browser type @e2 "text"`
- `agent-browser select @e3 "option"`
- `agent-browser check @e4`
- `agent-browser press Enter`
- `agent-browser scroll down 500`
- `agent-browser upload @e5 /path/to/file.pdf`

Use a new snapshot after navigation, form submission, large rerenders, or modal
changes.

## Get State Back

- `agent-browser get url`
- `agent-browser get title`
- `agent-browser get text @e1`
- `agent-browser get value @e2`
- `agent-browser get attr @e3 href`
- `agent-browser get box @e4`

Prefer `get` when the task only needs a specific value rather than a full new
snapshot.

## Wait Intentionally

- `agent-browser wait @e1`
- `agent-browser wait 1500`
- `agent-browser wait --text "Success"`
- `agent-browser wait --url "**/dashboard"`
- `agent-browser wait "#spinner" --state hidden`

Prefer element, text, or URL waits over `wait --load networkidle` unless the
page is known to become fully idle.

## Screenshots, PDFs, and Downloads

- `agent-browser screenshot`
- `agent-browser screenshot --full`
- `agent-browser screenshot --annotate`
- `agent-browser pdf output.pdf`
- `agent-browser download @e1 ./file.pdf`
- `agent-browser wait --download ./output.zip`

Use annotated screenshots when text snapshots miss icon-only controls or canvas
content.

## Tabs, Frames, and Sessions

- `agent-browser tab list`
- `agent-browser tab new https://example.com`
- `agent-browser tab 2`
- `agent-browser tab close`
- `agent-browser frame @e2`
- `agent-browser frame main`
- `agent-browser session list`
- `agent-browser close`
- `agent-browser close --all`

Use `--session <name>` when multiple automations may overlap.

## Batch Rules

Use `batch` only when later commands do not depend on reading intermediate
output.

Good:

```bash
echo '[["open", "https://example.com"], ["screenshot", "--full"]]' \
  | agent-browser batch
```

Good:

```bash
echo '[["click", "@e4"], ["wait", "--text", "Success"], ["screenshot"]]' \
  | agent-browser batch
```

Not good:

```bash
echo '[["open", "https://example.com/login"], ["snapshot", "-i"], ["click", "@e3"]]' \
  | agent-browser batch
```

That last example is wrong because `snapshot -i` must be read before choosing
the correct refs.

## Exact Syntax

If the environment is live and correctness matters more than speed, verify the
current syntax with local help before mutation:

```bash
agent-browser --help
agent-browser <group> --help
agent-browser <group> <subcommand> --help
```
