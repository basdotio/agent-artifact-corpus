# 团餐行政助手 · mcd-catering-butler

> 把「明天给 30 个人订麦当劳，人均 35」变成一份**能核价、能对账、能下单**的企业团餐方案。

基于[麦当劳中国官方 MCP](https://github.com/M-China/mcd-mcp-server) 的企业团餐（`beType=6`）能力，专为行政 / HR / 前台的日常团餐场景打造。

---

## 为什么需要它

企业团餐在麦当劳 MCP 里是一条**独立于麦乐送的专用链路**，参数传递规则完全不同。直接用一个通用 AI 去跑，会连续踩三个坑：

| 坑 | 表现 | 本Skill 的处理 |
|---|---|---|
| **beCode 来源搞错** | 用 `query-nearby-stores` 查门店后去调团餐接口，报 `600048` 错误 | 强制走 `delivery-query-stores(beType=6)` |
| **没有配送地址** | 账号默认无地址，团餐链路根本起不来 | 固定前置引导建地址 |
| **金额单位踩雷** | MCP 返回「分」，直接当「元」报给财务 | 分→元强制换算，费用表显式呈现 |

这三个坑都不是AI 的"能力问题"，而是**信息不完整导致的试错**。本 Skill 的价值就是把这部分知识固化下来，让行政人员一句话说清需求就能拿到方案。

**更实用的一点**：团餐真正的行政痛点不是点餐，是**报销对账**。本 Skill 在交付订单时会同时产出一张费用核对表，直接可交给财务。

---

## 核心能力

| 能力 | 说明 |
|---|---|
| **人均预算拆解** | 按麦当劳官方 5 档搭配规则（人均 20/30/40/50 元）自动定档编排 |
| **团餐覆盖查询** | 按企业地址查可配送团餐门店，含营业时间校验 |
| **助餐服务比选** | 团餐专属能力，识别专人服务等隐藏成本与时间约束 |
| **批量配餐编排** | 多人餐/拼盘类优先，支持忌口分组、荤素搭配、预算超标降配 |
| **核价与费用归集** | 输出「商品 / 打包 / 餐具 / 优惠 / 人均」五段式费用表 |
| **报销对账表** | 订单明细 + 费用汇总，直接交财务 |

---

## 安装

### 前置条件

1. **已申请麦当劳 MCP Token**
   访问 https://open.mcd.cn/mcp → 手机号登录 → 控制台 → 激活 → 复制 Token
2. **已安装 WorkBuddy**
   下载：https://www.workbuddy.cn

### 配置 MCP 连接器

在 WorkBuddy 中：**左侧边栏 → 专家·技能·连接器 → 连接器 → 右上角自定义连接器 → 配置 MCP**

填入：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN"
      }
    }
  }
}
```

> 记得把 `YOUR_MCP_TOKEN` 替换为真实 Token 并保存。

### 安装 Skill

将本仓库克隆到 `~/.workbuddy/skills/`：

```bash
git clone https://github.com/Chamelys/mcd-catering-butler.git \
  ~/.workbuddy/skills/mcd-catering-butler
```

或直接把整个目录复制到 `~/.workbuddy/skills/mcd-catering-butler`。

在 WorkBuddy 对话框中即可调用。

### 手动配置（可选）

`mcp-config.example.json` 是标准 MCP 配置样例，支持 Cherry Studio、Cursor、Trae、VS Code 等客户端：

```bash
cp mcp-config.example.json ~/.mcp.json
# 把 ${MCD_MCP_TOKEN} 替换为真实 Token
```

---

## 使用示例

### 示例 1 · 标准午餐（最高频）

```
你：明天中午给 30 个人订麦当劳，人均 35 块左右，送到公司

助手：先确认几个关键信息，一次问完：
  1. 送达地址是？（公司具体地址）
  2. 用餐时间是几点？需要预约吗？
  3. 30 人有无忌口或特殊需求？

（用户补充后）

助手：人均 35 元落在「30–40 元」档，官方搭配是汉堡 + 薯条/小食 + 饮料。
      按 30 人算，这是 10 份三人份组合的量，能省掉逐份点单的时间。

[调用 delivery-query-addresses]
助手：你的账号里还没有配送地址，团餐需要先建一个。
      请告诉我：公司名称、详细地址、联系人、联系电话。

[用户补充后调用 delivery-query-stores → query-meals → query-meal-assistance → calculate-price]

助手：【费用预估（30 人）】
      | 项目 | 金额 |
      |---|---|
      | 商品小计 | ¥xxx.xx |
      | 打包费 | ¥xx.xx |
      | 餐具费 | ¥xx.xx |
      | 优惠 | -¥xx.xx |
      | 应付总额 | ¥xxx.xx |

      人均约 ¥xx.xx，在 35 元预算内。
      确认无误可以说「创建订单」下单。
```

### 示例 2 · 预算超标

```
你：35 个人，人均最多 30，能搞定吗？

助手：按 35 人算，最省组合是 ¥xxx，超出预算 ¥xx.xx。三个方案：

      | 方案 | 人均 | 总价 | 调整 |
      |---|---|---|---|
      | A 精确控预算 | ¥xx.xx | ¥xxx | 主食单品 + 小食拼盘分摊 |
      | B 略超预算 | ¥xx.xx | ¥xxx | 换更划算的拼盘类 |
      | C 精确达标 | ¥xx.xx | ¥xxx | 30 人常规 + 5 人降配（荤素搭配）
```

> C 方案是行政场景最实用的解法：不追求全团统一，按人均拆成两种配置，预算能精确压到分。

### 示例 3 · 忌口分组

```
你：12 个人，其中 3 人吃素，还有 2 人不要汉堡

助手：已按 12 人分 3 组编排：
  - 素食 3 人：培根蔬萃双层牛堡（可去掉培根）
  - 无汉堡 2 人：小食拼盘 + 饮品
  - 常规 7 人：精选单人餐

      素食组需要去掉培根，我用特制处理。核价后你再确认。
```

### 示例 4 · 费用核对（下单后）

```
你：订单收到了，怎么跟财务对账？

助手：团餐费用核对表

      | 项目 | 内容 |
      |---|---|
      | 订单号 | create-order 返回 |
      | 门店 | 麦当劳XX餐厅（storeCode: xxxxx） |
      | 用餐人数 | 30 人 |
      | 助餐服务 | 专人服务（gmServiceCode: xxxx） |

      【商品明细】
      | 商品 | 单价 | 数量 | 小计 |
      |---|---|---|---|
      | ... | ¥xx.xx | 10 | ¥xxx.xx |

      【费用汇总】
      | 项目 | 金额 |
      |---|---|
      | 商品小计 | ¥xxx.xx |
      | 打包费 | ¥xx.xx |
      | 餐具费 | ¥xx.xx |
      | 优惠 | -¥xx.xx |
      | 应付总额 | ¥xxx.xx |
      | 人均 | ¥xx.xx |

      发票与凭证需在麦当劳 APP 订单页自行申请，本助手不代为处理。
```

更多场景见 `references/scenarios.md`。

---

## 目标用户

| 角色 | 痛点 | 本 Skill 如何解决 |
|---|---|---|
| **行政 / 前台** | 每周都要订团餐，对参数链路不熟，重复踩坑 | 固定 7 步流程，一句话触发 |
| **HR** | 需要多部门分组、忌口统计、预算控到分 | 分组编排 + 人均拆分解法 |
| **行政主管** | 报销时被财务质疑金额算错 | 分→元强制换算 + 五段式费用表 |
| **开发者 / MCP 学习者** | 想理解企业团餐链路的完整参数规则 | `references/mcp-tools.md` 含实测返回结构 |

---

## 项目结构

```
mcd-catering-butler/
├── SKILL.md                      # Skill 主文件（工作流 + 约束 + 边界）
├── README.md                     # 本文件
├── MCP_INTEGRATION.md            # MCP Tool 清单、调用流程、业务价值
├── CONTEST_DECLARATION.md        # 参赛声明（活动官方文件）
├── workbuddy.md                  # WorkBuddy 开发对话上下文
├── mcp-config.example.json       # 脱敏 MCP 配置示例
├── references/
│   ├── mcp-tools.md              # 工具参数与实测返回速查
│   └── scenarios.md              # 5 个真实场景对话脚本
└── examples/
    └── dialogue-transcript.md    # 完整实测对话记录
```

---

## 边界说明

- **不编造价格**：所有金额来自 MCP 实时调用，菜单与价格因门店因城市而异
- **不代为支付**：交付支付链接，支付动作由用户完成
- **不承诺发票 / 报销结果**：税务与财务合规由企业自行处理
- **个人信息不外传**：地址、联系人、电话不写入任何外部渠道
- **非官方产品**：本项目为参赛作品，非麦当劳官方产品，输出不构成专业建议

---

## 已验证的能力边界

| 能力 | 状态 |
|---|---|
| 到店门店查询 `query-nearby-stores` | 已实测 |
| 到店菜单查询 `query-meals(beType=1)` | 已实测 |
| 到店核价 `calculate-price(orderType=1)` | 已实测 |
| `600048` 缺 beCode 错误码复现 | 已实测 |
| 团餐 `beType=6` 完整下单链路 | **未实测** —— 个人账号无企业团餐地址与配送权限，链路逻辑依据官方工具契约编写，首次企业实操请人工核价确认 |

透明说明能力边界，比夸大功能更有助于工具被正确使用。

---

## 相关链接

- 麦当劳 MCP Server：https://github.com/M-China/mcd-mcp-server
- MCP 开放平台：https://open.mcd.cn/mcp
- 活动仓库：https://github.com/M-China/mcd-developer-innovation-challenge
- WorkBuddy：https://www.workbuddy.cn

## License

MIT