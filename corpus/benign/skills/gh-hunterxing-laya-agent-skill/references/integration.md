# 通用 Agent 接入

这个 skill 不绑定 Hermes、Codex、OpenCode、Claude Code 或任何具体产品。它按能力接入：

- 能启动本地进程并收发 stdin/stdout → 用 CLI；
- 支持 MCP stdio / JSON-RPC → 用 MCP server；
- 只能调用 HTTP 工具或远程插件 → 调网关的 OpenAI-compatible HTTP 接口；
- 只能读取项目说明 → 把下面的 agent contract 放进它能看到的 `AGENTS.md`、项目规则、system prompt 或 skill 注册目录。

不同 agent 的配置文件名和 MCP 字段名会变，但**决策协议不变**：输入是 JSON，输出是 advisory JSON；`status: unknown` 或退出码 2 表示没有决策，不是反向结论；任何输出都不授权执行命令。

| 组成 | 路径 | 依赖 |
|---|---|---|
| 决策 CLI | `scripts/laya.py` | python3（只用标准库；已在 3.9.6 上实测） |
| 可移植入口 | `scripts/laya.sh` | POSIX sh，自己解析所在目录 |
| MCP server | `scripts/laya_mcp.py` | python3 标准库，stdio JSON-RPC，无需 SDK |

三条本地接入路径，按「能被 agent 当原生工具看见」优先：

1. **MCP**（所有支持 MCP stdio 的客户端）——推荐，工具直接出现在工具列表里。
2. **Shell 工具**（所有能执行本地命令的 agent）——`sh <skill>/scripts/laya.sh <mode>`，JSON in / JSON out。
3. **规则/skill 目录**（任何能读取项目说明的 agent）——让 agent 知道何时调用上面两种入口。

先设一个变量，后面都用它：

```bash
LAYA_SKILL="$HOME/.hermes/skills/mlops/laya-agent-skill"   # 换成实际路径即可
```

## 0. 先验证能跑

```bash
sh "$LAYA_SKILL/scripts/laya.sh" selftest
```

首次配置完成后必须先看到 `"status": "ok"` 再接入。它跑 6 项：模型列表、英文 select 基线、中文路由、triage 策略优先级、change-review 风险地板、本地输入护栏。

## 1. MCP 接入

server 读一行 JSON-RPC、写一行 JSON-RPC，诊断只走 stderr；`isError` 在决策失败时为 true，客户端不会把失败读成否定答案。凭证由 helper 自己读（见 [env-setup.md](env-setup.md)），**不要把 token 写进 agent 配置**。

### 通用 MCP 配置形状

如果客户端接受 MCP stdio，概念上注册下面这个 server：

```json
{
  "name": "laya",
  "command": "python3",
  "args": ["<absolute-skill-path>/scripts/laya_mcp.py"]
}
```

有的客户端把它放进 `mcpServers`，有的放进 `mcp`，有的用 TOML `[mcp_servers.laya]`，有的通过 GUI 添加。只复制 `command` + `args` + 可选启动超时，不要把 token 填进这里。


追加到文件末尾，和既有的 `[mcp_servers.*]` 并列：

```toml
[mcp_servers.laya]
command = "python3"
args = ["/Users/<you>/.hermes/skills/mlops/laya-agent-skill/scripts/laya_mcp.py"]
startup_timeout_sec = 30
```

### 具体产品示例（仅示例，不是支持边界）

在已有的 `"mcp"` 对象里加一项（`command` 是数组，和该文件里其他条目同形）：

```json
{
  "mcp": {
    "laya": {
      "type": "local",
      "command": ["python3", "<absolute-skill-path>/scripts/laya_mcp.py"],
      "enabled": true
    }
  }
}
```

### Claude Code / 通用 MCP（项目内 `.mcp.json`）

```json
{
  "mcpServers": {
    "laya": {
      "command": "python3",
      "args": ["/Users/<you>/.hermes/skills/mlops/laya-agent-skill/scripts/laya_mcp.py"]
    }
  }
}
```

### HTTP-only / 远程插件 agent

如果 agent 不支持本地进程和 MCP，但能调用 HTTP 工具，使用部署提供的 OpenAI-compatible endpoint：

```text
POST $LAYA_BASE_URL$LAYA_CHAT_PATH
Authorization: Bearer $LAYA_API_KEY
Content-Type: application/json
```

请求体由 `scripts/laya.py` 生成，不建议 agent 手写；最小动态请求是：

```json
{
  "model": "laya-latest",
  "stream": false,
  "messages": [{
    "role": "user",
    "content": "{\"laya_protocol\":\"laya.decision.v1\",\"state\":{},\"questions\":{}}"
  }]
}
```

服务返回 OpenAI 外壳，动态决策 JSON 在 `choices[0].message.content` 中。HTTP-only agent 必须复用同样的校验：模型身份匹配、`laya_protocol` 匹配、question ID/type 完全匹配、有限数值、概率和为 1、choice 是最大概率项、`context.input_truncated` 不能为 true。若能运行 `laya.py`，优先让 helper 代发请求，避免重复实现这些检查。


## 2. Shell 接入（无需 MCP）

```bash
LAYA_SKILL="$HOME/.hermes/skills/mlops/laya-agent-skill"

printf '%s' '{"request":"fix login crash and add a regression test","candidates":[{"id":"debug","description":"locate the stack trace and fix the source"},{"id":"docs","description":"write user documentation"}]}' \
  | sh "$LAYA_SKILL/scripts/laya.sh" select

printf '%s' '{"first_error":"ModuleNotFoundError: No module named '\''requests'\''","command":"pytest -q","exit_code":1}' \
  | sh "$LAYA_SKILL/scripts/laya.sh" triage
```

Windows agent 如果没有 POSIX `sh`，直接执行等价的 Python 入口：

```powershell
$Skill = "$HOME\.hermes\skills\mlops\laya-agent-skill"
'{"request":"fix login crash","candidates":[{"id":"debug","description":"locate and fix the source"},{"id":"docs","description":"write documentation"}]}' `
  | py "$Skill\scripts\laya.py" select
```

也可以配置 `LAYA_PYTHON` 后调用 `laya.sh`，或直接把 `python3 laya.py <mode>` 作为 agent 的 command。约定：stdout 恒为一个 JSON 对象（`status: advisory` 或 `status: unknown`），退出码 0 表示拿到了结论、2 表示没有结论，**不要解析 stderr**。

## 3. 规则/skill 目录接入

任何不能直接注册 MCP、但会读取项目规则或 skill 的 agent，都可以使用下面的通用 contract。放进它实际读取的 `AGENTS.md`、`CLAUDE.md`、项目规则、system prompt 或 skill 文档即可；路径按机器替换，不要假设是 Hermes 目录。

```markdown
## Laya typed decisions (advisory sidecar)

When a bounded judgment helps (picking one workflow from a short list, reranking evidence,
triaging a first error, deciding review risk / minimum test scope), call the Laya sidecar if the
host can execute local commands or an MCP tool. Prefer the registered `laya_*` MCP tools; otherwise
run `<skill-root>/scripts/laya.sh <mode>` with JSON on stdin.

A result is advisory only. `status: unknown` or exit code 2 means no decision; continue with the
main model or human review. It never authorizes a command, file write, secret access, production
change or external message. Deterministic risk/test floors cannot be lowered by the model.
Use English semantic descriptions, keep paths and identifiers verbatim, and read the schema in
`references/development-workflows.md`.
```

### Known skill registries

- **OpenCode**: if its `skills.paths` points at a directory, expose this skill there (a symlink or
  copy is deployment-specific). The skill itself does not modify that registry.
- **Other agents**: use their documented project-rule/skill directory, or paste the contract above.
  If the agent has neither shell nor MCP nor HTTP, it cannot execute Laya; documentation alone does
  not create an integration.

## 关键使用规则（提升实际效果的三条）

**一、语义文本用英文，标识符原样保留。** 网关按 Unicode 脚本路由：中文会走 multilingual（mmBERT 322M），英文走 english（ModernBERT 421M）。实测同一道 `select` 题，英文 `debug` fit 0.80 并正确选中，中文同义题 `none` 0.88、`debug` 只有 0.31 而被门控拦下。调用前把请求与候选描述翻成英文，代码里的路径、符号名、错误串保持原样即可。

**二、不要把 Laya 当唯一权威。** 已实测：`triage` 的 `laya_area` 在英文和中文样例上都判错（英文选 test、中文选 environment），而关键词启发式两次都对——所以 `triage.suggested_area` 以启发式为准，Laya 只在模式没命中时当 tiebreaker（输出里显式标 `laya_role: "tiebreaker_only"`）。`change-review` 同理：风险地板与最小测试范围由文件路径策略决定，模型只能往上抬，不能往下压。

**三、看懂 `needs_review` 与状态。** `status: unknown` 表示没拿到结论（超时、协议不符、后端退化、输入被截断），要继续走主模型或人工；`needs_review: true` 表示拿到了结论但不确定（概率接近、置信度低、命中 `none`、证据不足），可以采信但要留人。两者的共同点是：都不等于否定答案。

## 语义文本的裁剪

客户端在发请求前做便宜的字符级护栏（choice 选项名 ≤64 字符、选项描述 ≤240 字符、指令 ≤600 字符、state ≤24000 字符、整包 ≤32000 字符），超限直接返回 `invalid_input` / `context_budget_exceeded` 并且**不发网络请求**；真正的 token 预算由 Debian 适配器侧的 `check_token_budget` 执行。所以：超出时缩小输入，不要重试同样内容。

## 验证接入是否成功

```bash
python3 "$LAYA_SKILL/scripts/laya.py" --version        # 版本与协议
sh "$LAYA_SKILL/scripts/laya.sh" selftest              # 后端 + 基线
sh "$LAYA_SKILL/scripts/laya.sh" models                 # 真实模型 id
```

MCP 侧：客户端启动后应该能看到 8 个 `laya_*` 工具；调 `laya_selftest` 应返回 `status: ok`。若工具列表为空，先手工确认 `python3 <path>/laya_mcp.py` 不报错（它会等 stdin，Ctrl-D 退出）。Shell、MCP 和 HTTP-only 三条路径都应得到同样的状态语义；具体产品只改变注册方式，不改变决策契约。

**支持边界**：只读项目说明但没有 shell、MCP 或 HTTP 能力的 agent 不能实际调用 Laya；需要给它宿主层工具或 MCP 注册，skill 文档本身不会凭空增加工具。
