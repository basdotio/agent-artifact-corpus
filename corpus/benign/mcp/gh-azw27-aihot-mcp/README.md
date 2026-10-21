# aihot-finance MCP Server

把**实时财经热点**接进 AI Agent：市场情绪指数、事件聚簇、关键词搜索、一键日报。

> 数据每 30 分钟更新一次，覆盖宏观 / A股 / 美股 / 港股 / 商品 / 外汇。

## 它能让 Agent 做什么

| 工具 | 作用 | 例子 |
|---|---|---|
| `get_hot` | 拉取财经热点 | "今天 A股 有什么大事？" |
| `get_mood` | 市场情绪指数 0-100 | "现在市场偏乐观还是恐慌？" |
| `search_news` | 按关键词搜快讯 | "最近关于降息的消息" |
| `get_digest` | 生成今日简报（Markdown）| "帮我写今天的财经早报" |

## 安装

```bash
git clone https://github.com/AZW27/aihot-mcp.git
cd aihot-mcp
```

只需要 Python 3.8+，**没有第三方依赖**。

## 配置

### Claude Desktop

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "aihot-finance": {
      "command": "python",
      "args": ["/绝对路径/aihot-mcp/server.py"],
      "env": { "AIHOT_API_KEY": "ah_你的Key" }
    }
  }
}
```

### Cursor / Codex / 其他客户端

同理，配置一个 stdio MCP server，命令 `python /path/to/server.py`，环境变量 `AIHOT_API_KEY`。

### 直接连远程 HTTP 端点

不想本地跑也行：

```json
{
  "mcpServers": {
    "aihot-finance": {
      "url": "http://123.56.157.68/mcp",
      "headers": { "X-API-Key": "ah_你的Key" }
    }
  }
}
```

## 获取 API Key

免费试用 7 天（1000 次/天），不用绑卡：

```bash
curl -X POST "http://123.56.157.68/v1/trial?email=you@example.com"
```

返回：

```json
{"key":"ah_...","plan":"trial","daily_limit":1000,"expires_at":"..."}
```

## 示例对话

> **你**：今天市场情绪怎么样？有什么值得关注的？
>
> **Agent**：*调用 get_mood → get_hot*
> 情绪指数 50/100（中性）。热榜第一是"德国央行：德国通胀风险明显偏向上行"……

## 接口

除了 MCP，也提供普通 REST API：

- `GET /v1/hot`、`/v1/top`、`/v1/search`、`/v1/mood`、`/v1/clusters`、`/v1/spikes`、`/v1/digest`
- `POST /v1/watch` 关键词 Webhook 推送
- 文档：<http://123.56.157.68/docs>

## 说明

- 返回的是**聚合标题 + 链接 + 自行计算的指标**，不复制原文，原文链接指向来源站点；
- 数据来源：华尔街见闻公开快讯；
- 本项目只包含 MCP 适配层，数据服务由 API 提供。

## License

MIT
