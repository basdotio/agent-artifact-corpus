# 投放知识渠道地图与实测可获取性

侦察日期：2026-09-21。**用途**：知道去哪学、哪些能程序化读、哪些读不到别浪费时间。

## 一、可获取性实测（最重要的一张表）

| 渠道 | 程序化读取 | 实测结论 | 建议 |
|---|---|---|---|
| **微信公众号** | ⚠️ 部分 | 搜狗微信检索（`weixin.sogou.com`）**可搜可读摘要**；`mp.weixin.qq.com/s/<token>` 直链**有时能读全文、有时被反爬拦**（实测：阿波罗 PD 复盘那篇能读，同号 SQP 那篇被拦） | 主要靠它；拿不到全文时用摘要 + 标题定位 |
| **抖音** | ❌ | 只能拿到热榜**标题**（见 info-hub 技能）；账号视频、文案、评论都需登录态或抓取 | 不要指望程序化学习；需要时人工看 |
| **小红书** | ❌ | 搜索与笔记详情都需登录 Cookie，服务端 IP 高概率触发风控 | 同上；插件版本地跑是唯一稳妥路径（见 info-hub/sources.md） |
| **Reddit** | ❌ | **本机实测 403（Blocked）** —— Reddit 屏蔽数据中心 IP | 用 Agent-Reach / last30days 的登录态通道，或放弃 |
| **海外博客** | ✅ | Jungle Scout / Helium 10 / Teikametrics / Perpetua / sell.amazon.com **均可直接抓取** | 可程序化学习 |
| **Amazon 官方** | ✅ | `advertising.amazon.com/API/docs/en-us`、`advertising.amazon.com/resources/whats-new` 可读 | 字段与政策口径的唯一权威来源 |

## 二、主流公众号（亚马逊投放方向）

检索方式：`https://weixin.sogou.com/weixin?type=2&query=<关键词>`（免登录，可程序化）

| 账号 | 内容特点 |
|---|---|
| **从宇宙大爆炸到PPC（阿波罗）** | 大促复盘框架、SQP、A9 算法专利解读、Rufus/GEO —— 偏**方法论与算法原理** |
| **跨境电商赢商荟** | 广告诊断优化 SOP、**11 条广告优化口诀** —— 偏**口诀式速查** |
| **亚逊精灵课堂** | **8 条广告优化准则** —— 偏**原则与耐心纪律** |
| **大宝站外推广** | ACoS/TACoS/ROAS 关系、广告位出价比例优化 CVR |
| **葫芦娃站外推广** | 广告表现不佳的优化策略 |
| **三头六臂跨境电商联盟** | 降低 ACoS 的思路（否定词等）、PPC 全攻略 |
| **百聚汇曾德威 / 大麦俱乐部** | 降 ACoS 实操案例、PPC 进阶玩法 |
| **易风说跨境** | **不同时期的广告打法**（季节性 / 即将断货 / 滞销）—— 场景化 |
| **Maxdon 跨境** | 广告投放的**4 个层级与 5 步优化法** |
| **ABA Hacker / Sorftime 资讯** | ABA/SQP 数据工具化、流量结构透视 |
| **Moss的精神家园 / 跨境派大师兄** | PPC 思路与玩法演变 |
| **跨境移花宫 / 天机处上圣天尊** | 自研广告系统、高阶操盘 SOP |

**检索关键词建议**：`亚马逊 广告 优化`、`亚马逊 PPC 打法`、`亚马逊 广告 诊断 优化 SOP`、`亚马逊 广告 优化 口诀`、`降低 ACoS`。

## 三、海外主流来源

| 来源 | 定位 |
|---|---|
| Amazon Ads 官方 API 文档 / What's New | 字段口径、政策变化的**唯一权威** |
| Helium 10 Ads Academy / Ads Learning Hub | 工具化投放与自动化 |
| Jungle Scout Academy / 博客 | 卖家实操、入门到进阶 |
| Teikametrics / Perpetua / SellerLabs | 自动化竞价与算法化投放（DSP、规则引擎） |
| Reddit（r/AmazonFBA、r/FulfillmentByAmazon、r/AmazonSeller） | 一线卖家经验与踩坑（**本机被 403，需走登录态通道**） |

## 四、中外方法论一致性核对（本次"验证"结论）

把国内主流（上表公众号）与海外主流（博客/官方）对照后，**核心方法论高度一致**，本 Skill 现有框架无需重构：

| 主流共识 | 本 Skill 对应位置 | 核对结果 |
|---|---|---|
| 调整节奏：每天只处理异常 / 每周常规优化 / 每月总结 | `reporting.md` 三份模板 | ✅ 一致 |
| 出价决策必须建立在盈亏平衡 ACoS 上 | `metrics.md` + `calc` | ✅ 一致 |
| 匹配方式组合使用，自动探索、手动收掌控 | `playbooks.md` 角色分工 | ✅ 一致 |
| 否定词是降 ACoS 的首要手段 | `diagnosis.md` 第 4 层 | ✅ 一致 |
| 广告位加价按边际效率调，不是一次拉满 | `diagnosis.md` 第 5 层 | ✅ 一致 |
| 改动前要等（学习期） | `diagnosis.md` 第 2 层 | ✅ 一致 |
| 分阶段打法（新品 / 成熟 / 清库 / 断货 / 季节） | `playbooks.md` A/B/D/**G/H** | ⚠️ 本次补齐 G、H |
| 份额视角（SQP）定位短板 | `sqp-framework.md` | ✅ 已补 |
| 大促专项复盘 | `peak-event-review.md` | ✅ 已补 |

**差异（不是优劣，是风格）**：国内内容偏**口诀与 SOP 速查**，海外内容偏**数据口径与自动化**。本 Skill 的做法是**用国外的口径严谨性做底（公式、字段、边界），用国内的口诀做检索效率（快速定位）**。

## 五、使用纪律

- 引用渠道内容时**注明来源与日期**，不把公众号观点当官方口径。
- 任何与 Amazon 官方文档冲突的说法，**以官方文档为准**并说明冲突。
- 口诀类内容（如「曝光高点击率低→优化主图」）**只作为检索线索**，落地前仍要走 `diagnosis.md` 的阈值与证据要求。
- 渠道文章常带引流钩子（扫码领 Skills 等），**只取方法论，不引入未审查的第三方代码/技能**。

---

## 六、官方来源（最高优先级，详见 official-resources.md）

**Amazon 官方有成体系的投流教程与理论教学**，实测均可访问：

| 入口 | 内容 | 门槛 |
|---|---|---|
| `advertising.amazon.com/academy` | **Amazon Ads Academy**：课程 / 学习路径 / 视频 / 认证 | 免费注册 |
| `advertising.amazon.com/resources/library` | 资源库：案例 / 专家建议 / **指南** / 新闻 | 免登录 |
| `advertising.amazon.com/resources/whats-new` | 产品与政策更新 | 免登录 |
| `advertising.amazon.com/API/docs/en-us` | API 与报表字段权威口径 | 免登录 |

**关键官方指南**：`acos-advertising-cost-of-sales`（含 **Break-even ACOS** 与 **target ACOS**）、`sponsored-products-best-practices`（含前 30 天优化节奏）、`ads-optimization`（场景化根因诊断）、`cost-per-click`。

**指南有中文版**：把 URL 语言段换成 `zh-cn` 即可。

> **权威优先级**：官方指南/API 文档 > 海外主流博客 > 国内公众号。任何冲突以官方为准。
> 完整核对结论（官方已覆盖什么、官方不讲什么）见 [official-resources.md](official-resources.md)。
