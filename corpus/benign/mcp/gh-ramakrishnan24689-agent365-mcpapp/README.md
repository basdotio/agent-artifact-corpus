# Agent 365 — MCP App for Microsoft 365 Copilot

> **The first authenticated MCP App sample** — calls Microsoft Graph API via the On-Behalf-Of (OBO) flow and renders interactive Fluent UI widgets inside M365 Copilot Chat.
>
> ⚠️ **This is a reference implementation / experiment** — intended to demonstrate patterns and best practices for building authenticated MCP Apps with rich UI. Not intended for production use as-is.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

<p align="center">
  <img src="media/Agent365-MCPApps.gif" alt="Agent 365 MCP App demo" width="800" />
</p>

Surface the full **Microsoft Agent 365** governance experience inside M365 Copilot Chat: browse the agent registry, visualize the agent landscape, monitor risky agents, and take admin actions — all through natural language with rich interactive widgets.

---

## What This Agent Can Do

### Rich UI Tools (render interactive widgets in chat)

| Tool | Widget | Description |
|------|--------|-------------|
| `show_agent_registry` | Agent Registry | Full inventory of all AI agents with search, filters, and detail drawer |
| `show_agent_map` | Agent Map | Circle-packing bubble visualization grouped by publisher type |
| `show_risky_agents` | Risky Agents | Agents with active identity protection risk signals |

### Admin Action Tools (callable from widgets)

| Tool | Description |
|------|-------------|
| `block_agent` | Block a compromised agent, preventing organization-wide use |
| `unblock_agent` | Restore a previously blocked agent to active status |
| `reassign_agent` | Transfer ownership of an agent to a different user |
| `search_users` | Search organization directory to find new agent owners |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     M365 Copilot Chat                            │
│                                                                  │
│  User: "Show me the agent registry"                              │
│                                                                  │
│  ┌─────────────────────┐                                         │
│  │ Declarative Agent    │  (declarativeAgent.json)                │
│  │ "Agent 365"          │                                         │
│  └────────┬────────────┘                                         │
│           │ invokes tool via MCP plugin                          │
│  ┌────────▼────────────┐                                         │
│  │ MCP Plugin           │  (agent365-plugin.json)                 │
│  │ OAuthPluginVault     │  → triggers OAuth sign-in (first use)  │
│  └────────┬────────────┘                                         │
└───────────┼──────────────────────────────────────────────────────┘
            │ HTTPS + Bearer Token
            │ (via devtunnel in dev)
┌───────────▼──────────────────────────────────────────────────────┐
│  MCP Server (Express + StreamableHTTP)         localhost:3001    │
│                                                                  │
│  1. Extract Bearer token from Authorization header               │
│  2. OBO exchange → Graph token (via MSAL)                        │
│  3. Call Graph API (beta endpoints)                              │
│  4. Return structuredContent + text                              │
│  5. Copilot renders widget from registered UI resource           │
└──────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────┐     ┌──────────────────────────────────────┐
│  Entra ID (Azure AD)│     │  Microsoft Graph API (beta)           │
│  OBO Token Exchange │────▶│  /copilot/admin/catalog/packages      │
│  MSAL Node          │     │  /identityProtection/riskyServiceP..  │
└─────────────────────┘     │  /users                               │
                            └──────────────────────────────────────┘
```

---

## What Makes This Unique

- **Full OAuth + OBO authentication** — demonstrates the complete token exchange flow from Copilot → your app → Microsoft Graph
- **Real Microsoft Graph API calls** — delegated user-context calls, not mock data
- **Interactive admin actions** — block/unblock/reassign agents directly from widgets
- **Mock data fallback** — toggle `USE_MOCK_DATA=true` for demos without Graph access
- **Production-ready patterns** — error handling, caching, accessibility, keyboard navigation

---

## Prerequisites

- [Node.js](https://nodejs.org/) 18+
- [Dev Tunnels CLI](https://learn.microsoft.com/azure/developer/dev-tunnels/get-started) (`devtunnel`)
- M365 tenant with **Copilot Chat** access (M365 E5 or M365 Copilot license)
- **Global Admin** or **Privileged Role Admin** to grant API consent
- Test user with **Global Reader** / **Security Reader** / **Copilot Admin** role

> 💡 ATK CLI is not installed globally — the provisioning command uses `npx` to download it automatically.

---

## Setup Guide

---

### Step 1 — Clone & Install

```bash
git clone https://github.com/Ramakrishnan24689/agent365-mcpapp.git
cd agent365-mcpapp
npm install
```

---

### Step 2 — Entra ID App Registration

Open **[Azure Portal → Entra ID → App registrations → + New registration](https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/RegisteredApps)**.

#### 2.1 — Register

| Field | Value |
|-------|-------|
| Name | `Agent365-MCPApp` |
| Supported account types | Single tenant |
| Redirect URI — Platform | **Web** |
| Redirect URI — URL | `https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect` |

Click **Register**. Note down **Application (client) ID** and **Directory (tenant) ID** from the Overview page.

#### 2.2 — API Permissions

Go to **API permissions → + Add a permission → Microsoft Graph → Delegated permissions**.

Add these 5 permissions:

| Permission | Admin Consent | Purpose |
|------------|:------------:|---------|
| `User.Read` | No | Sign-in |
| `User.Read.All` | Yes | User search for reassignment |
| `CopilotPackages.Read.All` | Yes | Read agent catalog |
| `CopilotPackages.ReadWrite.All` | Yes | Block/unblock/reassign agents |
| `IdentityRiskyServicePrincipal.Read.All` | Yes | Risky agent signals |

Then click **✓ Grant admin consent for \<your-tenant\>**. All 5 should show green ✅.

> 💡 Search "CopilotPackages" in the permission picker to find them.

#### 2.3 — Expose an API

Go to **Expose an API**:

1. Click **Add** next to Application ID URI → accept default `api://<your-client-id>` → **Save**
2. Click **+ Add a scope**:
   - Scope name: `access_as_user`
   - Who can consent: **Admins and users**
   - Fill display name/description fields → **Add scope**
3. Click **+ Add a client application**:
   - Client ID: `ab3be6b7-baf2-4ad0-ae4c-e0209abb4820` (this is M365 Copilot)
   - Check `access_as_user` → **Add application**

#### 2.4 — Client Secret

Go to **Certificates & secrets → + New client secret** → Add → **copy the Value immediately** (shown only once).

#### 2.5 — Set Token Version to v2 ⚠️

Go to **Manifest** tab → find `"accessTokenAcceptedVersion"` → change `null` to `2` → **Save**.

> Without this, OBO fails with `AADSTS50013`. This is the most common setup mistake.

---

### Step 3 — Configure Environment

```bash
cp .env.sample .env
cp env/.env.local.user.sample env/.env.local.user
```

**`.env`** (server runtime):
```env
PORT=3001
USE_MOCK_DATA=false
ENTRA_CLIENT_ID=<your-client-id>
ENTRA_CLIENT_SECRET=<your-client-secret>
ENTRA_TENANT_ID=<your-tenant-id>
```

**`env/.env.local.user`** (ATK provisioning — same values):
```env
AGENT365_MCP_CLIENT_ID=<your-client-id>
AGENT365_MCP_CLIENT_SECRET=<your-client-secret>
```

**`env/.env.local`** (update tunnel URL after Step 5):
```env
MCP_SERVER_URL=https://<tunnel-id>-3001.inc1.devtunnels.ms
MCP_SERVER_DOMAIN=<tunnel-id>-3001.inc1.devtunnels.ms
ENTRA_TENANT_ID=<your-tenant-id>
```

---

### Step 4 — Build

```bash
npm run build
```

---

### Step 5 — Start Dev Tunnel

In a separate terminal (keep running):

```bash
devtunnel create agent365-mcp --allow-anonymous
devtunnel port create agent365-mcp --port-number 3001
devtunnel host agent365-mcp
```

Copy the tunnel URL from output and update `env/.env.local` with it.

---

### Step 6 — Start MCP Server

In another terminal (keep running):

```bash
npm run serve
```

---

### Step 7 — Provision to M365 Copilot

```bash
npx -y --package @microsoft/m365agentstoolkit-cli atk provision --env local
```

> **Re-provisioning?** Clear `AGENT365_MCP_AUTH_ID` in `env/.env.local` first if you changed tunnel URL or client ID.

---

### Step 8 — Test

Open the URL from provision output:
```
https://m365.cloud.microsoft/chat/?titleId=<your-title-id>
```

Try: *"Show me the agent registry"* or *"Show the agent map"*

---

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `AADSTS50013` / `AADSTS500011` | Set `accessTokenAcceptedVersion` to `2` in Manifest |
| No sign-in prompt | Clear `AGENT365_MCP_AUTH_ID` → re-provision |
| 403 from Graph | Grant admin consent + assign admin role to test user |
| "We couldn't find this agent" | Re-provision (tunnel URL may have changed) |
| `CopilotPackages` permissions not found | Tenant needs M365 Copilot license |

---

## Project Structure

```
agent365-mcpapp/
├── appPackage/                    # Declarative Agent manifest
│   ├── manifest.json              # Teams app manifest (v1.26)
│   ├── declarativeAgent.json      # Agent config with conversation starters
│   ├── agent365-plugin.json       # MCP plugin — tools, auth, runtime URL
│   ├── instruction.txt            # Agent behavioral instructions
│   └── color.png / outline.png    # App icons
├── env/                           # ATK environment files
│   ├── .env.local                 # Non-secret config (committed)
│   ├── .env.local.user            # Secrets (gitignored)
│   └── .env.local.user.sample     # Template for secrets
├── src/
│   ├── tools/                     # MCP tool handlers
│   │   ├── show-registry.ts       # Agent registry tool
│   │   ├── show-agent-map.ts      # Agent map tool
│   │   ├── show-risky.ts          # Risky agents tool
│   │   ├── block-agent.ts         # Block action
│   │   ├── unblock-agent.ts       # Unblock action
│   │   └── reassign-agent.ts      # Reassign action
│   ├── graph/                     # Microsoft Graph API clients
│   │   ├── client.ts              # Graph fetch abstraction + mock switch
│   │   ├── packages.ts            # /copilot/admin/catalog/packages
│   │   ├── risk.ts                # /identityProtection/riskyServicePrincipals
│   │   └── users.ts               # /users (search)
│   ├── mock/                      # Mock data for demo/testing
│   │   ├── packages.ts            # 50 sample agents
│   │   ├── risk.ts                # Sample risk signals
│   │   └── users.ts               # Sample users
│   ├── widgets/                   # React + Fluent UI widget source
│   │   ├── agent-registry/        # Registry table with filters & detail drawer
│   │   ├── agent-map/             # D3 circle-packing visualization
│   │   ├── risky-agents/          # Risk signal cards
│   │   └── shared/                # Theme, providers, shared components
│   └── types.ts                   # Shared TypeScript types
├── ui/                            # Vite HTML entry points for widgets
├── dist/ui/                       # Built single-file HTML widgets (generated)
├── auth.ts                        # MSAL OBO token exchange
├── server.ts                      # MCP server — tool + resource registration
├── main.ts                        # Express entry point
├── build-ui.mjs                   # Widget build script (Vite)
├── m365agents.yml                 # ATK provisioning lifecycle
├── .env.sample                    # Server env template
├── package.json
├── tsconfig.json                  # Client TypeScript config
├── tsconfig.server.json           # Server TypeScript config
└── vite.config.ts                 # Vite config for widget builds
```

---

## Authentication Deep-Dive

### OBO Flow Summary

```
User → Copilot → [token: api://<client-id>/access_as_user] → MCP Server → [MSAL OBO] → Graph token → Graph API
```

Copilot obtains a token scoped to *your app* — it cannot call Graph directly. Your server exchanges it via OBO for a Graph-scoped token representing the same user.

### The `.default` Scope

The server requests `https://graph.microsoft.com/.default` (see [`auth.ts`](auth.ts)). This means permissions are controlled entirely by the **app registration's configured API permissions** — not by per-call scope strings. Add/remove permissions in Entra, grant admin consent, and the OBO token automatically reflects the change.

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `ENTRA_CLIENT_ID` | App identity for MSAL OBO exchange |
| `ENTRA_CLIENT_SECRET` | Proves app identity to Entra ID |
| `ENTRA_TENANT_ID` | Directs auth to your tenant |
| `AGENT365_MCP_CLIENT_ID` | Same as above — used by ATK provisioning |
| `AGENT365_MCP_AUTH_ID` | OAuth registration ID (created by ATK — clear to re-register) |

> `ENTRA_CLIENT_ID` and `AGENT365_MCP_CLIENT_ID` are the same app. Two vars exist because ATK and MSAL consume them independently.

---

## Mock Data Mode

Set `USE_MOCK_DATA=true` in `.env` to run without Graph API access. The server will return realistic sample data (50 agents, risk signals, users) — perfect for UI development or demos.

---

## Widget Lifecycle in Copilot

When Copilot renders an MCP App widget, it mounts the widget iframe in **multiple render slots** against a single `tools/call` response. This means your widget's `ontoolresult` callback (see [`McpAppProvider.tsx`](src/widgets/shared/McpAppProvider.tsx)) fires independently in each iframe instance. Widgets must be idempotent — they receive the same `structuredContent` payload each time and should render identically regardless of which slot they occupy. If you see your widget "mount 4 times" during debugging, this is expected behavior, not a bug. Action tools invoked via `callServerTool()` from any slot will trigger a fresh `tools/call` to the server.

---

## Development

```bash
# Start in dev mode (watch server + widgets)
npm run dev

# Build widgets only
node build-ui.mjs

# Inspect MCP server with MCP Inspector
npm run inspector

# Type-check without build
tsc --noEmit
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| **AADSTS500011** — resource principal not found | Wrong client ID in `env/.env.local.user` | Ensure `AGENT365_MCP_CLIENT_ID` matches your Entra app registration |
| **No sign-in prompt** in Copilot | Stale OAuth registration | Clear `AGENT365_MCP_AUTH_ID` in `env/.env.local` and re-provision |
| **Widget not rendering** | Tool returns error or no `structuredContent` | Check server logs for Graph API errors |
| **"We couldn't find this agent"** | Stale M365 title ID | Re-provision to get a fresh `M365_TITLE_ID` |
| **Auth token MISSING on server** | Copilot not sending bearer token | Verify OAuth is registered correctly (re-provision with empty AUTH_ID) |

---

## Graph API Endpoints Used

| Endpoint | Permission | Purpose |
|----------|-----------|---------|
| `GET /beta/copilot/admin/catalog/packages` | `CopilotPackages.Read.All` | List all registered agents |
| `GET /beta/copilot/admin/catalog/packages/{id}` | `CopilotPackages.Read.All` | Get agent detail (instructions, capabilities) |
| `POST /beta/copilot/admin/catalog/packages/{id}/block` | `CopilotPackages.ReadWrite.All` | Block an agent |
| `POST /beta/copilot/admin/catalog/packages/{id}/unblock` | `CopilotPackages.ReadWrite.All` | Unblock an agent |
| `PATCH /beta/copilot/admin/catalog/packages/{id}` | `CopilotPackages.ReadWrite.All` | Reassign agent ownership |
| `GET /beta/identityProtection/riskyServicePrincipals` | `IdentityRiskyServicePrincipal.Read.All` | Risk signals for service principals |
| `GET /v1.0/users` | `User.Read.All` | Search users for reassignment |

---

## Deploying to Azure (Production)

For production, replace the dev tunnel with an Azure-hosted endpoint:

| Component | Recommended Service | Notes |
|-----------|-------------------|-------|
| MCP Server | **Azure Container Apps** or App Service | Scales to zero, built-in HTTPS |
| Secrets | **Azure Key Vault** | Referenced via App Settings |
| Identity | **Managed Identity** | No credentials needed to access Key Vault |

**Steps:**
1. Deploy the Express server to Container Apps (or App Service)
2. Store `ENTRA_CLIENT_SECRET` in Key Vault; reference it via `@Microsoft.KeyVault(SecretUri=...)`
3. Set remaining env vars (`ENTRA_CLIENT_ID`, `ENTRA_TENANT_ID`, `PORT`) as App Settings
4. Update `MCP_SERVER_URL` / `MCP_SERVER_DOMAIN` in `env/.env.local` to the Azure URL
5. Re-provision with ATK: `atk provision --env local`

No code changes required — the server reads `process.env` identically whether values come from `.env` or Azure App Settings.

---

## Related Resources

- [MCP Apps Specification](https://modelcontextprotocol.github.io/ext-apps/api/documents/Overview.html)
- [M365 Agents Toolkit](https://aka.ms/teams-toolkit)
- [Declarative Agents Documentation](https://learn.microsoft.com/microsoft-365-copilot/extensibility/overview-declarative-agent)
- [Microsoft Graph API](https://learn.microsoft.com/graph/overview)
- [MSAL Node — On-Behalf-Of Flow](https://learn.microsoft.com/entra/msal/node/how-to/on-behalf-of)

---

## License

[MIT](LICENSE)
