# src/providers/

Per-channel adapters. Each upstream search API speaks a different wire format;
every adapter translates its channel's request/response into the shared
`SearchProvider` contract from `src/types.ts`, so the orchestrator, tools and
CLI never see channel-specific shapes.

## The adapter contract

An adapter is a factory `create<Name>Provider(cfg: ProviderConfig): SearchProvider`:

- `name` — the literal slot name (also the config key and the `source` tag).
- `timeoutMs` — optional per-slot budget override; falls back to the global
  `timeoutMs` when unset.
- `search(req, ctx)` — one logical search. Implementations stay thin:
  request construction and response parsing only. Timeout, retry, fallback
  and aggregation are always the orchestrator's job. The returned `_meta`
  carries `provider` (and `answer` where the channel synthesizes one); the
  orchestrator fills `attempts` and `total_latency_ms`.

## Registry

`index.ts` is the only registry: the `FACTORIES` map binds each
`ProviderName` to its factory, and `buildProviders()` instantiates adapters in
the configured order. Enabled/key checks are deliberately left to the caller
(`runtime.ts`).

Adding a provider takes: one adapter file here + one line in `FACTORIES` + the
name in `KNOWN_PROVIDERS` **and** its neutral defaults in `PROVIDER_DEFAULTS`
(both in `src/config.ts`). Both maps are typed `Record<ProviderName, …>`, so a
missing entry fails the build rather than the first run. The `<NAME>_*`
environment variables are derived from the name automatically, so no parsing
branches change.

## Slot matrix

| Slot | Wire channel | Result items | `_meta.answer` |
|---|---|---|---|
| `kimi.ts` | chat-completions with a declared `web_search` function tool; tool calls execute against `POST {base}/v1/formulas/moonshot/web-search:latest/fibers`; the fiber context's reference URLs become result items (URL-only items) | reference URLs from the fiber context | LLM-synthesized final answer |
| `mimo.ts` | chat-completions with a server-side `web_search` tool (`tools[0].type = "web_search"`); `message.annotations` carry `url_citation` / `web_search_highlight` entries, merged by URL into items | annotations merged by URL | LLM message content |
| `stepfun.ts` | Standalone search REST endpoint: `POST {base}/v1/search` with `{ query, n, category? }` | `results[]`: title, time, snippet, full-text `content` | — |
| `zhipu.ts` | Standalone web-search API: `POST {base}/api/paas/v4/web_search` | `search_result[]`: title, link, summary→snippet, full-text `content`, `publish_date` | — |

`{base}` above is the configured `baseUrl`; for the chat-completions
channels (`kimi`, `mimo`) it is normalized to end with `/v1` (`ensureV1` in
`src/config.ts`), so their request paths always carry the `/v1` prefix.

Each adapter documents its upstream basis (endpoint, request/response fields,
checked date) in the header comment of its own file; those comments are the
authoritative reference for the wire mapping. Channel-specific `options`
(max rounds/tokens, location, category, search engine, …) are read from
`ProviderConfig.options` and clamped inside the adapter.
