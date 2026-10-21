# src/providers/

逐通道适配器。每个上游搜索 API 的 wire 格式各不相同;每个适配器把自己通道的请求/响应翻译成 `src/types.ts` 中共享的 `SearchProvider` 契约,因此编排层、工具层与 CLI 永远看不到通道特定的结构。

## 适配器契约

适配器是一个工厂函数 `create<Name>Provider(cfg: ProviderConfig): SearchProvider`:

- `name` —— 字面槽位名(同时也是配置键与 `source` 标签)。
- `timeoutMs` —— 可选的单槽位超时预算覆盖;未设置时回退到全局 `timeoutMs`。
- `search(req, ctx)` —— 一次逻辑搜索。实现保持单薄:只做请求构造与响应解析。超时、重试、fallback 与聚合始终是编排层的职责。返回的 `_meta` 携带 `provider`(在通道会合成答案时还有 `answer`);`attempts` 与 `total_latency_ms` 由编排层填充。

## 注册表

`index.ts` 是唯一的注册表:`FACTORIES` 映射把每个 `ProviderName` 绑定到对应工厂,`buildProviders()` 按配置顺序实例化适配器。是否启用/是否有密钥的检查刻意留给调用方(`runtime.ts`)。

新增一个通道需要:此处一个适配器文件 + `FACTORIES` 中一行 + `KNOWN_PROVIDERS` 中的一个名字**以及** `PROVIDER_DEFAULTS` 中对应的中立默认值(后两者都在 `src/config.ts`)。两个映射都是 `Record<ProviderName, …>` 类型,漏项会在编译期报错而不是首次运行时。`<NAME>_*` 环境变量按名字自动推导,无需改动任何解析分支。

## 槽位矩阵

| 槽位 | Wire 通道 | 结果条目 | `_meta.answer` |
|---|---|---|---|
| `kimi.ts` | chat-completions,声明 `web_search` 函数工具;tool call 通过 `POST {base}/v1/formulas/moonshot/web-search:latest/fibers` 执行;fiber 上下文中的参考 URL 成为结果条目(仅有 URL 的条目) | fiber 上下文中的参考 URL | LLM 合成的最终答案 |
| `mimo.ts` | chat-completions,带服务端 `web_search` 工具(`tools[0].type = "web_search"`);`message.annotations` 携带 `url_citation` / `web_search_highlight`,按 URL 合并为条目 | 按 URL 合并的 annotations | LLM message content |
| `stepfun.ts` | 独立搜索 REST 端点:`POST {base}/v1/search`,请求体 `{ query, n, category? }` | `results[]`:title、time、snippet、全文 `content` | — |
| `zhipu.ts` | 独立联网搜索 API:`POST {base}/api/paas/v4/web_search` | `search_result[]`:title、link、摘要→snippet、全文 `content`、`publish_date` | — |

矩阵中的 `{base}` 指配置的 `baseUrl`;对 chat-completions 通道(`kimi`、`mimo`),它会被规范化为以 `/v1` 结尾(`src/config.ts` 的 `ensureV1`),因此其请求路径始终带 `/v1` 前缀。

每个适配器在自己的文件头注释中记录了上游依据(端点、请求/响应字段、核对的日期);这些注释是 wire 映射的权威参考。通道特定的 `options`(最大轮数/令牌数、location、category、搜索引擎等)从 `ProviderConfig.options` 读取,并在适配器内部做钳制。
