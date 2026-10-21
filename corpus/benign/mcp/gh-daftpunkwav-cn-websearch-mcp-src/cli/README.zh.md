# src/cli/

包的终端界面。同一个既通过 stdio 提供 MCP 服务的 `dist/index.js` 二进制文件同时也是 CLI,因此无需接入 MCP 客户端即可搜索、探测各通道。

`index.ts` 中的 `runCli()` 是唯一入口:`src/index.ts` 注入真实的 runtime、进程流与 stdio serve 实现,然后把返回的退出码转换为进程退出。本目录的所有代码都经由注入的依赖驱动,因此测试可以在不起子进程的情况下跑通整个 CLI。

## 命令

| 命令 | 行为 |
|---|---|
| `serve`(默认) | 启动 MCP stdio server。无参数时隐含此命令,保持 MCP 客户端现有的启动方式不变。别名:`mcp`。 |
| `search <query...>` | 一次性搜索;打印格式化结果,`--json` 时输出原始 JSON。 |
| `status` | 打印生效配置与各槽位状态(密钥只报告是否已设置)。 |
| `test [provider...]` | 用真实请求对每个就绪通道探测一次(默认查询词:`今日新闻`,可用 `-q/--query` 覆盖);任一探测失败则退出码为 1。 |
| `repl` | 交互会话。别名:`shell`、`interactive`。 |
| `help` / `version` | 用法文本 / 身份信息行。 |

选项:`-n/--count <1-50>`、`--strategy fallback|aggregate`、`--providers a,b`(限定单次调用)、`--no-dedupe`、`-q/--query`、`--json`。取值型选项同时支持 `--flag value` 与 `--flag=value` 两种形式;`--no-dedupe` 与 `--json` 是开关,带内联值(`--json=false`)会被拒绝并以退出码 2 退出,而不是被静默忽略——要打开它只能不带值写这个 flag。

入参边界与 MCP 工具层一致:`count` 夹到 1-50,查询词截到 400 字符,`search` 与 `test` 同样适用。

退出码(`EXIT` 契约,由 `commands.ts` 定义并由 `index.ts` 再导出):`0` 成功,`1` 运行时失败(搜索失败 / 无可用通道),`2` 用法错误——脚本与 CI 可以据此分支。

## 文件一览

| 文件 | 职责 |
|---|---|
| `index.ts` | 分发:解析 argv、路由到各命令、把失败收敛为退出码。从不抛错。 |
| `args.ts` | 纯 argv 解析器:裸单词先解析为命令,其余拼接为查询词;未知命令/选项总是返回可读错误,不做猜测。 |
| `commands.ts` | 一次性命令实现(`cmdSearch`、`cmdStatus`、`cmdTest`):把 CLI 参数叠加到配置上并调用编排层;`pickProviders` 只是共享命名规则的一层薄封装。 |
| `repl.ts` | 交互式 readline 会话:裸文本即搜索,`/` 命令控制会话状态(`/strategy`、`/count`、`/providers`、`/json` 等)。输入行串行处理,并发搜索不会交错输出;单个失败只打印并继续。 |
| `render.ts` | 纯「数据 → 文本」渲染:结果列表、状态表、探测表,以及 `redactedConfig`(只报告密钥是否已设置,绝不输出内容)。 |

## 会话状态与配置的关系

`repl.ts` 的会话状态(strategy、count、通道过滤、输出格式)只保存在内存中。CLI 是配置的消费方——它从不回写 `cn-websearch.config.json` 或 `.env`。
