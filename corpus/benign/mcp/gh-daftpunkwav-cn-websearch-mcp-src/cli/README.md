# src/cli/

The terminal interface of the package. The same `dist/index.js` binary that
serves MCP over stdio is also a CLI, so channels can be searched and probed
without wiring up an MCP client.

`runCli()` in `index.ts` is the single entry point: `src/index.ts` injects the
real runtime, process streams, and the stdio serve implementation, then
converts the returned exit code into a process exit. Everything in this
directory is driven through injected dependencies, so tests can run the whole
CLI without spawning a subprocess.

## Commands

| Command | Behavior |
|---|---|
| `serve` (default) | Start the MCP stdio server. With no arguments this is implied, preserving how MCP clients already launch the binary. Aliases: `mcp`. |
| `search <query...>` | One-shot search; prints formatted results or raw JSON with `--json`. |
| `status` | Print the effective config and per-slot status (keys reported as set/unset only). |
| `test [provider...]` | Probe each ready channel once with a real request (default query: `今日新闻`, overridable with `-q/--query`); exits 1 if any probe fails. |
| `repl` | Interactive session. Aliases: `shell`, `interactive`. |
| `help` / `version` | Usage text / identity line. |

Options: `-n/--count <1-50>`, `--strategy fallback|aggregate`,
`--providers a,b` (restrict one call), `--no-dedupe`, `-q/--query`,
`--json`. Options that take a value accept both `--flag value` and
`--flag=value`; `--no-dedupe` and `--json` are switches, so an inline value
(`--json=false`) is rejected with exit code 2 rather than silently ignored —
writing the flag without a value is the only way to turn it on.

Argument bounds match the MCP tool layer: `count` is clamped to 1-50 and a
query is capped at 400 characters, on `search` and `test` alike.

Exit codes (the `EXIT` contract, owned by `commands.ts` and re-exported by
`index.ts`): `0` success, `1` runtime failure (search failed / no usable
provider), `2` usage error — so scripts and CI can branch on them.

## File map

| File | Role |
|---|---|
| `index.ts` | Dispatch: parse argv, route to the command, collapse failures into exit codes. Never throws. |
| `args.ts` | Pure argv parser: bare words resolve the command first and join into the query afterwards; unknown commands/options always return a readable error instead of guessing. |
| `commands.ts` | One-shot implementations (`cmdSearch`, `cmdStatus`, `cmdTest`) that overlay CLI arguments onto the config and call the orchestration layer; `pickProviders` is a thin wrapper over the shared name rules. |
| `repl.ts` | Interactive readline session: bare text searches, `/` commands control session state (`/strategy`, `/count`, `/providers`, `/json`, …). Lines are processed serially so concurrent searches never interleave output; a single failure prints and continues. |
| `render.ts` | Data-to-text rendering only: result list, status table, probe table, and `redactedConfig` (echoes whether a key is set, never its contents). |

## Session state vs configuration

`repl.ts` keeps its session state (strategy, count, provider filter, output
format) in memory only. The CLI is a consumer of configuration — it never
writes back to `cn-websearch.config.json` or `.env`.
