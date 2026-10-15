# 实测对话记录

本文件记录 `mcd-catering-butler` 开发过程中与麦当劳 MCP Server 的**真实调用记录**，供核验项目确实使用了麦当劳 MCP 能力。

- 调用日期：2026-10-10
- MCP Server：`https://mcp.mcd.cn`（Streamable HTTP）
- MCP Server 版本基线：1.0.9（2026-09-10）

---

## 调用 1 · query-nearby-stores（到店门店查询）

**入参**：

```json
{
  "beType": 1,
  "searchType": 2,
  "city": "上海",
  "keyword": "陆家嘴"
}
```

**真实返回（节选）**：

```json
{
  "success": true,
  "code": 200,
  "message": "请求成功",
  "datetime": "2026-10-10 14:13:14",
  "traceId": "4f9481d701724a315b842d939567abe9",
  "data": [
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
    },
    { "storeCode": "1450579", "storeName": "麦当劳上海正大广场餐厅", "distance": 268 },
    { "storeCode": "1450512", "storeName": "麦当劳上海陆家嘴星展餐厅", "distance": 445 },
    { "storeCode": "1450330", "storeName": "麦当劳上海浦东上海中心餐厅", "distance": 490 },
    { "storeCode": "1450140", "storeName": "麦当劳上海东昌路世界广场餐厅", "distance": 1344 }
  ]
}
```

**观察**：`beType=1` 返回的门店**不含 beCode**，后续调用不传。`reservation=true` 时 `reservationTimeOptions` 需完整展示。

---

## 调用 2 · query-meals（团餐场景，缺 beCode）— 关键错误复现

**入参**：

```json
{ "beType": 6, "orderType": 2, "storeCode": "1450127" }
```

**真实返回**：

```json
{
  "success": false,
  "code": 600048,
  "message": "外送场景下，beType=2/5/6时必传beCode",
  "datetime": "2026-10-10 14:13:22",
  "traceId": "320496fa33f0867020e69ce4319af57d"
}
```

**观察**：这正是本 Skill 约束 1 的来源。`query-meal-assistance` 在同一情况下也返回相同错误码（见调用 4）。`query-nearby-stores` 的 `beType` 只接受 1 和 5，**没有团餐语义**，其结果不能用于 `beType=6`。

---

## 调用 3 · query-meals（到店菜单）

**入参**：

```json
{ "beType": 1, "orderType": 1, "storeCode": "1450127" }
```

**真实返回（节选）**：

```json
{
  "success": true,
  "code": 200,
  "datetime": "2026-10-10 14:13:31",
  "traceId": "c9dadab30fa6dd9a08b997b20e487a54",
  "data": {
    "categories": [
      { "name": "人气热卖", "meals": [{ "code": "9900016076", "tags": ["心形薯饼同款比心"] }] },
      { "name": "小食拼盘\n/多人餐", "meals": [
          { "code": "9900016076", "tags": ["上新", "心形薯饼同款比心"] },
          { "code": "9900015168", "tags": ["多人餐", "全球爆款", "全天供应"] },
          { "code": "9900006332", "tags": ["小食拼盘", "超值"] },
          { "code": "9900015730", "tags": ["小食拼盘", "随心拼"] },
          { "code": "9900004066", "tags": ["小食拼盘", "万种组合"] }
      ]},
      { "name": "饮品", "meals": [{ "code": "9900008751", "tags": ["冷饮"] }] }
    ],
    "meals": {
      "9900015168": {
        "name": "麦麦周末双人餐",
        "image": "https://menu-img.mcd.cn/pcm/prod/menu/ProductPool/product/MS_9900015168_320.gif",
        "currentPrice": "69.9",
        "originalPrice": "69.9",
        "canWithOrder": false
      },
      "9900004066": { "name": "堡堡随心拼（7件任选）", "currentPrice": "85", "originalPrice": "85" },
      "4810": { "name": "薯条", "currentPrice": "14.5", "originalPrice": "14.5" },
      "9900011121": {
        "name": "\"苹\"水相\"鱼\"套餐",
        "currentPrice": "55.5",
        "discountType": null,
        "canWithOrder": false
      },
      "510479": {
        "name": "燕麦奶铁",
        "currentPrice": "9.9",
        "originalPrice": "27",
        "discountType": "随单购麦金卡优惠",
        "withOrder": { "membershipCode": "106", "specId": "880" },
        "canWithOrder": true
      }
    },
    "frequent": {}
  }
}
```

**观察**：门店 1450127 实际返回 **14 个分类**、上百个餐品编码。多人餐/拼盘类编码与价格（团餐配餐的主要依据）：

| 餐品 | code | 现价 |
|---|---|---|
| 麦麦周末双人餐 | 9900015168 | 69.9 |
| BFF四宫格小食盘 | 9900015730 | 59 |
| 薄皮V翅双拼十翅 | 9900006332 | 61 |
| 堡堡随心拼（7件任选） | 9900004066 | 85 |
| 开心亲子双人餐 | 9900016055 | 78.5 |
| 蘸酱BFF四宫格小食盘 | 9900015729 | 62 |
| 薯条 | 4810 | 14.5 |

⚠️ 价格与供应因门店因城市而异，上表不可跨门店套用。这也是 Skill 要求"绝不凭常识报价格"的依据。

---

## 调用 4 · query-meal-assistance（团餐助餐服务，缺 beCode）

**入参**：

```json
{ "beType": 6, "orderType": 2, "storeCode": "1450127" }
```

**真实返回**：

```json
{
  "success": false,
  "code": 600048,
  "message": "外送场景下，beType=2/5/6时必传beCode",
  "datetime": "2026-10-10 14:13:38",
  "traceId": "55c95ee326933900f9c5b2d1d91f7918"
}
```

**观察**：助餐服务接口同样强制要求团餐 `beCode`，必须来自 `delivery-query-stores`。

---

## 调用 5 · delivery-query-addresses（配送地址）

**入参**：无

**真实返回**：

```json
{
  "success": true,
  "code": 200,
  "datetime": "2026-10-10 14:13:26",
  "traceId": "81675d0a1e3332ba93f174b476e59c64",
  "data": { "addresses": [] }
}
```

**观察**：**新申请的 MCP Token 默认无配送地址**，返回空数组。这是本 Skill 约束 2 的来源——团餐链路必须先引导用户建立地址，否则无法取得 `addressId`，整条链路断裂。

---

## 调用 6 · calculate-price（核价）

**入参**：

```json
{
  "storeCode": "1450127",
  "beType": 1,
  "orderType": 1,
  "needTableware": true,
  "items": [
    { "productCode": "9900015168", "quantity": 1 },
    { "productCode": "4810", "quantity": 2 }
  ]
}
```

**真实返回**：

```json
{
  "success": true,
  "code": 200,
  "datetime": "2026-10-10 14:13:38",
  "traceId": "3857a7e3a4230055c58e82bd5fffa133",
  "data": {
    "productOriginalPrice": 9890,
    "productPrice": 9890,
    "originalPrice": 9890,
    "discount": 0,
    "price": 9890,
    "productList": [
      { "productCode": "9900015168", "productName": "麦麦周末双人餐", "quantity": 1,
        "originalSubtotal": 6990, "subtotal": 6990 },
      { "productCode": "4810", "productName": "中薯条", "quantity": 2,
        "originalSubtotal": 2900, "subtotal": 2900 }
    ],
    "takeWayList": [
      { "code": "eat-in", "title": "堂食", "subtitle": "店内用餐" },
      { "code": "locker-in", "title": "外带", "subtitle": "店内取餐柜" }
    ]
  }
}
```

**观察**：
1. **`price: 9890` 单位为分，即 ¥98.90**。若直接当元报出，金额将放大 100 倍——这是行政场景最不可接受的错误。Skill 因此将分→元换算设为强制规则。
2. `productName` 从 "薯条" 变为 "中薯条"，说明规格信息在下单时才确定，编排阶段应按品类而非具体规格承诺。
3. `takeWayList` 仅在 `orderType=1` 有意义；团餐（`orderType=2`）不传 `takeWayCode`。

---

## 调用汇总

| # | Tool | 入参要点 | 结果 | 对Skill 的贡献 |
|---|---|---|---|---|
| 1 | `query-nearby-stores` | beType=1, 上海陆家嘴 | 5 家门店 | fallback 流程依据 |
| 2 | `query-meals` | beType=6 缺 beCode | **600048 失败** | **约束 1 来源** |
| 3 | `query-meals` | beType=1 | 14 分类真实菜单 | 配餐规则数据依据 |
| 4 | `query-meal-assistance` | beType=6 缺 beCode | **600048 失败** | **约束 1 佐证** |
| 5 | `delivery-query-addresses` | 无 | **空数组** | **约束 2 来源** |
| 6 | `calculate-price` | 到店 2 件商品 | 分单位价格明细 | **约束 3 来源** |

---

## 未能实测的部分

| 能力 | 原因 |
|---|---|
| `delivery-query-stores(beType=6)` | 个人 MCP 账号无企业团餐配送权限，无法产生有效地址，`addressId` 缺失 |
| `query-meals(beType=6, beCode=...)` | 依赖上一环节 |
| `query-meal-assistance` 成功返回 | 同上 |
| `create-order(beType=6)` | 同上，且涉及真实下单，不应在开发阶段触发 |

团餐主链路的参数规则依据 MCP Server 官方工具契约（`query-meal-assistance` 的 `When` / `Preconditions` / `Next` 段，以及各Tool 的 `beCode` 传递说明）编写。首次企业实操时请人工核价确认。