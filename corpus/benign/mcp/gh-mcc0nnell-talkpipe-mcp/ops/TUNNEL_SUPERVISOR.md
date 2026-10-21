# Butcher Commander Secure MCP Tunnel — crash recovery

This repository contains the complete **host-specific** source for the
WindAnvil Commander outbound tunnel watchdog:

- `scripts/supervise-commander-tunnel.py` — admission/pinning checks and
  start/check lifecycle. Only manages the `windanvil-commander` profile.
- `scripts/manage-tunnel-cron.py` — preserves other user crontab entries;
  adds the two reviewed tunnel jobs from `ops/tunnel-cron.example`.
- `ops/tunnel-cron.example` — `@reboot` startup and every-five-minute
  dead-process recovery; **not** a continuous remote-availability monitor.
- `scripts/audit-tunnel-deployment.py` and `scripts/commander-preflight.py` —
  structural validation and local signed MCP tool checks.

## Install on Butcher

```bash
cd ~/lab/talkpipe-mcp
python3 scripts/audit-tunnel-deployment.py
./scripts/private-tunnel.sh preflight
./scripts/private-tunnel.sh doctor
./scripts/manage-tunnel-cron.py install
./scripts/manage-tunnel-cron.py check
./scripts/supervise-commander-tunnel.py start
./scripts/supervise-commander-tunnel.py check
```

The managed tunnel's launch is independent of the interactive shell, uses
`start_new_session` and redirects stdout/stderr to a private `0600` log.
The health URL is written to a private `0600` file with an unpredictable
loopback-only port. Its health and readiness endpoints must both report
HTTP 200; this checks the **local tunnel client**, not the ChatGPT plugin.

The watchdog locks before starting, refuses a second instance for the same
profile, and checks:

1. the exact SHA-256 of the reviewed official `tunnel-client` binary;
2. the unchanged local YAML profile and separate same-UID `0600` key file;
3. the expected Blade signing/bundle integrity and live Blade health;
4. ownership/permissions of the private runtime state and profile directories;
5. the actual running executable and exact command-line profile identity;
6. a local health/readiness URL restricted to `127.0.0.1`.

`check` is read-only except lock creation. `start` is idempotent: an
existing healthy managed process remains untouched; a legacy command
session is not replaced or duplicated; a missing process is started.
A running but unhealthy managed process requires explicit review instead
of blindly killing a potentially useful connection. If Blade is down at
reboot, `start` fails closed and the scheduled five-minute retry allows
Blade's separate boot recovery to finish first.

The cron installer refuses unknown/duplicate tunnel entries and preserves
all existing jobs, including Desktop Commander and Blade. It makes private
`0600` backups before crontab modification, ensures its cron log is
`0600`, and is safe to run twice without adding duplicate jobs.

## Butcher verification — October 19, 2026

- A legacy long-running tunnel process was left untouched by `start`.
- The existing process was stopped deliberately and replaced by a managed
  launch. Both `/healthz` and `/readyz` passed.
- A **second** managed tunnel stop was performed: `check` returned
  `not-running`, `start` created a new process, and another `check`
  returned `healthy`. Exactly one matching tunnel client was running.
- The managed health URL and log file were mode `0600`.
- The cron installer added exactly two jobs, was idempotent, and retained
  the unrelated Desktop Commander watchdog and Blade cron entries.
- The automated tests reached **40 passing**, including tests for
  symlinked/world-readable health files, remote health URL rejection,
  process-duplication prevention, cron idempotence and unknown-job denial.

**Not yet tested:** recovery across an actual Butcher host reboot,
remote-OpenAI control-plane availability after an outage, and invocation of
the custom Commander tool by this ChatGPT conversation. A healthy local
client does not prove the final workspace/plugin authorization.

## Security and source control

The implementation, cron template, test fixtures, and runbook are
committed to private GitHub. The runtime API key, live profile, tunnel ID,
execution receipts, signed private keys, process logs and health file stay
on Butcher. Neither the watchdog nor the installer copies a credential.

Updating tunnel-client requires re-verifying the release artifact and
updating `EXPECTED_SHA256` in a reviewed change. Never disable digest
verification to bypass a deployment problem. Do not expose the Blade
socket or tunnel admin UI to the public Internet.

Do **not** uninstall Desktop Commander until a real, authenticated
ChatGPT call to the WindAnvil Commander plugin succeeds.
