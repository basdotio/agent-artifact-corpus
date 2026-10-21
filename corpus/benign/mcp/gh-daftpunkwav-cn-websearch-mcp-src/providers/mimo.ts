/**
 * @file providers/mimo
 * @description Xiaomi MiMo adapter: web_search over OpenAI chat completions.
 *
 * Responsibilities:
 * - Send the request shape the channel expects (tools[0].type=web_search, limit=count)
 * - Merge url_citation titles and web_search_highlight snippets by URL
 * - Expose the LLM's synthesized answer via _meta.answer
 * - Configurable options: location, maxKeyword, forceSearch
 */

// Xiaomi MiMo adapter: server-side web_search over OpenAI chat completions.
//
// MiMo offers web search only on the OpenAI chat completions format
// (neither responses nor the anthropic gateway supports it). The response is the LLM's
// synthesized answer plus structured references in message.annotations:
//   { type: "url_citation", title, url }
//   { type: "web_search_highlight", title /* highlighted text */, url }
//
// Location parameters always come from config; when unset, only the country level is given.

import {
  hostnameOf, asObject, asArray, clampInt, maybeObject, normalizeUrl, str,
} from '../normalize.js';
import { postJson } from '../http.js';
import type {
  NormalizedItem, NormalizedSearchResult, SearchContext, SearchProvider, SearchRequest,
} from '../types.js';
import type { ProviderConfig } from '../config.js';

interface Annotation {
  type?: unknown;
  title?: unknown;
  url?: unknown;
}

/**
 * This adapter's name, and the config key / `_meta.provider` stamp that must
 * agree with it: the registry, the chain filter and every result label key on
 * this one value, so a second hand-written copy could drift silently.
 */
const NAME = 'mimo';

/**
 * Merges url_citation (title) and web_search_highlight (snippet) entries by URL.
 *
 * The two annotation kinds can arrive in either order, so a hostname placeholder
 * is recorded explicitly: whenever a real title shows up later it must replace
 * the placeholder instead of being dropped by a non-empty check.
 */
function itemsFromAnnotations(annotations: unknown[]): NormalizedItem[] {
  const byUrl = new Map<string, NormalizedItem>();
  const placeholderTitles = new Set<string>();
  for (const raw of annotations) {
    // One malformed entry must not sink the whole citation list: a null element
    // carries no fields at all, and a non-object one carries none we can read.
    const annotation: Annotation | undefined = maybeObject(raw);
    if (!annotation) continue;
    const url = str(annotation.url).trim();
    if (!url) continue;
    // Same rule as every other adapter: a reference that is not an http(s)
    // link never reaches the client as a clickable URL.
    const urlNorm = normalizeUrl(url);
    if (!urlNorm) continue;
    const kind = str(annotation.type);
    const title = str(annotation.title).trim();
    const existing = byUrl.get(urlNorm);
    if (kind === 'url_citation') {
      if (existing) {
        if (title && placeholderTitles.delete(urlNorm)) existing.title = title;
      } else {
        byUrl.set(urlNorm, { title: title || hostnameOf(urlNorm), url: urlNorm, snippet: '' });
        if (!title) placeholderTitles.add(urlNorm);
      }
    } else if (kind === 'web_search_highlight') {
      if (existing) {
        if (!existing.snippet && title) existing.snippet = title;
      } else if (title) {
        byUrl.set(urlNorm, { title: hostnameOf(urlNorm), url: urlNorm, snippet: title });
        placeholderTitles.add(urlNorm);
      }
    }
  }
  return [...byUrl.values()];
}

/**
 * Assemble the user_location parameter. Fill only the levels explicitly given in config; the
 * open-source adapter deliberately does not guess a city when unset.
 */
function userLocation(options: Record<string, unknown> | undefined): Record<string, unknown> {
  const loc = maybeObject(options?.location);
  const location: Record<string, unknown> = { type: 'approximate' };
  const country = str(loc?.country).trim() || 'China';
  location.country = country;
  for (const key of ['region', 'city'] as const) {
    const value = str(loc?.[key]).trim();
    if (value) location[key] = value;
  }
  return location;
}

export default function createMimoProvider(cfg: ProviderConfig): SearchProvider {
  return {
    name: NAME,
    timeoutMs: cfg.timeoutMs,
    async search(req: SearchRequest, ctx: SearchContext): Promise<NormalizedSearchResult> {
      const { options } = cfg;
      // `limit` (max result pages) is the channel's closest knob to `count`. This
      // mapping is an assumption that should be revisited if the upstream
      // semantics change.
      const limit = clampInt(req.count, 1, 1, 10);
      const payload = {
        model: cfg.model ?? 'mimo-v2.5',
        messages: [{ role: 'user', content: req.query }],
        max_completion_tokens: 2048,
        stream: false,
        extra_body: { thinking: { type: 'disabled' } },
        tools: [
          {
            type: 'web_search',
            max_keyword: clampInt(options?.maxKeyword, 3, 1, 10),
            force_search: options?.forceSearch !== false,
            limit,
            user_location: userLocation(options),
          },
        ],
        tool_choice: 'auto',
      };
      const res = await postJson(
        `${cfg.baseUrl}/chat/completions`,
        payload,
        { Authorization: `Bearer ${cfg.apiKey}` },
        { timeoutMs: ctx.timeoutMs, signal: ctx.signal, fetchImpl: ctx.fetchImpl },
      );
      const body = asObject(res.json, 'mimo response');
      const choices = asArray(body.choices, 'mimo choices');
      const choice = asObject(choices[0] ?? null, 'mimo choice');
      const message = asObject(choice.message ?? null, 'mimo message');
      const answer = str(message.content).trim();
      // Treat missing or non-array annotations as empty: the answer still
      // works, just without references.
      const annotations = Array.isArray(message.annotations)
        ? (message.annotations as unknown[])
        : [];
      const results = itemsFromAnnotations(annotations).slice(0, req.count);
      return {
        results,
        _meta: {
          provider: NAME, total_latency_ms: 0, attempts: [], answer: answer || undefined,
        },
      };
    },
  };
}
