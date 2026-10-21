# Private WindAnvil Commander ChatGPT plugin

This repository is the **source of truth** for the private plugin's source
manifest and skill. A private ChatGPT plugin was created from this package
on October 19, 2026. It connects to the existing outbound OpenAI
Secure MCP Tunnel using the **tunnel identifier**, not any runtime API key.

## Source layout

- `plugin/windanvil-commander/plugin.json` — portable Agent Plugins manifest.
- `plugin/windanvil-commander/mcp.template.json` — connection declaration,
  with the tunnel ID intentionally replaced by a placeholder.
- `plugin/windanvil-commander/skills/commander-ops/SKILL.md` — signed
  authority boundaries and safe-use behavior.
- `scripts/package-commander-plugin.py` — deterministic ZIP packer which
  validates the tunnel ID and never reads the runtime key or private profile.
- `tests/test_private_plugin_package.py` — bundle structure, validation,
  determinism and no-secret checks.

## Rebuild the package

```bash
cd ~/lab/talkpipe-mcp
export CONTROL_PLANE_TUNNEL_ID='tunnel_FROM_YOUR_PLATFORM'
python3 scripts/package-commander-plugin.py
unzip -l dist/windanvil-commander-private.zip
```

The packer requires a `tunnel_` ID with exactly 32 lowercase letters or
digits. It writes only three files to a private `0600` ZIP: `plugin.json`,
`mcp.json`, and the Commander skill. No credentials, signing keys, or
host logs appear in the archive. The actual ID is inserted only into
the generated plugin archive, **not** the checked-in template.

The portable `mcp.json` uses:
- `type: streamable-http`
- `extensions.com.openai.tunnelId` with the actual verified tunnel ID
- **no public MCP URL**, no API key, and no untrusted auth proxy.

The published package is a **private user-scoped plugin**, not a public
marketplace listing. Keep the source and authenticated server lifecycle
separate: packaging does not start Blade or provision an OpenAI tunnel.

## Cutover validation

1. Check that Butcher's Blade and tunnel are healthy:
   `./scripts/supervise-commander-tunnel.py check` and
   `./scripts/private-tunnel.sh preflight`.
2. Open the private plugin inside ChatGPT and review its connection.
3. When approved, call `commander_health` and `commander_status` from
   **ChatGPT's native plugin tool surface**, not through Desktop Commander.
4. Confirm all eight tool names appear and compare signed capabilities,
   read-only behavior, and fail-closed denials. Then test separately
   authorized mutation operations, if needed.
5. Only consider retiring Desktop Commander after multi-device,
   interactive process/session and file-operation parity are met.

**Important:** A successful private plugin creation, good tool manifest,
or healthy outbound tunnel does **not** prove that its tools have loaded
in this specific conversation or that a native tool call succeeded.
Preserve Desktop Commander until that evidence exists.
