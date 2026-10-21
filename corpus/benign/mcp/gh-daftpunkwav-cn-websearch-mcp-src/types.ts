/**
 * @file types
 * @description Shared type contracts and vocabulary for the gateway (no imports, no I/O).
 *
 * Responsibilities:
 * - Define the normalized search result shape, per-attempt audit records, and merged
 *   multi-source metadata
 * - Define the search strategies, the search adapter interface, and the injectable search context
 * - Depend on no internal module itself; shared by the HTTP, normalization, orchestration,
 *   adapter and tool layers
 *
 * Design notes:
 * - It carries no logic, but it does own vocabulary: a name that more than one surface has to
 *   agree on lives here as a value, next to the type derived from it (see SEARCH_STRATEGIES).
 */

/** Injectable fetch implementation so tests can mock HTTP without real keys. */
export type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;

/**
 * Search strategies:
 * - `fallback`: try providers in priority order, return on the first success
 *   (fewer calls, lower latency)
 * - `aggregate`: query several providers in parallel, merge and dedupe for broader coverage
 *
 * This list is the single source of the vocabulary. The type below is derived from it, so the
 * type and the runtime list cannot drift, and every surface that enumerates or validates a
 * strategy — config parsing, the MCP tool schema, the `--strategy` flag, the REPL — reads this
 * one array instead of restating the names. It lives here rather than in the config layer so
 * that the argument parser, which must stay a dependency-free leaf, reaches the rule directly.
 */
export const SEARCH_STRATEGIES = ['fallback', 'aggregate'] as const;

export type SearchStrategy = (typeof SEARCH_STRATEGIES)[number];

/**
 * Search-argument bounds shared by every entry surface.
 *
 * Vocabulary rather than logic, and it lives here for the reason above: the
 * argument parser must stay a dependency-free leaf, yet it prints this range in
 * its help text, so the numbers it shows have to be the same ones the MCP tool
 * schema declares instead of a second hand-typed copy that drifts. The rule
 * that applies them (effectiveCount) stays in the config layer.
 */
export const COUNT_MIN = 1;
export const COUNT_MAX = 50;
export const QUERY_MAX = 400;

export interface SearchRequest {
  query: string;
  /** Desired result count, normalized by the tool layer; defaults from configuration. */
  count: number;
}

export interface NormalizedItem {
  title: string;
  /**
   * Always an `http:` or `https:` link, already canonicalized: a bare host gains
   * an `https://` prefix, a protocol-relative reference gains a scheme, and
   * anything else is kept verbatim. Non-http(s) references are never emitted —
   * normalizeUrl returns null for them and the whole item is dropped, so a
   * downstream implementation must never assign an arbitrary string here.
   */
  url: string;
  snippet: string;
  /** Body excerpt when the provider returns full text. */
  content?: string;
  published_date?: string;
  /** Provider that supplied this item; filled by the orchestrator only in aggregate mode. */
  source?: string;
}

export type AttemptStatus = 'ok' | 'timeout' | 'transient_error' | 'permanent_error' | 'cancelled';

/**
 * One row of the audit trail of a web_search call.
 *
 * `status` is the verdict of that single attempt, and a client can act on it:
 * "ok" carries no error, "timeout" means the wall-clock budget was spent (never
 * retried, whoever raised it), "transient_error" is the only retryable verdict,
 * and "cancelled" means the caller went away rather than the channel failing.
 */
export interface AttemptRecord {
  provider: string;
  status: AttemptStatus;
  latency_ms: number;
  /** Error summary. Must never contain keys or other sensitive material. */
  error?: string;
}

export interface ResultMeta {
  /** The first (highest-priority) provider that answered successfully. */
  provider: string;
  /**
   * All providers that answered successfully; one item for single-source,
   * several under aggregate.
   */
  providers?: string[];
  total_latency_ms: number;
  attempts: AttemptRecord[];
  /** Answer text when the provider works by LLM synthesis (kimi, mimo). */
  answer?: string;
}

export interface NormalizedSearchResult {
  results: NormalizedItem[];
  _meta: ResultMeta;
}

export interface SearchContext {
  /**
   * Wall-clock budget for a single search attempt, enforced by the orchestrator
   * through an abort signal. Note: a retry gets its own equal budget, and
   * adapters (e.g. kimi's multi-round HTTP calls) also use it as the
   * per-HTTP-request timeout cap. A shorter per-request cap of an adapter's own
   * would therefore still be a spent budget: a TimeoutError is never retried.
   */
  timeoutMs: number;
  /**
   * Aborted when the budget is exhausted or the caller goes away (MCP client
   * cancellation). The orchestrator merges both, so an adapter only has to
   * forward this signal to the HTTP layer.
   */
  signal: AbortSignal;
  fetchImpl: FetchLike;
}

export interface SearchProvider {
  readonly name: string;
  /** Per-provider timeout budget (ms); falls back to the global budget when unset. */
  readonly timeoutMs?: number;
  /**
   * Perform one logical search. Implementations must stay thin: request
   * construction and response parsing only; timeout, retry and fallback
   * are always the orchestrator's job. The returned _meta must carry
   * provider (and answer, where applicable); attempts and total_latency_ms
   * are filled in by the orchestrator.
   *
   * Whether a provider may search at all is not answered here: it needs the
   * `enabled` switch and the API key, which runtime.ts owns and filters on.
   */
  search(req: SearchRequest, ctx: SearchContext): Promise<NormalizedSearchResult>;
}
