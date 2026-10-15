# workbuddy.md

本文件记录 `mcd-catering-butler` 的开发过程与 WorkBuddy 对话上下文，用于核验项目符合 WorkBuddy 专项奖励条件。

- **开发工具**：腾讯 WorkBuddy
- **开发日期**：2026-10-10
- **参与专项**：麦当劳程序员创意开发大赛 · WorkBuddy 专项积分
- **连接器**：`mcd-mcp`（麦当劳中国官方 MCP Server，Streamable HTTP）

---

## 开发环境

| 项 | 值 |
|---|---|
| 平台 | Windows 11 |
| 智能体 | WorkBuddy（WorkBuddy 桌面端） |
| MCP Server | `https://mcp.mcd.cn` |
| MCP 版本基线 | 1.0.9（2026-09-10） |
| 授权方式 | `Authorization: Bearer <MCP_TOKEN>` |

MCP 接入路径：WorkBuddy → 左侧边栏「专家·技能·连接器」→ 连接器 → 自定义连接器 → 配置 MCP。

---

## 对话上下文时间线

### 阶段一 · 赛事信息调研

用户提出参与麦当劳 MCP 开发者挑战赛以获取 WorkBuddy 专项积分，随后要求针对「团餐行政助手」方向落地。

调研过程中通过查阅活动仓库（`M-China/mcd-developer-innovation-challenge`）与 MCP Server 仓库（`M-China/mcd-mcp-server`），确认了以下关键约束：

- 排名**仅按 GitHub 公开 Star 数**，不考察代码质量
- 活动截止 2026-10-25 23:59，定榜 10-26 00:00
- 前 100 名 + 提交 `workbuddy.md` = 3000 WorkBuddy 积分
- 前 3 名 = 10240 积分
- 仓库必含 `README.md` / `CONTEST_DECLARATION.md` / `MCP_INTEGRATION.md` / `mcp-config.example.json` / `workbuddy.md` / 源代码
- `CONTEST_DECLARATION.md` 内容一字不可修改

对赛题方向做了红海分析：省钱/优惠券、热量营养、积分三大方向已高度饱和，而**企业团餐（`beType=6`）方向仅 3 个项目且均未使用 `query-meal-assistance`**。选定团餐方向的理由：

| 理由 | 说明 |
|---|---|
| 工具独占 | `query-meal-assistance` 是 MCP 中唯一面向企业团餐的专属工具 |
| 链路完整 | 8 个 Tool 可串成从地址到下单的完整闭环 |
| 场景真实 | 行政团餐是企业高频刚需，非demo向 |
| 差异化 | 「人均预算拆解 + 费用归集核对」是其他团餐项目未覆盖的角度 |

### 阶段二 · MCP 真实探查（核心阶段）

在 WorkBuddy 中通过 `mcd-mcp` 连接器实际调用麦当劳 MCP，共 6 次真实调用，用于确认参数规则与返回结构。完整原始记录见 `examples/dialogue-transcript.md`。

探查过程中发现了**3 个官方文档中未直接说明、但会导致失败的关键约束**：

#### 发现 1 · 团餐 beCode 来源被误用是首要失败点

尝试 `query-meals(beType=6, orderType=2, storeCode=1450127)` 时返回：

```json
{"success":false,"code":600048,"message":"外送场景下，beType=2/5/6时必传beCode"}
```

追查发现 `query-nearby-stores` 的 `beType` 只接受 `1` 和 `5`，**根本没有团餐语义**。通用 AI 最容易犯的错是拿 `query-nearby-stores` 的结果去喂团餐接口，而团餐 `beCode` 的唯一合法来源是 `delivery-query-stores(addressId, beType=6)`。

`query-meal-assistance` 在同样情况下也返回 `600048`，佐证了这一约束的普遍性。

#### 发现 2 · 团餐链路强依赖配送地址

`delivery-query-addresses` 在新申请 Token 下返回空数组：

```json
{"success":true,"code":200,"data":{"addresses":[]}}
```

没有 `addressId` → 无法调 `delivery-query-stores` → 拿不到 `beCode` → 整条团餐链路断裂。这是**新用户必然遇到的第一道墙**，必须在 Skill 中作为固定前置步骤处理。

#### 发现 3 · 价格单位为「分」

`calculate-price` 到店场景实测返回：

```json
{
  "price": 9890,
  "productPrice": 9890,
  "productList": [
    {"productName": "麦麦周末双人餐", "quantity": 1, "subtotal": 6990},
    {"productName": "中薯条", "quantity": 2, "subtotal": 2900}
  ]
}
```

`price: 9890` 实际是 ¥98.90。但 `enjoyed.realDiscount` 字段单位是**元**——同一响应内两种单位混用，是极易出错的陷阱。

行政场景对金额零容忍，把分→元换算设为强制规则。

#### 附带发现

- `query-meals` 返回 `productName` "薯条"，核价时变为 "中薯条" → 规格在核价阶段才确定，编排阶段应按品类而非规格承诺
- `takeWayList` 仅在 `orderType=1` 有意义，团餐（`orderType=2`）不传 `takeWayCode`
- 多人餐/拼盘类实价：麦麦周末双人餐 69.9、BFF四宫格小食盘 59、堡堡随心拼 85、薄皮V翅双拼十翅 61、开心亲子双人餐 78.5
- 菜单价格因门店而异（以上为上海陆家嘴 1450127 门店实测值），绝不能凭常识或训练数据报价格

### 阶段三 · Skill 设计与撰写

基于探查结论，Skill 的设计围绕三条硬约束展开，而非围绕"AI 该如何点餐"展开。这与通用助手最大的区别在于：**通用助手每次都要重新试错，而本 Skill 把试错结论固化了**。

核心设计决策：

| 决策 | 理由 |
|---|---|
| 约束前置到SKILL.md 顶部 | 避免在流程末尾才提示，避免已经浪费用户时间 |
| 预算档位映射官方搭配规则 | 行政预算审批需要「每一档都有依据」，官方规则表恰好提供 |
| 助餐服务强制在核价前展示 | 这是行政预算最易漏算的隐藏成本，且 `unusableReason` 含时间约束 |
| 强制输出费用归集表 | 团餐真正的行政痛点是报销对账，不是点餐 |
| 明确写出未验证能力边界 | 团餐链路因个人账号无配送权限无法实测，诚实标注比夸大功能更有助于工具被正确使用 |

覆盖的 5 个场景（`references/scenarios.md`）：标准 30 人午餐、低预算 20 人、预算超标降配、忌口分组、下单后费用核对。

---

## WorkBuddy 在开发中的实际作用

| 环节 | WorkBuddy 的使用 |
|---|---|
| 赛事调研 | 抓取活动仓库与 MCP Server 仓库，提取时间节点、必填文件、排名规则、32 个 Tool 的完整契约 |
| MCP 探查 | 通过 `mcd-mcp` 连接器完成 6 次真实调用，验证参数规则、捕获错误码、记录真实返回 |
| Skill 撰写 | 基于探查结论生成 `SKILL.md`、`references/mcp-tools.md`、`references/scenarios.md` |
| 文档撰写 | 生成 `README.md`、`MCP_INTEGRATION.md`、`examples/dialogue-transcript.md` |
| 合规处理 | 下载并原样保留官方 `CONTEST_DECLARATION.md`，`mcp-config.example.json` 仅使用环境变量占位符 |

其中 **MCP 真实探查是项目质量的决定性环节**。三个关键约束（beCode 来源、地址前置、价格单位）全部来自实测，而非文档推断。若仅依赖官方 README，Skill 会沿用错误的 `query-nearby-stores` 路径，并在金额上出现 100 倍误差。

---

## 项目产出

```
mcd-catering-butler/
├── SKILL.md# Skill 主文件
├── README.md                 # 项目介绍与使用说明
├── MCP_INTEGRATION.md        # Tool 清单、调用流程、业务价值
├── CONTEST_DECLARATION.md    # 活动官方声明（原样）
├── workbuddy.md# 本文件
├── mcp-config.example.json   # 脱敏 MCP 配置
├── references/
│   ├── mcp-tools.md          # 工具速查（含实测返回结构）
│   └── scenarios.md          # 5 个场景脚本
└── examples/
    └── dialogue-transcript.md# 6 次真实调用的完整记录
```

---

## 声明

本项目为麦当劳程序员创意开发大赛参赛作品，由参赛者独立开发，非麦当劳官方产品。

项目在开发过程中通过 WorkBuddy 连接麦当劳官方 MCP Server 完成 6 次真实数据调用，记录见 `examples/dialogue-transcript.md`。企业团餐主链路因个人 MCP 账号不具备企业配送权限，未能完成端到端实测，链路逻辑依据 MCP 官方工具契约编写，该限制已在 `SKILL.md` 与 `README.md` 中明确标注。

项目不含真实 Token、密钥或任何他人个人信息，配置文件仅使用环境变量占位符。