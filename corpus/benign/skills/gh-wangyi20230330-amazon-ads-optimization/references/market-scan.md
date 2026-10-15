# 市场已有轮子对照（先看再装，避免重复造）

侦察时间：2026-09-21。结论：**投放优化方法论层已有成熟轮子，本 Skill 的差异化在「决策规则表 + 与本机 Ads API 数据层闭环 + 中国卖家口径」。**

## 一、WorkBuddy 本机技能市场

WorkBuddy 本机技能市场（应用内 UI；本地缓存在用户目录下的 `skills-marketplace/marketplace.json`）。侦察时该清单含 **268 个技能**。

**逐个筛过后：没有任何亚马逊广告 / PPC / 投放类技能。** 最接近的：

| 技能 | 覆盖 | 差距 |
|---|---|---|
| `admapix` (AdMapix) | 广告素材情报、App 分析、竞品排行、出海分析 | 偏移动 App 广告，不是亚马逊站内 PPC |
| `ecomseer` (EcomSeer) | TikTok Shop 电商数据、爆品、达人、广告素材 | TikTok 生态，非亚马逊 |
| `marketing-skills` | 23 个营销 playbook（CRO/SEO/文案/广告） | 通用营销，非亚马逊 PPC |
| `cn-ecommerce-search` / `taobao` | 中国电商比价搜索 | 与亚马逊投放无关 |
| `ecommerce-copywriter` | 电商文案/标题/详情页 | 素材侧，非投放决策 |
| `shopify-admin-api` | Shopify 店铺数据 | 独立站，非亚马逊 |

本机已装的亚马逊相关技能只有 `ziniao-amazon-ads-system`（**Ads API 数据查询/管理**，属数据层）与 `ziniao-cross-border-platform-data-research`（调研层）。**决策/优化层是缺口 —— 这就是本 Skill 的定位。**

WorkBuddy 技能市场是应用内 UI（推荐技能 + 上传技能 + 描述式查找/创建），没有公开可搜的 Web 目录；技能来源为官方团队、[ClawHub](https://clawhub.ai)、Anthropic skills、MiniMax skills、[skills.sh](https://skills.sh)。

## 二、ClawHub（可搜，有 API）

搜索接口：`https://clawhub.ai/api/search?q=<关键词>`

| 技能 | 下载 | 定位 |
|---|---|---|
| [Skill Amazon Ads Optimizer](https://clawhub.ai/zero2ai-hub/skills/skill-amazon-ads-optimizer) | 1,942 | **Amazon Ads API v3 数据层**：profiles / SP campaigns / budgets / 表现，需 LWA 凭据（clientId/secret/refreshToken/profileId）+ `scripts/ads.js` |
| [skill-amazon-ads-optimizer](https://clawhub.ai/zero2ai-hub/skills/skill-amazon-ads-optimizer) | 1,942 | 同上（同一技能） |
| [亚马逊-广告管理](https://clawhub.ai/linkfox-ai/skills/linkfox-amazon-ads-manager) | 1,116 | Linkfox 广告管理层（第三方数据服务） |
| [亚马逊-广告报表](https://clawhub.ai/linkfox-ai/skills/linkfox-amazon-ads-report) | 1,631 | Linkfox 广告报表 |
| [亚马逊-广告授权](https://clawhub.ai/linkfox-ai/skills/linkfox-amazon-ads-auth) | 1,469 | Linkfox 授权 |
| [亚马逊-广告SP洞察报告](https://clawhub.ai/linkfox-ai/skills/linkfox-amazon-ads-sp-insights-report) | 266 | SP 洞察报告 |
| [ads-amazon](https://clawhub.ai/skills-sh/agricidaniel/claude-ads/ads-amazon) | 2,827 | 多平台广告（含 Amazon） |
| [Amazon PPC](https://clawhub.ai/leooooooow/skills/amazon-ppc) | 863 | PPC 策略 |
| [Amazon Ppc Campaign](https://clawhub.ai/phheng/skills/amazon-ppc-campaign) | 950 | PPC 活动 |
| [LaunchFast PPC Research](https://clawhub.ai/blockchainhb/skills/launchfast-ppc-research) | 1,339 | PPC 关键词研究 |
| [amazon-ads-manager](https://clawhub.ai/linbeihanda/skills/amazon-ads-manager) | 595 | 广告管理 |
| [lingxiao-amazon-ads-check](https://clawhub.ai/mikeli20221102-ux/skills/lingxiao-amazon-ads-check) | 322 | 广告检查 |

## 三、skills.sh（可搜，有 API）

搜索接口：`https://skills.sh/api/search?q=<关键词>`

| 技能 | 安装量 | 定位 |
|---|---|---|
| `nexscope-ai/amazon-skills/amazon-ppc-campaign` | 1,226 | **最完整的方法论轮子**：Build + Optimize 双模式、ACoS 金融框架、Auto→Broad→Exact 漏斗、否定词、出价调整、周计划 |
| `nexscope-ai/amazon-skills/amazon-advertising-strategy` | 1,169 | SP/SB/SD 策略、预算分配、ACoS 优化 |
| `nexscope-ai/amazon-skills/amazon-display-ads` | 1,002 | SD 专项 |
| `nexscope-ai/amazon-skills/amazon-negative-keywords` | — | 否定词专项 |
| `nexscope-ai/amazon-skills/amazon-dayparting-strategy` | — | 分时策略专项 |
| `nexscope-ai/amazon-skills/amazon-keyword-research` | 1,379 | 关键词研究（喂给 PPC） |
| `nexscope-ai/amazon-skills/amazon-brand-analytics` | 1,030 | 品牌分析 |
| `nexscope-ai/amazon-skills/amazon-competitor-analysis` | 1,192 | 竞品分析 |
| `nexscope-ai/amazon-skills/amazon-profit-analyzer` | 1,041 | 利润分析（可辅助算盈亏线） |
| `linkfox-ai/linkfox-skills/linkfox-amazon-ads-report` | 391 | Linkfox 广告报表 |
| `claude-office-skills/skills/amazon-seller` | 4,631 | 泛亚马逊卖家助手 |
| `agricidaniel/claude-ads/ads-audit` | 3,476 | 广告审计（多平台） |

**中文二次开发**：[liangdabiao/Amazon-Skills-Liang](https://github.com/liangdabiao/Amazon-Skills-Liang)（★66）—— 在 nexscope Amazon-Skills 基础上改，面向中国卖家，含报告模板。

**API 层轮子**：[nexscope-ai/nexscope-ecommerce-skills](https://github.com/nexscope-ai/nexscope-ecommerce-skills)（★75，127 个技能）中的 `ecommerce-amazon-ads-manager` 覆盖 **61 个 SP/SB/SD 增删改查操作**，需 `NEXSCOPE_PROXY_BASE` + `NEXSCOPE_API_KEY`（付费代理）。

## 四、装不装？结论

| 需求 | 建议 |
|---|---|
| 要一套完整的优化方法论 | 装 `nexscope-ai/amazon-skills/amazon-ppc-campaign` 作为补充，与本 Skill 不冲突 |
| 要真实数据接入 | 本机已有 `ziniao-amazon-ads-system`（首选）；无授权再考虑 Linkfox / Zero2Ai |
| 要决策规则表 + 出价算术 + 中国卖家口径 | **用本 Skill** —— 市场上这层是空的 |
| 中文卖家视角 | `Amazon-Skills-Liang` 可参考，但注意其基于 nexscope 二次开发，维护差异大 |

安装示例（供参考，未经本 Skill 验证）：

```bash
npx skills add nexscope-ai/Amazon-Skills --skill amazon-ppc-campaign -g
openclaw skills install @zero2ai-hub/skill-amazon-ads-optimizer
```

**注意**：第三方技能装之前先做安全审查（WorkBuddy 有 `skill-scanner` / `skill-vetter` 两个安全扫描技能）。凡是要求提供商后台账号密码的，一律不要装。

---

## 五、采纳记录（2026-09-21）

**已采纳 1 个轮子，并保持单入口：**

| 项 | 内容 |
|---|---|
| 来源 | `nexscope-ai/Amazon-Skills` → `amazon-ppc-campaign` |
| 采纳方式 | **vendor 进本 Skill**，落地为 `references/vendor/amazon-ppc-campaign.md`，**不注册为独立技能**（唯一入口仍是本 Skill 的 SKILL.md） |
| 安全审查 | 正文为纯 Markdown，无脚本执行 / 无外联 / 无凭据读取 → 通过 |
| 剔除内容 | 上游 `scripts/fetch-competitor.sh`（浏览器 UA 抓 Amazon 商品页 + grep 解析 HTML）—— 违反本 Skill 取数红线，且解析脆弱 |
| 吸收要点 | 双目标 ACoS、初始出价相对关系、分档降价规则、5 维审计的第 5 维「错失机会」、建议出价 vs 可接受 CPC 的缺口决策、通用浪费修饰词表、亚马逊自动补全扩词 |
| 落地位置 | `playbooks.md`（双目标/初始出价）、`diagnosis.md`（分档降价/五维审计）、`actions.md`（缺口决策/修饰词表/扩词）、`scripts/ads_opt.mjs keywords` |

**为什么是 vendor 而不是直接安装独立技能**：直接装会多出一个 description 高度重叠的入口，Agent 在「亚马逊广告」类请求上会在两个技能间摇摆，路由不稳定。vendor 后由本 Skill 统一调度，用户侧只有一个触发点。

**未采纳**：`zero2ai-hub/skill-amazon-ads-optimizer`、Linkfox 广告系列 —— 二者均为**数据层**，与本机已有的 `ziniao-amazon-ads-system` 功能重叠，装了反而多一套凭据要维护。

