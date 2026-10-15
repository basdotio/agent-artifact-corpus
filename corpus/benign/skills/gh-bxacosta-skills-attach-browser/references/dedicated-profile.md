# Dedicated profile

Launch a browser with its own user data dir and remote debugging by flag. No toggle, no
dialog, unlimited connections, `/json/*` available. Reference: `scripts/src/launch.ts`.

## Launch

```
<browser-exe> --remote-debugging-port=0 --user-data-dir=<own dir> \
  --no-first-run --no-default-browser-check [--headless=new] [url]
```

- `--remote-debugging-port=0`: browser picks a free port and writes `DevToolsActivePort`
  into `<own dir>`. A fixed port collides with other browsers and does not write the file.
- Delete `<own dir>/DevToolsActivePort` before launching; then poll for it (100 ms) with a
  timeout (30 s). Ready in ~250 ms on a warm machine.
- If the process exits before the file appears, another process already uses that dir.
- Runs alongside the user's normal browser (different dir = different process).
- `--user-data-dir` must not be the user's real profile dir (see `how-it-works.md`).
- Add `--remote-allow-origins=<origin>` only if a web page must connect; native clients need nothing.

Executables:

| | Windows | macOS | Linux |
|---|---|---|---|
| Chrome | `%ProgramFiles%/Google/Chrome/Application/chrome.exe` | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` | `google-chrome`, `google-chrome-stable` |
| Edge | `%ProgramFiles(x86)%/Microsoft/Edge/Application/msedge.exe` | `/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge` | `microsoft-edge` |
| Brave | `%ProgramFiles%/BraveSoftware/Brave-Browser/Application/brave.exe` | `/Applications/Brave Browser.app/Contents/MacOS/Brave Browser` | `brave-browser` |
| Chromium | `%LOCALAPPDATA%/Chromium/Application/chrome.exe` | `/Applications/Chromium.app/Contents/MacOS/Chromium` | `chromium`, `chromium-browser` |

Also check per-user installs (`%LOCALAPPDATA%/…/Application/`) and allow an explicit path.

## Connect

Endpoint from the file (`ws://127.0.0.1:<port><line 2>`), or `GET /json/version` →
`webSocketDebuggerUrl`. Connections open in ~10 ms; timeouts of a few seconds are fine here.

## Persisting logins

- Reuse the same dir across runs; the user logs in once in that window.
- Keep the dir outside temp folders and treat it as a secret (it holds session cookies).
- One process per dir: serialize runs or give each parallel worker its own dir.
- Copying the user's real profile does not carry logins: cookies are encrypted with keys
  bound to the original install (App-Bound Encryption on Windows).

## Close

You own this browser: `Browser.close` is correct. It flushes cookies and profile data.
Wait for process exit (Edge can take over 5 s; wait 10 s) before killing it; a kill can lose
recent profile writes.

## Headless

`--headless=new` for unattended runs. Some sites detect headless; use a visible window
when the site matters. Headless and headed can share a profile dir, not concurrently.
