# grok-lab-bridge

An MCP server that gives AI bots tool access to the machines in a
home lab: run commands, read/write files, list directories, check GPU status,
plus web research, scheduled jobs, a shared memory store, and a deterministic
artifact-review harness. It is built on FastMCP (the `mcp` Python SDK 1.x) and
uvicorn, and runs as a systemd user service. Safety features are a command
denylist, per-command timeouts, an output cap, and an append-only JSONL audit
log.

It was deployed across a 6-machine home lab (3× NVIDIA DGX Spark, 2× Mac,
1× Windows Surface laptop) and driven by Grok bots over MCP.

> Formerly named `grok-mcp-bridge`. The public repo was renamed; config paths
> and the systemd unit now use `grok-lab-bridge`.

## What this is not

- **Not a general-purpose framework.** The machine map, OS dialects, cron
  lines, and unit file reflect one specific lab. You will need to edit
  `MACHINES` in `server.py` and several paths before it does anything useful.
- **Not a sandbox.** The denylist stops accidents, not a determined
  adversary. Anyone holding the bearer token can run arbitrary commands as
  the SSH user on every configured machine. See [Security model](#security-model).
- **Not multi-tenant.** All bots share one bearer token. There is no per-bot
  identity, scoping, or rate limiting.

## Architecture

```
  Grok bots (MCP clients, streamable HTTP)
          │  HTTPS  Authorization: Bearer <token>
          ▼
  ┌──────────────────────────────┐
  │ Tailscale Funnel :8443       │   optional public ingress
  │ (or any reverse proxy)       │   (Host header must match BRIDGE_PUBLIC_HOST)
  └──────────────┬───────────────┘
                 ▼
  ┌──────────────────────────────────────────────────────────┐
  │ bridge host (LOCAL_MACHINE, e.g. spark-2)                │
  │                                                          │
  │  server.py  FastMCP + uvicorn, 127.0.0.1:8000 ONLY       │
  │   ├─ BearerAuth middleware → 401 without token           │
  │   ├─ DNS-rebinding / Host allowlist → 421 on foreign Host│
  │   ├─ denylist · timeout (120s default, 600s max)         │
  │   │  · 1 MB output cap                                   │
  │   ├─ audit.log (JSONL)  memory.db (FTS5)  jobs.db        │
  │   └─ local commands → subprocess                         │
  │                                                          │
  │  job_runner.py   cron */5  → runs due jobs in-process    │
  │  maintenance.py  cron daily, niced → rotate/prune/health │
  └──────────────┬───────────────────────────────────────────┘
                 │ ssh -i bridge_key  (dedicated ed25519 key,
                 │ BatchMode, bridge-only known_hosts)
     ┌───────────┼──────────────┬──────────────┬─────────────┐
     ▼           ▼              ▼              ▼             ▼
  spark-1     spark-3         air            mbp          surface
  (linux)     (linux)       (darwin)       (darwin)      (windows)
```

Fan-out is one-way: the bridge host SSHes *out* to the lab. The server listens
on localhost only, so nothing reaches it except through the local proxy.

## Tools (17)

| Group | Tool | Notes |
|---|---|---|
| Machines | `exec(machine, command, timeout=120)` | Shell command. Denylist enforced, timeout clamped to 1–600 s, output capped at 1 MB. |
| | `read_file(machine, path)` | `cat` / `type` depending on OS. |
| | `write_file(machine, path, content)` | Base64 transport, OS-aware (`base64 -d`, `base64 -D`, PowerShell). Creates parent dirs. |
| | `list_dir(machine, path)` | `ls -la` / `dir`. |
| | `gpu_status(machine)` | `nvidia-smi` CSV on Linux/Windows; `system_profiler` on macOS. |
| Research | `web_search(query, count=5)` | Scrapes DuckDuckGo's HTML endpoint and caches results for 1 h. Detects DDG's bot-challenge page and returns an explicit rate-limit error. Empty results are never cached. |
| | `web_fetch(url, max_chars=20000)` | SSRF guard: http/https only; blocks `localhost`/`.local`/`.internal` and any resolved IP that is not globally routable (includes CGNAT, so Tailscale 100.x is blocked). 30 s timeout, 2 MB cap, strips scripts/styles/nav. |
| Scheduling | `schedule_job(name, run_at_iso, tool, arguments, retries=0)` | Future and ≤ 30 days out. Allowed tools: `exec`, `web_search`, `web_fetch`, `memory_write`, `gpu_status`. Retries 0–5 with 5 min·2^n backoff; exhausted jobs go to `error`. |
| | `list_jobs(limit=20)` · `job_results(job_id)` | |
| Shared memory | `memory_write(bot, namespace, key, value, tags=[], expires_at_iso=None)` | SQLite upsert with an FTS5 index. Optional TTL. Values up to 200 KB. |
| | `memory_read` · `memory_search(query, namespace=None, limit=10)` · `memory_forget` | Search results are FTS5-ranked, with `<<term>>` snippets. |
| Review harness | `submit_for_review(bot, task, artifact_description, acceptance_criteria, file_manifest=[])` | Deterministic PASS/FAIL. Checks existence and SHA-256 per `{machine, path, sha256}`, scans the description and the first 50 KB of each file for credential patterns (reports only the pattern *name*, never the matched value), and checks that total size is 1 B–100 MB. |
| | `review_queue(limit=20)` | Recent reviews for operator triage. |
| Ops | `bridge_status()` | One call returns job counts (incl. overdue/error), runner heartbeat, memory counts, 24 h reviews, cache size, file sizes, service state, and last maintenance anomalies. |

Scheduled jobs deliberately exclude `write_file`, a timer firing file writes
with no human in the loop is a foot-gun. They also exclude `read_file`,
`list_dir`, `memory_forget`, and the review tools.

The review harness is **callable, not enforced**. Bots are instructed to
submit their artifacts, and a human triages `review_queue`. The bridge cannot
force artifacts through review without breaking the plain tool model.

## Install (systemd user service)

On the bridge host, as the unprivileged user that will own the bridge:

```bash
git clone <this-repo> ~/grok-lab-bridge
cd ~/grok-lab-bridge
python3 -m venv venv
venv/bin/pip install -r requirements.txt      # mcp>=1.0,<2  (2.x renamed FastMCP)

# 1. Generate a DEDICATED keypair for the bridge. Never reuse your personal key.
mkdir -p ~/.config/grok-lab-bridge && chmod 700 ~/.config/grok-lab-bridge
ssh-keygen -t ed25519 -N "" -C "grok-lab-bridge@<your-host>" \
  -f ~/.config/grok-lab-bridge/bridge_key

# 2. Authorize the PUBLIC half on every target machine
ssh-copy-id -i ~/.config/grok-lab-bridge/bridge_key.pub user@lab-machine
#    Windows OpenSSH: if the user is an Administrator, sshd reads ONLY
#    C:\ProgramData\ssh\administrators_authorized_keys; append the key there.

# 3. Edit MACHINES / LOCAL_MACHINE at the top of server.py

# 4. Install and start the unit
mkdir -p ~/.config/systemd/user
cp grok-lab-bridge.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now grok-lab-bridge.service
loginctl enable-linger "$USER"                 # survive logout/reboot
```

The bearer token is generated on first start at
`~/.config/grok-lab-bridge/token` (mode 0600). Give it to your MCP client as
`Authorization: Bearer <token>`. To rotate it, delete the file and restart the
service.

Cron entries for the companion scripts:

```cron
*/5 * * * * ~/grok-lab-bridge/venv/bin/python ~/grok-lab-bridge/job_runner.py >> ~/.config/grok-lab-bridge/runner.log 2>&1
17 4 * * * nice -n 10 ~/grok-lab-bridge/venv/bin/python ~/grok-lab-bridge/maintenance.py >> ~/.config/grok-lab-bridge/maintenance.log 2>&1
```

### Exposing it to bots (optional)

The server binds `127.0.0.1:8000`. In the original lab the bots could not join
the tailnet, so it was published through Tailscale Funnel:

```bash
tailscale funnel --bg --https=8443 http://127.0.0.1:8000
# public URL: https://<your-host>.<your-tailnet>.ts.net:8443/mcp
```

Set `BRIDGE_PUBLIC_HOST=<your-host>.<your-tailnet>.ts.net:8443` in the unit
file, or requests arrive with an unrecognized Host header and get HTTP 421.
Set `BRIDGE_PUBLIC_URL` in the maintenance cron environment to enable its
"expects 401 without token" reachability probe. Funnel makes the endpoint
public by design, which leaves the bearer token as the only gate. If your
clients can join the tailnet, prefer `tailscale serve`.

## Configuration

| What | Where |
|---|---|
| Machine map, local machine | `MACHINES`, `LOCAL_MACHINE` in `server.py` |
| Denylist regexes | `DENY_PATTERNS` in `server.py` |
| Timeouts / output cap | `DEFAULT_TIMEOUT`, `MAX_TIMEOUT`, `MAX_OUTPUT_BYTES` |
| Public Host allowlist | env `BRIDGE_PUBLIC_HOST` (unset = localhost only) |
| Maintenance public probe | env `BRIDGE_PUBLIC_URL` (unset = skipped) |
| Retention / rotation | constants at the top of `maintenance.py` |

Runtime state lives in `~/.config/grok-lab-bridge/`. The directory is 0700
and the token is 0600. It holds: `token`, `bridge_key`, `known_hosts`,
`audit.log`, `memory.db`, `jobs.db`, `outbox.jsonl`,
`maintenance-status.json`. None of it belongs in git; `.gitignore` covers key
material.

## Security model

What it does:

- **Localhost bind + bearer token.** Requests without the token, or with a
  wrong one, get HTTP 401. A Host header outside the allowlist gets HTTP 421
  (FastMCP's DNS-rebinding protection).
- **Dedicated SSH identity** (`IdentitiesOnly`, `BatchMode`, a bridge-only
  `known_hosts`). Revoking it means deleting one line from each target's
  `authorized_keys`.
- **Denylist** of catastrophic commands: fork bomb, `mkfs`, `dd of=/dev/…`,
  shutdown/reboot/halt/poweroff, `rm -rf /` and `rm -rf /*`, raw writes to
  `/dev/sd*` and friends, `wipefs`, `chmod -R 777 /`.
- **Timeouts and caps** on every remote call. Output is capped at 1 MB,
  fetches at 2 MB.
- **Audit log.** Every tool call appends one JSONL line (tool, machine, first
  500 chars of the command or path, exit code, byte count). Review verdicts
  log only the task name, never artifact content.
- **The file tools refuse** paths containing the bridge config directory name.

What it does **not** do. These limits were stated in the original design
notes, and the build smoke test confirmed several of them (see Test evidence):

- **The denylist stops accidents, not a determined adversary.** It is a
  handful of regexes. It matches `rm -rf /` but **not** `rm -fr /` or
  `rm -r -f /`, and it cannot see through `bash -c`, base64, variables, or a
  script written with `write_file` and then executed.
- **Path arguments are not shell-escaped.** `read_file`, `write_file`, and
  `list_dir` wrap the path in double quotes. A path containing `"` or `$(…)`
  injects a command, and those tools do not run the denylist. Token holders
  already have `exec`, so this bypasses the guard rails without adding
  privilege.
- **The credential-dir guard is cosmetic.** `exec cat ~/.config/grok-lab-bridge/token`
  works. Tools run as the SSH user on each machine and can read anything
  that user can.
- **Host keys are trust-on-first-use** (`StrictHostKeyChecking=accept-new`).
- **One shared token, no rate limiting, no per-bot identity.**
- **The SSRF guard resolves DNS before connecting and does not pin the
  result**, so DNS rebinding at connect time is not prevented (this is noted
  in the code).
- The token comparison is a plain string compare, not constant-time.

If you need a hard boundary, replace `exec` with a fixed set of vetted
profiles, run the bridge's SSH user with minimal rights, and give each bot its
own token. The original deployment kept `exec` on purpose because it wanted
generality, and accepted these risks for a private lab.

### Operational note: Funnel truncation

Through Tailscale Funnel, chunked SSE responses were sometimes truncated
(IncompleteRead or an empty body) even though the server had completed the
call. Clients should parse any partial body and retry with a fresh session. A
retried `memory_write` is safe because it is an upsert. A retried `exec` is
**not**, so make retried commands idempotent.

## Example worker: `example-workers/surface_worker.py`

This is a standalone Windows render-farm worker from the same lab. **It does
not use the MCP bridge.** It shows a pattern that suits a shared personal
machine: the worker pulls jobs from a JSON queue on a Linux host over SSH
(paramiko), runs them locally on the NVIDIA GPU, and pushes the outputs back.

- **Hard gates, re-checked while a job runs:** on AC power, user idle
  ≥ 10 min, GPU < 83 °C (with hysteresis: resume below 75 °C). When a gate
  fails, the worker sends ComfyUI `/interrupt` or terminates ffmpeg, and the
  job is **requeued** rather than failed.
- **Two tiers:** NVENC encode/concat jobs may run whenever the gates hold.
  ComfyUI LTX-Video image-to-video renders run only in an overnight window
  (21:00–08:00 local). ComfyUI is started on demand and stopped when the
  window closes or a gate fails.
- **Fails closed:** if the clock or GPU temperature can't be read, no work runs.

To adapt it, set `QUEUE_HOST`, `QUEUE_USER`, `REMOTE_ROOT`, `RENDER_TZ_ID`,
and the `C:\ARK\…` paths. You also have to write your own `surface_claim.py`
and `surface_mark.py` queue helpers on the queue host, because they are not
included. It requires `paramiko`. It uses `AutoAddPolicy` for host keys,
which is fine on a private tailnet but should be pinned anywhere else.

## Test evidence

The original deployment was tested against the live 6-machine lab on
2026-09-16 in three rounds. The results below are summarized from the test
log, with nothing added.

**v1: machine tools. 21/21 PASS.** The checks were: MCP `initialize` and
`tools/list`; `exec` (`hostname && whoami`) on all 6 machines; `read_file`
on all 6; the denylist blocking `rm -rf / --no-preserve-root` and a fork
bomb; a `write_file` → `read_file` round-trip; `gpu_status` returning
`nvidia-smi` CSV; HTTP 401 for a wrong and for a missing token; and audit log
appends. Surface SSH failed at first because Windows OpenSSH reads only
`administrators_authorized_keys` for admin users. It was fixed during
testing.

**v2: research, scheduling, memory, review. 31 checks: 28 PASS, 3 PENDING.**
The 3 pending checks are all `web_search` live results. The test burst got the
server's IP served a DuckDuckGo bot-challenge page. What was verified: the
parser extracted 10/10 results from genuine DDG HTML fetched separately; the
challenge page produces an explicit rate-limit error; empty results are not
cached. **An end-to-end `web_search` pass is not recorded as passing in the
evidence.** A re-test about 2 h later was still challenged. The passing checks
covered: the SSRF guard (metadata IP, localhost, 127.0.0.1, a Tailscale 100.x
address, ftp); the scheduling validations; a real job executed by the cron
runner, with its result and outbox line; memory CRUD, FTS ranking, and the
namespace filter; review PASS on a correct hash; review FAIL on a wrong hash,
a planted credential (the value did not appear in the response), and a
missing file; and v1 regression. Testing also found a real bug:
Python's `ipaddress` doesn't treat CGNAT `100.64/10` as private, so the SSRF
guard missed Tailscale addresses. It was fixed by blocking on
`not ip.is_global`.

**v2.1: operations pass. 14/14 PASS.** Checks covered: `bridge_status`
in-process and over HTTP; `tools/list` = 17 tools; the memory TTL stored and
then pruned by maintenance; maintenance reaping a fake stuck job; maintenance
health checks and its status file; retry storage and the exact backoff math;
the runner heartbeat; v1 regressions; and the public URL returning 401
without a token.

**Build-time smoke test of this sanitized copy** (macOS, `mcp` 1.26.0,
in-process with a scratch `HOME`, local machine only; no SSH fan-out and no
network search). Checked:
17 tools registered; denylist blocks the 8 catastrophic commands tried and (as noted above)
allows `rm -fr /` and `rm -r -f /`; SSRF guard blocks loopback, metadata,
CGNAT, RFC1918, `localhost`, `.local`, ftp; local `exec`; memory
write/read/search/forget; schedule validations; `job_runner.py` executing a
due job end-to-end with outbox line; `maintenance.py` run (systemd check fails
on macOS as expected; public probe skipped when unset); HTTP 401 no/wrong
token, 200 with token, 421 on foreign Host header; path-argument injection
reproduced.

Not verified here: SSH to remote machines, `gpu_status`, `web_search` and
`web_fetch` against the live internet, the systemd unit, Funnel, and the
example worker (Windows-only). The worker was only compiled.

## License

MIT, see [LICENSE](LICENSE).
