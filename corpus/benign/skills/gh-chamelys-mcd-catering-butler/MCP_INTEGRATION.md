# MCP_INTEGRATION

本项目使用**麦当劳中国官方 MCP Server**（`https://mcp.mcd.cn`，Streamable HTTP 协议），聚焦其**企业团餐（`beType=6`）**能力链路。

- MCP Server 源码与工具契约：https://github.com/M-China/mcd-mcp-server
- 开放平台：https://open.mcd.cn/mcp
- 本项目 MCP Server 版本基线：`1.0.9`（2026-09-10）

---

## 使用的 MCP Tool清单

| # | Tool | 用途 | 在本项目中的角色 |
|---|---|---|---|
| 1 | `delivery-query-addresses` | 查询配送地址列表 | 团餐链路起点，获取 `addressId` |
| 2 | `delivery-create-address` | 新增配送地址 | 无地址时的兜底建单 |
| 3 | `delivery-query-stores` | 查询可配送门店（`beType=6`） | **团餐 `beCode` 唯一合法来源** |
| 4 | `query-meals` | 查询门店菜单 | 按人均预算编排配餐 |
| 5 | `query-meal-detail` | 餐品详情/套餐组成 | 忌口场景确认特制能力 |
| 6 | `query-meal-assistance` | 查询助餐服务 | **团餐专属**，识别隐藏成本 |
| 7 | `calculate-price` | 商品价格计算 | 核价与费用归集表 |
| 8 | `create-order` | 创建订单 | 最终下单 |
| 9 | `query-order` | 订单详情查询 | 支付后状态跟踪 |
| 10 | `query-nearby-stores` | 查询附近门店 | **仅用于 fallback**：团餐不可覆盖时改走到店自取（`beType=1`） |
| 11 | `query-my-coupons` | 查询用户优惠券 | 可选：叠加企业券进一步控本 |
| 12 | `list-nutrition-foods` | 餐品营养信息 | 可选：提供低卡配餐建议 |

其中 #1–#9 为**主链路必需**，#10–#12 为**增强能力**。

---

## 调用流程

### 主流程（团餐下单）

```
① delivery-query-addresses
   └─ 返回空 → delivery-create-address → 回到 ①
   └─ 返回地址列表 → 用户选定addressId
        ↓
② delivery-query-stores(addressId, beType=6)
   └─ 得到可配送团餐门店的 storeCode + beCode
   └─ 返回空 → 告知地址不在团餐覆盖范围，改走到店自取 fallback
        ↓
③ query-meals(storeCode, beType=6, orderType=2, beCode, [reservationDate])
   └─ 得到该门店实时菜单与价格
        ↓
④ query-meal-assistance(storeCode, beType=6, orderType=2, beCode, [reservationDate])
   └─ 得到助餐服务列表含 gmServiceCode / enable / unusableReason
   └─ 必须在 ⑤ 之前、用户选完商品之后调用
        ↓
⑤ calculate-price(storeCode, beType=6, orderType=2, beCode, items, gmServiceCode, [reservationDate])
   └─ 返回以「分」为单位的价格明细
        ↓
⑥ 【向用户展示费用归集表，等待明确确认】
        ↓
⑦ create-order(storeCode, beType=6, orderType=2, beCode, addressId, items, gmServiceCode, remark, [reservationDate])
   └─ 返回订单详情与支付链接
        ↓
⑧ query-order(storeCode) → 用户支付后跟踪状态
```

### Fallback 流程（团餐不可用时）

```
② 返回空 → query-nearby-stores(beType=1, searchType=2, city, keyword)
             → 改走到店自取：beType=1, orderType=1，不传 beCode
```

---

## 三个关键约束及其业务价值

### 约束 1 · 团餐 `beCode` 必须来自 `delivery-query-stores`

**技术表现**：`beType=6` 且缺少 `beCode` 时，MCP Server 返回

```json
{"success": false, "code": 600048, "message": "外送场景下，beType=2/5/6时必传beCode"}
```

本项目开发过程中实测复现（调用 `query-meals(beType=6, orderType=2)` 不带 beCode）：

```json
{"success":false,"code":600048,"message":"外送场景下，beType=2/5/6时必传beCode",
 "datetime":"2026-10-10 14:13:22","traceId":"320496fa33f0867020e69ce4319af57d"}
```

`query-meal-assistance` 缺 beCode 时同样返回该错误码。

**通用AI 的典型失败模式**：用 `query-nearby-stores` 查门店后，直接拿其返回的门店编码去调团餐接口。`query-nearby-stores` 的 `beType` 只接受 1 和 5，**根本没有团餐语义**，其返回结果在 `beType=6` 下无效。

**业务价值**：把这条约束写进 Skill，行政人员只需一句话描述需求，不必经历"查地址→ 查门店 → 报 600048 → 重试"的试错循环。这是本项目最直接的效率价值。

### 约束 2 · 地址是团餐链路的前置依赖

`delivery-query-addresses` 在新Token 下的默认返回为空数组（实测）。无 `addressId` 则 `delivery-query-stores` 无从调用，整条链路断裂。

**业务价值**：Skill 将"引导补建地址"作为固定前置步骤，避免用户在无地址时被反复重试消耗时间。

### 约束 3 · 价格字段单位为「分」

`calculate-price` 的 `price` / `discount` / `productPrice` / `packingPrice` / `tablewarePrice` 等全部以**分**为单位，但 `enjoyed.realDiscount` / `enjoyable.realDiscount` 的`realDiscount` 字段以**元**为单位。

实测样例（到店场景，`storeCode=1450127`，麦麦周末双人餐×1 + 中薯条×2）：

```json
{
  "productOriginalPrice": 9890,
  "productPrice": 9890,
  "originalPrice": 9890,
  "discount": 0,
  "price": 9890,
  "productList": [
    {"productCode":"9900015168","productName":"麦麦周末双人餐","quantity":1,
     "originalSubtotal":6990,"subtotal":6990},
    {"productCode":"4810","productName":"中薯条","quantity":2,
     "originalSubtotal":2900,"subtotal":2900}
  ],
  "takeWayList": [
    {"code":"eat-in","title":"堂食","subtitle":"店内用餐"},
    {"code":"locker-in","title":"外带","subtitle":"店内取餐柜"}
  ]
}
```

即总价¥98.90（9890 分 ÷ 100）。

**业务价值**：行政场景对金额零容忍。把分→元换算设为强制规则，并在费用表底部单独给出人均核算，避免向财务提交错误数字。

---

## 官方团餐搭配规则的使用

MCP `query-meals` 工具契约中明确给出企业团餐的官方搭配规则，本 Skill 将其作为预算档位的编排依据：

| 人均预算 | 官方推荐搭配 |
|---|---|
| 20 元以下 | 小食 |
| 20–30 元 | 汉堡 + 小食，或 汉堡 + 饮料 |
| 30–40 元 | 汉堡 + 薯条/小食 + 饮料 |
| 40–50 元 | 汉堡 + 薯条 + 小食 + 饮料 |
| 50 元以上 | 丰富组合，优先不重复小食 |

**业务价值**：把「人均预算」直接映射到官方档位，让配餐方案有据可依，而不是让 AI 凭感觉搭配。这是行政预算审批最容易通过的形态——每一档都能说清依据。

---

## 助餐服务（`query-meal-assistance`）的业务价值

`query-meal-assistance` 是麦当劳 MCP 中**唯一面向企业团餐的专属工具**（工具描述明确标注"仅企业团餐场景(beType=6)"）。它返回的助餐服务可能产生额外费用，是行政预算中最容易漏算的隐藏成本。

返回结构：

| 字段 | 说明 |
|---|---|
| `gmServiceCode` | 助餐服务编码，下单时传 `gmServiceCode` |
| `gmServiceName` | 服务名称 |
| `serviceItems[]` | 服务内容明细 |
| `selected` | 是否默认选中 |
| `enable` | 是否可选 |
| `unusableReason` | 不可用原因：1 = 送达时段限制；2 = 需提前 4h 预约 |

**业务价值**：Skill 强制在核价前调用该工具，并把 `enable=false` 的项连同 `unusableReason` 一并展示给用户。这让行政人员在预算阶段就知道"专人服务需提前 4 小时预约"这类时间约束，而不是下单失败后才发现。

---

## 已验证 / 未验证

| 能力 | 状态 | 说明 |
|---|---|---|
| `query-nearby-stores` | ✅ 已实测 | 返回上海陆家嘴 5 家门店，含 `reservationTimeOptions` |
| `query-meals`（`beType=1`） | ✅ 已实测 | 返回 14 个分类、上百餐品编码及真实价格 |
| `calculate-price`（`orderType=1`） | ✅ 已实测 | 返回分单位价格明细与 `takeWayList` |
| `600048` 错误码复现 | ✅ 已实测 | `query-meals` / `query-meal-assistance` 缺 beCode 时均复现 |
| `delivery-query-addresses` 空返回 | ✅ 已实测 | 新 Token 默认空数组 |
| 团餐 `beType=6` 完整下单链路 | ⛔未实测 | 个人 MCP 账号无企业团餐地址与配送权限，`delivery-query-stores(beType=6)` 无法取得有效 `beCode`。链路逻辑依据官方工具契约编写，**首次企业实操须人工核价确认** |

`references/mcp-tools.md` 记录了全部实测返回的原始结构。

---

## 错误码处理

| code | 含义 | Skill 处理策略 |
|---|---|---|
| 401 | Token 无效/过期 | 提示检查 `Authorization` 头与 Token |
| 429 | 超过 600 次/分钟 | 多部门批量点单时分批串行，不并发 |
| 600048 | `beType=2/5/6` 时缺 `beCode` | 回到 `delivery-query-stores(beType=6)` 取码，不用 `query-nearby-stores` 兜底 |

---

## 安全与合规

- MCP Token **仅通过环境变量占位符**传递，`mcp-config.example.json` 中不包含任何真实凭证
- Skill 不将地址、联系人、电话等个人信息写入任何外部渠道
- 不代为支付，不承诺发票与报销结果，指向麦当劳官方渠道