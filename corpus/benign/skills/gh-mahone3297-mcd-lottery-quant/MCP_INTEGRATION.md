# MCP 接入说明

本项目的全部结论都建立在麦当劳 MCP 的只读数据上。这份文档说清楚：连了什么、
调了什么、怎么调、以及过程中踩到的坑。

---

## 1. 服务端

| 项 | 值 |
|---|---|
| 名称 | 麦当劳 MCP Server（`mcd-mcp`） |
| 协议 | MCP Streamable HTTP |
| 地址 | `https://mcp.mcd.cn` |
| 鉴权 | 请求头 `Authorization: Bearer <Token>` |
| 协议版本 | `2025-06-18` |
| Token 申请 | https://open.mcd.cn/mcp |

会话握手走标准的 `initialize` → `notifications/initialized`，
服务端返回的 `Mcp-Session-Id` 由客户端透传到后续请求。

客户端实现在 `mcd_quant/client.py`，**只用 Python 标准库**（`urllib` + `json`），
不依赖任何 SDK。响应兼容 `text/event-stream`（SSE）与纯 JSON 两种形态。

### Token 怎么交给程序

按「`--token` → 环境变量 `MCD_MCP_TOKEN`」的顺序取，先取到先用：

```bash
python run.py --live --token 你的Token     # 推荐：跨 shell 通用
```

> ⚠️ **Windows 高频坑**：`set MCD_MCP_TOKEN=xxx` **只有 `cmd.exe` 认**。
> 在 PowerShell 里 `set` 是 `Set-Variable` 的别名，它不会创建环境变量，
> 而是造出一个名叫 `MCD_MCP_TOKEN=xxx`、值为空 的 PowerShell 变量，
> **不报错也不提示**，看着像成功了，实际 `$env:MCD_MCP_TOKEN` 仍是空的。
> Git Bash 同理（bash 的 `set X=Y` 只是设位置参数）。
> 正确的写法是 `$env:MCD_MCP_TOKEN="xxx"`（PowerShell）或 `export ...`（bash）。
>
> 程序在取不到 Token 时会打印一份按 shell 区分的设置指引并以退出码 2 结束，
> 不用自己去猜是哪儿写错了。另外 `resolve_token()` 会自动剥掉一层引号和首尾空白，
> 所以 `set MCD_MCP_TOKEN="abc"` 这种把引号一起存进去的写法也能救回来。

---

## 2. 用到的工具

### 2.1 `query-lottery-info` —— 抽奖活动（核心输入）

**入参**：无

**实际返回**（2026-10-09 原样截取）：

```json
{
  "activityName": "麦麦积分抽奖",
  "activityStatusText": "进行中",
  "beginTime": "2025-01-26 00:00:00",
  "endTime": "2030-12-31 23:59:59",
  "drawPoint": "24",
  "drawTypeText": "消耗积分抽奖",
  "availablePoint": "0",
  "drawDecision": {
    "resourceEligible": false,
    "reason": "积分不足",
    "nextConsumption": { "type": "POINTS", "points": "24", "text": "本次将消耗 24 积分" }
  },
  "prizes": [
    { "name": "下单立减3元券", "imageUrl": "https://img.mcd.cn/...", "typeText": "优惠券" },
    { "name": "麦辣三件套5折券", "imageUrl": "https://img.mcd.cn/...", "typeText": "优惠券" },
    { "name": "30积分", "imageUrl": "https://img.mcd.cn/...", "typeText": "积分奖" }
  ]
}
```

**关键观察：`prizes` 只有名称、图片、类型 —— 没有中奖概率。**

这一条决定了整个项目的设计。见第 5 节。

### 2.2 `mall-points-products` —— 积分商城（价值锚）

**入参**：无。（支持 `catRuleIds` 按类目筛选，本项目要全量，不传。）

**实际返回**（截取 2 条）：

```json
[
  {
    "spuName": "6.9元可乐麦炫酷",
    "spuId": 17073,
    "point": "50",
    "price": "0",
    "upTime": "2026-06-25 00:00:03",
    "downTime": "2026-12-30 23:59:59",
    "catName": "到店专用",
    "status": 2
  },
  {
    "spuName": "麦当劳亲子读书会",
    "spuId": 1830,
    "point": "0",
    "price": "45",
    "upTime": "2023-03-29 00:00:00",
    "downTime": "2026-12-30 23:59:59",
    "catName": "读书会",
    "status": 2
  }
]
```

**为什么这是全项目的锚**：

- 第 1 条：商品名里的「6.9元」就是麦当劳自己标的售价，`point = "50"`
  → `6.9 ÷ 50 = 0.138 元/分`，这就是**兑换最好档**。
- 第 2 条：`point = "0"`，`price = "45"` —— 这是**花钱买的**派对，不是积分兑换，
  必须过滤掉（否则会污染计算）。

过滤规则（`engine.usable_items`）三条，缺一不可：

1. `status == 2`（上架）
2. `point > 0`（得真的是积分兑换）
3. `downTime` 不早于今天（已下架的不算）

### 2.3 `query-my-account` —— 我的积分

**入参**：无

**实际返回**：

```json
{
  "availablePoint": "0",
  "accumulativePoint": "267.1",
  "usedPoint": "0",
  "frozenPoint": "0",
  "expiredPoint": "267.1",
  "currentMouthExpirePoint": "0",
  "nextMouthExpirePoint": "0"
}
```

注意 `currentMouthExpirePoint`（本月将过期）—— 报告里会单独提醒，
因为快过期的积分机会成本其实更高。

### 2.4 `query-my-prizes` —— 我的抽奖记录

**入参**：`pageNum`、`pageSize`（本项目传 `1` / `50`）

**返回**：`prizes[]`（含 `name` / `recordTime` / `statusText` / `timeRemindText`）、
`hasMore`、`nextCursor`。

本次抓取时该账号记录为空（`prizes: []`），所以样例数据也是空的。

### 2.5 `campaign-calendar` —— 活动日历

**入参**：无（可选 `specifiedDate`）

**返回格式和上面四个都不一样：这是一段 Markdown，不是 JSON。**

```markdown
### 当前时间：2026-10-09 15:50:28

### 活动列表：

#### 2026年10月9日 今日

-   **活动标题**：韩式风味蘸酱上新❤️就「酱」心有所「薯」
    **活动内容介绍**：...
```

所以要单独解析：定位 `#### YYYY年M月D日 今日` 这一节，
截到下一个标题行，再抽 `**活动标题**：` 后面的文字（`live.campaigns_today`）。

本项目只用到「今天有几项活动在跑」这一个数字。

---

## 3. 调用流程

```
run.py --live
   │
   ├─ client.initialize()                     握手
   │
   ├─ query-lottery-info   ─┐
   ├─ query-my-account      │  5 个只读工具依次调用，
   ├─ query-my-prizes       │  任一失败只降级那一段，不中断
   ├─ mall-points-products  │
   └─ campaign-calendar    ─┘
   │
   ├─ engine.redeem_items()     过滤出「现在真能换」的商品
   ├─ engine.point_rate()       算出 1 积分值多少钱（取中位数）
   ├─ engine.evaluate()         保本线 + 奖池逐件估价
   ├─ engine.compare()          抽奖上限 vs 兑换最好档
   └─ engine.mood()             翻译成人话
   │
   └─ report.render()           打印
```

---

## 4. 踩到的坑：响应被包了一层 Markdown

**这是真实踩到的第一个坑，值得单独记一笔。**

MCP 的 `tools/call` 返回结构本来是：

```json
{ "content": [ { "type": "text", "text": "<响应内容>" } ] }
```

但麦当劳 MCP 在 `text` 里塞的**不是纯 JSON**，而是给大模型看的一段说明：

```
# API Response Information

Below is the response from an API call. To help you understand the data, I've provided:

1. A detailed description of all fields in the response structure
2. The complete API response

## Response Structure

- **data.drawPoint**: 单次所需积分 (Type: string)
...

## Original Response

{"success":true,"code":200,"data":{"activityName":"麦麦积分抽奖",...}}
```

直接 `json.loads` 会失败 → 整份报告静默降级成样例数据，**而且不报错**。

解决办法（`client._parse_text`）是三级降级：

1. 整段当纯 JSON 解析
2. 找 ```` ```json ```` 代码块
3. 找 `## Original Response` 之后的第一个 JSON 值

第 3 步不能简单粗暴地取"第一个 `{`"——响应体本身可能是数组，
而结构说明里也有花括号。`client._first_json` 的做法是：
先看 `## Original Response` 后面**紧跟的第一个非空字符**是不是括号，
是就从那里开始做括号配平（跳过字符串里的引号和转义），不是才全文搜索。

这段逻辑有 7 项单测守着（`TestResponseParsing`），
包括"字符串里的花括号不能把扫描带偏"和"数组在前面时不能被跳过"。

---

## 5. 为什么不算期望值

`query-lottery-info` **不返回中奖概率**。只有奖品名称、图片、类型。

所以本工具**不估算**「平均能抽到多少」。那些号称能算抽奖期望值的实现，
概率要么是编的，要么是拍脑袋的假设 —— 数字看着精确，本质是算命。

改用两个**确定量**做决策，且不需要概率：

| 量 | 定义 | 本次真实值 |
|---|---|---|
| **保本线** | 抽一次消耗的积分 × 1 积分中位价值 | 24 × 0.0545 = **1.31 元** |
| **奖池上限** | 奖池里最值钱那件 | **3.00 元**（下单立减3元券） |
| **兑换最好档** | 商城最高的 元/积分 | **0.1380 元/分** |

论证：抽奖上限 `3.00 ÷ 24 = 0.1250 元/分` < 兑换最好档 `0.1380 元/分`
→ **连天花板都输，没有理由赌运气。**

折扣券（5 折 / 5.5 折 / 6 折）一律不估价：省多少钱取决于用户点什么，
硬估就得先假设消费内容，结论就是假的。宁可不答。

---

## 6. 降级与容错

| 情况 | 行为 |
|---|---|
| 某个工具调用失败 | 该段用内置样例顶上，其余照常，报告末尾列出失败工具 |
| 抽奖接口拿不到活动 | 直接报错退出（缺了这个就没得算） |
| 商城没有可兑换商品 | 直接报错退出（缺了锚就无从比价） |
| 没设 `MCD_MCP_TOKEN` | 走样例模式；`--live` / `--tools` 才要求 Token，缺了会打印一份按 shell 区分的设置指引并退出码 2 |
| Token 带了引号/空格 | `resolve_token()` 自动剥掉一层引号和首尾空白（Windows `set X="abc"` 的常见手滑） |

---

## 7. 安全边界

**只读白名单**在 `mcd_quant/live.py`：

```python
READ_ONLY_TOOLS = (
    "query-lottery-info",
    "query-my-account",
    "query-my-prizes",
    "mall-points-products",
    "campaign-calendar",
)
```

刻意不调用：

| 工具 | 为什么不调 |
|---|---|
| `draw-lottery` | 抽奖要花积分，是用户的决策，工具不代按 |
| `create-order` | 下单花钱 |
| `mall-create-order` | 积分商城下单 |
| `party-order-create` | 派对下单 |

`TestSafety` 三个测试守着这条边界：
白名单里不能出现会花钱的工具、每个实际调用必须在白名单内、
调用名不能含 `create` 或 `draw`。

---

## 8. 业务价值

- **对用户**：把「积分怎么花」从感觉变成算术题。一句话给出「该抽还是该换」。
- **对平台**：这是一个把积分体系透明度拉高的工具 ——
  它的结论（本次是"兑换更划算"）恰恰说明积分商城定价是厚道的，
  这比任何营销话术都有说服力。
- **对 MCP 生态**：演示了只用只读工具也能做出有决策价值的应用，
  且**不触碰交易链路**，是低风险接入的样板。
