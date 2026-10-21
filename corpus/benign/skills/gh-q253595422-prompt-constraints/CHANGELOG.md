# Changelog

本项目所有值得记录的变更都会写在这里。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### 计划中

- `references/models.md` 按高频模型拆分为独立子文档（Nano Banana Pro / Seedance）
- 英文版 `README.en.md`
- 更多经实测的 `examples/` 用例（产品摄影、角色一致性全流程）

---

## [1.0.0] - 2026-09-21

首个正式版本。建立完整的约束方法论与参考库。

### Added

- **SKILL.md** —— skill 入口：11 条路由规则、六层约束速查、输出契约、按需加载表。
- **六层约束模型**（`references/constraints-core.md`）—— 本项目核心方法论：
  L1 事实（不编造）→ L2 媒介（定边界）→ L3 结构（锚点前置）→ L4 一致性（不变量）
  → L5 排除（具象化）→ L6 参数（外置），每层含判定标准与自检项。
- **`references/image.md`** —— 12 维图像维度框架、参考图反推（图生文）完整流程、
  Level 1—3 复杂度分级、图生图编辑约束、7 类常见失败模式。
- **`references/video.md`** —— 视频与生图的根本差异对照、全局视频约束（T1—T6）、
  输入模式判定、参考资产映射、时间轴容量表、POV 物理约束表、镜头语言、
  音频导演、编号停靠 vs 红线路径控制两模式、8 类常见失败模式。
- **`references/consistency.md`** —— 三层锚点（角色/场景/风格）、character sheet
  workflow、写实身份表模式、不变量声明模板、多主体计数约束、漂移诊断表。
- **`references/negative.md`** —— 排除约束具象化第一原则、9 类分层组织、
  生图通用池 / 视频专属池、数量控制、5 条反模式。
- **`references/vocab.md`** —— 10 类中英词汇银行（风格、色彩、光照、镜头构图、
  材质、情绪、角色服装、场景、后期、视频动词）。
- **`references/models.md`** —— 8 个生图模型 + 9 个视频模型的适配表、
  通用适配原则、切换检查清单、跨模型迁移流程。
- **`references/templates.md`** —— T1—T3 生图模板、V1—V4 视频模板（含路径控制）、
  C1 角色工作表模板。
- **`references/checklists.md`** —— 8 组交付前质检清单 + 8 条高频扣分项。
- **`examples/`** —— 经实测的完整用例（生图、视频、角色一致性）。
- **LICENSE** —— MIT。
- **CONTRIBUTING.md** —— 贡献指南：写作约束、提交规范、新增模型流程。
- **.gitignore** —— 排除平台注入元数据与编辑器产物。

### 方法学来源

整合提炼自以下公开仓库，已在本项目内注明借鉴范围：

`LunarXuan/image-prompt-reverse`、`Square-Zero-Labs/video-prompting-skill`、
`zhouwei713/fpv-immersive-video-prompting`、`TanShilongMario/PromptSkill4image`、
`huangserva/skill-prompt-generator`、`YouMind-OpenLab/ai-image-prompts-skill`。
