# LeanWarp reference

## Commands

Run commands from the Lean project, or pass `leanwarp --project DIR`. Every
command prints one JSON object; `leanwarp COMMAND --help` lists its options.

| Command | What it does |
| --- | --- |
| `auth login`, `auth logout` | Save or forget the API key on this machine. |
| `doctor [--environment NAME]` | Show which environment the project runs on, and summarise the upload. No compute. |
| `files` | List the Lean files that would upload, their sizes and any problems. No key needed. |
| `connect [--environment NAME] [--max-spend USD]` | Create the project's workspace, optionally with a spending cap. No compute. |
| `check FILE [--draft]` | Compile a file and report Lean's errors and warnings. |
| `inspect FILE --line N --column N` | Show the goals and local context at a position. |
| `try-tactics FILE --line N --column N --tactic T [--tactic T …]` | Try tactics without editing the file. |
| `verify FILE --declaration NAME --target STATEMENT [--context-file PATH]` | Check that a declaration proves exactly the statement. |
| `wait [--timeout SECONDS]` | Wait for the latest operation's result. |
| `status` | Show the workspace and the latest operation. |
| `cancel` | Cancel the latest operation. |
| `stop` | Stop the worker. Files are kept. |
| `recover` | Resend a request whose response was lost. |
| `disconnect` | Forget a stopped workspace so the project can connect to another environment. |
| `environments`, `resources`, `account` | List environments, show the published worker's resources and pricing, or your credit. |
| `skill [--reference]` | Print the agent instructions or this reference. No key needed. |
| `mcp` | Run the MCP server for this project over stdio. |

Operations (`check`, `inspect`, `try-tactics`, `verify`) upload changed and deleted
files first, then accept:

- `--wait SECONDS`: how long to wait for the result, 0 to 40 (default 30).
- `--execution-timeout SECONDS`: the operation's time limit on the server, 1 to 600.

`verify --fresh` also uses a temporary worker. Otherwise operations share the
workspace's worker, which keeps imports loaded between calls.

`check` is strict by default: `sorry` is an error and the result is what a final
build would say. `check --draft` is faster while you edit: the worker keeps the
file open, and after an edit Lean reuses its work on the unchanged part of the
file. In a draft check `sorry` is only a warning, so finish with a full `check`
or with `verify`.

Tactic trials start from the same captured goal without changing the file.
They run in batches of up to four branches normally, or eight on the usage-based
worker, so a large portfolio fits the worker's CPU and memory limits. Results
keep the order of the supplied tactics. Hosted checks have demonstrated reuse
of the captured document. Read each result's `execution` fields for the path
that actually ran.

## Environments

An environment is a Lean release with Mathlib, already built on LeanWarp's
workers, such as `lean-4.26-mathlib`. `leanwarp environments` lists them with
their toolchain and Mathlib commit. LeanWarp updates an environment's build
(for example with engine fixes) without changing its Lean or Mathlib; workspaces
pick up the new build when their next worker starts.

`connect` chooses an environment from the project's `lean-toolchain` and
`lake-manifest.json`:

| The project has | LeanWarp uses | `match` |
| --- | --- | --- |
| A toolchain and lockfile that match an environment | That environment | `exact` |
| Only a toolchain that matches | That environment | `exact` |
| Neither file | The only served environment, or the newest served stable Lean release | `unpinned` |
| Files that match no environment | Nothing; `connect` lists the options | |
| Any of these, plus `--environment NAME` | That environment | `requested` |

With `--environment`, `matches_project` says whether the project's own files match.
When they don't, your files compile against the environment's Lean and Mathlib,
which can differ from a local build. Imports of packages the environment doesn't
contain fail like any missing import.

A workspace stays on its environment. If the project's toolchain or lockfile
changes, run `stop`, `disconnect` and `connect` again.

## Results

Operation results start with `success`, followed by the operation as LeanWarp
returned it:

| `success` | Meaning | Exit code |
| --- | --- | --- |
| `true` | The check passed, the proof was verified, inspection returned goal context, or the tactic trial ran. | `0` |
| `false` | It did not pass. Read `result.result`, or `error_message` if the operation failed. | `1` |
| `null` | Still running. Run `wait`; never submit it again. | `3` |

Other exit codes: `1` from `doctor` when no environment matches, and `2` when a
command could not run. Its JSON then has `error` (a stable code) and `message`.

What to read in `result.result`:

| Operation | Fields |
| --- | --- |
| `check` | `status` (`ok` when there are no errors), `diagnostics` and `cached`. |
| `inspect` | `goal_status`: `available` with `goal_contexts`, or `unavailable` with `unavailable_reason`. `retained_proof_state`, when present, says whether the worker retained a proof state; it does not promise which tactic execution path will run. Also `selected_hole`, `enclosing_declaration`, `premise_hints` and `context_omitted`. |
| `try_tactics` | `results`: one entry per tactic, in the order given, with `tactic`, `outcome`, `status`, `diagnostics`, `elapsed_ms` and `execution`. `skipped` lists tactics that did not run, with a reason. |
| `verify_target` | `status` `ok` and `receipt.policy` `fixed_target_kernel_check_v1`; a rejection has `failure_kind`. |

A trial's `outcome` is `closed_proof`, `open_proof_state` (the tactic ran and
goals remain, shown in its diagnostics), `tactic_error`, `timeout` or
`rejected`. An unavailable context doesn't mean a goal is solved, and a tactic that
succeeds in a trial isn't a proof until the file checks with it. Engine errors,
such as a position outside any proof, arrive as `status` `error` with an `error`
object holding `code` and `message`.

Inspection supports ordinary `sorry` drafts and explicit proof holes. The selected
position must identify one goal context. Tactic inputs are bare Lean tactics; a
`by` wrapper is optional.

For successful inspections, `status` retains the older `proof_state` or
`metadata_only` marker for compatibility. These describe retention, not goal
availability: `metadata_only` can still contain useful goals. Use `goal_status`
and `goal_contexts` to decide whether context was returned. An unavailable
context has `status: unavailable`, so older clients also report it as unsuccessful.

### How it ran

Completed operations also carry `execution`, which says what LeanWarp reused,
and `timing`, which says where the time went. Only facts that apply appear.

| `execution` field | Values |
| --- | --- |
| `worker` | `warm`: the workspace's running worker. `started`: a new worker started for this operation. `temporary`: a separate worker that stopped afterwards. |
| `imports` | `reused`: the file's imports were already loaded. `extended`: loaded imports were extended. `loaded`: imported now. |
| `document` | Draft checks only. `incremental`: Lean reused its earlier work on the file. `full`: the file was elaborated from the start. |
| `trials` | Tactic trials counted by how they ran. `proof_state`: from Lean's captured proof state. `document_state`: replayed from the captured document. `source_recheck`: the file rechecked with the tactic in place. `cached`: an identical earlier trial. |

`timing` has `queued_ms` (left out when the operation was recovered after a
failed attempt), `worker_ms` (getting a ready worker, including any start),
`upload_ms` and `run_ms`. Trials also report their own `execution` and
`elapsed_ms`.

Each result names the operation ID and source revision it belongs to. The SDK
rejects a result that doesn't match the operation the project submitted.
`result.generation` identifies the worker that ran it; a fresh or resized
verification runs on its own worker.

### Verification policy

`fixed_target_kernel_check_v1` elaborates the target statement on its own, with
only the context you supply, then checks the candidate proof against it with
Lean's kernel. Helper declarations in the candidate file can't change what the
target means. Supply the target's imports and definitions with `--context-file`
(MCP: `target_context`).

The checked theorem's axioms are audited transitively: only `propext`,
`Classical.choice` and `Quot.sound` are allowed. `sorry`, `admit` and any other
axiom are rejected, including ones reached through imports. Source using
`native_decide`, `set_option` or custom elaborators is rejected, and declaration
names must be ASCII. A rejection is not permission to weaken the statement.

The receipt records hashes and environment identities for the check. It is not a
signed, portable certificate: Lean and the environment's dependencies remain
trusted, and the check does not sandbox hostile metaprograms.

## MCP

Add the server to your client:

```json
{
  "mcpServers": {
    "leanwarp": {
      "command": "leanwarp",
      "args": ["--project", "/absolute/path/to/lean-project", "mcp"]
    }
  }
}
```

Use the absolute path of `leanwarp` if the client can't find it on its `PATH`.
The server reads the key saved by `auth login` or `LEANWARP_API_KEY`. It starts
without a key; tools that need one then say how to sign in. The resources
`leanwarp://guide` and `leanwarp://reference` serve the agent instructions and this
reference without a key. CLI and MCP share the project's `.leanwarp/` state; don't
run both against one project at the same time.

Tools: `doctor`, `files`, `environments`, `connect`, `check` (`draft`), `inspect`, `try_tactics`,
`verify_target` (`file`, `candidate_declaration`, `target_statement`,
`target_context`), `wait`, `status`, `cancel`, `stop`, `recover`, `disconnect`,
`account` and `resources`. Operation tools wait up to `wait_seconds` (default 20,
at most 40) and lead their result with `success`, like the CLI.

## Python

Install the library in your application's environment:

```sh
uv add 'leanwarp-sdk @ git+https://github.com/Isagoge-Labs/LeanWarp-SDK.git'
```

Without uv, use `python -m pip install` with the same requirement. The CLI's
isolated installation doesn't make the library importable in your application.

```python
from leanwarp_cloud import OperationOutcome, ProjectSession, load_client

with load_client() as cloud:
    project = ProjectSession(cloud, "/path/to/lean-project")
    project.connect()
    result = project.submit_and_wait(
        "verify_target",
        {
            "file": "LeanWarpExample.lean",
            "candidate_declaration": "add_zero_example",
            "target_statement": "∀ n : Nat, n + 0 = n",
            "execution_mode": "reusable",
        },
        wait_seconds=30,
    )
    if not OperationOutcome(result).terminal:
        result = project.wait(timeout=300)
    project.stop()
    if not OperationOutcome(result).verified:
        raise RuntimeError("the proof was not verified", result)
```

`load_client()` reads the same key as the CLI. `ProjectSession` keeps the
workspace, revisions and any unfinished request in `.leanwarp/session.json`, like
the CLI. `connect(environment=NAME)` chooses an environment explicitly. Closing the
client doesn't stop the worker; call `stop()`.

`LeanWarpCloud(api_key)` is the lower-level HTTP client for applications that
manage their own state. Before each create, sync or submit, save the request and
its idempotency key; after an uncertain response, resend exactly that request with
the same key. See the [HTTP API](https://github.com/Isagoge-Labs/LeanWarp-SDK/blob/main/docs/http-api.md).

## Recovery

| Situation | What to do |
| --- | --- |
| A create, upload or submit response was lost | `recover` resends the saved request, even if files changed since. |
| A file can't be uploaded, or the upload is too large | Run `files` to see every problem, then exclude unrelated files in `.leanwarpignore`. |
| `success` is `null`, or `wait` timed out | Run `wait` again. To abandon it, `cancel`, then `wait` until it ends. |
| Another LeanWarp command is using the project | Let it finish; a lock prevents overlapping writes. |
| `revision_conflict` from another machine | Decide which files to keep with the other writer. Don't delete `.leanwarp/` to force it. |
| The key was rotated | Sign in with a new key for the same account, then `recover`. |
| The toolchain or lockfile changed | `stop`, `disconnect`, then `doctor` and `connect`. |
| `.leanwarp/session.json` is damaged | Keep it; it may record an unfinished request. |
| Not enough credit, or a spending cap reached | Add credit or raise the cap in the dashboard, then retry. |

An operation's submission is two requests: the file upload, then the operation.
If `recover` returns an `operation_id`, the operation was submitted: wait for it.
If it returns only a workspace and revision, the upload or creation finished:
run the intended command again. With nothing to recover, `recover` returns the
same view as `status`.

`cancel` and `stop` aren't recorded for recovery. If their response is lost,
check `status` and run them again. Don't assume a lost response or a closed client
stopped billing.

The project's connection lives in its `.leanwarp/` directory. A clone of the
project on another machine connects its own workspace. To move a connection,
finish or cancel work, `stop`, then copy the project with `.leanwarp/` to a
machine signed in to the same account.

`disconnect` needs a confirmed `stop` and no queued or running operation.

## Credentials, credit and limits

`auth login` saves the key in `$XDG_CONFIG_HOME/leanwarp/credentials.json`
(normally `~/.config/leanwarp/credentials.json`), readable only by you.
`LEANWARP_API_KEY` takes precedence. The key decides which LeanWarp service is
used; there is no URL to configure. `auth logout` forgets the saved key; revoke it
in the dashboard to disable it.

Workers are billed per second while they run, including idle time. `resources`
reports one published `worker`: its starting minute quote, `usage_based`,
resource limits, startup credit hold and idle timeout. LeanWarp selects the
worker; you can set a spending cap when connecting or in the dashboard. Existing workspaces keep their
saved billing terms. The service holds credit while a worker runs and returns
the unused part once shutdown and final usage are confirmed. A stopped workspace
can temporarily retain reserved credit while that billing cleanup finishes.

`leanwarp connect --max-spend 2` creates a workspace capped at $2 in total,
including reserved credit. USD amounts allow up to six decimal places without
rounding. Python accepts `max_spend_microusd=2_000_000` on `connect`,
`create_workspace` and `create_workspace_for_project`; MCP `connect` accepts
`max_spend_microusd` in the same units. The allowed range is zero to $1,000,000.
Omitting the cap creates an uncapped workspace on a first connection and keeps
the existing cap on reconnect. A different supplied cap on reconnect is rejected;
change an existing cap in the dashboard. A cap of zero prevents compute starts.

When `usage_based` is true, CPU and RAM charges increase independently above
their reserved baselines. The starting rate remains a paid minimum while
running, including idle time. Bursting depends on available host capacity.
Otherwise the quoted minute rate applies for the time the worker runs.

A worker starts with the first operation and stays warm between operations until
the idle timeout, its maximum lifetime or `stop`. Closing the SDK client only
closes its HTTP connection; it does not stop compute or billing. `stop` discards
in-memory state but retains uploaded files and completed results; the next
operation reconstructs the worker without another upload. A cap change applies to future worker starts and
elastic lease renewals; if the next credit hold cannot fit, the worker stops and
an unfinished operation reports `leanwarp_budget_exceeded`.

`account` reports `balance_microusd`, `reserved_microusd` and
`available_microusd` as strings ($1 = 1000000).

| Limit | Value |
| --- | --- |
| Upload | 256 `.lean` files and 1 MiB per project, including paths |
| Module paths | ASCII letters, digits and `_`; not under `Init`, `Lean`, `Lake`, `Std` or `Mathlib` |
| Statement context | 128 KiB |
| Inline wait | 0 to 40 seconds (`wait` can poll longer) |
| Operation time limit | 1 to 600 seconds |
| Operations per workspace | One at a time |
| Active API keys | 100 per account |

Hidden directories, `.lake`, `lakefile.lean` and symlinks are never uploaded, and
symlinked Lean files are rejected. Lake scripts and dependency builds never run.

Patterns in the project's top-level `.gitignore` and `.leanwarpignore` exclude
files, with git's syntax. `.leanwarpignore` is read last, so it can exclude
something git tracks, such as an `archive/` folder, or re-include a file git
ignores with `!path`. A file inside an excluded directory can't be re-included.
`files` lists exactly what would upload.
