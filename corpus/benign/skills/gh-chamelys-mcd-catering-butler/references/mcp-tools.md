# 麦当劳 MCP 工具速查（团餐相关）

本文档只收录 `mcd-catering-butler` 实际调用的工具。所有字段均依据 MCP Server 官方工具契约，标注 `[已实测]` 的段落为本项目开发过程中真实调用验证过的返回。

---

## 1. delivery-query-addresses — 获取配送地址列表

**入参**：无

**返回**：

| 字段 | 说明 |
|---|---|
| `data.addresses[].addressId` | 地址 ID，**团餐链路的关键起点** |
| `data.addresses[].contactName` | 联系人 |
| `data.addresses[].fullAddress` | 完整地址 |
| `data.addresses[].phone` | 电话 |

`[已实测]` 新申请 Token 返回 `{"addresses": []}` —— 空列表是常态，必须准备好引导建地址的分支。

---

## 2. delivery-create-address — 新增配送地址

团餐链路必需。返回 `addressId`，后续 `delivery-query-stores` 依赖它。

---

## 3. delivery-query-stores — 查询可配送门店（团餐 beCode 唯一来源）

**入参**：

| 参数 | 必填 | 说明 |
|---|---|---|
| `addressId` | 是 | 来自 `delivery-query-addresses` |
| `beType` | 是 | 2 = 麦乐送，**6 = 企业团餐** |

⚠️ **这是团餐 `beCode` 的唯一合法来源**。用 `query-nearby-stores` 得到的门店编码在 `beType=6` 下不可用。

---

## 4. query-nearby-stores — 查询附近门店（到店场景）

**入参**：

| 参数 | 必填 | 说明 |
|---|---|---|
| `beType` | 是 | 1 = 到店自提，5 = 得来速 |
| `searchType` | 是 | 1 = 收藏餐厅，2 = 按位置搜索 |
| `city` | 条件必填 | `searchType=2` 时必填 |
| `keyword` | 条件必填 | `searchType=2` 时必填 |

`[已实测]` 返回字段：`storeName` / `address` / `distance` / `storeCode` / `beCode`（仅 beType=5）/ `reservation` / `reservationTimeOptions[]`（含 `date` / `today` / `reservationOptionText`）。

`[已实测]` 真实返回示例（上海陆家嘴，beType=1）：

```json
{
  "storeCode": "1450127",
  "storeName": "麦当劳上海陆家嘴明珠环餐厅",
  "address": "世纪大道55号2F-1室",
  "distance": 75,
  "businessStartTime": "07:00",
  "businessEndTime": "23:00",
  "reservation": true,
  "reservationTimeOptions": [
    { "date": "2026-10-10", "today": true,  "reservationOptionText": "下午茶(14:44至16:45)" },
    { "date": "2026-10-11", "today": false, "reservationOptionText": "早餐(07:14至10:15)，午餐(10:44至14:15)，下午茶(14:44至16:45)" }
  ]
}
```

⚠️ `reservation=true` 时 `reservationTimeOptions` **每一条都必须完整展示给用户**，漏一条用户就无法预约。

⚠️ `beType=1` 时返回的门店**不含可用团餐 beCode**，且后续工具调用传 `beCode` 会报错。

---

## 5. query-meals — 菜单查询

**入参**：`storeCode`（必填）、`beType`（必填）、`orderType`（必填）、`beCode`（条件必填）、`reservationDate`（预约必填）

**返回结构**：

| 字段 | 说明 |
|---|---|
| `data.categories[].name` | 分类名 |
| `data.categories[].meals[].code` | 餐品编码 |
| `data.categories[].meals[].tags[]` | 标签 |
| `data.meals[code].name` | 餐品名 |
| `data.meals[code].currentPrice` | 现价 |
| `data.meals[code].originalPrice` | 原价 |
| `data.meals[code].canWithOrder` | 是否可随单购 |
| `data.meals[code].discountType` | 优惠类型 |
| `data.meals[code].withOrder` | 随单购卡（cardId/cardType/membershipCode/specId） |
| `data.frequent` | 常点餐品 |

⚠️ `beType=6/2/5` 时 `beCode` 必传。`[已实测]` 缺失时返回：

```json
{"success": false, "code": 600048, "message": "外送场景下，beType=2/5/6时必传beCode"}
```

`[已实测]` 门店 1450127 实际返回 14 个分类，包含团餐常用的「小食拼盘/多人餐」「开心乐园」「小食甜品/其他」等。多人餐示例编码与价格：

| 餐品 | code | 现价 |
|---|---|---|
| 麦麦周末双人餐 | 9900015168 | 69.9 |
| BFF四宫格小食盘 | 9900015730 | 59 |
| 薄皮V翅双拼十翅 | 9900006332 | 61 |
| 堡堡随心拼（7件任选） | 9900004066 | 85 |
| 开心亲子双人餐 | 9900016055 | 78.5 |
| 蘸酱BFF四宫格小食盘 | 9900015729 | 62 |
| 薯条 | 4810 | 14.5 |

⚠️ 价格与供应**因门店因城市而异**，上表仅为 1450127 门店实测值，不可跨门店套用。

---

## 6. query-meal-detail — 餐品详情/套餐组成

**入参**：在 `query-meals` 基础上增加 `code`（必填）

**返回关键字段**：`data.supportModify`（是否支持特调）、`data.choice.supportModify`、`data.modification`（特调项，含 `selectedKey` / `unselectedKey`）

⚠️ 展示规则：`supportModify=true` 时在名称后标注【可特调】；**不要主动展开特调列表**，仅用户询问时展示；展示完要总结 `isDefault=1` 的默认搭配。

---

## 7. query-meal-assistance — 助餐服务（团餐专属）

**入参**：`storeCode`（必填）、`beType`（固定 6）、`orderType`（固定 2）、`beCode`（必填）、`reservationDate`（预约必填）

**前置条件**：必须在用户选完商品、`calculate-price` **之前**调用。

**返回**：

| 字段 | 说明 |
|---|---|
| `data.mealAssistanceItems[].gmServiceCode` | 助餐服务编码，下单传 `gmServiceCode` |
| `data.mealAssistanceItems[].gmServiceName` | 服务名 |
| `data.mealAssistanceItems[].serviceItems[]` | 服务内容 |
| `data.mealAssistanceItems[].selected` | 默认选中 |
| `data.mealAssistanceItems[].enable` | 是否可选 |
| `data.mealAssistanceItems[].unusableReason` | 不可用原因：1 = 送达时段限制；2 = 需提前 4h 预约 |

⚠️ `beCode` 必传，否则同样报 `600048`。`[已实测]` 无 beCode 调用返回：

```json
{"success": false, "code": 600048, "message": "外送场景下，beType=2/5/6时必传beCode"}
```

---

## 8. calculate-price — 核价

**入参**：`storeCode` / `beType` / `orderType` 必填；`beType=6` 时 `beCode` 必填；团餐建议传 `gmServiceCode`、`needTableware`、`reservationDate`

**返回 ——⚠️ 所有价格字段单位为「分」**：

| 字段 | 说明 |
|---|---|
| `productOriginalPrice` / `productPrice` | 商品原价 / 现价（分） |
| `deliveryOriginalPrice` / `deliveryPrice` | 运费原价 / 现价（分） |
| `packingOriginalPrice` / `packingPrice` | 打包费（分） |
| `tablewarePrice` | 餐具费（分） |
| `originalPrice` / `discount` / `price` | 原价 / 优惠 / 现价（分） |
| `data.productList[]` | `productCode` / `productName` / `quantity` / `originalSubtotal` / `subtotal` |
| `data.takeWayList[]` | 取餐方式（仅 orderType=1 有意义） |
| `data.mealAssistanceList[]` | 助餐服务 |
| `data.enjoyed` / `data.enjoyable` | 已享受 / 可享受优惠，含 `amountType`（1 特价/2 折扣/3 立减）、`realDiscount`（**单位元**）、`balance`（门槛差额，单位分） |

⚠️ **单位陷阱**：`discount` / `price` 等为分，但 `enjoyed.realDiscount` 为**元**。混用会导致金额差 100 倍。

`[已实测]` 到店场景真实返回（storeCode=1450127，麦麦周末双人餐×1 + 中薯条×2）：

```json
{
  "productOriginalPrice": 9890,
  "productPrice": 9890,
  "originalPrice": 9890,
  "discount": 0,
  "price": 9890,
  "productList": [
    { "productCode": "9900015168", "productName": "麦麦周末双人餐", "quantity": 1, "originalSubtotal": 6990, "subtotal": 6990 },
    { "productCode": "4810", "productName": "中薯条", "quantity": 2, "originalSubtotal": 2900, "subtotal": 2900 }
  ],
  "takeWayList": [
    { "code": "eat-in",   "title": "堂食", "subtitle": "店内用餐" },
    { "code": "locker-in", "title": "外带", "subtitle": "店内取餐柜" }
  ]
}
```

即总价 ¥98.90 = 9890 分 ÷ 100。

⚠️ 团餐/外送（`orderType=2`）**不传 `takeWayCode`**。

---

## 9. create-order — 创建订单

**入参**：`storeCode` / `beType` / `orderType` 必填；团餐必传 `beCode` + `addressId` + `gmServiceCode`；预约传 `reservationDate`

- `remark`：最多 50 字，仅 `orderType=2` 需要引导填写
- `takeWayCode`：仅 `orderType=1` 必填，取自 `calculate-price` 的 `takeWayList[].code`
- 返回支付链接，引导用户自行完成支付

---

## 10. query-order — 订单状态跟踪

下单后用于确认支付结果与出餐进度。

---

## 通用错误码

| code | 含义 | 处理 |
|---|---|---|
| 401 | Token 无效/过期 | 检查 Authorization 头|
| 429 | 超过 600 次/分钟 | 降低频率，分批串行 |
| 600048 | beType=2/5/6 时缺 beCode | 走 `delivery-query-stores` 取 beCode |