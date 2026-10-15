# 变更记录

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

（待补充）

---

## [1.1.0] — 2026-09-21

首个开源版本。经过 **6 轮理论交叉验证**后定稿。

### 新增

- **核心框架**：盈亏平衡 ACoS / 目标 ACoS / 可接受 CPC 的完整口径与扣项（含头程与退货损耗）
- **9 层诊断规则表** `references/diagnosis.md`（份额 → 店铺 → 活动 → 广告组 → 搜索词 → 广告位 → 时段 → 大促期 → 新词）
- **SQP 份额漏斗框架** `references/sqp-framework.md`（份额断崖定位法 + 词簇法）
- **8 个场景手册** `references/playbooks.md`（新品 / 成熟 / 旺季 / 清库 / 防守 / 季节性 / 断货 / 大促后）
- **大促专项复盘** `references/peak-event-review.md`（三维度九问 + 自然权重验证法）
- **动作库与安全边界** `references/actions.md`（分级、限速、回滚、执行前检查清单）
- **报告模板** `references/reporting.md`（日报 / 周报 / 月度）
- **官方资源清单** `references/official-resources.md`
- **渠道可达性实测** `references/sources-map.md`
- **理论验证矩阵** `references/verification.md`（六轮证据留痕）
- **脚本** `scripts/ads_opt.mjs`：`calc` / `diagnose` / `sqp` / `keywords` 四个子命令
- **示例数据** `examples/`（可直接运行）

### 采纳（第三方）

- 采纳 `nexscope-ai/Amazon-Skills` 的 `amazon-ppc-campaign` 方法论（vendor 到 `references/vendor/`，经安全审查，剔除其可执行脚本）
- 采纳 Amazon Ads Academy 与官方指南作为权威口径来源

### 修正（验证过程中推翻的自身写法）

- **广告位判定**：删除「Product Pages ACoS 低 → 提高 PP 加价」（独立实现明确否定该做法），改为按 ACoS 相对盈亏平衡线的倍数判定
- **收割判据**：从「订单 ≥2 **且 ACoS ≤ 目标**」改为**转化速率**制；ACoS 只用于决定收割后的出价，不用于决定是否收割
- **时段优化**：删除「暂停投放」选项，改为降预算与出价（暂停会破坏连续性、降低广告权重与质量得分）

### 变更

- 否定词点击阈值：从固定 15 次 → 固定 10 次 → 最终改为 **`1 ÷ CVR` 动态推导（下限 5）**
- 学习期：由「7 天」改为「**保守默认 7 天，最小不低于 3 天**」，并补充「频繁调整会重置/延长学习期」的机制说明
- 观察窗口：明确 **3~5 天** 的调价观察期与 **7/14 天** 的复盘窗口

### 安全

- 全仓库无凭据、无密钥；脚本无网络写操作
- 剔除上游附带的页面抓取脚本（与取数红线冲突）

---

## 版本号含义

- **MAJOR**：诊断框架或核心公式发生不兼容变化（如层级重排、公式定义变更）
- **MINOR**：新增场景/子命令/参考文档，或补充验证使阈值发生调整
- **PATCH**：文字修正、示例补充、无行为变化的修复
