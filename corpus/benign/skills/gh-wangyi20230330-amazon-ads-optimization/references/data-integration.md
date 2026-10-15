# 数据接入：怎么把数拿到手

本 Skill 负责**决策**，不负责**取数**。取数按下面的优先级选通道。

## 通道优先级

| 优先级 | 通道 | 适用 | 前置条件 |
|---|---|---|---|
| 1 | **本机已装的亚马逊广告 API 数据技能** | 有 Ads API 授权的店铺：活动/广告组/关键词/投放/预算/报表 | 店铺已完成 Ads 平台授权 |
| 2 | Linkfox 等第三方数据服务 | 没有 Ads API 授权，但有 Linkfox 账号 | 账号 + API Key |
| 3 | 用户手动导出 CSV | 任何情况都可行，作为兜底 | 从广告后台导出搜索词/广告位/已推广商品报告 |
| 0 | **品牌分析 SQP 报告**（搜索查询绩效） | 定位份额短板（曝光/点击/加购/购买哪一环漏） | **需品牌备案**；无备案则跳过第 0 层 |

**禁止**：抓取亚马逊卖家后台/广告后台页面来取数。合规与稳定性都不可接受。

## 通道 1：本机 Ads API 数据技能

本机已安装的 `ziniao-amazon-ads-system` 提供 Amazon Ads API 的数据查询与管理能力（profiles / campaigns / ad groups / keywords / targeting / budgets / 报表）。

调用前必须先完成该技能规定的账户解析与授权闸门（它会自行处理凭据与店铺选择），**本 Skill 不重复实现取数逻辑，也不接触密钥**。

典型用法：
- 需要「活动清单 + 预算 + 状态」→ 走它的 campaigns / ad groups 查询
- 需要「搜索词报告」→ 走它的异步报告流程（创建报告 → 轮询状态 → 取报告文件）
- 需要「广告位报告 / 已推广商品报告」→ 同上，注意报表类型不同

**交接约定**：把取到的数据整理成下表列名后交给本 Skill 的诊断规则，不要直接把原始 JSON 贴给用户。

## 通道 3：手工 CSV 的列名约定

`scripts/ads_opt.mjs diagnose` 认这些列名（大小写不敏感，允许中英混用）：

**搜索词模式（默认 `--mode searchterm`）**

| 列 | 含义 | 必需 |
|---|---|---|
| `term` / `搜索词` / `customer search term` | 搜索词 | ✅ |
| `clicks` / `点击` | 点击 | ✅ |
| `orders` / `订单` / `purchases` | 订单 | ✅ |
| `spend` / `花费` / `cost` | 花费 | ✅ |
| `sales` / `销售额` | 广告销售额 | ⬜（缺则用 spend/ACoS 反推） |
| `campaign` / `活动` | 活动名 | ⬜ |
| `matchtype` / `匹配方式` | 匹配方式 | ⬜ |

**广告位模式（`--mode placement`）**

| 列 | 含义 |
|---|---|
| `placement` / `广告位` | Top of Search / Product Pages / Rest of Search |
| `clicks` / `点击` | 点击 |
| `orders` / `订单` | 订单 |
| `spend` / `花费` | 花费 |
| `sales` / `销售额` | 广告销售额 |

示例：

```bash
node scripts/ads_opt.mjs diagnose --file search-terms.csv --target-acos 25 --break-even-acos 40
node scripts/ads_opt.mjs diagnose --file placement.csv --mode placement --target-acos 25
node scripts/ads_opt.mjs diagnose --file st.xlsx.json --format json
```

输出为 Markdown 动作清单（P0/P1/P2 分级）。CSV 支持逗号、制表符分隔，UTF-8（含 BOM 亦可）。

## 数据不足时的降级策略

| 缺什么 | 还能做什么 | 不能做什么 |
|---|---|---|
| 缺搜索词报告 | 只做活动层诊断（ACoS/预算/IS） | 不能产出否定词清单、不能做收割 |
| 缺广告位报告 | 只做活动与搜索词层 | 不能给出广告位加价建议 |
| 只有汇总 ACoS/花费/销售额 | 只能判断「是否超标」「该收还是该放」 | 不能给出到词级的出价数字 |
| 无退货率/费用明细 | 只能给 ACoS 区间参考 | 不能给精确盈亏平衡 ACoS |

**明确说出缺什么、因此哪些结论不能给** —— 这比硬凑一个数字更有价值。

## 输出与保密

- 只输出业务可读名称与结论；不输出内部 profile ID、代理地址、密钥、原始 JSON。
- 币种与时间窗必须标注。
- 跨店铺数据不混用。

