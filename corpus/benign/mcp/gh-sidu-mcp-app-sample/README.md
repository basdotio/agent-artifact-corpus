# mcp-app-sample

A kitchen-sink MCP server that exercises as much of the Model Context
Protocol + [MCP Apps (SEP-1865)][mcp-apps] surface as it can, and ships an
automated verification harness so you can see at a glance which capabilities
work in a given host.

This is a **verification exhibit**, not a realistic product — every tool,
resource, and prompt exists to demonstrate one specific protocol feature and
is labelled in `server.ts` with a `[CAP-*]` tag so you can trace behavior to
spec.

## What's demonstrated

Base MCP (spec 2025-11-25):

- Tools with `inputSchema`, `outputSchema`, `structuredContent`, annotations,
  resource-link results
- Resources — static, templated (RFC 6570), binary blob, subscribable
- Prompts with arguments and `completion/complete` autocomplete
- Server-to-client capabilities: sampling, elicitation, roots
- Logging (`logging/setLevel` + `notifications/message`)
- Progress notifications with `progressToken`
- Cancellation via `notifications/cancelled`
- `list_changed` for tools
- Both stdio and Streamable HTTP transports

MCP Apps extension (spec 2026-01-26):

- UI-linked tools via `_meta.ui.resourceUri`
- App-only tools (`_meta.ui.visibility: ["app"]`)
- Preferred display modes (inline, fullscreen, pip)
- View → Host: `callServerTool`, `sendMessage`, `updateModelContext`,
  `openLink`, `readServerResource`, `requestDisplayMode`
- View lifecycle: `ontoolresult`, `ontoolinput`, `ontoolinputpartial`,
  `onteardown`, `onhostcontextchanged`
- Theming via CSS variables from host context
- `_meta.viewUUID` for state persistence
- CSP metadata on UI resources
- Chunked binary read pattern (server-side, App-only tool)

See [`VERIFY.md`](./VERIFY.md) for the full capability matrix.

## Requirements

- **Node.js 22+** — the `@modelcontextprotocol/ext-apps` and vite 7 packages
  require 20.19+/22.12+. If you have `mise` installed, `mise use node@22`
  in this directory. On plain systems, use `nvm use 22`.

## Install and build

```bash
npm install
npm run build
```

This produces:

- `dist/main.js` and `dist/server.js` — the server
- `dist/dashboard.html`, `dist/shader.html`, `dist/counter.html` — the Views,
  bundled by vite into single-file HTML

## Run

```bash
# Streamable HTTP (for basic-host, web clients, MCP Inspector)
npm run serve:http    # listens on http://localhost:3001/mcp

# stdio (for Claude Desktop, MCP Inspector CLI)
npm run serve:stdio
```

## Verify

The `verify.sh` script drives the stdio server with raw JSON-RPC frames and
greps the responses for expected fields and notifications. It has zero
runtime dependencies beyond node + bash + awk + grep.

```bash
./verify.sh
```

Expected output ends with `pass=44 fail=0 total=44` and
`All automated checks passed`.

Client-side capabilities that require a real host (sampling, elicitation,
roots, MCP Apps UI rendering) are checked at the outbound-request level here
and left as manual steps in [`VERIFY.md`](./VERIFY.md).

## Wire into Quick Work

The bundled script edits Quick Work's active profile MCP config (backs up first):

```bash
./install-quickwork.sh           # HTTP transport (recommended for local dev)
./install-quickwork.sh --stdio   # stdio transport (Quick Work spawns the server)
./install-quickwork.sh --remove  # unregister
```

After running, fully restart Quick Work. The server appears as **MCP App Sample**
in the MCP servers panel with 9 model-visible tools. See
[`VERIFY.md`](./VERIFY.md) for the Quick Work capability matrix — MCP Apps
rendering + View↔Host APIs work, but sampling / elicitation / roots are not
supported today.

## Wire into Claude Desktop

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

Then restart Claude Desktop. Run through the Tier 3 checklist in
[`VERIFY.md`](./VERIFY.md).

## Wire into basic-host (MCP Apps reference host)

```bash
git clone https://github.com/modelcontextprotocol/ext-apps.git
cd ext-apps/examples/basic-host
npm install
npm start
# Browser: http://localhost:8080 — point it at http://localhost:3001/mcp
```

Then run through Tier 2 in [`VERIFY.md`](./VERIFY.md).

## Host compatibility findings (2026-07-06)

| Host | Tools + Apps UI | View↔Host APIs | Sampling / Elicit / Roots | Resources to model |
|---|---|---|---|---|
| **verify.sh** (headless) | ✅ | n/a | ✅ (outbound-only) | ✅ |
| **MCP Inspector** | ✅ | n/a | ✅ (outbound-only) | ✅ |
| **basic-host** (ext-apps reference) | ✅ | ✅ | ❌ | n/a (dev tool) |
| **Quick Work** | ✅ | ✅ | ❌ (hangs on sampling/roots, clean reject on elicit) | ❌ |
| **Claude Desktop** | (not yet tested) | | | |

Full per-capability matrix in [`VERIFY.md`](./VERIFY.md).

## Files

```
main.ts                 stdio + HTTP transports
server.ts               all tool/resource/prompt registrations, [CAP-*] tagged
dashboard.html          main UI: metrics dashboard
shader.html             fullscreen shader View (streaming input)
counter.html            picture-in-picture live counter
src/dashboard.ts        View script for dashboard
src/shader.ts           View script for shader (WebGL + IntersectionObserver)
src/counter.ts          View script for counter (polls readServerResource)
verify.sh               automated capability checks (44 checks)
install-quickwork.sh    register/unregister with Quick Work's active profile
VERIFY.md               full capability matrix + manual checklist
```

## What's intentionally not here

- OAuth 2.1 authentication — see the `server/auth` module in the SDK
- Tasks (SEP-1686 experimental) — separate spec
- MCP-UI (the community React-component variant) — this repo uses the
  official ext-apps SDK
- A real dataset — every tool returns synthetic data

[mcp-apps]: https://modelcontextprotocol.io/extensions/apps/overview
