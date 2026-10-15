# How remote debugging works in Chromium

Contents: server modes · approval mode lifecycle · HTTP and WebSocket rules · dialog ·
banner · policies · other browsers.

## Two server modes

| | Approval mode (attach) | Flag mode (dedicated) |
|---|---|---|
| Enabled by | Toggle at `<scheme>://inspect/#remote-debugging` | `--remote-debugging-port=<n>` + non-default `--user-data-dir` |
| Profile | User's default profile | Any non-default dir |
| Dialog per connection | Yes | No |
| HTTP `/json/*` | 404 | 200 |
| Accepted WS paths | `/devtools/browser*` only | browser and page paths |
| `DevToolsActivePort` | Always written | Written only with `--remote-debugging-port=0` |

Chrome 136+ ignores `--remote-debugging-port` / `--remote-debugging-pipe` on the default
user data dir (Google-branded builds; protects cookies from infostealers). Flags take
precedence: if a flag started the server, approval mode does not start.

## Approval mode lifecycle

- Toggle state: `Local State` → `devtools.remote_debugging.user-enabled` (bool). One
  setting per browser install (user data dir), not per profile. Written immediately.
- Toggle on: server starts immediately (no restart). The inspect page shows
  `Server running at: 127.0.0.1:<port>`.
- Port choice: port in the previous `DevToolsActivePort`, else 9222, else any free port;
  127.0.0.1 preferred over `[::1]`. Two browsers never share a port.
- `DevToolsActivePort` is rewritten on every start and toggle-on: same port if free,
  **new UUID each time**. Format `<port>\n/devtools/browser/<uuid>`, no trailing newline.
- Toggle off: port closes immediately, open connections drop (close 1006), file stays.
- Browser exit: file stays. Browser start with toggle on: server comes back automatically.

## HTTP and WebSocket rules (approval mode)

- All HTTP routes return 404, including while a dialog is pending.
- WebSocket upgrade accepted only for paths starting with `/devtools/browser`. The UUID
  is not validated. Page paths get 403.
- `Origin` header must be absent or same-origin: web pages cannot connect; native clients can.
- `Host` header must be an IP or `localhost`.
- Every accepted upgrade triggers the dialog. Allow → HTTP 101. Cancel, "Turn off in
  settings" or closing the dialog → HTTP 403.

## Dialog

Text (browser name varies): "Allow remote debugging? An external app wants full control
over this Chrome session to debug it. This includes access to your saved data, cookies
and site data, and the ability to navigate to any URL." Buttons: **Turn off in settings**,
**Allow**, **Cancel** (focused by default).

- One per WebSocket connection; stacks if several are pending.
- No timeout; stays even if the client disconnects (orphaned dialog).
- Shown on the last active browser window, which is brought to the front. With no open
  window, the connection is denied immediately (from source; not verified).
- "Turn off in settings" denies and opens the inspect page; it does not turn the toggle off.

## Banner

While at least one connection is open: infobar "Chrome is being controlled by automated
test software" with a "Turn off in settings" button. It shares the infobar slot, so
another infobar can hide it. It disappears when the last connection closes.

## Policies

- `RemoteDebuggingAllowed = false` (enterprise policy) disables both modes and greys out
  the toggle; flipping it at runtime kills open sessions.
- Check on Windows: `HKLM\SOFTWARE\Policies\Google\Chrome` (Edge: `Microsoft\Edge`,
  Brave: `BraveSoftware\Brave`). macOS/Linux: managed preferences / `/etc/opt/chrome/policies`.

## Other browsers

| Browser | Attach mode | Notes |
|---|---|---|
| Chrome 144+ | Yes | Verified on 154 |
| Edge 144+ | Yes, `edge://inspect` | Verified on 154; identical behaviour |
| Brave (Chromium 144+) | Yes, `brave://inspect` | Verified on 1.96 / Chromium 154 |
| Vivaldi, Opera, Arc | Likely (shared Chromium code) | Not verified |
| ChromeOS | Disabled | Developer mode only |
| Firefox | No | CDP removed (Firefox 141); WebDriver BiDi only at launch |
| WebView2 | No toggle | Flag mode via `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS` |

Non-Google builds (Brave, Chromium) do not enforce the Chrome 136 default-profile block.
Still use a separate profile for flag mode: a user data dir serves one browser process, so
launching with the user's dir while the browser runs just opens a window in the existing
process and the flag is ignored.
