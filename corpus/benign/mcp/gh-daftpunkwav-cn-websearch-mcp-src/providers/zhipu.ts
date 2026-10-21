/**
 * @file providers/zhipu
 * @description Zhipu GLM adapter: the standalone Web Search API.
 *
 * Responsibilities:
 * - POST {base}/api/paas/v4/web_search (docs checked on 2026-09-15)
 * - Map search_result[] entries {title,link,content,publish_date} to items
 * - Truncate search_query to 70 characters and clamp count to 1..50
 * - Configurable options: searchEngine, contentSize
 */

// Zhipu GLM adapter: the standalone Web Search API on open.bigmodel.cn.
//
// Basis (checked on 2026-09-15):
//   https://docs.bigmodel.cn/api-reference/工具-api/网络搜索
//   POST {base}/api/paas/v4/web_search, Bearer auth; returns a structured
//   search_result array: { title, content, link, media, icon, refer, publish_date }.
//
// Note: `web_search_prime` (with a `location: cn|us` parameter) is actually a
// remote MCP tool of the GLM Coding Plan (the mcp-broker endpoint), not the
// platform chat tools API — the platform chat tool is plain `web_search` with
// no location knob. The standalone Web Search API above is the documented,
// structured, model-independent path, and is what this adapter uses.

import {
  asArray, asObject, clampInt, str, toItem, truncate,
} from '../normalize.js';
import { postJson } from '../http.js';
import type {
  NormalizedSearchResult, SearchContext, SearchProvider, SearchRequest,
} from '../types.js';
import type { ProviderConfig } from '../config.js';

/**
 * This adapter's name, and the config key / `_meta.provider` stamp that must
 * agree with it: the registry, the chain filter and every result label key on
 * this one value, so a second hand-written copy could drift silently.
 */
const NAME = 'zhipu';

export default function createZhipuProvider(cfg: ProviderConfig): SearchProvider {
  return {
    name: NAME,
    timeoutMs: cfg.timeoutMs,
    async search(req: SearchRequest, ctx: SearchContext): Promise<NormalizedSearchResult> {
      const { options } = cfg;
      const payload = {
        // Per the API docs, search_query is capped at 70 characters.
        search_query: truncate(req.query, 70),
        search_engine: str(options?.searchEngine).trim() || 'search_std',
        search_intent: false,
        count: clampInt(req.count, 10, 1, 50),
        content_size: str(options?.contentSize).trim() || 'high',
      };
      const res = await postJson(
        `${cfg.baseUrl}/api/paas/v4/web_search`,
        payload,
        { Authorization: `Bearer ${cfg.apiKey}` },
        { timeoutMs: ctx.timeoutMs, signal: ctx.signal, fetchImpl: ctx.fetchImpl },
      );
      const body = asObject(res.json, 'zhipu response');
      const hits = asArray(body.search_result, 'zhipu search_result');
      // A malformed single hit affects only that hit: degrade to an empty
      // object and let toItem decide.
      const results = hits
        .map((hit) => {
          const fields = (hit && typeof hit === 'object' ? hit : {}) as Record<string, unknown>;
          const content = str(fields.content).trim();
          return toItem({
            title: fields.title,
            url: fields.link,
            snippet: truncate(content, 300),
            content,
            published_date: fields.publish_date,
          });
        })
        .filter((item): item is NonNullable<typeof item> => item !== null)
        .slice(0, req.count);
      return { results, _meta: { provider: NAME, total_latency_ms: 0, attempts: [] } };
    },
  };
}
