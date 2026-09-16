---
name: agent-browser
description: Use when Codex needs to drive a real browser through the local `agent-browser` CLI for website navigation, form filling, screenshots, downloads, scraping, login reuse, tab or session management, or DOM inspection. Apply it to browser automation tasks that should use `agent-browser` instead of hand-written shell flows, and prefer it over broader page-cloning workflows when the goal is to interact with or inspect a live site.
---

# agent-browser CLI

Use this skill to operate websites through the `agent-browser` command with a
repeatable inspect -> interact -> verify loop.

## Boundaries

- Use this skill for live browser automation and inspection.
- Use `$web-clone` when the user wants to recreate a site as code from a URL.
- Prefer browser MCP or DevTools-specific workflows when the task is explicitly
  about Playwright MCP or Chrome DevTools tooling rather than the
  `agent-browser` CLI.
- Do not invent refs, selectors, or login steps. Inspect the page first.

## Workflow

1. Verify the tool surface only when needed.
   - If availability is unknown, check `command -v agent-browser` or
     `agent-browser --help`.
   - When exact flags matter, consult `references/commands.md`.
2. Choose the right persistence model before opening the page.
   - One-off work: default ephemeral session.
   - Concurrent tasks: use `--session <name>`.
   - Reusable cookies or localStorage: use `--session-name <name>`.
   - Reuse an existing browser profile: use `--profile <path-or-name>`.
   - Login credentials: prefer the auth vault flow in
     `references/authentication.md`.
3. Inspect before interacting.
   - Start with `agent-browser open <url>`.
  - Use `agent-browser snapshot -i` as the default discovery step.
  - Use `agent-browser screenshot --annotate` when the page is visually dense,
    contains unlabeled controls, or spatial reasoning matters.
4. Interact with refs, then verify.
   - Use `click`, `fill`, `select`, `check`, `press`, `get`, and `wait`.
   - After each meaningful action, confirm the new state with `snapshot -i`,
     `get url`, `get text`, or a screenshot.
5. Batch only when the next commands are already known.
   - Use `agent-browser batch ...` for fixed sequences like open -> screenshot.
   - Do not batch across a discovery step whose output determines later refs.
6. Re-snapshot whenever refs may be stale.
   - Refs become unreliable after navigation, form submit, modal expansion,
     major DOM rerenders, or tab changes.
   - See `references/snapshot-refs.md` for the exact lifecycle rules.
7. Clean up sessions and secrets.
   - Close named or temporary sessions when the task is done.
   - Remove one-off state files and keep them out of git.

## Default Tactics

- Prefer `snapshot -i` over screenshots when the goal is structure or refs.
- Prefer targeted `get attr <ref> href` calls for a few links, and use `eval`
  only when bulk URL extraction is truly necessary.
- Prefer explicit waits like `wait @e1`, `wait --url`, or `wait --text`.
- Avoid `wait --load networkidle` on sites with analytics, ads, polling, or
  websockets unless you know the page becomes idle.
- Prefer direct `open <url>` on harvested links over repeated back/forward
  navigation.
- Use named sessions for concurrent or parallel browser work to avoid crosstalk.

## Security

- Treat state files as sensitive because they may contain cookies or tokens.
- Prefer auth vault or profile reuse over embedding secrets in shell history.
- Do not commit auth state, downloaded private data, or screenshots containing
  secrets.

## Load On Demand

- Read [references/commands.md](references/commands.md) for exact command
  families, high-signal examples, and when to use `batch`.
- Read [references/authentication.md](references/authentication.md) for login
  reuse, auth vault, session-state hygiene, and 2FA handling.
- Read [references/session-management.md](references/session-management.md) for
  `--session`, `--session-name`, `--profile`, cleanup, and concurrency rules.
- Read [references/snapshot-refs.md](references/snapshot-refs.md) for ref
  invalidation, annotated screenshot mapping, and extraction tactics.

## Copyable Assets

- [assets/form-automation.sh](assets/form-automation.sh): starter flow for form
  discovery, fill, submit, and evidence capture.
- [assets/capture-workflow.sh](assets/capture-workflow.sh): starter flow for
  screenshots, text capture, and PDF export.
- [assets/authenticated-session.sh](assets/authenticated-session.sh): starter
  flow for manual login discovery and state reuse.

Treat these assets as starting points. Adjust refs, waits, paths, and any
site-specific assumptions before running them on real targets.
