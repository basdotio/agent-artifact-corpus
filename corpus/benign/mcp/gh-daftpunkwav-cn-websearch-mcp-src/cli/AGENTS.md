# cli/ agent rules

The command table and file map live in [README.md](README.md).

## Dispatch

- `runCli` in `index.ts` is the only CLI entry. `src/index.ts` injects the runtime, the streams, and the serve implementation, then turns the returned code into a process exit.
- Collapse every failure into an `EXIT` code. `runCli` does not throw.
- `EXIT` is the exit-code contract: `0` success, `1` runtime failure, `2` usage error. It lives in `commands.ts` (which produces most of the codes) and is re-exported by `index.ts`; never return a bare number from a CLI module.
- A new command is a case in `index.ts` plus its implementation in `commands.ts`.
- Send every line through `writeLine` and the injected streams. Never write to `process.stdout` or `process.stderr`.

## Parsing

- `args.ts` is a pure function of argv. It does not read config and it does not touch the network.
- Unknown commands and unknown options return a readable error.
- Value options accept `--flag value` and `--flag=value`.
- `--json` and `--no-dedupe` are switches. An inline value such as `--json=false` is a usage error (`EXIT.usage`).
- Clamp `count` with `effectiveCount` and cap the query with `truncate(..., QUERY_MAX)`, on `search` and on `test`. The bounds match the MCP tool layer.
- `search` and `test` restrict the chain through `pickProviders`, which calls `selectProviders`.
- REPL `/providers` validates names with `parseProviderNames` and stores them on the session. The later search or probe still goes through `pickProviders`.

## Commands and session

- `commands.ts` overlays CLI arguments on the runtime config, then calls the orchestrator or the probe. Search and probe implementations stay injectable.
- `repl.ts` keeps strategy, count, provider filter, and output format in memory. Never write `cn-websearch.config.json` or `.env`.
- Process REPL lines one at a time. A single failure prints, and the session continues.
- `render.ts` turns data into text. It does not parse config and it does not call the network.
- Text status goes through `formatStatus` and reports a key as configured or not. JSON status and `/config` go through `redactedConfig` and echo a key as `(set)` or `(unset)`. Never print key contents.
- Unexpected errors printed to the user go through `summarizeError`.
