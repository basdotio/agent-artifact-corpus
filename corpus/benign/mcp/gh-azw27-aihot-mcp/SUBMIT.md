# 发布清单（照做即可）

## 0. 我需要什么

| 需要 | 用途 |
|---|---|
| GitHub 用户名 | 建仓库地址 |
| 一个 **Personal Access Token**（细粒度，勾 `repo` + `workflow`）| 我直接 push 代码、开 PR |
| 或者：你自己 git push | 我把文件给你，你执行两条命令 |

其余目录站（Smithery / mcp.so / PulseMCP）大多用 GitHub 登录一键提交，我给你填好的文案。

---

## 1. 建 GitHub 仓库

- 仓库名：`aihot-mcp`
- 描述：`Finance hot news & market sentiment as MCP tools for AI agents`
- 可见性：**Public**
- 初始化：不要加 README（我们要自己传）

Topics 填：

```
mcp mcp-server finance stocks news ai-agent claude cursor
```

---

## 2. 推代码（二选一）

**A. 给我 token，我来推**

**B. 你自己执行：**

```bash
cd aihot-mcp
git init
git add .
git commit -m "feat: finance hot news MCP server"
git branch -M main
git remote add origin https://github.com/AZW27/aihot-mcp.git
git push -u origin main
```

---

## 3. 提交 awesome-mcp-servers（流量最大的一步）

仓库：<https://github.com/punkpeye/awesome-mcp-servers>

找到 **Finance** 分类，加一行（按字母序插入）：

```markdown
- [aihot-finance](https://github.com/AZW27/aihot-mcp) - Real-time Chinese finance news, market sentiment index (0-100), event clustering and auto-generated daily digest for AI agents.
```

PR 标题：

```
Add aihot-finance MCP server (finance news + sentiment)
```

PR 描述：

```markdown
## What
An MCP server that gives agents real-time Chinese finance news and derived signals.

## Tools
- `get_hot` — top finance news by category (macro / A-share / US / HK / commodities / FX)
- `get_mood` — market sentiment index 0–100 computed from a positive/negative lexicon
- `search_news` — keyword search
- `get_digest` — auto-generated daily digest in Markdown

## Notes
- No third-party Python deps; stdlib only
- Data refreshes every 30 min
- Free 7-day trial key, no card required
- Returns aggregated titles + links, not full-text copies
```

---

## 4. 其他目录（GitHub 登录，1 分钟一个）

| 站点 | 地址 | 做法 |
|---|---|---|
| Smithery | <https://smithery.ai> | 用 GitHub 登录 → Add Server → 填仓库地址 |
| mcp.so | <https://mcp.so/submit> | 填 GitHub 地址 + 一句话描述 |
| PulseMCP | <https://www.pulsemcp.com/submit> | 同上 |
| Glama | <https://glama.ai/mcp/servers> | 自动抓取 GitHub，无需提交 |

**通用一句话描述：**

> Real-time Chinese finance news, market sentiment index and auto digest, exposed as MCP tools.

---

## 5. 教程文章（转化率最高）

已写好：`article.md`

发布渠道优先级：

1. **掘金**（搜索流量长尾）
2. **V2EX 分享创造**
3. **小红书**（改成图文，标题党一点）
4. **公众号**（沉淀私域）

文章里所有 `http://123.56.157.68` 都指向你的 API，末尾留微信 `azw912722yi`。

---

## 6. 发完之后盯三个数

| 指标 | 及格 | 说明 |
|---|---|---|
| GitHub star | 20/周 | 低于 10 说明定位不准 |
| 试用 Key 申请 | 30/周 | 来自 `/v1/trial` |
| 加微信 | 5/周 | 真正的付费信号 |

低于及格线，别加功能，改文案和人群。
