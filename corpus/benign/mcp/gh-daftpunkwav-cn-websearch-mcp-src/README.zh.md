# src/

包的全部运行时代码,使用 TypeScript 编写,由 `tsc` 编译到 `dist/`(ESM,`"type": "module"`)。同一棵源码树支撑两个入口形态:MCP stdio server 与 CLI——两者都从同一个 runtime 装配而成(见下文「运行时装配」)。

## 模块一览

| 文件 | 职责 |
|---|---|
| `types.ts` | 共享契约:`SearchProvider`、`SearchRequest`、`NormalizedSearchResult`、`AttemptRecord`、`SearchContext`,以及各入口面据以校验的 `SEARCH_STRATEGIES` 词表。无 import、无 I/O、无分支;它位于被统计的覆盖率树内,且自身保持 100%。 |
| `errors.ts` | 错误分类(`TimeoutError`、`NetworkError`、`HttpError`、`ParseError`)、瞬时/永久失败判定,以及用于生成不含密钥的审计文本的 `redactSecrets` / `summarizeError`。 |
| `normalize.ts` | 所有适配器共享的字段归一化:`toItem`、`clampInt`、`truncate`、`normalizeDate`、结构断言(`asObject` / `asArray`)、不可信上游文本的控制字符剥离、URL 规范化与多来源合并(`mergeSourceItems`)。 |
| `config-file.ts` | 仅负责配置文件 I/O:定位(`WEBSEARCH_CONFIG` 或 cwd 下的 `cn-websearch.config.json`)、检查体积上限、解析 JSON。从不做语义校验、从不抛错——失败只告警并返回 `undefined`。 |
| `config.ts` | 配置解析:把「内置默认值 → 配置文件 → 环境变量」合并为 `GatewayConfig`。每个值都宽松解析(非法输入告警并回退);任意一层的空值视为「未设置」;超时值有上限。定义 `KNOWN_PROVIDERS`、中立的每槽位默认值,以及工具层与 CLI 共用的搜索入参边界(`COUNT_MIN` / `COUNT_MAX` / `QUERY_MAX`)。 |
| `dotenv.ts` | 极简 `.env` 加载器(零依赖):有体积上限,只导出网关读取的变量名,且从不覆盖已存在的 `process.env` 条目。 |
| `http.ts` | 共享 JSON POST 辅助:把调用方 signal 与每请求超时合并(兼容 Node 18),限制响应体的缓冲量,把失败映射到错误分类,上游响应体在进入错误消息前完成脱敏。 |
| `orchestrator.ts` | 搜索编排:`runSearch` 按策略分发;`searchWithFallback` 依次遍历链路,`searchAggregate` 并行调用各通道并合并。独占每次尝试的墙钟预算、单次瞬时重试与 `_meta.attempts` 审计轨迹。 |
| `probe.ts` | 单通道在线探测(`probeProvider`),以数据行代替抛错返回;`probeAll` 顺序执行探测。CLI `test` 命令与 `scripts/smoke.ts` 共用。 |
| `providers/` | 各通道适配器(`kimi`、`mimo`、`stepfun`、`zhipu`)与工厂注册表。见 [providers/README.zh.md](providers/README.zh.md)。 |
| `provider-selection.ts` | 把请求的通道名列表解析为可用适配器的唯一规则;由 `tools.ts` 与 `cli/` 共用。 |
| `runtime.ts` | 唯一的运行时装配点:解析配置文件、加载配置、构建全部适配器、计算可用链路(已启用 + 有密钥)。从不抛错——配置问题只告警。 |
| `tools.ts` | MCP 工具层:`web_search` 与 `provider_status` 的定义、参数校验、分发到编排层、结构化错误输出。仅依赖注入的 deps。 |
| `server-info.ts` | `SERVER_NAME` / `SERVER_VERSION` 常量;`test/server-info.test.ts` 断言其与 `package.json` 一致。 |
| `index.ts` | 进程入口:加载 `.env`、装配 runtime、把 MCP SDK 的处理器绑定到工具层、把 argv 交给 CLI。所有实质逻辑都在其他模块中。 |
| `cli/` | 终端界面:参数解析、一次性命令、交互会话、渲染。见 [cli/README.zh.md](cli/README.zh.md)。 |

## 分层

依赖单向指向,下层从不引用上层:

```
index.ts ─┬─→ tools.ts ─────────┐
          ├─→ cli/ ─────────────┤
          └─→ runtime.ts ─→ providers/ ─┐
                            orchestrator ┤
                            probe ───────┤
                            config ──────┤
                  config-file ┤         │
                  dotenv ─────┤         │
                  provider-   ┤         │
                  selection ──┘         │
                            http ────────┤
                            normalize ───┤
                            errors ──────┘
                                     types.ts(纯契约,被所有层引用)
```

- `types.ts` / `errors.ts` / `normalize.ts` / `config-file.ts` 构成底层:它们不引用任何上层,内部依赖边只有指向 `errors.ts` 的两条(`normalize.ts` → `errors.ts` 与 `config-file.ts` → `errors.ts`)。全树只有 `config-file.ts`(自己的配置文件)与 `dotenv.ts`(`.env`)触碰磁盘。
- 其上为 `config.ts` 与 `http.ts`。
- `provider-selection.ts` 与 `config.ts` 同层:它只需要已知通道名与适配器接口,由顶层共用而非只服务一个调用方。
- `orchestrator.ts` 与 `probe.ts` 负责协调适配器;适配器保持单薄(只做请求构造与响应解析)。
- `runtime.ts` / `tools.ts` / `cli/` 位于顶层:消费装配好的依赖,从不自行重建。

## 运行时装配

`runtime.ts` 中的 `createRuntime()` 是唯一的组合点。MCP 入口(`src/index.ts`)与 CLI 共用同一个装配,因此两个界面看到的生效配置与通道链路完全一致。配置文件读取与文件存在性检查均可注入,使得每个分支都无需触碰磁盘即可测试。

只有当某通道已启用**且** API key 非空时,它才参与搜索;`runtime.chain` 按解析出的优先级顺序恰好保存这些适配器。没有密钥的通道会被自动跳过,而不是导致调用失败。
