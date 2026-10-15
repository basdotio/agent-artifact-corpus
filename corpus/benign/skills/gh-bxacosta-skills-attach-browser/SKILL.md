---
name: attach-browser
description: >-
  Connects to the user's running Chromium browser via CDP to reuse its sessions, or launches
  a debug profile. Use for connectOverCDP, "Allow remote debugging?" or "use my browser".
license: MIT
compatibility: Chromium 144+ for attach mode. Reference scripts need Bun 1.x. Local machine only.
---

# Attach browser

Connect to a Chromium browser over CDP, either the user's running browser (attach mode) or
one you launch with its own profile (dedicated mode). Applies to any language: the
TypeScript in `scripts/` is the reference implementation to port.

Terms used throughout:
- **Endpoint**: browser-level WebSocket URL `ws://127.0.0.1:<port>/devtools/browser/<id>`.
- **Connection**: one WebSocket to the endpoint. Tabs are multiplexed on it via sessions.
- **Target**: a CDP target; a **tab** is a target of type `page`.

## Choose a mode

| Need | Mode |
|---|---|
| User's real tabs, cookies, logins; user is present to click Allow | **Attach** |
| Unattended runs, CI, parallel workers, or isolation from the user's profile | **Dedicated**, read `references/dedicated-profile.md` |
| Logged-in state without the user present | Dedicated profile, logged in once manually, then reused |

## Gotchas (verified on Chrome, Edge and Brave 154)

- Attach mode requires the user to tick "Allow remote debugging for this browser instance" at
  `<scheme>://inspect/#remote-debugging` (`chrome`, `edge`, `brave`). The setting persists
  across restarts. `--remote-debugging-port` does not work on the default profile (Chrome 136+).
- Every new connection shows an "Allow remote debugging?" dialog, even while another
  connection is open. One connection, reused, means one click.
- The dialog has no timeout. If the client gives up, the dialog stays on screen (orphaned)
  and the next attempt stacks a second dialog. Wait without a timeout; never retry in a loop.
- The endpoint comes from the `DevToolsActivePort` file (line 1 port, line 2 path) in the
  user data dir. The browser reuses its last port, else 9222, else a random one; with
  several browsers running only one can have 9222. Always read the file.
- `DevToolsActivePort` is never deleted: it is stale when the browser is closed or the
  toggle is off. Confirm the port is open with a raw TCP connect, which shows no dialog.
- In attach mode every HTTP route (`/json/version`, `/json/list`, `/`) returns 404. Tools
  that discover via `http://host:port` fail; pass the `ws://` endpoint.
- Deny ("Cancel" or "Turn off in settings") answers the WebSocket upgrade with HTTP 403.
  Turning the toggle off kills open connections (close code 1006) and closes the port.
- Page-level sockets (`/devtools/page/<id>`) are rejected. Use the browser endpoint and
  `Target.attachToTarget({ flatten: true })`.
- The dialog appears on the browser's last active window and brings it to the front.

Items marked "not verified" in the references come from source code only: mention them,
do not build logic on them.

## Rules

- Never send `Browser.close` or close tabs you did not create: it is the user's browser.
- Do not steal focus: open tabs with `Target.createTarget({ background: true })`; never
  `Target.activateTarget` or `Page.bringToFront` unless the user asks.
- Tell the user before connecting that a dialog will appear and what it is for.
- Treat the connection as full access to the user's accounts. Read only what the task
  needs; never log or persist cookies or tokens unless asked. See `references/security.md`.
- Never expose the port beyond 127.0.0.1 (no port proxies, no `0.0.0.0`).

## Attach workflow

```
- [ ] 1. Discover without connecting (`bun scripts/find-endpoint.ts`, or port src/discovery.ts)
- [ ] 2. state != listening → show the user the hint (enable toggle / start browser); stop until confirmed
- [ ] 3. Tell the user to click Allow; open ONE connection with no handshake timeout
- [ ] 4. Handle refusal (403 / close before open) as "user denied"; do not reconnect automatically
- [ ] 5. List tabs; act on the tab the user means, or on an own background tab
- [ ] 6. Reuse the same connection for all further work
- [ ] 7. Disconnect when done (close the WebSocket; the browser stays open)
```

Short-lived scripts (one task, then exit) cost one click per run. Processes that serve
repeated requests must keep one long-lived connection: read `references/persistent-connection.md`.

## Implementing in a project

- Scale to the request: a one-off script needs discovery + one connection + clear errors;
  a broker only when many short invocations share a browser. Copy only the modules used.
- Discovery (~60 lines, no dependency) always belongs in the project: port `scripts/src/browsers.ts`
  and `scripts/src/discovery.ts`.
- Transport: a hand-rolled client (`scripts/src/cdp-client.ts`, ~200 lines) for targeted tasks;
  a library when you need high-level automation (selectors, waits, input). Per-language
  choices and required options (e.g. Playwright `timeout: 0`): `references/clients.md`.

## Scripts

Run from the skill root. JSON on stdout, diagnostics on stderr. Zero runtime dependencies.

| Command | Purpose | Exit codes |
|---|---|---|
| `bun scripts/find-endpoint.ts [--browser <id>] [--user-data-dir <dir>] [--text]` | State of each installed browser; never connects | 0 listening · 1 none · 2 bad args |
| `bun scripts/example-attach.ts [--browser <id>] [--url <u>]` | End-to-end attach demo (one dialog) | 0 ok · 1 not ready · 3 denied · 4 error |

Reference modules (read and port): `scripts/src/browsers.ts` (profile paths),
`discovery.ts` (no-dialog discovery), `cdp-client.ts` (single-connection client),
`targets.ts` (tab helpers), `launch.ts` (dedicated mode).

## Read when needed

- How approval mode works, per-browser differences, policies, Firefox → `references/how-it-works.md`
- Profile paths per OS/browser, discovery states, multiple browsers → `references/discovery.md`
- Long-lived connection, reconnection, several consumers → `references/persistent-connection.md`
- Choosing or configuring a CDP library in any language → `references/clients.md`
- Selecting, attaching to, creating tabs; common operations → `references/tabs.md`
- Launching an own browser/profile → `references/dedicated-profile.md`
- Cookies, credentials, consent, remote hosts → `references/security.md`
- Error or symptom → `references/troubleshooting.md`
