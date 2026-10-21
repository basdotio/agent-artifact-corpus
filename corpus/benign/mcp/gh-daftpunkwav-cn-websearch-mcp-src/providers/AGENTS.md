# providers/ agent rules

The adapter contract and slot matrix live in [README.md](README.md).

## Shape

- One adapter file per slot. Export `create<Name>Provider(cfg: ProviderConfig): SearchProvider`.
- Keep the slot name in one module-level constant. Use it for `name` and for `_meta.provider`. That string matches the config key in `KNOWN_PROVIDERS`.
- `search` builds the request and parses the response. Leave the attempt budget, retry, fallback, aggregation, and the cancellation verdict to `orchestrator.ts`.
- A multi-round adapter rethrows an already-aborted `ctx.signal` before the next hop. `kimi.ts` does this in `throwIfAborted`.
- Send HTTP through `postJson` in `http.ts`.
- Import only lower layers: `types`, `errors`, `normalize`, `http`, and `config` types. Never import `orchestrator`, `runtime`, `tools`, `cli`, or a sibling adapter.
- Read channel-specific options from `ProviderConfig.options` and clamp them in the adapter. A new option is a field on that object.
- When adding or changing an adapter, record the upstream endpoint, the request fields, the response fields, and the date they were checked in the file header.

## Result metadata

- Set `_meta.provider` to the slot-name constant.
- Set `_meta.answer` only when the channel synthesizes an answer.
- Set `attempts` to `[]` and `total_latency_ms` to `0`. `orchestrator.ts` writes the real attempt trail and latency.

## Registry

- `index.ts` is the only registry. `FACTORIES` maps every `ProviderName` to its factory. `buildProviders` instantiates adapters in configured order.
- Enabled checks and API-key checks stay in `runtime.ts`.
- Inside `src/`, only `runtime.ts` imports `buildProviders`. Tests may import it.

## Adding a provider

- Add the adapter file in this directory.
- Add one `FACTORIES` entry in `index.ts`.
- Add the name to `KNOWN_PROVIDERS` in `config.ts`. `ProviderName` is derived from that array.
- Add a `PROVIDER_DEFAULTS` entry in `config.ts`. `baseUrl` is required. Set `model` and `openAiCompatible: true` on OpenAI-compatible slots only. REST slots omit `openAiCompatible`.
- `FACTORIES` and `PROVIDER_DEFAULTS` are `Record<ProviderName, …>`. A missing entry fails the build.
- Per-slot environment variables use `providerEnvKey` and `PROVIDER_ENV_SUFFIXES`. A new suffix is added there, not as its own parser branch.
- Keep the legacy `ZHIPU_SEARCH_ENGINE` name in `GATEWAY_ENV_KEYS`, in the `loadConfig` zhipu branch, and in the dotenv `SEARCH_ENGINE` recognizer.
- `baseUrl` normalization stays in `config.ts`. OpenAI-compatible slots use `ensureV1`. Other slots use trailing-slash trimming.
