# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| No `DevToolsActivePort` | Toggle never enabled, or custom `--user-data-dir` | Enable toggle; pass the custom dir |
| File exists, TCP refused | Browser closed or toggle off (stale file) | Check `Local State` `user-enabled`; start browser or enable toggle |
| `/json/version` 404 | Attach mode disables HTTP | Connect to `ws://127.0.0.1:<port><path from file>` |
| Connect hangs | Dialog waiting for the user on the browser's last active window (possibly another monitor or virtual desktop) | Ask the user to click Allow; do not time out and retry |
| Handshake fails with 403 (WebSocket libs: "Unexpected response 403", "Expected 101") | User clicked Cancel / "Turn off in settings" | Report; retry only when the user asks |
| Several dialogs on screen | Earlier attempts timed out or retried, or several clients connected | Cancel stale ones; fix the code to reuse one connection |
| Dialog for every run | New connection per run | Accept (short scripts) or keep one connection (`persistent-connection.md`) |
| Connection closed 1006 mid-session | Toggle turned off, browser closed, or policy changed | Classify via TCP probe + `Local State`; reconnect on demand |
| Immediate refusal, no dialog shown | No browser window open (not verified) | Ask the user to open a window |
| Toggle greyed out on inspect page | `RemoteDebuggingAllowed` policy false | Managed device; use dedicated mode or ask the admin |
| `--remote-debugging-port` ignored | Default user data dir (Chrome 136+), or browser already running with that dir | Use a separate `--user-data-dir` |
| Launched browser exits at once, no port file | Another process owns that `--user-data-dir` | Close it or use another dir |
| Playwright `connectOverCDP` timeout after 30 s | Default timeout shorter than the user's reaction | `timeout: 0` |
| `chrome-remote-interface` 404 on `/json/protocol` | Fetches protocol over HTTP by default | `local: true` |
| `Page.enable` never returns | Tab discarded/frozen by memory saver | Probe with `Runtime.evaluate("1")`, short timeout; skip or reload the tab |
| "Session with given id not found" | Tab closed, or session from an old connection | Re-attach by `targetId` |
| Message too big / socket closes on screenshot | Client max message size too small | Raise it (≥100 MB) |
| Automation banner not visible | Another infobar occupies the slot | Harmless; check the connection count instead |
| Cannot reach 127.0.0.1 from a container or VM | Separate network namespace; browser binds host loopback only | Run the client on the host; do not expose the port |
