# TalkPipe MCP

An intentionally narrow **local MCP tool adapter** for [mcc0nnell/talkpipe](https://github.com/mcc0nnell/talkpipe). Built to make approved TalkPipe pipelines invocable by MCP clients, including future ChatGPT connections.

**Status (October 2026):** The stdio adapter has been exercised by the official MCP Python SDK client. This is **not yet connected to ChatGPT as a custom plugin**. It is not a network service.

## Setup

Python 3.11+:

```bash
git clone https://github.com/mcc0nnell/talkpipe-mcp.git
cd talkpipe-mcp
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -u talkpipe_mcp.py
```

Installation pins the user's TalkPipe fork to commit `1b40f4c73a27a6ffb72f4715f5768c7cb12f3ffd` and MCP SDK version `1.30.0`. No other model or network provider is required for the three included workflows.

## Tools

| Tool | Description |
| --- | --- |
| `talkpipe_capabilities` | List fixed workflows and per-call limits |
| `talkpipe_run` | Run a selected, bounded TalkPipe Pipe API pipeline |

Approved `talkpipe_run` workflows:

- `normalize`: collapse whitespace within each item.
- `keyword_filter`: normalize then filter items containing `needle` (literal, case-insensitive).
- `text_statistics`: normalize then yield character/word counts and a 160-character preview.

Example MCP tool arguments:

```json
{"workflow":"keyword_filter","items":["  SignPipe  ", "TalkPipe on Butcher", "Lightpanda MCP"],"needle":"pipe"}
```

MCP clients that support local `stdio` servers can configure the command as the **absolute path** to the venv's Python executable and the arguments as `-u` and the **absolute path** to `talkpipe_mcp.py`. See [examples/stdio-config.json](examples/stdio-config.json) and replace paths before use.

## Safety boundaries

Only approved deterministic workflows may run. No arbitrary ChatterLang, Python evaluation, shell subprocesses, web requests, data persistence, or model-provider calls are exposed. Input is bounded to 100 strings, 4096 characters each, 65536 total characters; result output is capped at 50 items. Results are returned to the MCP caller and never intentionally written to storage by this adapter.

**Do not expose this stdio server to the public Internet.** The absence of a network listener does not imply it is safe to wrap in an unauthenticated HTTP gateway. Deploying via Cloudflare requires identity-based access, an authenticated Streamable HTTP MCP endpoint, request authorization, destination/pipeline policy, resource isolation, and operational audit controls. The ChatGPT connection requires user-controlled installation/authorization.

## Scope and next steps

This is a real TalkPipe pipeline adapter, not an LLM or a generalized code runner. Future versions can add *reviewed* named workflows for accessibility testing, browser receipt normalization, or WindAnvil evidence. A ChatGPT-installable remote MCP connector is **not claimed or implemented**.

License: Apache-2.0. See [LICENSE](LICENSE).

## Connect privately to ChatGPT

**Desktop-only compatibility and web/mobile research:** [See the verified surface matrix and migration runbook](ops/WEB_MOBILE_ACCESS.md). Bundled `mcp.json` / `.mcp.json` makes the current imported plugin Desktop only. A **Connection → Tunnel** custom MCP connection is a web option only on eligible workspaces; OpenAI does **not** currently document custom MCP connections as mobile-ready. Plus-compatible ChatGPT Sites is another candidate, but requires its own authenticated connection to Blade and a real invocation test. Preserve the working plugin until a replacement passes.

The preferred deployment for the private Blade-gated Commander MCP is OpenAI's
**Secure MCP Tunnel**: no public Cloudflare URL, firewall opening, or inbound
HTTP listener is required. The tunnel client calls the signed-Blade-gated Commander MCP server over local
stdio and polls the OpenAI control plane via outbound HTTPS.

### On Butcher

The supported `tunnel-client` release is installed at
`~/.local/bin/tunnel-client` and the TalkPipe runtime is at
`~/lab/talkpipe-runtime/.venv/bin/python`. Run the adapter tests first:

```bash
cd ~/lab/talkpipe-mcp
~/lab/talkpipe-runtime/.venv/bin/python -m unittest discover -s tests -v
```

In [OpenAI Platform tunnel settings](https://platform.openai.com/settings/organization/tunnels),
create a tunnel and associate it with the ChatGPT workspace you will use.
It must be usable by a runtime API key with the **Tunnels Read + Use**
permission. Do not use an admin key as the long-lived runtime key.

In a shell on Butcher, obtain the exact tunnel identifier and configure:

```bash
export CONTROL_PLANE_TUNNEL_ID='tunnel_REPLACE_WITH_YOUR_ID'
./scripts/private-tunnel.sh configure
```

The private profile is saved in `~/.config/tunnel-client/`, mode `0600`,
and contains a key **reference**, not a credential. The script refuses
missing or invalid identifiers. For security, **do not put secrets in a command
line or in Git**. Provision a Restricted **Tunnels Read + Use** key
interactively on Butcher (not through ChatGPT):

```bash
./scripts/install-tunnel-runtime-key.sh
```

The prompt hides your input and writes a private `0600` key file at
`~/.config/tunnel-client/windanvil-runtime-key`. The tunnel profile
references that file without embedding the key.

```bash
./scripts/private-tunnel.sh doctor
./scripts/private-tunnel.sh run
```

Keep the `run` process alive while using Commander in ChatGPT. Its health
admin UI is loopback-only and the tunnel is outbound-only.

### In ChatGPT (web)

Open [Plugins](https://chatgpt.com/plugins), select **+ → Add custom MCP
server**, enter the name `WindAnvil Commander`, select **Tunnel**, choose the
associated tunnel or enter its ID, and review authentication and the
risk warning. Select **Create as a plugin** only after inspecting the
discovered eight `commander_*` tools. Review write/execute permissions
for `commander_talkpipe_run` and `commander_file_create`.

This user-initiated connection requires the relevant ChatGPT workspace
permissions and Platform tunnel permissions. A functioning local adapter
or stored tunnel profile does not mean ChatGPT is connected. Test by invoking
`commander_health` and `commander_status` from ChatGPT; only that confirms the end-to-end path.

**Current operational boundary:** Until those account-side tunnel and
ChatGPT steps are completed and a real tool call succeeds, this repository
is *ready for private connection*, not *connected*. The Commander adapter does not
expose arbitrary ChatterLang or Python.

Cloudflare Workers/Tunnel can provide a public alternative, but that would
require a separate authenticated MCP transport and identity configuration.
Do not publish the existing unprotected stdio tool behind an anonymous HTTP
proxy.

## WindAnvil Commander gateway (Blade-gated)

`windanvil_commander_mcp.py` is the safer replacement entrypoint for the
private tunnel. It exposes **three tools** over local MCP stdio:

- `commander_health`: query the Blade Unix socket health
- `commander_status`: inspect admitted capabilities and grants
- `commander_talkpipe_run`: send a pinned TalkPipe pipeline envelope via
  `EXEC` + tab + `talkpipe.run`, never directly invoke Python or ChatterLang

All three require `WINDANVIL_LOCAL_SOCKET` (default
`~/runtime/blade/blade.sock`) to exist, be Unix-domain, have permissions
`0600`, and be owned by the current UID. The client also checks the peer
UID and same socket inode after connect. There is **no alternate execution
path** if Blade refuses a request. `commander_talkpipe_run` accepts only
a constrained pipeline name and lowercase 64-character SHA-256; the native
Blade runtime retains signature verification, admission, revocation, pipeline
digest enforcement, and evidence receipt authority. The MCP facade cannot
issue or renew grants.

The protocol is the repository's `tools/blade-local.py` wire format from
[mcc0nnell/windanvil-blade](https://github.com/mcc0nnell/windanvil-blade).

**Observed limitation on Butcher:** the native `blade.sock` is missing;
Commander tool calls therefore return `BLOCKED`. The unit and MCP integration
tests use a synthetic local socket to check the wire/protocol boundary, **not**
to claim a live signed-grant execution. This does not yet replace the existing
Desktop Commander connection, and `commander.windanvil.com/mcp` currently
returns HTTP 503 (`control_plane_not_configured`). No remote endpoint was
activated by this work.

Run tests with `python -m unittest discover -s tests -v`. The private tunnel
launcher now points to this Blade-gated entrypoint instead of direct TalkPipe.
The original `talkpipe_mcp.py` remains a local-only development interface
for the existing bounded text workflows and must not be the production remote
execution target.

## Native host-inspection parity slice

WindAnvil Blade now has a separate signed `host.inspect` capability in
[mcc0nnell/windanvil-blade](https://github.com/mcc0nnell/windanvil-blade).
`commander_host_inspect` exposes its **three** read-only operations:

- `system.info`: OS release, architecture, numeric UID (empty path)
- `dir.list`: capped directory listing relative to an administrator-pinned root
- `file.read`: capped 16 KiB regular text-file reads, under the same root
- `file.find`: bounded recursive filename search under that root
- `content.search`: bounded literal content search returning path and line numbers only

Example tool arguments:

```json
{"operation":"file.read","path":"inside.txt"}
```

The client only sends `EXEC host.inspect` to the local Blade socket; both
client-side path validation and native `openat` + `O_NOFOLLOW` checks apply.
Hidden paths, traversal and symlinks are denied. The native Celix bundle must
already be admitted by a valid Ed25519-signed manifest for the exact bundle
SHA-256. There is **no** file-read fallback to shell or direct Python.

**Proof scope:** a local development Blade authority on Butcher admitted the
bundle, repeated directory listings returned identical results, file reads
worked, and symlink/traversal attempts were blocked. Native receipts record
the decisions. The cloud endpoint at `commander.windanvil.com/mcp` remains
unconnected to Blade until the secure control plane is configured; this
proof does **not** establish ChatGPT plugin connectivity or device parity.

Desktop Commander should remain active until host/file/process/shell/session
and remote-device operations are all implemented behind signed capabilities,
authenticated end to end, and verified from ChatGPT.

## Independently admitted process inspection

`commander_process_list` invokes precisely
`EXEC process.inspect` with operation `process.list` on the same protected
Blade Unix socket. It is a **separate signed native Celix capability**,
not an expansion of `host.inspect` permissions. There are no PID, command
line or signal arguments. The native capability returns at most 100 PIDs
and 64-character sanitized process names for processes owned by Blade's
UID. Other users' processes, environment variables, shell access and
process termination are not exposed.

The MCP tool declares read-only, non-destructive annotations. When the
process inspection grant is unavailable or the Blade socket fails, the
result is `BLOCKED` with no direct-process Python fallback. Verified with
the official MCP Python SDK and native signed Blade runtime on Butcher;
22 automated adapter tests passed. This is local proof only and does
not imply that ChatGPT has connected to the public Commander endpoint.

## Signed read-only Git inspection

`commander_git_inspect` invokes the separate dynamically admitted
`git.inspect` Blade capability. It accepts only `git.status` or
`git.history`; the MCP caller cannot provide a repository path, Git
arguments, arbitrary commands, Git config or executable hooks.

The native libgit2 capability pins a same-UID worktree and returns
sanitized branch/HEAD and status counts or the five most recent commit
hashes/timestamps. The implementation intentionally excludes raw diffs,
Git commit messages, secrets, checkout, fetch, push, and commit commands.
Only the signed bundle can authorize it. When the signed grant is absent,
the tool returns `BLOCKED`, never a fallback Git shell.

Verified with an official MCP SDK client and a real signed Blade bundle:
status/history PASS and `git.push` BLOCKED; 23 adapter tests passed. The
host's malicious test hook and configured external diff did not execute.
See the separate WindAnvil Blade repository's
`docs/git-inspect-capability.md`. This is a local development proof, not
registration as a native ChatGPT plugin or Desktop Commander parity.

## Signed atomic create-only file writes

`commander_file_create` accepts only a safe relative path and up to 2048
UTF-8 bytes. It invokes the separately signed `file.create` Blade
capability through the default private socket. The native bundle uses a
dedicated operator-pinned private directory and publishes data through an
exclusive temporary file and atomic hard link. It **never overwrites**.

The tool has write-capability MCP annotations and requires appropriate
caller approval. No shell, Python, or unchecked remote-HTTP fallback is
available. An unavailable or refused Blade grant returns `BLOCKED`.

Verified on Butcher with an official MCP client: new create PASS, duplicate
BLOCKED, traversal BLOCKED; mode `0600` and contents verified. The adapter
suite passed 24 tests. This is a development grant, not an active public
ChatGPT connection or permission to edit arbitrary system files.

## Blade-gated fixed process probes

`commander_process_probe` accepts only `kernel`, `uptime` or `disk`,
and invokes a separate signed native `process.probe` Celix capability.
The Blade runtime runs fixed, root-owned absolute executables through
`posix_spawn` with a minimal environment, three-second deadline, no
shell, and a 4096-byte output cap. There are no user-supplied
executables, arguments, working directories or process IDs.

A missing or denied grant returns `BLOCKED`. On Butcher an official MCP
SDK client verified all three fixed probes and rejection of an attempted
`sh` probe. The adapter suite passed 25 tests. This is not a
general-purpose command runner, interactive shell or ChatGPT cloud
plugin; service persistence and production identity remain separate.

## Verified local-to-ChatGPT connection boundary (October 2026)

The preferred private connection is **OpenAI Secure MCP Tunnel**, not a
public Cloudflare proxy to Blade. The host has a supported `tunnel-client`
binary, but requires an **actual** Platform `tunnel_id`, a restricted
runtime key with Tunnels Read + Use permissions, and the
user-controlled ChatGPT plugin connection. A publicly reachable
`commander.windanvil.com/mcp` Worker currently responds with
`503 control_plane_not_configured`; do not bypass this guard.

To check the **eight** actual Commander tools and six development-signed
capabilities before requesting tunnel access:

```bash
cd ~/lab/talkpipe-mcp
./scripts/private-tunnel.sh preflight
```

The preflight makes five real nonmutating MCP calls using official SDK
stdio transport and checks each admitted capability. No remote connection,
token, tunnel, cloud availability or ChatGPT installation is claimed.
The same command must **fail closed** if Blade is unavailable.

After creating a tunnel in Platform settings and associating it with the
intended ChatGPT workspace, set `CONTROL_PLANE_TUNNEL_ID` (do not guess
an ID) and invoke `./scripts/private-tunnel.sh configure`. The generated
mode-0600 profile references a local `file:` secret and contains no key.
Run `./scripts/install-tunnel-runtime-key.sh` interactively on Butcher
to store the restricted runtime key with mode `0600`. Never provide
it in a repo, chat, CLI argument or recorded log. Only then run
`./scripts/private-tunnel.sh doctor` and `./scripts/private-tunnel.sh run`.
In ChatGPT Plugins choose **Add custom MCP server → Tunnel**, select
that same tunnel, review permissions for all eight tools, connect, and
verify at least one benign tool call from the chat. These account-side
actions are not accomplished by configuring a profile.

Cloudflare Wrangler authentication is separate from the OpenAI tunnel.
An expired Wrangler OAuth access token can usually be refreshed with
`wrangler whoami`; a valid Cloudflare account session does **not**
provision the missing Cloudflare Worker control plane or any OpenAI tunnel.

## Deployment-as-code (Butcher)

[ops/DEPLOYMENT.md](ops/DEPLOYMENT.md) is the canonical deployment map:
tracked tunnel profile example, real-profile drift audit, signed Blade MCP
preflight, restricted runtime-key installation and pointers to the Blade
cron/boot recovery scripts. The real tunnel ID and credentials remain
in private host configuration rather than source control.

Run `python3 scripts/audit-tunnel-deployment.py` before tunnel `doctor`.
A successful deployment audit **does not** imply a connected ChatGPT plugin.

## Persistent outbound tunnel (Butcher)

The version-controlled watchdog in
[`ops/TUNNEL_SUPERVISOR.md`](ops/TUNNEL_SUPERVISOR.md) manages the exact
WindAnvil Commander tunnel profile, validates the reviewed tunnel-client
binary and private key-file permissions, checks Blade integrity, and starts
a detached tunnel with private health/log files. A tracked cron installer
preserves Desktop Commander and other existing jobs while adding
`@reboot` and five-minute recovery:

```bash
./scripts/manage-tunnel-cron.py install
./scripts/supervise-commander-tunnel.py check
```

A controlled stop/restart recovery has been exercised on Butcher. **Host
reboot recovery and native ChatGPT plugin connectivity are not yet proven.**

## Private ChatGPT plugin package

See [ops/PLUGIN.md](ops/PLUGIN.md) for the version-controlled private
plugin manifest, Secure MCP Tunnel connection declaration and signed-use
skill. The package generator substitutes the approved tunnel ID into a
locally built ZIP without copying any runtime credential or signed private
key. Private plugin creation is distinct from verified availability of its
tools in the current ChatGPT conversation.
