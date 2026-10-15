# Discovery

Find the endpoint without opening a connection (no dialog). Reference: `scripts/src/discovery.ts`,
`scripts/src/browsers.ts`.

## Algorithm

For each candidate user data dir:

1. Read `DevToolsActivePort`. Missing or malformed → `no-port-file`.
2. TCP-connect to `127.0.0.1:<port>` (300 ms timeout). Refused → `not-listening` (stale file).
3. Open → `listening`; endpoint = `ws://127.0.0.1:<port><line 2>`.
4. Read `Local State` → `devtools.remote_debugging.user-enabled` to explain `not-listening`:
   `false`/absent → toggle off; `true` → browser not running.

Do not use HTTP (`/json/version`) to discover in attach mode: it returns 404. Do not open a
WebSocket to "test" the endpoint: that shows a dialog and, if closed, orphans it.

## States and what to tell the user

| State | Toggle | Meaning | Action |
|---|---|---|---|
| `listening` | true | Ready | Warn about the Allow dialog, then connect |
| `not-listening` | true | Browser closed | Ask the user to start the browser |
| `not-listening` | false/absent | Toggle off | Ask the user to open `<scheme>://inspect/#remote-debugging` and tick the checkbox |
| `no-port-file` | any | Never enabled / not installed | Same as toggle off |

After the user ticks the toggle, re-run discovery; the port file appears immediately.
A foreign process on a stale port would show as `listening`; the handshake then fails.

## User data dirs

`DevToolsActivePort` and `Local State` sit in the user data dir root (not in `Default/`).

Windows (`%LOCALAPPDATA%/`):

| Browser | Path |
|---|---|
| Chrome / Beta / Dev / Canary | `Google/Chrome/User Data`, `Google/Chrome Beta/User Data`, `Google/Chrome Dev/User Data`, `Google/Chrome SxS/User Data` |
| Chromium | `Chromium/User Data` |
| Edge / Beta / Dev / Canary | `Microsoft/Edge/User Data`, `Microsoft/Edge Beta/User Data`, `Microsoft/Edge Dev/User Data`, `Microsoft/Edge SxS/User Data` |
| Brave | `BraveSoftware/Brave-Browser/User Data` |
| Vivaldi | `Vivaldi/User Data` |
| Opera | `%APPDATA%/Opera Software/Opera Stable` |

macOS (`~/Library/Application Support/`): `Google/Chrome`, `Google/Chrome Beta`,
`Google/Chrome Dev`, `Google/Chrome Canary`, `Chromium`, `Microsoft Edge`,
`Microsoft Edge Beta`, `Microsoft Edge Dev`, `Microsoft Edge Canary`,
`BraveSoftware/Brave-Browser`, `Vivaldi`, `com.operasoftware.Opera`.

Linux (`$XDG_CONFIG_HOME`, default `~/.config/`): `google-chrome`, `google-chrome-beta`,
`google-chrome-unstable`, `google-chrome-canary`, `chromium`, `microsoft-edge`,
`microsoft-edge-beta`, `microsoft-edge-dev`, `BraveSoftware/Brave-Browser`, `vivaldi`, `opera`.
Flatpak: `~/.var/app/<app-id>/config/<same>`. Snap Chromium cannot expose CDP.

A browser started with a custom `--user-data-dir` writes the file there; accept an explicit
dir from configuration.

## Several browsers at once

Each running browser has its own port and file. Return all matches and let configuration or
the user choose (`--browser edge`); do not silently pick the first. When exactly one is
listening, using it is reasonable.

## Configuration surface for projects

Expose, in precedence order: explicit endpoint (`ws://…`) → explicit user data dir →
browser id → auto (single listening browser). Never require a hard-coded port.
