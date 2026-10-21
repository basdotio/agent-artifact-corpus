# src/

All runtime code of the package, written in TypeScript and compiled by `tsc`
to `dist/` (ESM, `"type": "module"`). The same tree serves two entry surfaces:
the MCP stdio server and the CLI — both are assembled from the same runtime
(see [Runtime assembly](#runtime-assembly) below).

## Module map

| File | Role |
|---|---|
| `types.ts` | Shared contracts: `SearchProvider`, `SearchRequest`, `NormalizedSearchResult`, `AttemptRecord`, `SearchContext`, and the `SEARCH_STRATEGIES` vocabulary every surface validates against. No imports, no I/O and no branching; it is inside the measured tree and stays at 100% on its own. |
| `errors.ts` | Error taxonomy (`TimeoutError`, `NetworkError`, `HttpError`, `ParseError`), transient/permanent classification, and `redactSecrets` / `summarizeError` for key-free audit text. |
| `normalize.ts` | Field normalization shared by all adapters: `toItem`, `clampInt`, `truncate`, `normalizeDate`, shape asserts (`asObject` / `asArray`), control-character stripping for untrusted upstream text, URL canonicalization and multi-source merge (`mergeSourceItems`). |
| `config-file.ts` | Config file I/O only: locate (`WEBSEARCH_CONFIG` or `cn-websearch.config.json` under cwd), check the size bound, and parse JSON. Never validates semantics and never throws — failures warn and return `undefined`. |
| `config.ts` | Config resolution: merges built-in defaults → config file → environment variables into `GatewayConfig`. Every value is parsed leniently (invalid input warns and falls back), a blank value at any layer means "unset", and timeouts are bounded. Defines `KNOWN_PROVIDERS`, the neutral per-slot defaults, and the search-argument bounds (`COUNT_MIN` / `COUNT_MAX` / `QUERY_MAX`) shared by the tool layer and the CLI. |
| `dotenv.ts` | Minimal `.env` loader (no dependencies): size-bounded, exports only the names the gateway reads, and never overwrites an existing `process.env` entry. |
| `http.ts` | Shared JSON POST helper: merges caller signal with a per-request timeout (Node 18 compatible), caps how much of a response body is buffered, maps failures to the error taxonomy, redacts upstream bodies before they reach error messages. |
| `orchestrator.ts` | Search orchestration: `runSearch` dispatches by strategy; `searchWithFallback` walks the chain, `searchAggregate` runs providers in parallel and merges. Owns the per-attempt wall-clock budget, caller cancellation, the single transient retry with its backoff, and the `_meta.attempts` audit trail. |
| `probe.ts` | Single-provider live probe (`probeProvider`) returning a data row instead of throwing; `probeAll` runs probes sequentially. Shared by the CLI `test` command and `scripts/smoke.ts`. |
| `providers/` | Per-channel adapters (`kimi`, `mimo`, `stepfun`, `zhipu`) and the factory registry. See [providers/README.md](providers/README.md). |
| `provider-selection.ts` | The single rule for turning a requested provider list into usable adapters; shared by `tools.ts` and `cli/`. |
| `runtime.ts` | The single runtime assembly point: resolves the config file, loads config, builds all adapters, and computes the usable chain (enabled + has a key). Never throws — config problems only warn. |
| `tools.ts` | MCP tool layer: `web_search` and `provider_status` definitions, argument validation, dispatch to the orchestrator, structured error output. Depends only on injected deps. |
| `server-info.ts` | `SERVER_NAME` / `SERVER_VERSION` constants; `test/server-info.test.ts` asserts they match `package.json`. |
| `index.ts` | Process entry point: loads `.env`, assembles the runtime, binds the MCP SDK handlers to the tool layer, and hands argv to the CLI. All substantive logic lives in the other modules. |
| `cli/` | Terminal interface: argument parsing, one-shot commands, interactive session, rendering. See [cli/README.md](cli/README.md). |

## Layering

Dependencies point in one direction; lower layers never import upper ones:

```
index.ts ─┬─→ tools.ts ─────────┐
          ├─→ cli/ ─────────────┤
          └─→ runtime.ts ─→ providers/ ─┐
                            orchestrator ┤
                            probe ───────┤
                            config ──────┤
                  config-file ┤         │
                  dotenv ─────┤         │
                  provider-   ┤         │
                  selection ──┘         │
                            http ────────┤
                            normalize ───┤
                            errors ──────┘
                                     types.ts (pure contracts, imported by all)
```

- `types.ts` / `errors.ts` / `normalize.ts` / `config-file.ts` form the
  bottom: they never import an upper layer, and the only internal edges among
  them point at `errors.ts` (`normalize.ts` → `errors.ts` and
  `config-file.ts` → `errors.ts`). The tree's only disk readers are
  `config-file.ts` (its own config file) and `dotenv.ts` (`.env`).
- `config.ts` and `http.ts` sit above them.
- `provider-selection.ts` sits with `config.ts`: it needs the known provider
  names and the adapter interface, nothing else, and is shared by the top layer
  rather than used by one caller.
- `orchestrator.ts` and `probe.ts` coordinate providers; adapters stay thin
  (request construction and response parsing only).
- `runtime.ts` / `tools.ts` / `cli/` are the top: they consume assembled
  dependencies and never rebuild them.

## Runtime assembly

`createRuntime()` in `runtime.ts` is the only composition point. It is shared
by the MCP entry (`src/index.ts`) and the CLI, so both surfaces always see the
same effective config and the same provider chain. Config file reading and
file-existence checks are injectable, which keeps every branch testable
without touching the disk.

A provider participates in searches only when it is enabled **and** has a
non-empty API key; `runtime.chain` holds exactly those adapters, in the
resolved priority order. Channels without a key are skipped automatically
rather than failing the call.
