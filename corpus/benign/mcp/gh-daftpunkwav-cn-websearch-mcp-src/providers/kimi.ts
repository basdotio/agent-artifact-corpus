/**
 * @file providers/kimi
 * @description Moonshot Kimi adapter: the four-step web-search formula loop.
 *
 * Responsibilities:
 * - Declare the web_search tool; execute tool_calls via the web-search fiber
 * - Pass reasoning_content back on the assistant turn (a hard requirement for K2.5/K2.6)
 * - Collect the final answer and turn deduplicated fiber reference URLs into result items
 * - Configurable options: maxRounds, maxTokens
 */

// Moonshot Kimi adapter: the web-search "formula" on top of the OpenAI chat format.
//
// Why this flow is needed: Kimi's built-in $web_search channel is currently unavailable
// (officially marked "under upgrade"; the various echo variants all return empty results), and
// the anthropic gateway silently ignores the native server tool. The only officially working
// path is the four-step loop:
//   1. Call chat/completions with a web_search function tool declaration
//   2. The model returns tool_calls
//   3. Each tool_call is executed server-side via
//      POST /formulas/moonshot/web-search:latest/fibers
//      (encrypted_output comes back, with plaintext references attached)
//   4. After appending the tool outputs, send one more chat call to produce the final answer
//
// K2.5/K2.6 thinking mode requires the assistant turn to pass reasoning_content back,
// otherwise the server rejects subsequent requests.

import {
  asObject, asArray, clampInt, str, toItem,
} from '../normalize.js';
import { postJson } from '../http.js';
import { ParseError } from '../errors.js';
import type {
  NormalizedItem, NormalizedSearchResult, SearchContext, SearchProvider, SearchRequest,
} from '../types.js';
import type { ProviderConfig } from '../config.js';

const WEB_SEARCH_URI = 'moonshot/web-search:latest';
const DEFAULT_MAX_ROUNDS = 2;
const DEFAULT_MAX_TOKENS = 8192;

/**
 * This adapter's name, and the config key / `_meta.provider` stamp that must
 * agree with it: the registry, the chain filter and every result label key on
 * this one value, so a second hand-written copy could drift silently.
 */
const NAME = 'kimi';

const WEB_SEARCH_TOOL = {
  type: 'function',
  function: {
    name: 'web_search',
    description: '用于信息检索的网络搜索',
    parameters: {
      type: 'object',
      properties: { query: { type: 'string', description: '要搜索的内容' } },
      required: ['query'],
    },
  },
};

interface ChatMessage {
  role: string;
  content: string | null;
  tool_calls?: unknown[];
  tool_call_id?: string;
  reasoning_content?: string;
}

/** Calls chat/completions once and extracts the first choice's message. */
async function chat(
  cfg: ProviderConfig,
  messages: ChatMessage[],
  ctx: SearchContext,
  opts: { withTools: boolean; maxTokens: number },
): Promise<ChatMessage> {
  const res = await postJson(
    `${cfg.baseUrl}/chat/completions`,
    {
      model: cfg.model ?? 'kimi-k3',
      messages,
      max_tokens: opts.maxTokens,
      ...(opts.withTools ? { tools: [WEB_SEARCH_TOOL] } : {}),
    },
    { Authorization: `Bearer ${cfg.apiKey}` },
    { timeoutMs: ctx.timeoutMs, signal: ctx.signal, fetchImpl: ctx.fetchImpl },
  );
  const body = asObject(res.json, 'kimi chat response');
  const choices = asArray(body.choices, 'kimi choices');
  const choice = asObject(choices[0] ?? null, 'kimi choice');
  return asObject(choice.message ?? null, 'kimi message') as unknown as ChatMessage;
}

/** Executes a single tool_call server-side; returns the fiber context. */
async function runFiber(
  cfg: ProviderConfig,
  name: string,
  args: string,
  ctx: SearchContext,
): Promise<Record<string, unknown>> {
  const res = await postJson(
    `${cfg.baseUrl}/formulas/${WEB_SEARCH_URI}/fibers`,
    { name, arguments: args },
    { Authorization: `Bearer ${cfg.apiKey}` },
    { timeoutMs: ctx.timeoutMs, signal: ctx.signal, fetchImpl: ctx.fetchImpl },
  );
  const body = asObject(res.json, 'kimi fiber response');
  return asObject(body.context ?? {}, 'kimi fiber context');
}

/**
 * Extracts reference URLs from the fiber context; returns an empty array on
 * malformed structure instead of throwing.
 */
function urlsFromFiber(fiberContext: Record<string, unknown>): string[] {
  const refs = fiberContext.references;
  if (!Array.isArray(refs)) return [];
  const urls: string[] = [];
  for (const ref of refs) {
    if (typeof ref === 'string') urls.push(ref);
    else if (ref && typeof ref === 'object' && typeof (ref as { url?: unknown }).url === 'string') {
      urls.push((ref as { url: string }).url);
    }
  }
  return urls;
}

/** Checks for abort before each network call; if aborted, rethrows the abort reason as-is. */
function throwIfAborted(ctx: SearchContext): void {
  if (ctx.signal.aborted) {
    throw ctx.signal.reason instanceof Error ? ctx.signal.reason : new ParseError('aborted before completion');
  }
}

export default function createKimiProvider(cfg: ProviderConfig): SearchProvider {
  return {
    name: NAME,
    timeoutMs: cfg.timeoutMs,
    async search(req: SearchRequest, ctx: SearchContext): Promise<NormalizedSearchResult> {
      const maxRounds = clampInt(cfg.options?.maxRounds, DEFAULT_MAX_ROUNDS, 1, 5);
      const maxTokens = clampInt(cfg.options?.maxTokens, DEFAULT_MAX_TOKENS, 256, 32_768);
      const messages: ChatMessage[] = [{ role: 'user', content: req.query }];
      const urls: string[] = [];
      let answer = '';

      // Four-step loop: at most maxRounds rounds; if the last round still returns tool_calls,
      // drop tools and issue one more chat call to force a final answer.
      for (let round = 0; round < maxRounds; round += 1) {
        throwIfAborted(ctx);
        const message = await chat(cfg, messages, ctx, { withTools: true, maxTokens });
        const toolCalls = Array.isArray(message.tool_calls) ? message.tool_calls : [];
        if (!toolCalls.length) {
          answer = str(message.content).trim();
          break;
        }
        // In thinking mode the server requires the assistant turn to pass
        // reasoning_content back verbatim.
        const assistant: ChatMessage = { role: 'assistant', content: message.content ?? null, tool_calls: toolCalls };
        if (message.reasoning_content) assistant.reasoning_content = message.reasoning_content;
        messages.push(assistant);
        for (const rawCall of toolCalls) {
          const call = asObject(rawCall, 'kimi tool_call');
          const fn = asObject(call.function ?? null, 'kimi tool_call.function');
          throwIfAborted(ctx);
          const fiberContext = await runFiber(cfg, str(fn.name), str(fn.arguments), ctx);
          // Appended one at a time rather than with push(...refs): the spread
          // passes every reference as a call argument, and the engine's
          // argument stack overflows around 125k of them. A fiber that
          // references that many pages is a ~4MB body, which the 8MB response
          // cap admits — so the spread would turn a large-but-legal upstream
          // response into a RangeError instead of results.
          for (const url of urlsFromFiber(fiberContext)) urls.push(url);
          const output = str(fiberContext.encrypted_output) || str(fiberContext.output);
          messages.push({ role: 'tool', content: output, tool_call_id: str(call.id) });
        }
        if (round === maxRounds - 1) {
          throwIfAborted(ctx);
          const final = await chat(cfg, messages, ctx, { withTools: false, maxTokens });
          answer = str(final.content).trim();
        }
      }

      // Dedupe fiber reference URLs and cap at the requested count; the URL is
      // the only trustworthy field.
      const seen = new Set<string>();
      const results: NormalizedItem[] = [];
      for (const url of urls) {
        const item = toItem({ url });
        // Key on the normalized URL actually emitted, so a bare-host reference
        // and its absolute twin collapse instead of yielding the same item twice.
        if (!item || seen.has(item.url)) continue;
        seen.add(item.url);
        results.push(item);
        if (results.length >= req.count) break;
      }
      return {
        results,
        _meta: {
          provider: NAME, total_latency_ms: 0, attempts: [], answer: answer || undefined,
        },
      };
    },
  };
}
