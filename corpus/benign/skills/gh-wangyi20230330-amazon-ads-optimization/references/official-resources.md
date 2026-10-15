# 亚马逊官方投流教程与理论教学（实测清单）

调研日期：2026-09-21。**结论先说：官方不仅有，而且有成体系的教程 + 理论基础，其中「盈亏平衡 ACoS / 目标 ACoS」就是官方口径 —— 本 Skill 的核心公式与官方一致。**

## 一、官方学习体系（6 个入口，均已实测可访问）

| 入口 | 地址 | 内容 | 门槛 |
|---|---|---|---|
| **Amazon Ads Academy** | https://advertising.amazon.com/academy | 官方培训总站：**课程 / 学习路径 / 视频 / 认证**。自定进度课程含引导练习与真实场景 | **免费注册**（页面明确「It is free to create an account」），任何人都可用 |
| **Academy 课程目录** | https://advertising.amazon.com/academy/catalog | 可按内容类型筛选：Certifications / Courses / Learning Paths / Videos | 同上 |
| **Academy 认证** | https://advertising.amazon.com/academy/certifications | 认证徽章 + 学习路径奖章（涵盖 Sponsored ads 到 Amazon DSP） | 同上 |
| **资源库 Library** | https://advertising.amazon.com/resources/library | 案例研究 / 专家建议 / **指南 Guides** / 新闻 / 产品，可按内容类型与产品筛选 | 免登录可读 |
| **What's New** | https://advertising.amazon.com/resources/whats-new | 产品与政策更新（认证上线、新功能） | 免登录可读 |
| **API 文档** | https://advertising.amazon.com/API/docs/en-us | 字段口径、报表类型、接口规范的**唯一权威来源** | 免登录可读 |

**重要：指南有中文版**。把 URL 里的语言段换成 `zh-cn` 即可，例如：
`https://advertising.amazon.com/zh-cn/library/guides/acos-advertising-cost-of-sales` → 《什么是广告投入产出比 (ACOS)？》

## 二、与投放直接相关的官方指南（已逐篇实测）

| 指南 | 地址（en） | 覆盖内容 |
|---|---|---|
| **ACOS（广告投入产出比）** | /library/guides/acos-advertising-cost-of-sales | 什么是 ACOS、如何计算、ROAS 区别、**什么算好的 ACOS、理解利润边际、Break-even ACOS、如何降低 ACOS、确定 target ACOS**、4 个品牌案例、*为什么不该过度关注 ACOS* |
| **商品推广优秀实践** | /library/guides/sponsored-products-best-practices | 目标设定、详情页、**投放选项、预算与出价管理、报表与衡量、前 30 天如何优化**、跨商品活动 |
| **广告优化** | /library/guides/ads-optimization | **场景化根因分析**：①把曝光转成转化（根因：投放过宽/出价错配/详情页不佳/未再营销）②让广告花费更有效（大促流量激增/预算节奏/出价优化）③把新客变回头客 |
| **CPC 是什么** | /library/guides/cost-per-click | CPC vs CPM、CPC 计算、平均与最高 CPC、手动/增强 CPC 竞价、如何降低 CPC |
| **Understanding Amazon Ads** | /library/guides/basics-of-success-understanding-amazon-advertising | 广告入门：为什么投、有什么产品、如何定目标、成本构成、术语表、如何开始 |

**sitemap 可见、未逐篇验证的其余相关指南**（路径规律同上，可自行拼接）：
`sponsored-products-budget-best-practices`、`targeting-with-sponsored-products`、`return-on-ad-spend-roas`、`ads-math`、`advertising-budget`、`boost-seasonal-sales`、`black-friday-and-cyber-monday-advertising-tips`、`6-holiday-advertising-campaigns`、`tips-to-optimize-your-display-ads-campaigns`、`sponsored-brands-what-to-know`、`brand-plus-performance-plus-best-practices`。

> 获取方式：`https://advertising.amazon.com/sitemap1.xml` ~ `sitemap11.xml`（共 32,657 条 URL），是枚举官方指南最省事的办法。

## 三、官方认证（含"广告优化"专项）

`/blog/six-amazon-ads-certifications` 列出的入门推荐：

| 认证 | 说明 |
|---|---|
| **Amazon Ads Foundations Certification** | 所有后续知识的基础（被多家代理商列为全员必修） |
| **Amazon Ads Retail Certification** | 零售与广告如何互相作用 |
| **Campaign Optimization / Advanced Retail** | **广告优化专项**（What's New 记录显示已上线） |
| Amazon DSP Advanced | DSP 进阶 |
| Amazon Video Ads | 视频广告 |
| Amazon AMC | 营销云 |

认证在 Learning Console 免费获取。**对做 skill 的启示**：官方把「广告优化」单列为认证方向，说明这确实是一块独立能力域。

## 四、官方理论 vs 本 Skill：覆盖与边界（关键）

### 官方已覆盖、且与本 Skill 一致的部分 ✅

| 理论点 | 官方原文要点 | 本 Skill 对应 |
|---|---|---|
| **盈亏平衡 ACoS** | 「Break-even ACOS 与你的利润边际直接相关；要保持盈利，ACOS 必须低于利润边际，否则你在广告上的花费超过收入」 | `metrics.md` 盈亏平衡 ACoS 公式 —— **口径一致** |
| **目标 ACoS** | 「每个品牌的目标 ACOS 不同；第一步应是先算盈亏平衡 ACoS，再与利润边际比较，然后决定目标是增销还是提品牌认知」 | `metrics.md` 目标 ACoS + `SKILL.md` 第 0 步「目标不明确不给通用建议」 |
| **不要只看 ACoS** | 官方指南专门有一节「Why you shouldn't focus too much on ACOS」 | `metrics.md` TACoS 与「ACoS 高不代表亏」 |
| **出价与预算管理** | SP 优秀实践含「Managing budgets and bids」 | `diagnosis.md` 第 2 层预算规则 + `actions.md` 出价动作库 |
| **前 30 天优化节奏** | SP 优秀实践含「如何在头 30 天优化活动」 | `playbooks.md` 场景 A 新品冷启动节奏表 |
| **场景化根因诊断** | `ads-optimization` 指南按场景列根因 | `diagnosis.md` 分层诊断规则表（同构，本 Skill 更细到阈值） |
| **大促与季节性** | `boost-seasonal-sales`、`black-friday-and-cyber-monday-advertising-tips` | `playbooks.md` 场景 C/G + `peak-event-review.md` |

### 官方不讲、本 Skill 补的部分 ⚠️（这就是本 Skill 的存在价值）

| 官方空白 | 原因 | 本 Skill 的做法 |
|---|---|---|
| **具体决策阈值**（如"点击 ≥15 且 0 单就否定"） | 官方不承担具体运营决策责任，只给方向 | `diagnosis.md` 给出阈值表，并标注"起点不是教条" |
| **跨平台/第三方工具对比** | 官方只讲自家产品 | `market-scan.md` |
| **中国卖家成本口径**（头程、退税、汇率、退货损耗） | 官方按美国/全球通用口径 | `metrics.md` 要求逐项扣 FBA/佣金/头程/退货 |
| **可执行的出价算术** | 官方讲概念不讲算式落地 | `ads_opt.mjs calc` 直接算可接受 CPC |
| **份额漏斗定位（SQP）** | 需品牌备案，官方有报表但不教分析框架 | `sqp-framework.md` |
| **渠道与情报来源** | 不属于官方职责 | `sources-map.md` |

**定位结论**：**官方给"口径与方向"，本 Skill 给"阈值与动作"。** 两者不冲突 —— 遇到任何与官方口径冲突的说法，以官方为准。

## 五、使用建议

1. **算法/字段/政策存疑时** → 先查官方指南与 API 文档，再参考第三方内容。
2. **要给客户或团队做培训** → 直接引 Amazon Ads Academy（免费、有认证、可出徽章），比转述公众号更权威。
3. **公式有争议时** → 用官方 `acos-advertising-cost-of-sales` 指南对齐；本 Skill 的盈亏平衡公式与其一致，只是扣项更细（多扣头程与退货）。
4. **中文阅读** → 把指南 URL 的 locale 段改成 `zh-cn`。
5. **不要照抄官方"最佳实践"当阈值** —— 官方给的是方向（如"出价要与目标一致"），具体数字仍需本 Skill 的阈值表 + 你自己的数据。
