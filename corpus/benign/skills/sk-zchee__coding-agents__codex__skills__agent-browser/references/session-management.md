# Session Management

Load this file when multiple browser tasks may overlap or when state needs to
survive beyond a single command sequence.

## Pick The Right Isolation Level

- Default session
  - Best for one-off work.
  - Lowest setup cost.
- `--session <name>`
  - Best for concurrent browser automations in the same environment.
  - Keeps tabs, refs, and runtime state separate across tasks.
- `--session-name <name>`
  - Best when cookies and localStorage should persist across browser restarts.
- `--profile <path-or-name>`
  - Best when reusing a real browser profile is intentional.
- `--state <file>`
  - Best when a specific exported session file must be loaded.

## Concurrency Rule

If two automations may overlap, do not share the default session. Use explicit
session names:

```bash
agent-browser --session site-a open https://site-a.example
agent-browser --session site-b open https://site-b.example
```

This avoids tab collisions and accidental state leakage between tasks.

## Cleanup

Close what you opened:

```bash
agent-browser close
agent-browser --session site-a close
agent-browser close --all
```

Use `close --all` when a prior run leaked browser processes or you need to
reset the environment.

## Tabs

Use tabs when the work belongs to one logical session:

```bash
agent-browser tab list
agent-browser tab new https://example.com
agent-browser tab 1
agent-browser tab close
```

After switching tabs, verify state again because refs from the previous page may
no longer describe the active tab.

## Downloads and Output Paths

Make output locations explicit for long or repeated workflows:

```bash
agent-browser --download-path ./downloads open https://example.com
agent-browser wait --download ./downloads/report.csv
```

Avoid mixing files from unrelated sessions into the same temp directory when
the outputs matter.

## Failure Recovery

When state looks wrong:

1. Check the active URL.
2. List tabs or sessions.
3. Re-open the target page in the intended session.
4. Take a new snapshot before resuming.

If a named session becomes unreliable, close it and reopen it cleanly instead
of trying to salvage stale refs.
