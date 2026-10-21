# Butcher Commander tunnel — verified deployment state

Verified 2026-10-19 on the Butcher host. This is a **point-in-time record**,
not a continuous health guarantee and not proof of ChatGPT plugin registration.

## Sources of truth

- `mcc0nnell/windanvil-blade` — signed native authority, six dynamically
  admitted Celix capabilities, tracked boot launcher, cron template,
  idempotent cron installer.
- `mcc0nnell/talkpipe-mcp` — Commander MCP facade, eight tools,
  bounded workflows, private Secure MCP Tunnel launcher, profile template,
  credential installer, test suite, drift auditor.

## Local verification performed

1. `python3 scripts/audit-tunnel-deployment.py` — PASS. The installed profile
   is owner-only `0600`, references the restricted runtime key as a local
   `file:` secret and launches the Blade-gated Commander MCP stdio script.
   The credential contents were **not** copied or read into this repo.
2. `./scripts/private-tunnel.sh preflight` — PASS on the existing Blade
   socket. Eight tools and six signed capabilities were discovered, with
   five nonmutating MCP calls successful.
3. `python -m unittest discover -s tests` — 33 tests passed.
4. In the Blade repository,
   `tools/dev/manage-butcher-cron.sh check` — PASS. It verified the installed
   boot launcher matches GitHub and preserved Desktop Commander's cron job.
5. `./scripts/private-tunnel.sh doctor` — exited successfully after
   operator provisioning of a restricted runtime key on Butcher.
6. `./scripts/private-tunnel.sh run` — the official outbound tunnel client
   started and fetched the expected OpenAI Platform tunnel metadata.
   A local stdio Commander MCP child started. The private health and
   readiness handlers both returned HTTP 200.

## Security and remaining verification

- The real tunnel ID, the complete local YAML profile, runtime API keys,
  development signing key, executed-process receipts, and logs remain
  **on Butcher**, not in this Git repository.
- The tunnel's administrative health endpoint binds to `127.0.0.1`.
  No public Blade socket or anonymous Cloudflare MCP bridge was deployed.
- The current tunnel process was launched as a live command session.
  Automatic tunnel restarts after a host reboot have **not** been validated.
  Blade's own cron recovery is independent and already configured.
- The public Cloudflare Worker still has a distinct
  `503 control_plane_not_configured` status; it is not the outbound
  OpenAI Secure MCP Tunnel.
- **Not verified:** adding the tunnel as a custom plugin to the user's
  ChatGPT workspace and calling `commander_health` from that workspace.
  Do not disable the existing Desktop Commander plugin until a native
  ChatGPT tool call succeeds.
- **Not claimed:** full feature parity with Desktop Commander,
  multi-device management, or a production hardware-backed signing root.

## Safe re-verification (from Butcher)

```bash
cd ~/lab/talkpipe-mcp
python3 scripts/audit-tunnel-deployment.py
./scripts/private-tunnel.sh preflight
./scripts/private-tunnel.sh doctor
```

Use `./scripts/private-tunnel.sh run` to start the outbound tunnel if it
is not already running. Avoid starting duplicate tunnel processes.
Do not commit keys, process logs or the local profile to GitHub.

## Update: managed tunnel and cron recovery

The earlier statement that the tunnel was launched only as an interactive
live-command session is superseded by
[`TUNNEL_SUPERVISOR.md`](TUNNEL_SUPERVISOR.md). The tunnel is now supervised
from a detached process, has owner-only log/health files, and has two tracked
cron jobs for boot startup and five-minute dead-process recovery.
A controlled **managed-process stop and restart** passed on Butcher.
This does not prove a real machine reboot or ChatGPT plugin registration.
