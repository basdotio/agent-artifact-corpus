# Tabs and common operations

Reference: `scripts/src/targets.ts`.

## Listing

`Target.getTargets` (browser level, no session). Keep `type === "page"` and drop internal URLs:
`chrome:`, `edge:`, `brave:`, `vivaldi:`, `opera:`, `devtools:`, `chrome-extension:`,
`chrome-untrusted:`, `about:`. Other types seen on a real browser: `iframe`,
`service_worker`, `background_page`, `browser_ui`, `worker`.

- Result order is not the tab-strip order and does not tell which tab is active.
- Identify tabs by `targetId`, never by index. `sessionId` is per connection.
- To find "the tab the user means": match URL/title from the request; if ambiguous, show
  the candidates and ask. Heuristic for the active tab: `document.visibilityState ===
  "visible"` (one per window; `document.hasFocus()` also needs the window focused).
- All profiles of the browser are visible; `browserContextId` separates them.

## Attaching

```
{ sessionId } = Target.attachToTarget({ targetId, flatten: true })
... send commands with sessionId ...
Target.detachFromTarget({ sessionId })   # leaves the tab open
```

- Enable only the domains you need (`Page.enable`, `Runtime.enable`, `Network.enable`);
  each adds event traffic. Domain state is per session and ends with it.
- Discarded/frozen tabs (memory saver) can hang `Page.enable`. Probe first with
  `Runtime.evaluate({ expression: "1" })` and a short timeout (2 s).
- `Target.setAutoAttach` attaches to every tab and new tab: avoid on a user browser unless
  you need all of them.

## Own tabs

- `Target.createTarget({ url: "about:blank", background: true })`, attach, then navigate.
  Creating blank first avoids missing early events of the load.
- Close only tabs you created: `Target.closeTarget({ targetId })`, in a `finally`.
- Track created `targetId`s; on reconnect, close leftovers from a previous run if the
  project owns them (e.g. marked by URL or title).

## Leave no trace on user tabs

- No `Emulation.*` overrides (viewport, media, timezone) on user tabs; if needed, use an own tab.
- No `Page.bringToFront` / `Target.activateTarget` unless asked.
- Restore anything changed (e.g. `Network.setExtraHTTPHeaders`) before detaching.
- Navigating a user tab destroys its state (forms, scroll); prefer an own tab.

## Common operations

| Task | Command | Level |
|---|---|---|
| All cookies incl. httpOnly/partitioned | `Storage.getCookies` | Browser (no tab attach) |
| Cookies for URLs | `Network.getCookies({ urls })` | Session |
| Run JS | `Runtime.evaluate({ expression, awaitPromise: true, returnByValue: true })` | Session |
| Navigate and wait | `Page.enable`, `Page.navigate`, wait `Page.loadEventFired` | Session |
| Screenshot | `Page.captureScreenshot({ format: "png" })` → base64 | Session |
| Full-page screenshot | `captureBeyondViewport: true` | Session |
| PDF | `Page.printToPDF` | Session |
| Downloads to a folder | `Browser.setDownloadBehavior({ behavior: "allowAndName", downloadPath, eventsEnabled: true })`; reset to `"default"` when done | Browser |
| Response bodies | `Network.enable`, `Network.getResponseBody({ requestId })` | Session |
| Accessibility tree | `Accessibility.getFullAXTree` | Session |
| Click/type | `Input.dispatchMouseEvent` / `Input.insertText` | Session |
| Browser version | `Browser.getVersion` | Browser |

`Browser.setDownloadBehavior` changes the user's global download behaviour: restore it.
