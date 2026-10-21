# WindAnvil Commander — GitHub deployment contract

Two private GitHub repositories are the maintained engineering source of truth:

- [mcc0nnell/windanvil-blade](https://github.com/mcc0nnell/windanvil-blade): native Celix capabilities, signed admission logic, tests, development boot launcher, and Butcher cron installation template.
- [mcc0nnell/talkpipe-mcp](https://github.com/mcc0nnell/talkpipe-mcp): the Commander stdio MCP server, Python policy adapter, private outbound tunnel launcher, credential installer, preflight, profile example, and deployment audit.

## Reproduce on Butcher

Do not copy the live tunnel YAML into Git. Use the committed
`ops/tunnel-profile.example.yaml` to review the configuration structure, then
generate the real profile with the CLI:

```bash
cd ~/lab/talkpipe-mcp
export CONTROL_PLANE_TUNNEL_ID='tunnel_FROM_PLATFORM'
./scripts/private-tunnel.sh configure
python3 scripts/audit-tunnel-deployment.py
./scripts/private-tunnel.sh preflight
```

The actual tunnel ID is supplied by Platform and remains in Butcher's local
`~/.config/tunnel-client/windanvil-commander.yaml` (mode `0600`).
The profile references a separate credential file and never embeds an API key.
The checked-in example deliberately has placeholder ID, username and paths.

Install the restricted **Tunnels Read + Use** runtime key with
`./scripts/install-tunnel-runtime-key.sh` **in a real interactive terminal**.
Never paste the key into ChatGPT, send it to GitHub, or store it in logs.
Then run `./scripts/private-tunnel.sh doctor`. If doctor succeeds, the
tunnel can be started with `./scripts/private-tunnel.sh run`. A true remote
connection additionally requires the ChatGPT workspace/plugin association
and an actual `commander_health` invocation **from ChatGPT**.

## Operational drift checks

`python3 scripts/audit-tunnel-deployment.py` checks the runtime profile's
secure permissions, loopback-only health endpoint, exact local MCP command,
correct type of tunnel ID and file-based secret reference. It does not
inspect the secret's contents, claim remote connectivity, or validate key
scopes. The included unit tests use synthetic IDs and fake non-secret keys.

`./scripts/private-tunnel.sh preflight` checks the actual local signed Blade
runtime through the official MCP SDK. It verifies the eight tool schemas,
six signed capabilities and five nonmutating tool calls.

In the Blade repo:
`tools/dev/manage-butcher-cron.sh check` verifies the deployed Blade launcher
matches the exact committed script and its two cron entries match
`ops/butcher-cron.example`. `install` adds missing Blade entries without
removing unrelated cron jobs (including Desktop Commander); it fails on
unexpected or duplicate Blade entries.

## Never commit

- OpenAI or Cloudflare API tokens, private keys, signing material or credential
  files
- The live `windanvil-runtime-key` or a fully configured secret-bearing
  environment file
- Receipts or execution logs containing potentially sensitive operations
- Private runtime databases, installed dependencies, cached bundle binaries,
  process state, or the local `.config/tunnel-client` directory

Changes to pinned native bundle hashes require a new authorized signed
manifest. GitHub code review cannot substitute for signed admission.

## Boundaries still outstanding

The Cloudflare Worker at `commander.windanvil.com/mcp` currently has a
separate unconfigured control-plane backend, so the supported connection
path is OpenAI's **outbound-only Secure MCP Tunnel**. Cloudflare's existing
deployed Worker is **not** reproduced by these two repositories, and should
not be represented as version-controlled until its source/config are
recovered, reviewed and published. Do not create an anonymous HTTP bridge.

The Blade development signing authority is not a production trust root,
and this repository split does not yet establish full Desktop Commander
feature parity or an installed ChatGPT custom plugin.
