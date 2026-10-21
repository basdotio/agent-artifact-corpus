# AGENTS.md — AI Assistant Guide for agent365-mcpapp

## Project Overview

This is an **MCP App** (Model Context Protocol) that runs as a Declarative Agent inside Microsoft 365 Copilot Chat. It surfaces Microsoft Agent 365 governance capabilities via Microsoft Graph API with OAuth/OBO authentication, rendering interactive Fluent UI widgets.

## Commands

```bash
npm run build        # TypeScript check + build widgets + compile server
npm run serve        # Start MCP server (requires .env configured)
npm run dev          # Watch mode (widgets + server)
npm run inspector    # Launch MCP Inspector for testing tools
tsc --noEmit         # Type-check only (no emit)
node build-ui.mjs    # Rebuild widgets only
```

## Architecture

- **Entry point:** `main.ts` → Express server on port 3001
- **MCP server:** `server.ts` → registers tools + UI resources via `@modelcontextprotocol/ext-apps`
- **Auth:** `auth.ts` → MSAL OBO token exchange (Copilot token → Graph token)
- **Tools:** `src/tools/` → each file exports a handler function
- **Graph clients:** `src/graph/` → typed fetch wrappers for Graph endpoints
- **Mock data:** `src/mock/` → realistic sample data (50 agents)
- **Widgets:** `src/widgets/` → React + Fluent UI v9 components
- **Widget build:** Vite + `vite-plugin-singlefile` → single HTML files in `dist/ui/`
- **App manifest:** `appPackage/` → Teams manifest, agent config, MCP plugin def

## Key Patterns

### Stateless MCP Server
Each HTTP request creates a fresh `McpServer` instance with the bearer token from that request. No session state is stored.

### Mock vs Live Mode
Controlled by `USE_MOCK_DATA` env var. The `src/graph/client.ts` → `useMockData()` function gates all Graph calls. When mock, tools return data from `src/mock/`.

### Tool + Widget Pairing
Every primary tool has a corresponding widget. The `registerToolWithUI()` helper in `server.ts` pairs a tool name with a `ui://` resource URI pointing to a built HTML file in `dist/ui/`.

### Widget Architecture
Widgets use `useToolData()` from `@modelcontextprotocol/ext-apps` to receive `structuredContent` from the tool response. They render with Fluent UI v9 components and support the `callServerTool()` pattern for action tools (block/unblock/reassign).

### OBO Authentication Flow
1. Copilot sends bearer token scoped to `api://<client-id>/access_as_user`
2. `auth.ts` exchanges it via MSAL OBO for `https://graph.microsoft.com/.default`
3. Graph client uses the exchanged token for API calls

## Coding Conventions

- **TypeScript** throughout (both server and widgets)
- **ES Modules** (`"type": "module"` in package.json)
- **Imports use `.js` extension** (required for ESM with TypeScript)
- **Two tsconfigs:** `tsconfig.json` (client/widgets), `tsconfig.server.json` (server)
- **Types centralized** in `src/types.ts`
- **No classes** — functional patterns, exported handler functions
- **Error handling:** tools return `{ isError: true, content: [...] }` on failure

## Environment Files

| File | Purpose | Committed? |
|------|---------|------------|
| `.env` | Server runtime (port, secrets, mock flag) | No |
| `env/.env.local` | ATK provisioning config (tunnel URL, tenant) | Yes (placeholders) |
| `env/.env.local.user` | ATK secrets (client ID/secret) | No |

## ATK Provisioning

Deployment uses M365 Agents Toolkit CLI (`atk provision --env local`). The lifecycle is defined in `m365agents.yml` — creates Teams app, registers OAuth, builds/validates package, deploys to M365.

**Critical:** Clear `AGENT365_MCP_AUTH_ID` in `env/.env.local` before re-provisioning if OAuth needs to be re-registered (e.g., after changing client ID or tunnel URL).

## Graph API Endpoints (Beta)

- `/copilot/admin/catalog/packages` — agent registry
- `/identityProtection/riskyServicePrincipals` — risk signals
- `/users` — user search
- `/copilot/agentRegistrations/{id}` — agent ownership

## Adding a New Tool

1. Create handler in `src/tools/new-tool.ts`
2. Create widget in `src/widgets/new-tool/` (React + Fluent UI)
3. Add HTML entry in `ui/new-tool.html`
4. Register in `server.ts` with `registerToolWithUI()`
5. Add to `appPackage/agent365-plugin.json` (functions + mcp_tool_description)
6. Add to `appPackage/instruction.txt`
7. Rebuild: `npm run build`
8. Re-provision: `atk provision --env local`
