---
name: mcd-catering-butler
version: "1.0.0"
display_name: 团餐行政助手
display_name_en: McD Catering Butler
description: "麦当劳企业团餐行政助手：把「订一份 30 人的午餐」这类模糊需求，变成可核价、可下单的企业团餐方案。核心能力是人均预算拆解、门店团餐覆盖查询、助餐服务比选、批量配餐编排与费用归集核对。适用于行政/HR/前台等需要为团队点麦当劳团餐的场景，依赖麦当劳 MCP 的企业团餐（beType=6）能力。"
description_zh: "企业团餐行政助手：人均预算拆解、团餐门店覆盖查询、助餐服务比选、批量配餐编排与费用归集。"
description_en: "Corporate catering admin assistant: per-person budget breakdown, catering coverage lookup, assistance-service comparison, bulk meal orchestration and expense reconciliation."
license: MIT
---

# 团餐行政助手（mcd-catering-butler）

帮行政、HR、前台把「明天给 30 个人订午餐」变成**一份能核价、能对账、能下单**的企业团餐方案。

## 核心定位

麦当劳 MCP 的 `beType=6`（企业团餐）是一条**独立于麦乐送的专用链路**，参数传递规则与到店/外送完全不同。绝大多数通用 AI 会在这里踩坑——本Skill 的第一价值是把这条链路的**硬约束**固化下来，避免试错。

## ⚠️ 三个已实测的硬约束（踩过才知道）

### 约束 1：团餐 `beCode` 只能来自 `delivery-query-stores`，不能用 `query-nearby-stores`

这是最常见的致命错误。团餐场景（`beType=6`）的 `beCode` 来源链路是：

```
delivery-query-addresses   → 拿到 addressId
delivery-query-stores(addressId, beType=6) → 拿到 storeCode + beCode
```

**实测证据**：直接调`query-meals(beType=6, orderType=2)` 而不带 beCode，返回：

```json
{"success":false,"code":600048,"message":"外送场景下，beType=2/5/6时必传beCode"}
```

`query-nearby-stores` 返回的门店在`beType=1/5` 下**不含可用的团餐 beCode**，不能拿来喂团餐链路。

### 约束 2：用户没有地址 → 整条团餐链路直接断死

`delivery-query-addresses` 返回空数组时（实测新Token 的默认状态就是空），**必须先引导用户用 `delivery-create-address` 建地址**，否则拿不到 addressId，`delivery-query-stores` 就无从调用。

不要在无地址时反复重试 `delivery-query-stores`，也不要退回到 `query-nearby-stores` 硬凑——那会产出错误的 beCode。

### 约束 3：`orderType` 与 `beType` 的映射是固定的，不要自创组合

| 场景 | beType | orderType | beCode 来源 |
|---|---|---|---|
| 到店自取 | 1 | 1 | **不传** |
| 得来速车道取餐 | 5 | 1 | `query-nearby-stores` |
| 麦乐送 | 2 | 2 | `delivery-query-stores` |
| **企业团餐** | **6** | **2** | **`delivery-query-stores`** |

到店自取场景传`beCode` 会直接报错，这是 MCP 侧的显式约束。

## 标准工作流

按顺序推进，**不要跳步，也不要在价格未确认前创建订单**。

### Step 1 · 需求澄清（必做，一次问全）

行政场景的高频信息缺口，用一次提问补齐，避免来回追问：

| 要素 | 追问话术 | 缺失后果 |
|---|---|---|
| 人数 | 「一共多少人用餐？」 | 无法算人均 |
| 总预算 | 「预算是人均还是总预算？大概多少？」 | 无法选档位 |
| 用餐时间 | 「几点用餐？需要预约吗？」 | 决定是否传 `reservationDate` |
| 送达/自取地点 | 「送到公司还是到店自取？公司地址是？」 | 决定走哪条链路 |
|忌口/特殊需求 | 「有无忌口、素食、不吃辣等？」 | 影响配餐 |

**预算档位对照**（MCP 官方给出的企业团餐搭配规则）：

| 人均预算 | 官方推荐搭配 |
|---|---|
| 20 元以下 | 小食 |
| 20–30 元 | 汉堡 + 小食，或 汉堡 + 饮料 |
| 30–40 元 | 汉堡 + 薯条/小食 + 饮料 |
| 40–50 元 | 汉堡 + 薯条 + 小食 + 饮料 |
| 50 元以上 | 丰富组合，优先不重复小食 |

先把预算落到档位，再去菜单里选品，不要拿菜单自由组合去碰预算。

### Step 2 · 建立地址与门店链路

```
delivery-query-addresses
  └─ 空 → delivery-create-address（引导用户填写）
  └─ 有 → 让用户选一个作为团餐收货地址
       ↓
delivery-query-stores(addressId, beType=6)
  └─ 返回该地址可配送的团餐门店（含 storeCode + beCode）
```

**展示门店时必须完整展示 `storeCode`**（后续所有工具都要用），并同时说明营业时间——团餐一般需要提前量，营业时间是硬约束。

如果可配送门店为空，说明该地址不在团餐覆盖范围内，应当明确告知用户，并给出替代方案（换地址 / 改为到店自取走 `beType=1`）。

### Step 3 · 拉取该门店真实菜单

```
query-meals(storeCode, beType=6, orderType=2, beCode, [reservationDate])
```

**关键点**：菜单是**门店级实时数据**，不同城市、不同门店的品类和价格都不同。绝不能凭常识或训练数据报价格和品名，必须以本次调用返回的 `currentPrice` 为准。

返回结构要点：
- `data.categories[].name` — 分类名
- `data.categories[].meals[].code` — 餐品编码（下单用）
- `data.meals[code].currentPrice` — 现价
- `data.meals[code].canWithOrder` — 是否可随单购
- `data.meals[code].withOrder` — 随单购卡信息

**多人餐/拼盘类是团餐的核心品类**，优先在分类中定位「小食拼盘/多人餐」「开心亲子餐」这类多人组合，再按人数配比拆分。

### Step 4 · 助餐服务比选（团餐独有，行政最关心的隐藏成本）

```
query-meal-assistance(storeCode, beType=6, orderType=2, beCode, [reservationDate])
```

返回 `data.mealAssistanceItems[]`：

| 字段 | 含义 |
|---|---|
| `gmServiceCode` | 助餐服务编码，下单时传 `gmServiceCode` |
| `gmServiceName` | 服务名称 |
| `serviceItems[]` | 服务内容明细 |
| `selected` | 是否默认选中 |
| `enable` | 当前是否可选 |
| `unusableReason` | 不可用原因（1: 送达时段限制；2: 需提前 4h 预约） |

**这是行政预算里最容易漏掉的一项**：助餐服务（专人服务/摆台等）可能产生额外费用。必须主动展示给用户，并明确提示 `enable=false` 的项及其 `unusableReason`，让用户知道为什么选不了。

如果所有项都 `enable=false`，立即提示用户调整送达时间——`unusableReason=1` 说明该服务只在特定时段可用。

### Step 5 · 配餐编排

按人均预算档位，从真实菜单里选品，**算出并展示人均与总额**。

配餐原则：
- 预算紧张时优先选**多人餐/拼盘类**单品，而不是逐人点单品——拼盘类单价更低且出餐更快
- 50 元以上档位要避免小食重复（官方规则明确要求）
- 有忌口/素食需求时，用 `query-meal-detail` 确认是否支持特制，再统一处理

需要调整套餐内容时：
```
query-meal-detail(storeCode, code, beType=6, orderType=2, beCode, [reservationDate])
```
返回 `supportModify=true` 表示支持特调。特调项**不要主动展开**，仅在用户主动询问时展示，并按MCP 规定标注【可特调】。

### Step 6 · 核价（必须先核价，再下单）

```
calculate-price(storeCode, beType=6, orderType=2, beCode, items, gmServiceCode, reservationDate)
```

⚠️ **返回的所有价格字段单位是「分」，展示时必须除以 100 转为「元」**。这是最容易出的错——直接把分当元报给用户，是严重信任事故。

核价结果要展示的字段：

| 字段 | 含义 | 展示方式 |
|---|---|---|
| `productOriginalPrice` | 商品原价（分） | ÷100 |
| `productPrice` | 商品现价（分） | ÷100 |
| `packingPrice` | 打包费（分） | ÷100 |
| `tablewarePrice` | 餐具费（分） | ÷100 |
| `discount` | 优惠金额（分） | ÷100 |
| `price` | 应付总价（分） | ÷100 |
| `enjoyed` / `enjoyable` | 已享受/可享受的优惠 | 说明门槛差额 |

**团餐场景不传 `takeWayCode`**（仅 `orderType=1` 到店场景需要，从 `takeWayList[].code` 取）。

核价后向用户展示**一张费用归集表**：

```
人均：¥XX（= 总价 / 人数）
商品小计 / 打包费 / 餐具费 / 优惠 / 应付总额
```

然后明确询问：「确认无误可以说『创建订单』下单。」

### Step 7 · 下单

```
create-order(storeCode, beType=6, orderType=2, beCode, addressId, items, gmServiceCode, remark, reservationDate)
```

- `gmServiceCode` 团餐场景**必传**
- `remark` 最多 50 字，仅 `orderType=2` 场景需要引导填写。行政场景常见备注：「放前台」「XX 部门」「无接触配送」
- 预约场景必须传 `reservationDate`，格式 `yyyy-MM-dd HH:mm`

下单成功后引导：「可通过支付链接扫码或在麦当劳 APP 完成支付，支付完成后回复『支付完成』。」

随后用 `query-order` 跟踪订单状态。

## 费用归集核对（团餐行政的刚需）

团餐真正的行政痛点不是点餐，是**报销对账**。交付订单后，主动生成一张核对表：

| 项目 | 数据来源 |
|---|---|
| 订单号 | `create-order` 返回 |
| 商品明细 | `calculate-price` 的 `productList[]`（含 `productName` / `quantity` / `subtotal`） |
| 各项费用 | `packingPrice` / `tablewarePrice` / `discount` |
| 应付总额 | `price` ÷ 100 |
| 助餐服务 | `gmServiceName` + 是否产生费用 |

行政场景高频追问的三个问题，Skill 都要能直接答：
1. **「一个人多少钱」** → `price` ÷ 人数，展示时四舍五入到分
2. **「发票/凭证怎么弄」** → 引导到麦当劳官方订单页获取，本Skill 不代为处理
3. **「能不能开发票」** → 不承诺，指向官方渠道

## 边界与诚实原则

- **不编造价格**：所有金额必须来自本次 MCP 调用，不确定就再调一次
- **不承诺发票/报销结果**：税务与财务合规由企业自行处理，Skill 只提供订单数据
- **不代做支付**：Skill 交付支付链接，支付动作由用户完成
- **地址信息敏感**：完整地址、联系人、电话属于个人信息，不写入任何外部渠道
- **单位换算永远显式**：分→元 的换算必须在给用户的回复里体现，不允许沉默处理

## 限流注意

MCP Token 每分钟最多 600 次请求，超限返回 429。批量为多部门点单时，避免在同一轮内并发大量调用，建议分批串行。

## 已验证的能力边界

- ✅ 到店门店查询（`query-nearby-stores`，实测返回上海陆家嘴5 家门店，含 `reservationTimeOptions`）
- ✅ 到店菜单查询（`query-meals`，实测返回 14 个分类、上百个餐品编码）
- ✅ 到店核价（`calculate-price`，实测返回分单位价格 + `takeWayList`）
- ⛔ 团餐链路完整下单：受限于个人账号无企业团餐地址权限，`beCode` 获取与助餐服务返回未能在真实企业账号下验证。链路逻辑依据 MCP 官方工具契约编写，**首次企业实操时请人工核价确认**

## 参考文档

- `references/mcp-tools.md` — 本 Skill 使用的 MCP 工具参数与返回字段速查
- `references/scenarios.md` — 4 个真实团餐场景的完整对话脚本