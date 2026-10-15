# Amazon Ads Optimization · 亚马逊广告投放优化 Skill

> 一套**可执行**的亚马逊广告投放优化方法论，打包成 Agent Skill（`SKILL.md`）。
> 不做泛泛的策略描述 —— **所有结论都必须落到「改什么、改成多少、为什么」。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-blue)
![No API Key](https://img.shields.io/badge/API%20Key-不需要-green)

---

## 这是什么

把亚马逊广告优化从"凭经验拍脑袋"变成**可复算、可追溯、可审计**的流程：

```
拉数 → 诊断 → 决策 → 执行 → 复盘
```

它不是一个爬虫或自动化工具，而是一套**决策层**能力：接在数据层（官方 Ads API / 后台报表导出）之上，产出**具体的动作清单**（改哪个词、改到多少、依据是什么）。

**适合谁**：亚马逊运营 / 广告优化师 / 代运营团队 / 想系统化学广告的卖家。
**不适合谁**：想要"一键自动调价机器人"的人 —— 本项目默认**只出方案，不落盘**。

---

## 核心特性

### 1. 从「出价算术」开始，而不是从「策略」开始

所有出价决策锚定在**盈亏平衡 ACoS** 上，并且给出可复算的算式：

```
盈亏平衡 ACoS = 单位广告前贡献 ÷ 售价
可接受 CPC    = 售价 × 转化率 × 目标 ACoS
动态点击阈值  = 1 ÷ 转化率
```

### 2. 一条命令算出你的出价天花板

```bash
node scripts/ads_opt.mjs calc \
  --price 39.99 --cost 8 --fba 7.5 --first-leg 3 \
  --commission-rate 15 --return-rate 5 --target-margin 15 --cvr 8
```

输出（实测）：

```
广告前单位贡献  USD 13.49
盈亏平衡 ACoS   33.74%   (ROAS 2.96)
目标 ACoS       18.74%   (目标单件净利 USD 6.00)
可接受 CPC      USD 0.60   <- 目标 ACoS 18.74% × CVR 8.00% × 售价
CPC 上限(不亏)  USD 1.08
```

> **没有这个数，任何「出价该涨还是该降」都是拍脑袋。**

### 3. 诊断器：把报表变成动作清单

```bash
# 搜索词报告 → P0/P1/P2 分级动作
node scripts/ads_opt.mjs diagnose --file examples/sample-search-term-report.csv \
  --target-acos 25 --break-even-acos 40

# 广告位报告 → 按位置给建议
node scripts/ads_opt.mjs diagnose --file examples/sample-placement-report.csv \
  --mode placement --target-acos 25

# SQP 份额报告 → 定位漏斗短板在哪一环
node scripts/ads_opt.mjs sqp --file examples/sample-sqp-report.csv

# 官方自动补全扩词（免登录，12 个站点）
node scripts/ads_opt.mjs keywords --seed "portable blender" --site us
```

### 4. 每个阈值都能追到证据

这是本项目最不同于其他"经验贴整理"的地方 —— **每个非官方阈值都有出处与证据强度标注**：

`references/verification.md` 记录了 **6 轮交叉验证**：11 个独立开源实现 + 32 个中文公开来源 + 2 个官方来源，
标注了每条理论的**证据源、原文依据、是否达标（≥5 佐证）、以及哪些只是经验起点**。

**验证过程中推翻了自己 3 处写法**（这正是做验证的意义）：

| 被推翻的原写法 | 为什么错 | 改后 |
|---|---|---|
| Product Pages ACoS 低 → 提高 PP 加价 | 独立实现明确否定：*There is no "Product Pages boost" in any sensible ruleset* | 按 ACoS 相对盈亏平衡线的倍数判定，PP 只有收紧档 |
| 收割判据 = 订单 ≥2 **且 ACoS ≤ 目标** | ACoS 差但稳定转化的词，恰恰最需要独立活动来调出价 | 改为**转化速率**制，ACoS 只用于定出价 |
| 时段低迷 → **暂停投放** | 暂停会破坏连续性、降低广告权重与质量得分 | 改为**降预算与出价，不暂停** |

### 5. 明确区分「官方口径」与「经验起点」

**权威优先级**：Amazon 官方指南 / API 文档 > 官方 Academy 课程 > 海外主流来源 > 国内公开媒体。

本项目的盈亏平衡 ACoS 与目标 ACoS 框架**与官方口径一致**（官方 `acos-advertising-cost-of-sales` 明确有 *Break-even ACOS* 与 *target ACOS* 两节），我们只是把扣项做得更细（多扣头程与退货损耗）。

---

## 快速开始

### 安装为 Agent Skill

把整个目录放到你的 Agent 技能目录即可（`SKILL.md` 必须保留在根目录）：

```bash
# Claude Code / Codex / OpenClaw 等通用 Agent Skills 目录
git clone https://github.com/<owner>/amazon-ads-optimization.git \
  ~/.agents/skills/amazon-ads-optimization

# Windows PowerShell
git clone https://github.com/<owner>/amazon-ads-optimization.git `
  "$env:USERPROFILE\.agents\skills\amazon-ads-optimization"
```

重启 Agent 或新开会话即可被发现。

### 直接当作方法论文档阅读

不需要 Agent 也能用。建议阅读顺序：

```
SKILL.md                       → 主流程（5 分钟了解全貌）
references/metrics.md          → 公式与口径
references/diagnosis.md        → 诊断规则表（最常用）
references/playbooks.md        → 8 个场景手册
references/actions.md          → 动作库与安全边界
```

### 环境要求

- **Node.js ≥ 18**（仅 `scripts/ads_opt.mjs` 需要；纯 Markdown 部分无依赖）
- 无第三方依赖，无 API Key

---

## 目录结构

```
amazon-ads-optimization/
├── SKILL.md                      # Agent Skill 入口（主流程）
├── references/
│   ├── metrics.md                # 指标口径与核心公式
│   ├── diagnosis.md              # 9 层诊断规则表（含份额层）
│   ├── sqp-framework.md          # SQP 份额漏斗分析框架
│   ├── playbooks.md              # 8 个场景手册
│   ├── actions.md                # 动作库 / 限速 / 回滚
│   ├── reporting.md              # 日报 / 周报 / 月度模板
│   ├── peak-event-review.md      # 大促专项复盘
│   ├── data-integration.md       # 取数通道与 CSV 列名约定
│   ├── official-resources.md     # 官方教程与理论清单
│   ├── sources-map.md            # 渠道地图与可达性实测
│   ├── market-scan.md            # 已有开源方案对照
│   ├── verification.md           # ★ 六轮理论验证与证据矩阵
│   └── vendor/
│       └── amazon-ppc-campaign.md  # 已审查采纳的上游方法论
├── scripts/
│   └── ads_opt.mjs               # calc / diagnose / sqp / keywords
├── examples/                     # 样例报表（可直接跑）
├── README.md · README.en.md
├── CONTRIBUTING.md · CHANGELOG.md · SECURITY.md · NOTICE.md
└── LICENSE
```

---

## 诊断框架（9 层）

顺序固定 —— **上层问题会掩盖下层，跳层调优等于在错误的地基上装修。**

```
第 0 层  份额漏斗（SQP）   ← 先定位短板在 曝光/点击/加购/购买 哪一环
第 1 层  店铺 / 账户        TACoS 趋势、广告占比、是否蚕食自然位
第 2 层  广告活动           预算是否烧穿、ACoS vs 目标、曝光份额
第 3 层  广告组 / 关键词     结构是否混杂、匹配方式是否打架
第 4 层  搜索词             收割 / 否定 / 迁移
第 5 层  广告位             TOS / Rest of Search / Product Pages
第 6 层  时段               预算节奏与竞价
第 7 层  大促期指标解读      CTR↓ + CVR↑ 是正常现象，不是效率下降
第 8 层  新增需求分析       新词 vs 历史词的增量信号
```

**第 0 层的意义**：防止把「转化问题」当成「出价问题」而不断加价 —— 这是投放优化里最贵的错误。
> 份额落差在哪一环，钱就不该花在广告上，而该花在那一环。

---

## 使用纪律（重要）

本项目把下面这些当成**硬约束**写进了 Skill：

| 纪律 | 说明 |
|---|---|
| **默认只出方案，不落盘** | 查数、诊断、生成方案可直接做；**改出价/预算/状态必须逐条确认** |
| **批量变更 ≤ 总量的 20%** | 限速规则，防止把账户调坏 |
| **必须记录改前值** | 拿不到改前值的批量工具不要用（无法回滚） |
| **学习期不动** | 新建或大改后 < 3 天（保守默认 7 天）不调出价与结构 |
| **库存不足不加投** | 可售天数 < 30 天停止所有加投类动作 |
| **大促当天不做结构判断** | 大促数据不可与日常比 |
| **不抓平台页面取数** | 只走官方 API 与后台报表导出 |

---

## 常见问题

**Q：一定要有品牌备案吗？**
只有**第 0 层（SQP 份额漏斗）**需要品牌备案。没有备案可以跳过第 0 层，直接从第 1 层开始诊断，但要意识到"转化问题 vs 投放问题"的区分能力会下降。

**Q：没有 API 授权能用吗？**
可以。从广告后台导出搜索词报告 / 广告位报告为 CSV，直接喂给 `diagnose` 子命令即可。列名约定见 `references/data-integration.md`。

**Q：脚本会自动改我的广告吗？**
**不会。** 脚本只做本地算术和两个公开只读接口调用，不包含任何写操作。

**Q：这些阈值适合我的类目吗？**
阈值是**起点不是教条**。文档中已明确标注哪些是**多源验证**、哪些只是**经验起点**（见 `references/verification.md`）。请用自己类目的数据校准。

**Q：为什么不直接给一个"最优 ACoS"？**
因为官方立场也是「每个品牌目标不同，第一步应先算盈亏平衡 ACoS」—— 同一句"目标 30%"对 55% 毛利的产品是胜利，对 20% 毛利的产品是灾难。

---

## 贡献

欢迎补充**带证据**的内容。请先读 [CONTRIBUTING.md](CONTRIBUTING.md)。

特别欢迎这两类贡献：
1. 为 `references/verification.md` 中标记为「经验起点 / 单一来源」的条目**补充证据源**
2. 补充**你所在类目**的阈值校准数据（请脱敏）

## 变更记录

见 [CHANGELOG.md](CHANGELOG.md)。

## 许可与来源

- 本项目原创内容：[MIT](LICENSE)
- 第三方来源与授权说明：见 [NOTICE.md](NOTICE.md)
- 安全政策：[SECURITY.md](SECURITY.md)

> 本项目与 Amazon.com, Inc. 无隶属或背书关系。Amazon 及相关商标归其所有者所有。
