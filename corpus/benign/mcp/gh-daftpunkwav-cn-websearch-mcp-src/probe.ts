/**
 * @file probe
 * @description Single-provider probe: one live call plus a structured result row.
 *
 * Responsibilities:
 * - Call a single provider with an independent timeout, returning a data row on success or
 *   failure instead of throwing
 * - Provide one shared implementation for the CLI's `test` command and `npm run smoke`
 */

// Probe logic lives in its own module so the CLI and the smoke script share one implementation.

import { summarizeError, TimeoutError } from './errors.js';
import type { FetchLike, SearchProvider, SearchRequest } from './types.js';

export interface ProbeOptions {
  timeoutMs: number;
  fetchImpl?: FetchLike;
}

/** Probe result row for a single provider. */
export interface ProbeRow {
  provider: string;
  ok: boolean;
  latency_ms: number;
  /**
   * How many results the channel returned. A count, not the results
   * themselves — `cmdTest` serializes this row verbatim under `--json`, so the
   * name is part of that output's field names.
   */
  results: number;
  /**
   * Title of the first result (on success), for eyeballing whether the channel
   * really works: the first result's title capped at SAMPLE_TITLE_MAX, or
   * "(no results)" when the channel answered with an empty list.
   */
  sample: string;
  /** Failure summary; empty string on success. */
  error: string;
}

/** Sample-title cap: enough to recognize the channel's first hit in a table row, not a preview. */
const SAMPLE_TITLE_MAX = 60;

/**
 * Probe one provider. Any failure (network, timeout, protocol, parsing) is
 * converted into a row with ok=false and never thrown — the whole point of a
 * probe is to find the broken provider.
 *
 * An answer that only arrives after this probe's own deadline is a failure, not
 * a success: a channel that reliably blows its budget must not be reported
 * healthy, because `test` exits 0 on it and the caller then trusts a channel
 * that cannot answer in time.
 */
export async function probeProvider(
  p: SearchProvider,
  req: SearchRequest,
  opts: ProbeOptions,
): Promise<ProbeRow> {
  const ac = new AbortController();
  const timer = setTimeout(() => {
    ac.abort(new TimeoutError());
  }, opts.timeoutMs);
  const t0 = Date.now();
  try {
    const result = await p.search(req, {
      timeoutMs: opts.timeoutMs,
      signal: ac.signal,
      fetchImpl: opts.fetchImpl ?? fetch,
    });
    if (ac.signal.aborted) {
      throw ac.signal.reason instanceof Error ? ac.signal.reason : new TimeoutError();
    }
    return {
      provider: p.name,
      ok: true,
      latency_ms: Date.now() - t0,
      results: result.results.length,
      sample: result.results[0]?.title?.slice(0, SAMPLE_TITLE_MAX) ?? '(no results)',
      error: '',
    };
  } catch (err) {
    return {
      provider: p.name,
      ok: false,
      latency_ms: Date.now() - t0,
      results: 0,
      sample: '',
      error: summarizeError(err),
    };
  } finally {
    clearTimeout(timer);
  }
}

/** Probe a group of providers sequentially (avoids saturating every upstream quota at once). */
export async function probeAll(
  providers: SearchProvider[],
  req: SearchRequest,
  opts: ProbeOptions,
): Promise<ProbeRow[]> {
  const rows: ProbeRow[] = [];
  for (const p of providers) {
    rows.push(await probeProvider(p, req, opts));
  }
  return rows;
}
