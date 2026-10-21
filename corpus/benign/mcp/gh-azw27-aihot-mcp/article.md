# 给 Claude 接上实时财经数据：我写了个 MCP Server

> 5 分钟，让你的 AI 助手自己去看行情。

## 痛点

我用 Claude 写财经内容，每次都要手动贴新闻：

> "帮我看看今天 A股 有什么大事" → 我得先打开三个网站，复制十几条标题，再粘进去。

MCP（Model Context Protocol）出来之后，这件事可以彻底自动化——**让 Agent 自己去查**。

## 我做了什么

一个 MCP Server，把财经热点 API 包成 4 个工具：

| 工具 | 作用 |
|---|---|
| `get_hot` | 拉取分类热点（宏观/A股/美股/港股/商品/外汇）|
| `get_mood` | 市场情绪指数 0-100 |
| `search_news` | 关键词搜索 |
| `get_digest` | 生成今日简报 Markdown |

数据每 30 分钟更新，纯 Python 标准库，**不需要装任何依赖**。

## 3 步接上

### 第 1 步：拿 Key（30 秒）

```bash
curl -X POST "http://123.56.157.68/v1/trial?email=你的邮箱"
```

返回一串 `ah_` 开头的 Key，7 天免费，1000 次/天，不用绑卡。

### 第 2 步：克隆

```bash
git clone https://github.com/AZW27/aihot-mcp.git
```

### 第 3 步：改配置

Claude Desktop 的 `claude_desktop_config.json`：

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

重启 Claude，输入框旁边会出现工具图标。

## 实际用起来是什么样

> **我**：今天市场情绪怎么样？有什么值得关注的，帮我写个早报。
>
> **Claude**：*调用 get_mood、get_hot、get_digest*
>
> 情绪指数 50/100（中性）。今天最值得关注的三件事：
> 1. 德国央行警告通胀风险偏向上行
> 2. 白宫经济委员会：通胀似乎又回来了
> 3. 央行开展 800 亿逆回购，利率 1.40%
>
> 早报草稿：……

以前这活儿要 20 分钟，现在一句话。

## 为什么不用现成的新闻插件

- 中文财经信源，国外的插件基本没有；
- 情绪指数、事件聚簇这些**衍生指标**，比原始新闻有用；
- 自己部署，数据不过第三方。

## 还能接别的

同样的 MCP 配置，`Cursor`、`Codex`、任何支持 MCP 的客户端都能用。也可以直接连远程端点，不用本地跑：

```json
{"mcpServers":{"aihot-finance":{
  "url":"http://123.56.157.68/mcp",
  "headers":{"X-API-Key":"ah_你的Key"}}}}
```

## 最后

这套东西我自己天天在用。现在开放出来：

- 免费试用：<http://123.56.157.68/>
- 文档：<http://123.56.157.68/docs>
- 有问题加微信：`azw912722yi`

如果你也在做财经内容或者盯盘，欢迎试试，评论区告诉我你想加什么工具。
