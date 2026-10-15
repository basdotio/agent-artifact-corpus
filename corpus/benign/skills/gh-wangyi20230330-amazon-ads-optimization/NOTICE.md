# 来源与授权说明（NOTICE）

本项目的知识内容来自**公开来源的整理与交叉验证**，不是亚马逊官方文档的转载。

## 一、官方来源（无版权争议，仅引用与指向）

- Amazon Ads 官方指南与 API 文档（仅引用链接与口径，未复制正文）
  - `advertising.amazon.com/API/docs/en-us`
  - `advertising.amazon.com/resources/whats-new`
  - `advertising.amazon.com/library/guides/*`

## 二、第三方开源技能（已审查后采纳）

| 来源 | 授权 | 采纳方式 | 位置 |
|---|---|---|---|
| [`nexscope-ai/Amazon-Skills`](https://github.com/nexscope-ai/Amazon-Skills) → `amazon-ppc-campaign` | 上游仓库自带 LICENSE | **完整 vendor 上游正文**，去除可执行脚本 | `references/vendor/amazon-ppc-campaign.md` |

> 采纳时已做安全审查（正文为纯 Markdown，无可执行代码），并**剔除了上游附带的 `scripts/fetch-competitor.sh`**（浏览器 UA 抓取 Amazon 商品页，与本项目取数红线冲突）。该文件的版权仍归上游作者所有。

## 三、仅作为**证据引用**、未复制正文的内容

本项目在 `references/verification.md` 中记录了验证过程，引用了以下来源的**结论、数值或短句**（均为合理引用，未整文转载）：

- 开源实现：`shikhamishra379/sellerstack-amazon-seller-toolkit`、`nospicyplease/amazon-ppc-advanced-skills`、`TheBurdz/amazon-operators-field-guide`、`elementenergy41-cell/RedHen-Labs`
- 技能市场：ClawHub（`leooooooow/amazon-ppc`、`phheng/amazon-ppc-campaign`、`linbeihanda/amazon-ads-manager`、`blockchainhb/launchfast-ppc-research`、`zero2ai-hub/skill-amazon-ads-optimizer`）
- 中文公开媒体：微信公众号（阿波罗、赢商荟、亚逊精灵、私人音缘、芬香、跨境大白说、剑圣喵Amz 等）、雨果网（`cifnews.com`）转载文章
- **雨果网内容的版权归原作者所有**。本项目仅引用其方法论要点与短句用于验证记录，**不构成转载**；如需引用原文请访问雨果网对应文章。

## 四、权利主张

- 本仓库的**原创文本、脚本与结构**采用 MIT 许可（见 [LICENSE](LICENSE)）。
- **被引用内容的版权归各自权利人**。若权利人认为某处引用超出合理范围，请提 Issue，我们会立即调整或移除。
- 亚马逊相关名称与商标归 Amazon.com, Inc. 所有。本项目与亚马逊无隶属或背书关系。
