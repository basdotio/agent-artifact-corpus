/**
 * @file cli/commands
 * @description One-shot CLI command implementations: search / status / test.
 *
 * Responsibilities:
 * - Overlay parsed arguments onto the config and call the orchestration layer to run the
 *   search
 * - Print results or structured errors; express success/failure via exit codes (handy for
 *   scripts and CI)
 * - All output goes through the injected io, so tests can assert on it without polluting
 *   process globals
 */

// One-shot commands. Exit code convention: 0 success; 1 runtime failure (search failed / no usable
// provider); 2 usage error (returned by the entry point when parsing fails).

import { effectiveCount, QUERY_MAX, type GatewayConfig } from '../config.js';
import { isStructuredFailure, runSearch, type DispatchOptions } from '../orchestrator.js';
import { probeAll, type ProbeOptions, type ProbeRow } from '../probe.js';
import { selectProviders, type ProviderSelection } from '../provider-selection.js';
import { summarizeError } from '../errors.js';
import { truncate } from '../normalize.js';
import {
  formatProbeTable, formatSearchResult, formatStatus, redactedConfig,
} from './render.js';
import type { CliArgs } from './args.js';
import type {
  NormalizedSearchResult, SearchProvider, SearchRequest, SearchStrategy,
} from '../types.js';
import type { GatewayRuntime } from '../runtime.js';

/** Search implementation used by cmdSearch; injectable so tests never hit the network. */
export type CliSearchFn = (
  req: SearchRequest,
  opts: DispatchOptions,
) => Promise<NormalizedSearchResult>;

/** Probe implementation used by cmdTest; injectable so tests never need the network. */
export type CliProbeFn = (
  providers: SearchProvider[],
  req: SearchRequest,
  opts: ProbeOptions,
) => Promise<ProbeRow[]>;

/** CLI dependencies: runtime + output streams + injectable search/probe impls (for tests). */
export interface CliDeps {
  runtime: GatewayRuntime;
  output: NodeJS.WritableStream;
  error: NodeJS.WritableStream;
  search?: CliSearchFn;
  probe?: CliProbeFn;
}

/** Default probe query for the `test` command: generic and non-personalized. */
export const DEFAULT_PROBE_QUERY = '今日新闻';

/**
 * The exit-code contract: 0 success, 1 runtime failure, 2 usage error.
 *
 * Defined here, not in the dispatcher, because this module is where most of the
 * codes are actually produced. A bare `return 1` / `return 2` is a second copy
 * of the same contract that these constants cannot see, and moving the contract
 * then means hunting down every literal in both files — or silently leaving the
 * CLI reporting two different numbers for the same class of failure.
 */
export const EXIT = { ok: 0, failure: 1, usage: 2 } as const;

/**
 * Write one line, terminating it exactly once.
 *
 * Shared by every CLI module that prints (commands, the dispatcher and the
 * REPL) so a message is never double-spaced or left unterminated by one of
 * them; it lives here because this is the module the other two already import.
 */
export function writeLine(stream: NodeJS.WritableStream, text: string): void {
  stream.write(text.endsWith('\n') ? text : `${text}\n`);
}

/** The hint printed by both commands that need a usable provider before they can run. */
const NO_READY_PROVIDER = 'error: no provider is ready — set an API key via env or a config file, then retry';

/**
 * Restrict the call to the named providers, using the same name rules as the MCP
 * tool layer. An absent or empty list means "no filter": the CLI already rejects
 * an empty --providers at parse time, so this only covers a direct caller.
 */
export function pickProviders(
  names: string[] | undefined,
  chain: SearchProvider[],
): ProviderSelection {
  if (!names?.length) return { ok: true, providers: chain };
  return selectProviders(names, chain);
}

/**
 * Run one search and print it. Precedence for strategy/dedupe/count is
 * command-line arguments > config file/env vars.
 */
export async function cmdSearch(deps: CliDeps, args: CliArgs): Promise<number> {
  const { runtime, output, error } = deps;
  const config: GatewayConfig = runtime.config;
  if (!args.query.trim()) {
    writeLine(error, 'error: missing query (usage: cn-websearch-mcp search <query>)');
    return EXIT.usage;
  }
  if (!runtime.chain.length) {
    writeLine(error, NO_READY_PROVIDER);
    return EXIT.failure;
  }
  const picked = pickProviders(args.providers, runtime.chain);
  if (!picked.ok) {
    writeLine(error, `error: ${picked.error}`);
    return EXIT.usage;
  }

  const search = deps.search ?? runSearch;
  const strategy: SearchStrategy = args.strategy ?? config.strategy;
  // Same argument contract as the MCP tool layer: a count is clamped to the
  // shared range and a query is capped, so both surfaces search alike.
  const count = effectiveCount(args.count, config.count);
  const query = truncate(args.query.trim(), QUERY_MAX);
  try {
    const result = await search(
      { query, count },
      {
        providers: picked.providers,
        timeoutMs: config.timeoutMs,
        maxProviders: config.maxProviders,
        dedupe: args.dedupe ?? config.dedupe,
        strategy,
      },
    );
    writeLine(output, args.json ? JSON.stringify(result, null, 2) : formatSearchResult(result));
    return EXIT.ok;
  } catch (err) {
    // Every structured failure carries an audit trail; print it the same way
    // instead of special-casing each one. (A call that never reached a provider
    // carries an empty trail, so it prints the message alone.)
    if (isStructuredFailure(err)) {
      writeLine(error, `error: ${err.message}`);
      for (const a of err.attempts) {
        writeLine(error, `  - ${a.provider}: ${a.status} (${a.latency_ms}ms)${a.error ? ` ${a.error}` : ''}`);
      }
      return EXIT.failure;
    }
    writeLine(error, `error: unexpected failure: ${summarizeError(err)}`);
    return EXIT.failure;
  }
}

/** Prints the effective config and provider status. */
export async function cmdStatus(deps: CliDeps, args: CliArgs): Promise<number> {
  const { runtime, output } = deps;
  const payload = args.json
    ? JSON.stringify(redactedConfig(runtime.config), null, 2)
    : formatStatus(runtime.config, runtime.chain.map((p) => p.name));
  writeLine(output, payload);
  return EXIT.ok;
}

/**
 * Probe providers one by one (real network calls). Returns exit code 1 if any provider fails,
 * so scripts can tell whether all channels are healthy.
 */
export async function cmdTest(deps: CliDeps, args: CliArgs): Promise<number> {
  const { runtime, output, error } = deps;
  if (!runtime.chain.length) {
    writeLine(error, NO_READY_PROVIDER);
    return EXIT.failure;
  }
  const picked = pickProviders(args.providers, runtime.chain);
  if (!picked.ok) {
    writeLine(error, `error: ${picked.error}`);
    return EXIT.usage;
  }

  const probe = deps.probe ?? probeAll;
  // Same argument bounds as `search` and the MCP tool layer, so a probe is sent
  // the same shape of request whichever surface asks for it.
  const rows: ProbeRow[] = await probe(
    picked.providers,
    {
      query: truncate(args.query.trim() || DEFAULT_PROBE_QUERY, QUERY_MAX),
      count: effectiveCount(args.count, runtime.config.count),
    },
    { timeoutMs: runtime.config.timeoutMs },
  );
  writeLine(output, args.json ? JSON.stringify(rows, null, 2) : formatProbeTable(rows));
  return rows.every((r) => r.ok) ? EXIT.ok : EXIT.failure;
}
