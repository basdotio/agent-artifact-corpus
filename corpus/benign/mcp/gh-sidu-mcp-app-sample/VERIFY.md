# Verification Matrix

This document exercises every capability the sample server advertises. It has
three tiers:

- **Tier 1 — automated (`./verify.sh`)** — drives the server over stdio with
  raw JSON-RPC and greps for expected fields/notifications. All 44 checks pass
  headlessly with no host required.
- **Tier 2 — basic-host** — the reference host from `modelcontextprotocol/ext-apps`.
  Renders MCP Apps in iframes, exercises the View-side API surface.
- **Tier 3 — Claude Desktop / other real hosts** — end-to-end verification
  including sampling, elicitation, and roots (which require a real client).

Each capability is tagged with a `[CAP-*]` code so you can trace it to
`server.ts` where the code that implements it lives.

## Legend

- ✅ Supported and verified
- ⚠️ Supported but host-dependent (needs a client)
- ❌ Not supported / not implemented

## Tier 1 — automated

Run `./verify.sh` after `npm run build`. Expected output ends with
`All automated checks passed`.

| Capability | Tag | Notes |
|---|---|---|
| Tools capability advertised | `CAP-TOOL` | ✅ |
| Resources subscribe advertised | `CAP-RES-SUBSCRIBE` | ✅ |
| Prompts capability advertised | `CAP-PROMPT` | ✅ |
| Logging capability advertised | `CAP-LOG` | ✅ |
| Completions capability advertised | `CAP-COMPLETE` | ✅ |
| 11 tools listed | `CAP-TOOL` | ✅ |
| Tool annotations (`readOnlyHint`) | `CAP-TOOL-ANNOT` | ✅ |
| Tool `_meta.ui.resourceUri` (MCP Apps) | `CAP-APP` | ✅ |
| Tool `_meta.ui.visibility: ["app"]` | `CAP-APP-APPONLY` | ✅ |
| Text + structured content in tool result | `CAP-TOOL` | ✅ |
| Resource link in tool result | `CAP-TOOL-RESLINK` | ✅ |
| `_meta.viewUUID` for state persistence | `CAP-APP-VIEWUUID` | ✅ |
| Progress notifications | `CAP-PROGRESS` | ✅ |
| Log messages | `CAP-LOG` | ✅ |
| Static resource | `CAP-RES-STATIC` | ✅ |
| Binary blob resource (base64) | `CAP-RES-BLOB` | ✅ |
| Templated resource | `CAP-RES-TEMPLATE` | ✅ |
| Resource subscription + updates | `CAP-RES-SUBSCRIBE` | ✅ |
| Prompt with args + `prompts/get` | `CAP-PROMPT` | ✅ |
| Argument completion | `CAP-COMPLETE` | ✅ |
| `tools/list_changed` notification | `CAP-LISTCHANGED` | ✅ |
| Server issues `sampling/createMessage` | `CAP-SAMPLING` | ✅ (outbound only — needs host to fulfil) |
| Server issues `elicitation/create` | `CAP-ELICIT` | ✅ (outbound only) |
| Server issues `roots/list` | `CAP-ROOTS` | ✅ (outbound only) |
| Chunked binary read | `CAP-APP-CHUNK` | ✅ |

## Tier 2 — basic-host (MCP Apps UI)

The [`basic-host`](https://github.com/modelcontextprotocol/ext-apps/tree/main/examples/basic-host)
in the ext-apps repo supports the full MCP Apps surface. Setup:

```bash
# In one shell — start our server
cd mcp-app-sample
npm run build && npm run serve:http
# Server listens on http://localhost:3001/mcp

# In another shell — start basic-host, pointed at our server
cd /path/to/ext-apps/examples/basic-host
npm install
npm start
# Then open http://localhost:8080 in a browser
```

Then walk this checklist:

| # | Capability | Steps | Expected |
|---|---|---|---|
| 1 | `[CAP-APP]` | Select tool `dashboard`, click **Call Tool** | Iframe with title + 3 metrics + bar chart |
| 2 | `[CAP-APP-STRUCT]` | Same as above | Metric values render from `structuredContent`, not the text block |
| 3 | `[CAP-TOOL-RESLINK]` | Same as above | Text response references `config.json` resource link |
| 4 | `[CAP-APP-VIEWUUID]` | Reload the dashboard iframe | Metrics reappear from `localStorage`; log shows "Restored state" |
| 5 | Theming | Toggle basic-host to dark mode | Dashboard adapts colors via CSS variables |
| 6 | `[CAP-APP-APPONLY]` | Click **Refresh** on dashboard | New metrics appear; the app-only `poll-metrics` tool never appears in the visible tool list |
| 7 | `callServerTool` | Click **Call echo Tool** | Log shows `echo -> hello from the view (received …)` |
| 8 | `sendMessage` | Click **Send Message to Chat** | The chat shows a user message "Refresh the dashboard, please." |
| 9 | `updateModelContext` | Click **Update Model Context** | No visible UI change; ask the chat "what is the user looking at?" — it should know about the dashboard |
| 10 | `openLink` | Click **Open Link** | Host prompts / opens `https://modelcontextprotocol.io/` |
| 11 | Fullscreen | Click **Toggle Fullscreen** | Iframe expands (or a "Host does not offer" log if unsupported) |
| 12 | `[CAP-APP-PARTIAL]` | In chat: "run shader-preview with a slowly-typed shader" (best done via an LLM host — see Tier 3) | Preview `<pre>` displays code as it streams; final code compiles and renders |
| 13 | Shader offscreen pause | Scroll the shader iframe out of view | Info line reads "paused (offscreen)"; scroll back → "rendering" |
| 14 | Counter View + `preferredDisplayMode: pip` | Call `open-counter` | Counter renders; ticks once per second while visible |
| 15 | `[CAP-APP-CHUNK]` | Not directly visible — inspect DevTools; the dashboard doesn't currently exercise this. Trigger via Inspector for now. | — |
| 16 | `[CAP-APP-CSP]` | DevTools → Network → dashboard iframe | Iframe has restrictive CSP (no outbound network requests permitted) |

## Tier 3 — real LLM host

### 3b-A. Quick Work

Register with the bundled script (edits `~/.quickwork/profiles/<active>/mcp_config.json`, backs up first):

```bash
./install-quickwork.sh           # HTTP transport (server on :3001 must be running)
./install-quickwork.sh --stdio   # stdio transport (Quick Work spawns the server)
./install-quickwork.sh --remove  # unregister
```

Then fully restart Quick Work. The server appears under **MCP App Sample** in the servers panel and exposes 9 tools (the 2 app-only tools are correctly hidden).

#### Results (tested 2026-07-06)

| Capability | Tag | Quick Work behavior |
|---|---|---|
| Tool discovery + invocation | `[CAP-TOOL]` | ✅ 9/11 tools shown to model, `echo` returns instantly |
| MCP Apps UI rendering | `[CAP-APP]` | ✅ Dashboard renders as interactive iframe in chat with metrics + bar chart |
| App-only tools hidden from model | `[CAP-APP-APPONLY]` | ✅ `poll-metrics` and `read-large-file` don't appear in tool list |
| App→server `callServerTool` | | ✅ Refresh button updates metrics via `poll-metrics` |
| App→host `sendMessage` | | ✅ Text appears in the chat as if user sent it |
| App→host `updateModelContext` | | ✅ Model shows awareness of injected context |
| App→host `openLink` | | ✅ Opens URL in default browser |
| `requestDisplayMode(fullscreen)` | | ❌ Host does not offer fullscreen mode |
| Resources exposed to model | `[CAP-RES-STATIC]`, `[CAP-RES-TEMPLATE]`, `[CAP-RES-BLOB]` | ❌ Model has no generic `resources/read` capability — resources aren't in the model's toolbox |
| App→server `readServerResource` | `[CAP-RES-*]` | ❌ Returns `-32603 Internal error` — Quick Work's View-side resource proxy fails for `resource:///` URIs |
| Sampling (`sampling/createMessage`) | `[CAP-SAMPLING]` | ❌ Hangs; times out after ~60s. Fails **gracefully** — server returns `Sampling not supported by this client: <timeout>` |
| Elicitation (`elicitation/create`) | `[CAP-ELICIT]` | ❌ Clean reject — model reports elicitation capability unavailable |
| Roots (`roots/list`) | `[CAP-ROOTS]` | ❌ Same behavior as sampling: hangs, then times out |
| Progress notifications | `[CAP-PROGRESS]` | ⚠️ Client-side timeouts observed on tool calls; may be affected by earlier hung reverse-direction requests. Server-side emission verified in Tier 1. |
| Counter View polling | | ❌ View mounts but `readServerResource` fails (see above) |

**Summary:** Quick Work is a solid **base MCP client + MCP Apps host** — every UI-rendering + View↔Host capability we tested worked. It does not implement the reverse-direction protocol requests (sampling/elicitation/roots) or expose MCP resources to the model. The graceful "not supported" fallbacks in our tools worked as designed.

**Recommendations to Quick Work team:**
- Reject unsupported server→client requests immediately (like elicitation) rather than hanging until timeout (like sampling/roots).
- Expose MCP resources to the model (either as attachable context or as a generic read tool).
- Fix `readServerResource` handling from Views for `resource:///` scheme URIs.

### 3b-B. Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-app-sample": {
      "command": "node",
      "args": ["/absolute/path/to/mcp-app-sample/dist/main.js", "--stdio"]
    }
  }
}
```

Restart Claude Desktop.

### Checklist (any host)

| # | Capability | Prompt | Expected |
|---|---|---|---|
| 17 | `[CAP-SAMPLING]` | "Use the `summarize-with-llm` tool on the text 'The quick brown fox jumps over the lazy dog.'" | Host returns a one-sentence summary. If unsupported: tool result says "Sampling not supported by this client". |
| 18 | `[CAP-ELICIT]` | "Use the `ask-user` tool." | A modal asks for name + favorite color. Result reports `action=accept` and the input. If unsupported: tool result explains. |
| 19 | `[CAP-ROOTS]` | "Use the `list-roots` tool." | Tool result lists the roots the client provided, or reports unsupported. |
| 20 | `[CAP-CANCEL]` | "Run `long-task` with 20 steps of 500ms delay, then cancel it." | Task starts, cancellation causes `isError: true` result with `"Cancelled at step N/20"`. |

## Known limitations

- The subscribe → notifications/resources/updated protocol path is exercised
  by `verify.sh` and MCP Inspector. The App SDK's View surface does not
  currently expose `resources/subscribe`, so the counter View polls
  `readServerResource` instead. This means the *server* subscription path is
  supported and demonstrated; the *client-in-a-View* subscription path is
  simulated by polling.
- Cancellation is exercised only at the protocol level in `verify.sh` (the
  server accepts the notification). Interactive cancellation requires a host
  that surfaces cancellation controls; see Tier 3 row 20.
- The dynamic tool registration path emits `tools/list_changed`, but the
  MCP TypeScript SDK does not currently expose a public `unregisterTool` API,
  so re-running `toggle-dynamic-tool` conceptually removes `dynamic-hello`
  but leaves the registered handler active until the process restarts.
- OAuth is not implemented. Add it if you need to exercise the auth surface —
  see the MCP TypeScript SDK's `server/auth` module.
- MCP Apps CSP declaration is a `_meta` field on the UI resource; whether the
  host honors it depends on the host implementation.
