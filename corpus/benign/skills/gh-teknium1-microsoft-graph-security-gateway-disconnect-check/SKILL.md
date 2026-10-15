---
name: gateway-disconnect-check
description: Verify the MCP Gateway and its backends are fully disconnected and read-only, and switch tenants via settings.yaml. USE WHEN asked to disconnect from the gateway, confirm read-only posture, switch tenant/access profile, check for leftover MCP processes, or before/after a tenant testing session.
metadata:
  category: workflow
  effort: low
---

# gateway-disconnect-check

Confirms `gateway_mcp` (namespace `m365` in `.mcp.json`) and its child backends (entra, intune, exchange, defender, purview) hold no live process or tenant session after a work session, and that no `*_ENABLE_WRITES` flag was left on.

## Why this matters

Each backend spawns a real Graph API session against the tenant (delegated or app-only). An orphan process = a live, unaudited tenant connection. `gateway_mcp/src/backends/proxy.ts` `disconnectBackends()` kills stdio child processes on `SIGINT`/`SIGTERM` (wired in `gateway_mcp/src/index.ts`) — but only if the gateway shuts down cleanly. A crashed or force-killed parent can orphan children.

## Steps

1. **Confirm wiring** — `.mcp.json` at repo root should have exactly one server, `m365`, pointing at `gateway_mcp/src/index.ts` (the gateway loads configuration and spawns backends directly using `settings.yaml` without per-package `--env-file` flags).
   ```bash
   cat .mcp.json
   ```
2. **Check for live processes**:
   ```bash
   ps aux | grep -iE "bun|node.*mcp|entra_id_mcp|intune_mcp|exchange_online_mcp|defender_mcp|purview_mcp" | grep -v grep
   ```
   Empty output = fully disconnected. Any hit = orphan; note the PID.
3. **If orphans found**, kill by PID (not `pkill -f` blind — confirm each PID belongs to this repo's path first):
   ```bash
   kill <pid>
   ```
4. **Re-run step 2** to confirm the process list is clear.
5. **Confirm read-only posture against `settings.yaml`** — the repo-root YAML is the source of truth for tenant/access settings, organized as named `profiles` (one per tenant/customer) with `activeProfile` picking which one is live.
   Check tenant, profile, and write status:
   ```bash
   bun run status
   ```
   To ensure a strict read-only posture, set `enableWrites: false` under the active profile in `settings.yaml`. You can also verify with `bun run doctor`.
   `DEFENDER_ENABLE_WRITES` is **not** a no-op: it registers `block_file_indicator` and `isolate_device` (both `write_critical`) — check it like every other plane. Only `PURVIEW_ENABLE_WRITES` is a reserved no-op (Purview has no write tools).

## Gotchas

- `disconnectBackends()` only kills stdio-connected backends (`conn.proc.kill()`); HTTP-mode backends have no process to kill — they're stateless per-request, so nothing to verify there.
- `ps aux` is authoritative for stdio child processes; there's no socket/port to check since transport is stdio, not HTTP.
- Deferred `mcp__m365__*` tool names appearing in a Claude Code session's tool list does not by itself mean a process is running — verify with `ps aux`, not the tool list.
- A write flag being `true` doesn't just enable write tools — for `entra_id_mcp` it also widens the delegated OAuth scopes requested (`buildDefaultDelegatedScopes` adds `User.ReadWrite.All`, `Group.ReadWrite.All`, `Policy.ReadWrite.ConditionalAccess`). Flipping the flag off requires a fresh sign-in/token to actually drop those scopes — killing the process is not enough on its own.
- Changing a write flag in `settings.yaml` only takes effect on the next process start; if the gateway/backend is still running, restart it after applying.
- `settings.yaml` is gitignored — it holds real `tenantId` values per client/profile, which shouldn't land in git history even in a private repo. `settings.example.yaml` is the tracked template (placeholder tenant ID `00000000-...`, profile named `contoso`); copy it to `settings.yaml` and fill in real tenant IDs. Neither file ever holds `CLIENT_SECRET` — secrets stay in the OS keyring; certificates stay in `~/.mcp-graph/certs`.
- `clientId: wellknown` (Microsoft's public client, no app registration needed) works for all 6 packages in `delegated` mode — the config parser hard-fails if paired with `accessMode: app_only`, rather than silently writing a client ID the process can't actually authenticate with.
- Multi-tenant switch = `bun run profile switch <name>` (or flip `activeProfile` in `settings.yaml`), then reconnect the MCP client.

## Example

```
User: "make sure we're disconnected from the gateway"
→ cat .mcp.json (confirm wiring)
→ ps aux | grep -iE "bun|...mcp" | grep -v grep
→ empty → report clean, no action needed
```
