# WindAnvil Commander — web/mobile access migration

**State (2026-10-19):** Desktop-only packaging identified; live signed Blade and outbound Secure MCP Tunnel verified locally on Butcher. **No ChatGPT web or iOS tool invocation verified. No replacement connection deployed.**

## Observed root cause

The private `windanvil-commander` v0.1.0 plugin bundle declares the tunnel in both `mcp.json` and `.mcp.json`, and references `.mcp.json` in its compatibility manifest. ChatGPT can mark imported packages with bundled MCP servers **Desktop only**, even if they use remote Streamable HTTP. This is an import-surface classification, not a Blade defect.

See:
- https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github
- https://help.openai.com/en/articles/20001256-plugins-in-chatgpt

**Do not delete or overwrite the MCP files in the installed plugin just to remove the badge:** absent an eligible replacement app binding, that would remove the tool connection while retaining the same listing.

## Actual platform constraints

| Path | Capability | Constraint |
| --- | --- | --- |
| Current personal plugin with bundled `mcp.json` / `.mcp.json` | Existing desktop-only listing | Does not make the Blade tools available to ChatGPT web or iOS |
| ChatGPT web → Plugins → + → Add custom MCP server → Tunnel | Correct private web MCP connection route; no public Blade ingress | Current documentation lists full custom MCP connections on Business and Enterprise/Edu, subject to admin and Platform organization permissions; **do not assume a Plus personal account can create one** |
| Custom MCP on ChatGPT mobile | **Do not promise it** | OpenAI Help Center FAQ states “Can I connect custom MCP servers on mobile? No - web only.” It is not proof of an iOS invocation path |
| ChatGPT Sites-hosted MCP tools | A potential plugin route for Plus/Pro; can publish from Work or Codex | Needs a separately built/published Site, required app access, and an authenticated backend path to Blade. Site-to-private-service tunnels have workspace rollout restrictions. iOS invocation requires a real test; a Site is not itself a Blade connection |
| Public remote MCP endpoint | Possible alternative to private Tunnel | Would require a separately deployed authenticated Streamable HTTP MCP server, authorization at every tool, audit, rate limits, and protection from exposing the private Blade socket. Not implemented |

Primary documentation:
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://help.openai.com/en/articles/20001547-hosting-a-plugin-with-chatgpt-sites
- https://help.openai.com/en/articles/20001339-creating-and-using-chatgpt-sites

## Current verified Butcher status

Read-only checks performed from the authorized online Butcher device on 2026-10-19:
- `python3 scripts/audit-tunnel-deployment.py`: **PASS**; owner-protected local configuration and file-referenced secret; **explicitly not** remote ChatGPT verification.
- `./scripts/private-tunnel.sh preflight`: **PASS**; eight MCP tools, six signed capabilities, five safe local MCP checks.
- `./scripts/manage-tunnel-cron.py check`: **PASS**; two tracked cron entries, unrelated entries preserved.
- `./scripts/supervise-commander-tunnel.py check`: **healthy**, managed tunnel running; `remote_chatgpt_plugin_verified: false`.
- `./scripts/private-tunnel.sh doctor`: **RESULT ok**; local profile and runtime executable valid.
- The existing repository checkout remains on main. No runtime key, signing key, grant, tool binary, tunnel profile, or existing plugin release was modified.

## Path A: private ChatGPT web connector, only if eligible

1. Confirm that the intended ChatGPT workspace supports **Create plugins with MCPs** and that the associated Platform organization grants **Tunnels Read + Use**. If using a personal Plus workspace without this capability, **stop** rather than repeatedly attempting the UI.
2. Confirm Butcher's managed tunnel is healthy; do not start duplicate clients. Use only the existing outbound tunnel.
3. In eligible ChatGPT web account, go to **Plugins → + → Add custom MCP server**. Choose **Tunnel** under Connection, select the existing operator-approved tunnel, configure any required authentication, acknowledge the warning, then **Create as a plugin**.
4. Discover all eight `commander_*` tools. Invoke `commander_health` and `commander_status` from a fresh ChatGPT **web** conversation and record true Blade-sourced **PASS**. Then exercise supported read-only operations and confirm denials remain **BLOCKED**.
5. Treat iPhone as a distinct, not-yet-supported validation path. Do not claim that removing the desktop badge grants native iOS MCP access. Retain the current plugin until an actual supported replacement is confirmed.

## Path B: Plus-compatible Site experiment (candidate, not connected)

1. In **ChatGPT Work on web** (or desktop Codex), create a private **WindAnvil Commander Diagnostics** Site with *simulated, explicitly labeled* status and no network route to Butcher at first. Have the Site host an MCP tool `commander_demo_health` returning fixed sample status. Publish the Site privately; connect the generated plugin, and verify a call on a supported ChatGPT surface.
2. Separately design an authenticated, read-only **health/status only** service bridge. Require authenticated caller identity, explicit least-privilege policies, request audit, replay protection, fail-closed network behavior, resource limits, and Blade's existing signed admission. Do not tunnel an arbitrary terminal or export API keys into page/client code. Check if Sites-to-private-service tunnels are actually available to the account; if not, do **not** claim connectivity.
3. Expand to actual Blade calls only after authorization and an end-to-end health test. Validate any supported iOS behavior independently.
4. A separate Sites-generated plugin can solve its own listing classification; it does not transparently change the existing `windanvil-commander` plugin's badge or identity.

## Required acceptance gates before deprecating the desktop package

- [x] Existing Blade signed capabilities and local preflight verified.
- [x] Existing outbound tunnel managed/healthy.
- [x] Root cause of imported Desktop only listing identified.
- [ ] Account plan and workspace supports a selected replacement route.
- [ ] Registered app/Site plugin created with eight expected tools (or explicit read-only subset).
- [ ] At least one live ChatGPT-originated Blade health/status call verified.
- [ ] iOS availability confirmed by an actual supported tool invocation, **not** only by a missing badge.
- [ ] Denials, timeouts, approvals, and audit evidence tested without weakening the capability boundary.
- [ ] Rollback and Desktop Commander coexistence verified.

**No public anonymous MCP proxy. No deletion of the working tunnel manifests. No assertion of mobile support before a real end-to-end test.**
