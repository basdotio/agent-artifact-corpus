---
name: amazon-ads-optimization
version: 1.1.0
description: '亚马逊广告投放优化。当用户需要搭建亚马逊广告结构（SP/SB/SD）、诊断广告表现、优化 ACoS/TACoS/ROAS、调整出价与预算、加否定词、做广告位与时段优化、分析搜索词报告、或生成广告日报/周报/月度复盘时使用。关键词：亚马逊广告、PPC、ACoS、TACoS、ROAS、出价、否定关键词、搜索词报告、Spend 报表、广告位。'
metadata:
  requires:
    bins:
      - node
---

# 亚马逊广告投放优化

一套可执行的投放优化 SOP：**拉数 → 诊断 → 决策 → 执行 → 复盘**。不做泛泛策略描述，所有结论必须落到「改什么、改成多少、为什么」。

**权威优先级**（遇冲突时按此取舍）：Amazon 官方指南 / API 文档 > 官方 Academy 课程 > 海外主流来源 > 国内公众号。本 Skill 的盈亏平衡 ACoS 与目标 ACoS 框架**与官方口径一致**（官方 `acos-advertising-cost-of-sales` 明确有 Break-even ACoS 与 target ACoS 两节），我们只是把扣项做得更细（多扣头程与退货损耗）。

## 使用前先读（重要）

- 数据怎么来、能不能直接下指令 → [references/data-integration.md](references/data-integration.md)
- 公式与阈值 → [references/metrics.md](references/metrics.md)
- 诊断规则表（最常用）→ [references/diagnosis.md](references/diagnosis.md)
- **SQP 份额漏斗（第 0 层，先定位短板在漏斗哪一环）→ [references/sqp-framework.md](references/sqp-framework.md)**
- 场景手册（新品 / 老品 / 旺季 / 清库 / 防守 / **季节性** / **断货**）→ [references/playbooks.md](references/playbooks.md)
- 动作库与安全边界 → [references/actions.md](references/actions.md)
- **大促专项复盘（PD / 黑五 / 会员日）→ [references/peak-event-review.md](references/peak-event-review.md)**
- 市场已有轮子对照（装之前先看）→ [references/market-scan.md](references/market-scan.md)
- 各渠道可获取性与主流来源地图 → [references/sources-map.md](references/sources-map.md)
- **官方教程与理论教学清单（口径存疑时先查这里）→ [references/official-resources.md](references/official-resources.md)
- **理论验证矩阵（每条阈值的证据强度与来源）→ [references/verification.md](references/verification.md)**
- 上游 PPC 方法论全文（已采纳，内部参考）→ [references/vendor/amazon-ppc-campaign.md](references/vendor/amazon-ppc-campaign.md)

## 第 0 步：先问清四件事（缺一个就不要开始算）

1. **站点**（US/UK/DE/JP…）与币种 —— 决定费用项与汇率。
2. **盈亏平衡线**：毛利率（税前、扣掉 FBA/佣金/头程/退货）→ 换算成允许的最大 ACoS。
3. **目标**：清库存 / 推新品抢占排名 / 稳定利润 / 旺季冲量 —— 目标不同，同一个 ACoS 的结论完全相反。
4. **数据可得性**：能否拿到搜索词报告、广告位报告、已推广商品报告；只有汇总数就只能做粗诊断。

**红线**：目标不明确时不要给「降 ACoS」的通用建议。清库存期 ACoS 高于盈亏平衡线可能是对的，推新品期 TACoS 上升也未必是坏事。

## 第 1 步：算清盈亏平衡 ACoS（一切出价决策的锚）

```bash
node scripts/ads_opt.mjs calc --price 39.99 --cost 8 --fba 7.5 --first-leg 3 --commission-rate 15 --return-rate 5 --target-margin 15
```

输出：盈亏平衡 ACoS、目标 ACoS、目标 ROAS、各广告位的最高可接受 CPC。公式与口径见 [references/metrics.md](references/metrics.md)。

**没有这个数，任何「出价该涨还是该降」都是拍脑袋。**

还没有关键词？先用官方自动补全扩词（免登录，12 个站点）：

```bash
node scripts/ads_opt.mjs keywords --seed "portable blender" --site us
```

## 第 2 步：诊断（按层往下切，不要一上来就调出价）

顺序固定，因为上层的错误会掩盖下层：

0. **份额层（SQP 份额漏斗）**：先定位短板在 曝光 / 点击 / 加购 / 购买 的哪一环 —— **短板在转化环节就不要调广告，去修 Listing 与价格**（需品牌备案；框架见 [references/sqp-framework.md](references/sqp-framework.md)）

1. **账户/店铺层**：TACoS 趋势、广告占比、自然位有没有被广告蚕食
2. **广告活动层**：预算是否烧穿、ACoS vs 目标、曝光份额（IS）够不够
3. **广告组层**：词包是否混杂、匹配方式是否打架
4. **搜索词层**：收割（转 Exact）、否定（浪费词）、迁移（Auto→Broad→Exact）
5. **广告位层**：Top of Search / Product Pages / Rest of Search 的转化差异
6. **时段层**：分时表现差异是否大到值得做 dayparting

每层跑一遍 [references/diagnosis.md](references/diagnosis.md) 的规则表，产出结构化问题清单，再进第 3 步。

搜索词/广告位数据可以直接喂给脚本产出动作清单：

```bash
node scripts/ads_opt.mjs diagnose --file search-terms.csv --target-acos 25 --break-even-acos 40
node scripts/ads_opt.mjs diagnose --file placement.csv --mode placement --target-acos 25

# SQP 份额漏斗（有品牌备案时先跑这个，定位短板在漏斗哪一环）
node scripts/ads_opt.mjs sqp --file sqp-report.csv
```

## 第 3 步：出动作清单（不是建议，是可执行变更）

每条动作必须写全四要素：**对象（活动/组/词/ASIN）→ 现值 → 目标值 → 依据**。标准形态：

| 优先级 | 对象 | 动作 | 依据 |
|---|---|---|---|
| P0 | 活动 X 自动型 | 否定精确 12 个词 | 点击 ≥15 且 0 转化，累计浪费 ≥$X |
| P1 | 关键词 A（广泛） | 出价 0.85 → 0.62 | ACoS 58% > 盈亏线 40%，已过学习期 |
| P1 | 搜索词 B | 新建 Exact 并迁移 | 2+ 单、ACoS 18% |
| P2 | 广告位 Top of Search | 加价 0% → 25% | TOS 转化率是其余位置 2.3 倍 |

动作定义、限速与回滚要求见 [references/actions.md](references/actions.md)。

## 第 4 步：执行（默认只出方案，改数要你点头）

- **只读默认**：查询、诊断、生成方案、生成报表 —— 直接做。
- **写操作必须逐条确认**：改出价/预算/状态、加否定词、建活动。批量变更前先给用户看变更清单与影响预估。
- 变更留痕：记录改前值，便于回滚；单次批量变更建议 ≤ 变更总量的 20%（见 actions.md 的限速规则）。
- 数据接入方式见 [references/data-integration.md](references/data-integration.md) —— 本机优先复用已有的 Ads API 代理能力。

## 第 5 步：复盘节奏

| 周期 | 看什么 | 不看什么 |
|---|---|---|
| 每日 | 预算烧穿、异常花费、跑飞的词 | 不要因单日波动调出价 |
| 每周 | 搜索词收割/否定、出价调整、广告位 | 不要每周改结构 |
| 每两周 | 广告组与匹配方式结构、预算分配 | 不要频繁重启活动（打断学习期） |
| 每月 | TACoS 与利润、ACoS 目标校准、旺季预算 | — |
| **大促后 1~2 周** | **专项复盘：新词占比、时段结构、匹配方式角色、观察名单** | 不要跳过复盘就「恢复日常广告」 |

报告模板见 [references/reporting.md](references/reporting.md)。

## 输出纪律

- 每个结论带数据依据（时间窗 + 数值 + 来源报表）。
- 区分「事实（报表数据）」与「推断（Agent 判断）」，推断要标注假设。
- 数据不足时说清缺哪张报表、为什么影响结论，不要用行业均值硬凑。
- 币种与时间窗必须写明；跨站点不要直接比 ACoS 绝对值。

## 数据与合规

- 广告数据只通过官方 Ads API（或本机已有代理能力）获取，不抓取卖家后台页面。
- 不要向用户回显内部 ID、代理地址、密钥；输出只保留业务结论与可读的活动/关键词名。
- 不要跨卖家/跨账号混用数据。








