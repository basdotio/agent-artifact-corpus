/**
 * @file tools
 * @description MCP tool layer: tool definitions, argument validation and dispatch.
 *
 * Responsibilities:
 * - Expose two tools: web_search (with strategy and provider selection) and provider_status
 * - Validate and normalize tool arguments before the orchestrator runs
 * - Format successful results and structured failures as MCP text content
 * - All dependencies are injected via deps; this module never reads the environment or builds
 *   providers itself
 */

// MCP tool layer. Upward it depends only on the injected deps object; downward
// it only knows the SearchProvider interface and the orchestration entry — no
// concrete provider adapter implementation (provider_status only enumerates the
// KNOWN_PROVIDERS name list, which is data, not behaviour), keeping the layers
// decoupled. Provider-name rules live in provider-selection.ts, which the CLI
// shares, so both surfaces accept exactly the same names.

import {
  COUNT_MAX, COUNT_MIN, effectiveCount, KNOWN_PROVIDERS, QUERY_MAX, type GatewayConfig,
} from './config.js';
import { isStructuredFailure, runSearch, type DispatchOptions } from './orchestrator.js';
import { selectProviders } from './provider-selection.js';
import { summarizeError } from './errors.js';
import { truncate } from './normalize.js';
import { SERVER_NAME } from './server-info.js';
import {
  SEARCH_STRATEGIES,
  type AttemptRecord,
  type NormalizedSearchResult,
  type SearchProvider,
  type SearchRequest,
  type SearchStrategy,
} from './types.js';

export interface ToolOutput {
  content: { type: 'text'; text: string }[];
  isError?: boolean;
}

/**
 * The two tool names, once each. A definition and its dispatcher have to agree
 * on these strings, and they are written in different places — renaming a tool
 * in the schema while the dispatch still compares the old literal would leave
 * the tool listed but always answering "unknown tool", which is a confusing way
 * to discover the rename.
 */
const WEB_SEARCH = 'web_search';
const PROVIDER_STATUS = 'provider_status';

/** Search execution function signature (runSearch by default; injectable for tests). */
export type SearchFn = (
  req: SearchRequest,
  opts: DispatchOptions,
) => Promise<NormalizedSearchResult>;

/** Dependencies injected by the entry (keeps this module independently testable). */
export interface GatewayToolsDeps {
  /** Effective config (strategy, timeout, default result count, provider switches and
   *  priorities). */
  config: GatewayConfig;
  /** Adapters that can actually search, in priority order. */
  chain: SearchProvider[];
  /** Search implementation; defaults to the orchestrator's runSearch. */
  searchFn?: SearchFn;
}

/** Wrap any payload as a single JSON text content (flagged when isError is true). */
export function textContent(payload: unknown, isError = false): ToolOutput {
  return {
    content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }],
    ...(isError ? { isError: true } : {}),
  };
}

/**
 * Build the tool definitions. The default result count comes from config, so
 * the schema's default always matches actual behavior.
 */
export function buildToolDefinitions(defaultCount: number, defaultStrategy: SearchStrategy) {
  return [
    {
      name: WEB_SEARCH,
      description:
        'Search the web through any of the configured built-in search channels. '
        + "Two strategies: 'fallback' tries slots in your configured priority order and returns the first success; "
        + "'aggregate' queries several slots in parallel and merges the results (deduplicated by URL unless the dedupe "
        + 'setting is off, each item tagged with its source slot). Per-attempt timeout, with one retry after a '
        + 'transient failure (network error, HTTP 5xx, 429); an attempt that times out is never retried. '
        + 'Returns normalized results '
        + '{ title, url, snippet, content?, published_date?, source? } plus _meta with the answering slot(s), '
        + 'total latency, and a per-attempt audit trail.',
      inputSchema: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'The search query' },
          count: {
            type: 'integer',
            minimum: COUNT_MIN,
            maximum: COUNT_MAX,
            default: defaultCount,
            description: `Desired number of results; a value outside ${COUNT_MIN}-${COUNT_MAX} is clamped to that range rather than rejected, and a value that is not a number falls back to the configured default`,
          },
          strategy: {
            type: 'string',
            enum: SEARCH_STRATEGIES,
            default: defaultStrategy,
            description:
              "'fallback' = first provider that answers wins; 'aggregate' = query several providers and merge. "
              + 'Defaults to the configured strategy.',
          },
          providers: {
            type: 'array',
            items: { type: 'string', enum: KNOWN_PROVIDERS },
            description:
              'Optional subset of providers to use for this call, in priority order. '
              + 'Only providers that are enabled and have an API key can be selected.',
          },
        },
        required: ['query'],
      },
    },
    {
      name: PROVIDER_STATUS,
      description:
        'Read-only status: effective strategy and settings, plus which providers are enabled, have API keys and '
        + 'are part of the active search chain.',
      inputSchema: { type: 'object', properties: {} },
    },
  ] as const;
}

/** Validate the strategy argument: falls back to the configured default when not provided. */
function selectStrategy(requested: unknown, fallback: SearchStrategy): SearchStrategy | 'invalid' {
  if (requested === undefined) return fallback;
  const value = typeof requested === 'string' ? (requested.trim().toLowerCase() as SearchStrategy) : 'invalid';
  return (SEARCH_STRATEGIES as readonly string[]).includes(value) ? value : 'invalid';
}

export function createGatewayTools(deps: GatewayToolsDeps) {
  const { config } = deps;
  const chainNames = new Set(deps.chain.map((p) => p.name));
  const searchFn: SearchFn = deps.searchFn ?? runSearch;

  /**
   * Read-only status: config plus each provider's enabled/key/in-chain state
   * (keys are never echoed).
   */
  function providerStatus() {
    return {
      strategy: config.strategy,
      order: config.order,
      timeout_ms: config.timeoutMs,
      count: config.count,
      max_providers: config.maxProviders,
      dedupe: config.dedupe,
      config_file: config.configFile ?? null,
      providers: KNOWN_PROVIDERS.map((name) => {
        const p = config.providers[name];
        return {
          name,
          enabled: p.enabled,
          configured: p.apiKey.trim() !== '',
          in_chain: chainNames.has(name),
          priority: p.priority,
          model: p.model ?? null,
          timeout_ms: p.timeoutMs ?? null,
        };
      }),
    };
  }

  /**
   * Dispatch one tools/call request; structured error for unknown tools.
   *
   * `signal` is the MCP client's own cancellation signal: aborting it stops the
   * upstream search instead of running the whole fallback chain against a peer
   * that already gave up.
   */
  async function call(
    name: string,
    args: Record<string, unknown>,
    signal?: AbortSignal,
  ): Promise<ToolOutput> {
    if (name === PROVIDER_STATUS) {
      return textContent(providerStatus());
    }

    if (name === WEB_SEARCH) {
      const query = typeof args.query === 'string' ? args.query.trim() : '';
      if (!query) {
        return textContent({ error: "invalid arguments: 'query' must be a non-empty string" }, true);
      }
      const count = effectiveCount(args.count, config.count);
      const strategy = selectStrategy(args.strategy, config.strategy);
      if (strategy === 'invalid') {
        return textContent(
          { error: `invalid arguments: 'strategy' must be one of ${SEARCH_STRATEGIES.join(', ')}` },
          true,
        );
      }
      const selection = selectProviders(args.providers, deps.chain);
      if (!selection.ok) {
        return textContent({ error: selection.error }, true);
      }

      try {
        const result = await searchFn(
          { query: truncate(query, QUERY_MAX), count },
          {
            providers: selection.providers,
            timeoutMs: config.timeoutMs,
            maxProviders: config.maxProviders,
            dedupe: config.dedupe,
            strategy,
            signal,
          },
        );
        return textContent(result);
      } catch (err) {
        // The expected outcomes of a call — nobody was configured, every provider
        // failed, the caller went away — are answers, not crashes: each one
        // carries its audit trail and reaches the client as a structured error
        // instead of a log line. An empty chain in particular is the ordinary
        // state of a fresh install, not an unexpected failure. isStructuredFailure
        // is the one place that knows the full list, so a fourth outcome has to be
        // added there rather than in every renderer.
        if (isStructuredFailure(err)) {
          return textContent({ error: err.message, attempts: err.attempts }, true);
        }
        // Any other exception is unexpected: log the full error to stderr, return only a
        // redacted summary, so no code path can echo credential-looking text back to a client.
        console.error(`[${SERVER_NAME}] unexpected error:`, err);
        return textContent({ error: summarizeError(err), attempts: [] as AttemptRecord[] }, true);
      }
    }

    return textContent({ error: `unknown tool: ${name}` }, true);
  }

  return { list: () => buildToolDefinitions(config.count, config.strategy), call };
}
