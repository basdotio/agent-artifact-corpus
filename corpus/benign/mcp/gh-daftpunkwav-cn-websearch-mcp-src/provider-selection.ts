/**
 * @file provider-selection
 * @description The one rule for turning a requested provider list into usable
 *   adapters.
 *
 * Responsibilities:
 * - Normalize requested names (trim, lowercase, drop blanks, dedupe, keep order)
 * - Reject unknown names and names that are not in the usable chain, with a message
 *   naming the problem
 * - Resolve an ordered subset of the chain for the MCP tool layer, the one-shot CLI
 *   and the REPL
 *
 * Design notes:
 * - This lives in its own module because three surfaces (MCP tools, one-shot
 *   CLI, REPL) must agree on the same rules; keeping one implementation means a
 *   new rule cannot be applied to two of them and forgotten on the third
 * - It only knows the chain it is handed, so the MCP tool layer stays free of
 *   any concrete provider adapter
 */

import { KNOWN_PROVIDERS, type ProviderName } from './config.js';
import type { SearchProvider } from './types.js';

/**
 * Provider selection result: adapters on success, or an error ready to return
 * to the caller on failure.
 */
export type ProviderSelection = (
  | { ok: true; providers: SearchProvider[] }
  | { ok: false; error: string }
);

/** Result of validating a bare list of names, before the chain is consulted. */
export type ProviderNameSelection = (
  | { ok: true; names: ProviderName[] }
  | { ok: false; error: string }
);

/** Trim, lowercase, drop blanks and dedupe while preserving first-occurrence order. */
function normalizeNames(parts: unknown[]): string[] {
  return [...new Set(
    parts.map((p) => (typeof p === 'string' ? p : '').trim().toLowerCase()).filter((p) => p !== ''),
  )];
}

function unknownNamesError(names: string[]): string | undefined {
  const unknown = names.filter((n) => !(KNOWN_PROVIDERS as readonly string[]).includes(n));
  return unknown.length
    ? `unknown provider(s): ${unknown.join(', ')} (known: ${KNOWN_PROVIDERS.join(', ')})`
    : undefined;
}

/**
 * Parse a comma-separated provider list as typed by a user (REPL `/providers`).
 * An empty result is an error: it would otherwise mean "no filter" while
 * looking like a filter, so callers handle "no filter" with an absent argument.
 */
export function parseProviderNames(raw: string): ProviderNameSelection {
  const names = normalizeNames(raw.split(','));
  if (!names.length) return { ok: false, error: 'provider list must not be empty' };
  const error = unknownNamesError(names);
  return error ? { ok: false, error } : { ok: true, names: names as ProviderName[] };
}

/**
 * Filter usable adapters by a requested name subset. Fails explicitly instead
 * of silently ignoring: the caller named specific providers, so an unmet
 * request must be reported back. An absent argument means "use the chain".
 */
export function selectProviders(requested: unknown, chain: SearchProvider[]): ProviderSelection {
  if (requested === undefined) return { ok: true, providers: chain };
  if (!Array.isArray(requested) || requested.some((x) => typeof x !== 'string')) {
    return { ok: false, error: "invalid arguments: 'providers' must be an array of provider names" };
  }
  const names = normalizeNames(requested);
  if (!names.length) return { ok: false, error: "invalid arguments: 'providers' must not be empty" };

  const unknown = unknownNamesError(names);
  if (unknown) return { ok: false, error: unknown };

  const byName = new Map(chain.map((p) => [p.name, p]));
  const unavailable = names.filter((n) => !byName.has(n));
  if (unavailable.length) {
    // The chain it is handed does not record why a slot is missing from it, and
    // there are three reasons: disabled, no API key, or left out of an explicit
    // order (runtime builds the chain from that list alone). Naming only the
    // first two would send an operator to debug a key and an enabled switch that
    // were both fine.
    return {
      ok: false,
      error: `provider(s) unavailable: ${unavailable.join(', ')} `
        + '(not in the active chain: disabled, no API key, or excluded by the configured order)',
    };
  }
  return { ok: true, providers: names.map((n) => byName.get(n)!) };
}
