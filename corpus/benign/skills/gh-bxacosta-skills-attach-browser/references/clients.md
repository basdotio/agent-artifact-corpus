# CDP clients

Every client needs the endpoint from discovery (`references/discovery.md`); no library
except Puppeteer/Playwright channel mode reads `DevToolsActivePort` for you, and none of
them gives state classification or no-dialog probing.

## Hand-rolled vs library

- Hand-rolled (`scripts/src/cdp-client.ts`): targeted tasks (cookies, evaluate, screenshot,
  tab list, navigation). Exactly one connection, no hidden HTTP calls, no auto-attach to
  every tab. About 200 lines in any language with a WebSocket.
- Library: when you need high-level automation (selectors, auto-waiting, input events,
  frames). Configure it as below so it does not break attach mode.

Minimal client requirements (any language):
1. One WebSocket to the browser endpoint; large max message size (screenshots and response
   bodies are several MB; Python `websockets` defaults to 1 MiB).
2. Incrementing `id`; map `id → {method, resolve, reject, timer}`. Responses do not echo
   `method`, so keep it for error messages.
3. Flatten sessions: send `{id, method, params, sessionId}`; route events by `(method, sessionId)`.
4. Connect: no timeout by default. Per-command timeout separate (30 s default).
5. On socket close: reject every pending call; expose an `onClose` hook.
6. `close()` only closes the socket. Never `Browser.close` on an attached browser.

## Libraries

| Language | Default | Attach-mode configuration |
|---|---|---|
| TS/JS | Hand-rolled + `devtools-protocol` (types only) | — |
| TS/JS | `chrome-remote-interface` | `CDP({ target: endpoint, local: true })`; without `local` it fetches `/json/protocol` (404) |
| TS/JS | `puppeteer-core` | `puppeteer.connect({ browserWSEndpoint: endpoint, defaultViewport: null })`; `targetFilter` to skip tabs; channel auto-discovery `connect({ channel: "chrome" })` is experimental and Chrome-only |
| TS/JS | `playwright-core` | `chromium.connectOverCDP(endpoint, { timeout: 0, noDefaults: true })` (1.60+). Default 30 s timeout fails while the user reads the dialog; `noDefaults` avoids changing the user's context. Waits for every open tab at connect: slow with many tabs |
| Python | `cdp-use` | Pass the `ws://` endpoint; raise `websockets` `max_size`; remove the open timeout |
| Go | `chromedp` + `cdproto` | `chromedp.NewRemoteAllocator(ctx, endpoint)`; use `chromedp.WithTargetID` to attach to an existing tab (default creates a new one) |
| Rust | `chromiumoxide` | `Browser::connect(endpoint)`; flatten sessions supported |
| Java/Kotlin | `chrome-devtools-kotlin` | Pass the `ws://` endpoint |
| .NET | Hand-rolled on `ClientWebSocket` | — |

Disconnecting from the user's browser (never quits it):

| Client | Call |
|---|---|
| Hand-rolled / chrome-remote-interface | Close the WebSocket (`client.close()`) |
| Puppeteer | `browser.disconnect()`; `browser.close()` would quit the browser |
| Playwright (`connectOverCDP`) | `browser.close()`: disconnects and closes only contexts you created; the browser keeps running |

Avoid for attach mode: clients that open one socket per tab (each is another dialog) or
that only accept `http://host:port` (HTTP discovery returns 404). Examples: `pychrome`,
`nodriver`/`zendriver`, Rust `headless_chrome` (deprecated `sendMessageToTarget`).

## Tool integrations

| Tool | Attach mode |
|---|---|
| chrome-devtools-mcp | `--autoConnect` (Chrome channels); Edge/Brave: `--autoConnect --userDataDir <dir>`. `--browserUrl` fails (needs `/json/version`) |
| Playwright MCP / playwright-cli | `--cdp-endpoint=<ws endpoint or channel>`, raise `--cdp-timeout`; `attach --cdp=<channel>` |
| Playwright MCP `--extension` | Uses a browser extension (`chrome.debugger`) instead of remote debugging: no toggle, no per-connection dialog, requires installing the extension |
| agent-browser, browser-use | Built-in attach with their own daemon |
