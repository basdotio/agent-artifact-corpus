---
name: mcd-saver-strategist
description: 麦门省钱精算师。当用户在麦当劳（麦当劳/麦麦/金拱门/麦乐送/到店取餐）点餐，并希望"最省钱、凑满减、把优惠券用到极致、性价比最高、在预算内吃好"时使用；也适用于"帮我看看这些券怎么用最划算""我想吃XX但想便宜点""30块钱能吃到什么"这类诉求。它通过麦当劳 MCP 拉取门店菜单、可用优惠券、营养信息，再用确定性组合优化算法穷举出总价最低的合规点餐方案，并在用户确认后下单。
agent_created: true
---

# 麦门省钱精算师

## 这个 Skill 解决什么问题

麦当劳的优惠体系是「菜单 × 优惠券 × 叠加规则」的组合爆炸问题：同一顿饭，
直选可能花 47 元，「1+1 随心配」+ 单点一杯饮料只要 21.9 元。人类用户懒得算，
大模型**算不准**（组合数多、券规则细、口算容易错）。

本 Skill 的分工非常明确：

- **MCP 负责「取数」**：菜单、价格、优惠券、营养、门店。
- **`scripts/optimizer.py` 负责「算」**：在组合空间里穷举，给出确定性最优解，
  并回答四个衍生问题——多目标选型、券体检、凑单建议、帕累托前沿。
- **你（Agent）负责「说」和「做」**：把结果讲成人话、给出推荐、经用户确认后下单。

> 核心纪律：**永远不要自己口算价格或用券组合**。所有金额必须来自
> `optimizer.py` 的输出或 MCP 的 `calculate-price` 返回值。

## 何时使用

触发场景举例：

- "我想吃巨无霸套餐，怎么点最便宜？"
- "我有这些券，帮我看看怎么用最划算"
- "30 块钱在麦当劳能吃到什么？"
- "减肥中，想吃麦当劳但热量控制在 800 大卡以内，还要便宜"
- "帮我在麦乐送点一份午餐，别超过 40"

## 工作流

### 第 0 步：确认前提（缺一不可）

开始前必须明确这几件事，缺哪个就向用户问哪个：

1. **就餐方式**：外送到家 / 到店取餐 / 堂食外带（决定用 `delivery-*` 还是 `query-nearby-stores`）。
2. **位置或门店**：外送需要配送地址，到店需要哪个门店。
3. **想吃的东西 / 约束**：想吃什么（可模糊）、预算上限、热量上限、几人吃。
4. **点餐目标**（可选）：默认「最省钱」；用户在意"吃全一点""低卡""少点几件"时，
   分别用 `objective: balanced / lightest / fewest`。不用反复追问，按语气判断即可。

### 第 1 步：通过 MCP 取数

按顺序调用（注意 600 次/分钟的限流）：

1. `now-time-info` —— 拿当前时间，判断早餐/正餐时段与活动。
2. **门店**
   - 到店：`query-nearby-stores` 定位门店。
   - 外送：`delivery-query-addresses` 选地址 → `delivery-query-stores` 查可配送门店。
   - 团餐：额外 `query-meal-assistance`。
3. `query-meals` —— 拉当前门店可售菜单（分类、编码、价格、标签）。
4. `query-meal-detail` —— 对候选套餐拉详情，确认可选替换项。
5. **优惠券（四路都要查，缺一会漏钱）**
   - `available-coupons` —— 麦麦省当前可领券。
   - `auto-bind-coupons` —— 一键领取麦麦省全部可用券（**必须调用**，否则券池不全）。
   - `query-my-coupons` —— 我账户下已有的券。
   - `query-store-coupons` —— 当前门店专属券。
6. `list-nutrition-foods` —— 当用户有热量/营养约束时拉取。

### 第 2 步：归一化数据并调用优化器

把 MCP 结果整理成 `optimizer.py` 的输入契约（见
[`references/mcp-tools.md`](references/mcp-tools.md) 的「字段映射表」），写到临时目录：

```
tmp/menu.json     # {store_code, currency, items:[{code,name,category,price,calories,tags}]}
tmp/coupons.json  # {coupons:[...]}  见 references/coupon-strategy.md 的券类型定义
tmp/request.json  # {wants, budget, max_calories, max_items, allow_extras,
                  #  dining_mode:"pickup"|"delivery", delivery_fee(外送时必填),
                  #  objective:"cheapest"|"balanced"|"lightest"|"fewest",
                  #  party_size: 人数(默认 1)}
```

券的场景字段：能判断「仅到店 / 仅外送可用」的券，标注 `"channel":"pickup"` 或 `"delivery"`，
不确定就留空（默认 `any`）。外送场景优化器会自动剔除不可用券，并把配送费计入总价。

然后运行：

```bash
python scripts/optimizer.py <临时目录>
```

- 加 `--json` 可同时输出结构化 JSON，便于你读取字段。
- 加 `--audit` 额外输出券体检（每张券的名义面额 / 实际节省 / 机会成本）。
- 想看内置样例：`python scripts/optimizer.py sample_data`
- 一键看 7 个真实场景：`python scripts/demo.py`
- 改完逻辑务必跑 `python scripts/selftest.py`（46 项断言应全绿）。

**优化器返回里值得讲给用户的三块**（都在 JSON 里）：

- `objective_reason` —— 为什么选这个方案（多目标时必讲）。
- `gap` —— 凑单建议：差几元到下一档、补位商品、净变化。
  `net_change < 0` 意味着"加购反而更省"，`verdict=costly` 意味着"别为凑门槛多花钱"，都要如实说。
- `pareto` —— 价格 × 热量的不可支配解集。用户纠结"便宜还是低卡"时，把这条边界摊给他看。

### 第 2.5 步：券体检（券多时强烈建议）

用户手里券多、或纠结用哪张时，跑 `audit_coupons()`（CLI: `--audit`），它会回答：

- **名义面额** vs **实际节省** —— 两者的差额体现为兑现率（实际省 / 名义面额）。
- **机会成本** —— 只用这张券会比全局最优多花多少。最需要留意的情况不是"券没用"，
  而是"小券挤掉大组合"：每张券单看都在省钱，用了它反而吃不到 1+1 随心配。
- 判定分级：`worth`（值得用）> `marginal`（聊胜于无）> `suboptimal`（不是最优）
  > `trap`（机会成本偏高）> `conditional`（需先加购）> `useless` / `invalid`。

把 `worth` 和 `trap` 讲清楚就够了，不要把 8 张券全部念一遍。
> 表述纪律：只陈述**券面数据与算法计算结果**，使用中性词（"名义面额与实际优惠的差额"
> "机会成本较高"），不对麦当劳的券或产品做主观评价。

### 第 3 步：把结果讲给用户

- 默认展示 **Top 3** 方案，用「到手价」而不是「原价」开头。
- 每个方案说明：**省了多少钱 / 折算几折 / 用了哪张券 / 关键约束（预算、热量）是否满足**。
- 多人拼单时报**总价和人均**，并说明"优惠只计一次（保守），到店实际可能更便宜"。
- 如果最优方案为了用券而**加购**了东西（`notes` 里会提示），要显式告诉用户：
  "为了用满 35 减 7，多加了 X，但总价反而更低" —— 让用户自己判断值不值。
- 用中文、口语化，不要罗列 JSON。金额保留两位小数。

### 第 4 步：下单（务必先确认）

用户选定方案后：

1. 用 `query-meal-detail` + `calculate-price` 做**下单前最终核价**：
   把方案里的 `code` 列表传给 `calculate-price`，确认 MCP 侧算出的价格与
   `optimizer.py` 结果一致（差异通常来自门店实时变价或缺货）。
2. **把最终价格、门店、菜品清单复述给用户，等待明确确认。**
3. 确认后用 `create-order` 下单，把支付链接交给用户；或按用户要求 `cancel-order`。

> ⚠️ 下单 / 取消是**不可逆的对外动作**，未经用户明确同意绝不执行。

## 硬性约束

- 价格、优惠、券的可用性一律以 **MCP 实时返回**为准；本地数据只是计算用的快照。
- 绝不编造不存在的优惠券、菜品或价格。MCP 没有返回的券，就不能算进方案。
- 若 `optimizer.py` 无解（预算/热量过严），如实告知并给出「放宽哪一项」的建议，
  不要为了凑出答案而突破用户约束。
- 不提供医疗、营养或健康诊断建议；营养数据仅供参考。

## 资源索引

- [`scripts/optimizer.py`](scripts/optimizer.py) —— 确定性优惠组合优化器 v2（多目标 / 券体检 / 凑单 / 帕累托 / 拼单，纯标准库）。
- [`scripts/selftest.py`](scripts/selftest.py) —— 46 项自测，改动逻辑后必跑。
- [`scripts/demo.py`](scripts/demo.py) —— 7 个真实场景一键演示（离线可跑）。
- [`scripts/bench.py`](scripts/bench.py) —— 性能基准：菜品 10~160 款规模下的耗时。
- [`scripts/mcp_probe.py`](scripts/mcp_probe.py) —— MCP 连通自检：握手 / 工具清单 / 试调用。
- [`scripts/parity_check.mjs`](scripts/parity_check.mjs) —— 前后端对拍（需 Node）。
- [`scripts/sample_data/`](scripts/sample_data/) —— 可离线跑通的示例菜单/券/请求。
- [`references/mcp-tools.md`](references/mcp-tools.md) —— 用到的 MCP Tool 清单与字段映射表。
- [`references/coupon-strategy.md`](references/coupon-strategy.md) —— 5 类优惠券建模、叠加与互斥规则、券体检与省钱策略。
