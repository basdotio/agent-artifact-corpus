/**
 * @file normalize
 * @description Field normalization helpers shared by all adapters.
 *
 * Responsibilities:
 * - Coerce raw provider fields into normalized result items
 * - Numeric clamping, string truncation, date and URL normalization
 * - Strip control characters from untrusted upstream text (single chokepoint in `str`)
 * - URL canonicalization and multi-source result merging (used by the aggregate strategy)
 * - Assert on payload shapes, throwing a readable ParseError with context on failure
 */

// Normalization helpers shared by the adapters. Every function is safe on
// garbage input: normalize what can be normalized, otherwise throw ParseError
// or return a fallback — never an unexpected exception.

import { ParseError, stripControlChars } from './errors.js';
import type { NormalizedItem } from './types.js';

/** Best-effort hostname extraction; returns an empty string on parse failure. */
export function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return '';
  }
}

/**
 * Read a number out of an untyped value, or NaN when nothing numeric was supplied.
 *
 * One rule for "is this a number here?", shared by clampInt below and by every
 * numeric setting in the config layer, because the layers disagree about almost
 * everything else: a config file may carry JSON numbers, a .env file can only
 * carry strings, and both funnel into these functions.
 *
 * A blank or whitespace-only string counts as "not supplied" rather than as
 * zero: `Number("")` is 0, which would silently make an empty `WEBSEARCH_COUNT=`
 * or `KIMI_PRIORITY=` a real value. A number and a non-blank numeric string both
 * count; nothing else does — notably `Number(true)` is 1, so a stray boolean
 * must not become a 1 ms budget with no warning at all.
 */
export function lenientInt(v: unknown): number {
  if (typeof v === 'number') return v;
  if (typeof v === 'string' && v.trim() !== '') return Number(v);
  return Number.NaN;
}

/**
 * Clamp to an integer in [min, max]; returns fallback when not parseable as a finite number.
 *
 * A blank or whitespace-only string counts as "not supplied" rather than as zero:
 * `Number("")` is 0, which would silently clamp such a value to `min` instead of
 * falling back, making "" and null — both meaning "no value given" — disagree.
 */
export function clampInt(
  v: unknown,
  fallback: number,
  min: number,
  max: number,
): number {
  const n = lenientInt(v);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, Math.round(n)));
}

/** Truncate overlong strings to max characters. */
export function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) : s;
}

/**
 * Non-empty string dates pass through; numbers are treated as unix seconds and
 * converted to ISO 8601.
 */
export function normalizeDate(d: unknown): string | undefined {
  if (typeof d === 'string' && d.trim() !== '') return stripControlChars(d).trim() || undefined;
  if (typeof d === 'number' && Number.isFinite(d)) {
    try {
      return new Date(d * 1000).toISOString();
    } catch {
      // toISOString throws RangeError when the number exceeds Date's range; treat as no date.
      return undefined;
    }
  }
  return undefined;
}

/**
 * Assert that an unknown parsed value is a plain object; throws a contextual
 * ParseError on failure.
 */
export function asObject(v: unknown, what: string): Record<string, unknown> {
  if (v && typeof v === 'object' && !Array.isArray(v)) return v as Record<string, unknown>;
  throw new ParseError(`${what}: expected object`);
}

/**
 * Lenient object getter: always returns undefined for non-objects, never
 * throws (for optional config values).
 */
export function maybeObject(v: unknown): Record<string, unknown> | undefined {
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : undefined;
}

/** Assert that an unknown parsed value is an array; throws a contextual ParseError on failure. */
export function asArray(v: unknown, what: string): unknown[] {
  if (Array.isArray(v)) return v;
  throw new ParseError(`${what}: expected array`);
}

/**
 * Safe string getter: returns an empty string for anything that is not a
 * string, control characters stripped.
 */
export function str(v: unknown): string {
  return typeof v === 'string' ? stripControlChars(v) : '';
}

/**
 * Drop a leading UTF-8 byte-order mark from text read off disk or off the wire.
 *
 * Editors on Windows commonly save with a BOM, and neither `JSON.parse` nor the
 * `.env` key parser tolerates one: without this the first key of a `.env` carries
 * an invisible prefix and never matches an env lookup, and a BOM'd JSON body is
 * rejected outright. The failure is silent in both cases — the file loads, the
 * value is simply never found — so the rule lives in one place rather than being
 * restated by each reader, where a variant would quietly stop covering one of
 * them. Three readers need it: the `.env` loader, the config file reader and the
 * HTTP body reader.
 */
export function stripBom(text: string): string {
  return text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
}

/**
 * Scheme syntax of RFC 3986 (`scheme ":" ...`). The negative lookahead keeps a
 * bare "host:port/path" on the path that gets the https:// prefix: the digits
 * after the colon are a port there, not a scheme.
 */
const URL_SCHEME = /^[a-z][a-z0-9+.-]*:(?!\d)/i;

/**
 * The only protocols a result URL may use. Every field this gateway normalizes
 * is handed to an MCP client or a terminal that turns a URL into a live link,
 * and a script-executing scheme (`javascript:`, `data:`, `vbscript:`) would
 * then run in that consumer's context. A web search returns web pages, so any
 * other scheme is data this tool has no business passing along.
 */
const ALLOWED_PROTOCOLS: ReadonlySet<string> = new Set(['http:', 'https:']);

/**
 * Canonicalize one upstream reference's URL, or return null when the value must
 * not become a link: a value that already carries a scheme is kept verbatim, a
 * protocol-relative "//host/path" gets the scheme only, and a bare host gets
 * "https://" in front.
 *
 * The result is then re-read through the URL parser instead of trusting the
 * syntax test alone. The parser deletes tab and newline before it looks at the
 * scheme, so "java\tscript:alert(1)" is a javascript: URL even though the regex
 * above sees no scheme at all — checking `protocol` there closes that gap and
 * every other way a crafted reference could slip past.
 */
export function normalizeUrl(url: string): string | null {
  const raw = url.trim();
  if (!raw) return null;
  let candidate: string;
  if (raw.startsWith('//')) candidate = `https:${raw}`;
  else if (URL_SCHEME.test(raw)) candidate = raw;
  else candidate = `https://${raw}`;
  try {
    return ALLOWED_PROTOCOLS.has(new URL(candidate).protocol) ? candidate : null;
  } catch {
    return null;
  }
}

/**
 * Normalize a raw search item into a NormalizedItem. `url` is required —
 * items without a URL, or whose URL is not an http(s) link, are dropped
 * outright, never fabricated and never passed on as a clickable scheme.
 */
export function toItem(raw: {
  title?: unknown;
  url?: unknown;
  snippet?: unknown;
  content?: unknown;
  published_date?: unknown;
}): NormalizedItem | null {
  const url = str(raw.url).trim();
  if (!url) return null;
  const urlNorm = normalizeUrl(url);
  if (!urlNorm) return null;
  const item: NormalizedItem = {
    title: str(raw.title).trim() || hostnameOf(urlNorm),
    url: urlNorm,
    snippet: str(raw.snippet).trim(),
  };
  const content = str(raw.content).trim();
  if (content) item.content = content;
  const date = normalizeDate(raw.published_date);
  if (date) item.published_date = date;
  return item;
}

/**
 * Common tracking/share parameters: the same article often yields multiple
 * distinct URLs because of them, so aggregate dedupe must ignore them.
 * Deliberately conservative — only well-known tracking keys are listed,
 * avoiding accidental removal of semantic parameters.
 */
const TRACKING_PARAM = /^(utm_|spm|scm$|share_|gclid$|fbclid$|_hs(enc|mi)$|mc_(cid|eid)$|ref$|ref_|fr$)/i;

/**
 * Produce the canonical form of a URL for dedupe: strip the fragment,
 * tracking parameters, and the trailing slash on the root path. Returns the
 * trimmed original when the URL cannot be parsed — prefer under-merging
 * to wrong merging.
 */
export function canonicalUrl(url: string): string {
  const raw = url.trim();
  try {
    const u = new URL(raw);
    u.hash = '';
    // Collect the survivors and rewrite the query once, instead of calling
    // searchParams.delete() per matching key: that method is not a list edit but
    // a URL mutation, and the URL binding runs the "update steps" on every one —
    // re-serializing the whole parameter list back into the URL. Deleting k keys
    // from a URL carrying P of them therefore costs O(P*k), which on a tracking-
    // heavy link (every key matching, so k = P) is quadratic in the query length:
    // measured on this Node line, a URL with 8000 utm_* parameters took 9.0 s
    // to canonicalize, and the 8 MB body cap admits one with ~800000. One
    // rewrite costs the same O(P) the single delete already did, and the result
    // is byte-identical because the surviving pairs are re-serialized by the
    // same code that used to.
    const kept: [string, string][] = [];
    let removed = false;
    for (const [key, value] of u.searchParams) {
      if (TRACKING_PARAM.test(key)) removed = true;
      else kept.push([key, value]);
    }
    if (removed) u.search = new URLSearchParams(kept).toString();
    const out = u.toString();
    // "https://a.com/" and "https://a.com" are the same resource.
    return u.pathname === '/' && u.search === '' ? out.replace(/\/$/, '') : out;
  } catch {
    return raw;
  }
}

/**
 * Merge two items with the same URL, keeping the more informative one.
 * title/url follow the first arrival (the higher-priority provider);
 * snippet/content take the longer; published_date takes the first non-empty;
 * source keeps the first origin to preserve attributability.
 */
export function mergeItems(a: NormalizedItem, b: NormalizedItem): NormalizedItem {
  const longer = (x: string, y: string): string => (y.length > x.length ? y : x);
  const merged: NormalizedItem = {
    title: a.title || b.title,
    url: a.url,
    snippet: longer(a.snippet, b.snippet),
  };
  const content = longer(a.content ?? '', b.content ?? '');
  if (content) merged.content = content;
  const date = a.published_date ?? b.published_date;
  if (date) merged.published_date = date;
  const source = a.source ?? b.source;
  if (source) merged.source = source;
  return merged;
}

/**
 * Multi-source result merge. The order of `sources` is the priority order and
 * decides which entry wins as the primary body for the same URL. With dedupe
 * disabled, only source tags are added, no merging.
 */
export function mergeSourceItems(
  sources: { provider: string; items: NormalizedItem[] }[],
  dedupe = true,
): NormalizedItem[] {
  if (!dedupe) {
    return sources.flatMap((s) => s.items.map(
      (item) => ({ ...item, source: item.source ?? s.provider }),
    ));
  }
  const seenAt = new Map<string, number>();
  const merged: NormalizedItem[] = [];
  for (const s of sources) {
    for (const item of s.items) {
      const tagged: NormalizedItem = item.source ? item : { ...item, source: s.provider };
      const key = canonicalUrl(tagged.url);
      const at = seenAt.get(key);
      if (at === undefined) {
        seenAt.set(key, merged.length);
        merged.push(tagged);
      } else {
        merged[at] = mergeItems(merged[at]!, tagged);
      }
    }
  }
  return merged;
}
