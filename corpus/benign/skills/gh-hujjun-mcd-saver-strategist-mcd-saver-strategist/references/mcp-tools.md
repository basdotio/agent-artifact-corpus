# 麦当劳 MCP 工具清单与字段映射

本 Skill 实际使用的麦当劳 MCP Server：**`mcd-mcp`**，接入地址 `https://mcp.mcd.cn`，
Streamable HTTP 协议，`Authorization: Bearer <MCP_TOKEN>`。

> 字段名以 MCP 实时返回为准。下表给出的是「归一化目标字段」，若实际返回字段名不同，
> 按语义对应填入 `optimizer.py` 的输入契约即可。**不要臆造字段，以真实返回为准。**

## 一、用到的 Tool

| Tool | 中文名 | 在本 Skill 中的作用 |
|---|---|---|
| `now-time-info` | 获取当前时间 | 判断时段（早餐/正餐），决定菜单范围 |
| `query-nearby-stores` | 查询附近门店 | 到店场景定位门店、拿 `storeCode` |
| `delivery-query-addresses` | 获取配送地址 | 外送场景选择收货地址 |
| `delivery-create-address` | 新增配送地址 | 用户无地址时新增 |
| `delivery-query-stores` | 查询可配送门店 | 外送场景确定门店 |
| `query-meal-assistance` | 查询助餐服务 | 企业团餐场景 |
| `query-meals` | 查询可售餐品列表 | **菜单与价格主数据源** |
| `query-meal-detail` | 查询餐品详情 | 套餐组成、可选替换项 |
| `list-nutrition-foods` | 餐品营养信息 | 热量/营养约束求解 |
| `available-coupons` | 麦麦省券列表 | 可领券 → 券池 |
| `auto-bind-coupons` | 麦麦省一键领券 | **必须调用**，把所有可领券领到手 |
| `query-my-coupons` | 我的优惠券 | 账户已有券 → 券池 |
| `query-store-coupons` | 门店可用券 | 门店专属券 → 券池 |
| `calculate-price` | 商品价格计算 | **下单前最终核价**，校验优化器结果 |
| `create-order` | 创建订单 | 用户确认后下单，返回支付链接 |
| `cancel-order` | 取消订单 | 用户要求时取消 |

## 二、字段映射表（MCP 返回 → optimizer 输入）

### menu.json

| 目标字段 | 来源 | 说明 |
|---|---|---|
| `store_code` | `query-nearby-stores` / `delivery-query-stores` | 门店编码 |
| `items[].code` | `query-meals` 餐品编码 | 唯一标识，下单时使用 |
| `items[].name` | `query-meals` 餐品名称 | 用于模糊匹配用户「想吃的」 |
| `items[].category` | `query-meals` 分类 | burger/side/drink/dessert/combo |
| `items[].price` | `query-meals` 现价 | 单点原价 |
| `items[].calories` | `list-nutrition-foods` 能量 | 无营养约束时可置 0 |
| `items[].tags` | `query-meals` 标签/口味 | 辅助模糊匹配（牛肉/辣/低卡…） |

### coupons.json

| 目标字段 | 来源 | 说明 |
|---|---|---|
| `id` | 券 ID / couponId | 唯一标识 |
| `type` | 见下方判定 | 5 类之一，判定规则见 coupon-strategy.md |
| `title` | 券名称 | 展示用 |
| `item_codes` | 适用商品编码 | 单品类券 |
| `override_price` / `discount_pct` | 券面优惠 | 单品改价 / 折扣 |
| `min_spend` / `discount` | 券面门槛与金额 | 满减类 |
| `groups` / `price` | 组合规则 | 组合价类（如 1+1 随心配） |
| `gift_codes` | 赠品编码 | 赠品类 |
| `stackable` | 券面规则 | 是否可与其它券叠加，拿不准时置 false |

### request.json

| 字段 | 来源 | 说明 |
|---|---|---|
| `wants` | 用户原话 | 「想吃的」，支持模糊词如"汉堡""薯条" |
| `budget` | 用户原话 | 总价上限，可空 |
| `max_calories` | 用户原话 | 热量上限，可空 |
| `max_items` | 默认 5 | 最多几件 |
| `allow_extras` | 默认 true | 是否允许为凑满减而加购 |

## 三、调用流程（时序）

```
用户提出需求
   │
   ├─ now-time-info ────────────► 时段
   ├─ 门店定位 (nearby / delivery-*) ─► storeCode
   ├─ query-meals ──────────────► 菜单
   ├─ query-meal-detail ────────► 套餐详情
   ├─ auto-bind-coupons ────────► 先领券
   ├─ available-coupons ┐
   ├─ query-my-coupons  ├───────► 券池(四路合并、去重)
   ├─ query-store-coupons ┘
   ├─ list-nutrition-foods ─────► 营养(可选)
   │
   ▼
归一化 → optimizer.py → Top-N 方案 → 讲给用户
   │
   └─ 用户确认 → calculate-price 核价 → create-order → 支付链接
```

## 三点五、连通性自检（mcp_probe.py）

`scripts/mcp_probe.py` 用纯标准库按 MCP 规范（JSON-RPC 2.0 / Streamable HTTP）
现场验证这条链路是不是真的：initialize 握手 → notifications/initialized →
tools/list → 可选 tools/call。

```bash
export MCD_MCP_TOKEN=你的token
python mcp_probe.py                      # 握手 + 35 个工具清单
python mcp_probe.py --call now-time-info # 再真调一个工具
```

退出码：0 成功 / 1 网络或协议错误 / 2 Token 缺失或无效。
Skill 安装完先跑一遍它，能避免"算法对、数据链路错"的尴尬。

## 四、错误码与限流

| code | 原因 | 处理 |
|---|---|---|
| 401 | Token 无效/过期 | 提示用户检查 `mcp-config.example.json` 中的 Token 配置 |
| 429 | 超过 600 次/分钟 | 降低调用频率，合并请求，稍后重试 |

## 五、业务价值

1. **把钱省在明处**：把「菜单 × 券 × 叠加」的组合优化交给确定性算法，避免大模型口算出错。
2. **券不白领**：四路券池合并 + 自动领券，让用户手里的每一张券都参与最优解计算。
3. **可核验**：所有价格在下单前用 `calculate-price` 复核，方案与实际支付一致。
4. **闭环**：从「想吃」到「下单支付」全程在对话内完成，减少用户比价成本。
