# BUILD-REPORT — grok-lab-bridge

Built 2026-09-27 from the read-only source snapshot `~/github-portfolio-src/grok-lab-bridge-src/`
(never modified). All paths below are repo-relative. No secret values appear in this report.

## Files

| File | Origin |
|---|---|
| `README.md` | Rewritten from scratch (old README + TEST-EVIDENCE folded in, sanitized) |
| `LICENSE` | New, MIT |
| `.gitignore` | New (Python, key material `*.pem` `*.key` `*_key` `id_*` `token` `known_hosts`, runtime DBs/logs, `.smoke-home/`) |
| `server.py` | Sanitized source |
| `job_runner.py` | Sanitized source |
| `maintenance.py` | Sanitized source |
| `requirements.txt` | Unchanged |
| `grok-lab-bridge.service` | Renamed from `grok-mcp-bridge.service`, sanitized |
| `example-workers/surface_worker.py` | Sanitized source |
| `example-workers/requirements.txt` | New (`paramiko`, needed by the worker) |
| `BUILD-REPORT.md` | This file |

Not carried over: the source `TEST-EVIDENCE.md` (substance folded into README
"Test evidence"; the raw file is full of hostnames/usernames/IPs) and the source
`README.md` (leaked identifying details, see below).

## Key-material check

- `ls ~/github-portfolio-src/grok-lab-bridge-src | grep -i key` → no output (exit 1).
  Recursive listing also shows no key file. **No private key material was seen at any point.**
- Bearer token: the old README's "redacted" claim holds. No token value exists in
  any source file. The token is generated at runtime (`secrets.token_urlsafe`).
  Verified by grepping for long random strings and `Bearer <value>` patterns.

## Renamed / sanitized (locations only)

- `server.py`: module docstring (owner name, host, and user removed, "formerly
  grok-mcp-bridge" note added); config dir path renamed; `MACHINES` map (6 real
  users and IPs, 5 on the tailnet and 1 on the LAN) → placeholders; the
  hard-coded local machine became a `LOCAL_MACHINE` constant; `PUBLIC_HOST`
  default (the real tailnet FQDN) → env-only, and unset means localhost only;
  the credential-dir guard now derives from `CONFIG_DIR.name` instead of the
  old literal; the systemd unit name in `bridge_status`; the `review_queue`
  docstring (a named operator bot → "operator").
- `job_runner.py`, `maintenance.py`: the hard-coded `sys.path` home dir → the
  script's own dir; in maintenance, `PUBLIC_URL` (real tailnet FQDN) → env
  `BRIDGE_PUBLIC_URL`, and the probe is skipped when it is unset; the unit
  name; comments naming the lab's production project.
- `grok-lab-bridge.service`: ExecStart paths renamed, and a commented
  `BRIDGE_PUBLIC_HOST` example added.
- `example-workers/surface_worker.py`: the queue host IP and SSH user (hard-coded
  twice) → `QUEUE_HOST`/`QUEUE_USER` placeholders; remote home paths →
  `REMOTE_ROOT` placeholder; city time zone → `RENDER_TZ_ID` constant
  (`detroit_hour` → `local_hour`); the owner's name removed from the docstring;
  a header added stating this is not part of the MCP server and that its two
  queue helper scripts are not included; a host-key TOFU comment added.
- Old README items **dropped**: the bridge SSH public-key fingerprint, the
  tailnet name, per-machine usernames and home paths, and machine hostnames.
  TEST-EVIDENCE items dropped: machine hostnames, usernames, and a Tailscale IP.

## Verification (run in this session)

1. `py_compile` on all 4 `.py` files with Homebrew python 3.14 → all OK.
   The same 4 files under system python3 3.9.6 → OK.
2. The prescribed secrets/PII grep → **3 hits, all non-secret**: the `SECRET_PATTERNS`
   detector regexes in `server.py` (review harness's scanner definitions for
   `api_key`, `password`, `BEGIN … PRIVATE KEY`). No real values, IPs, or keys.
   Extended identity grep (usernames, hostnames, tailnet, `/Users/`, `/home/…`,
   fingerprints, 100.x) → only `<your-host>` placeholders plus the LICENSE
   copyright line.
3. Smoke test of the sanitized code (Homebrew python 3.14, `mcp` 1.26.0,
   `HOME` = scratch dir inside the repo, local machine only):
   - 17 tools registered.
   - Denylist blocks 8 of 8 catastrophic commands tried, but **allows `rm -fr /` and
     `rm -r -f /`**.
   - The SSRF guard blocks loopback, metadata, CGNAT, RFC1918, localhost,
     `.local`, and ftp.
   - Local `exec` works; memory CRUD and FTS work; the schedule validations work.
   - `job_runner.py` ran a due job end-to-end (status done, outbox line
     written); exit 0.
   - `maintenance.py` ran: exit 0, one expected anomaly (no `systemctl` on
     macOS).
   - HTTP via the Starlette TestClient: 401 with no token or a wrong token,
     200 with the right one, 421 for a foreign Host header.
   - **Path-argument shell injection reproduced** (`read_file` with an embedded
     `"; echo …; "` executed the echo).
4. README re-read for overstatement. Test counts are quoted as the evidence
   file states them. It says v1 21/21, v2 28/31 with 3 PENDING (`web_search`
   end-to-end never recorded as passing), and v2.1 14/14. "21/21" is used
   only for v1.

**Not verified:** SSH fan-out to remote machines, `gpu_status`, live
`web_search`/`web_fetch`, the systemd unit, Funnel, and the Windows worker
(compile-only).

## Judgment calls

- **The code was kept faithful to production. The security gaps are
  documented, not fixed.** These are the denylist flag-order gap, the
  unescaped path args bypassing the denylist, the cosmetic credential-dir
  guard, the non-constant-time token compare, and TOFU host keys. Fixing them
  would ship untested code under the "production" label. The README's
  Security model section states each one plainly.
- The only code changes are sanitization and portability: placeholders,
  `LOCAL_MACHINE`, env-driven public host/URL, and `sys.path` from `__file__`.
  The env-driven `PUBLIC_HOST`, and the skip when `BRIDGE_PUBLIC_URL` is
  unset, are small behavior changes. They are needed because otherwise a real
  FQDN or a meaningless placeholder would have been baked in. All were
  exercised by the smoke test except the `PUBLIC_HOST`-set branch.
- The machine labels (`spark-1..3`, `air`, `mbp`, `surface`) were kept as
  logical names, because they describe hardware classes rather than real
  hostnames.
- The LICENSE names Steven Haller as the copyright holder. That is
  intentional attribution for a portfolio repo, not a leaked path.
- The recipe prompt text, the `C:\ARK\…` paths, and `STYLE_ARK` in the worker
  were kept. They are a project name and a render recipe, not personal data.
- The README states that the example worker does **not** use the bridge. The
  source didn't make this obvious, and presenting it as a bridge client would
  have been an overstatement.

## Leftovers needing manual cleanup

Deleting the smoke-test scratch was **denied by the permission layer**. It
was not retried. Both items are gitignored, but delete them before publishing:

- `.smoke-home/`: scratch HOME containing a throwaway random token generated
  during the smoke test (not a production credential), test DBs, and logs.
- `__pycache__/` (+ `example-workers/__pycache__/` from py_compile).

No git repo was initialized and nothing was pushed.
