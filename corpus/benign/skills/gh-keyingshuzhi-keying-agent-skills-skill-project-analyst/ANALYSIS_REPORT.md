# 项目分析报告

## 1. 项目概览

**Project Analyst（项目分析）** 是一个 DeepSeek Harness 的 **Skill**（技能），用于系统化地分析陌生的软件项目或代码仓库。它本身不是应用、框架或服务端项目，而是一个 **元工具（meta-tool）**：当用户需要理解项目用途、技术栈、架构、入口、核心模块、依赖、构建测试部署、风险等事项时，该 Skill 提供分析流程与输出模板。

当前工作区中的"当前项目"就是该 Skill 自身的实现。

## 2. 技术栈

- **类型**：DSH Skill（Markdown 指令文件 + extension.json 清单）
- **清单格式**：`extension.json`（name / displayName / version / type: "skill" / author / publisher / license）
- **语言**：Markdown（SKILL.md）为指令载体；JavaScript/TypeScript 代码无（Skill 本身不包含运行时代码）
- **运行时**：依附于 DeepSeek Harness（DSH）宿主环境
- **版本管理**：目录快照式（v0.1.0 / v0.1.1），无 Git 仓库、无 lockfile、无构建工具

## 3. 项目结构

```
project-analyst/
├── SKILL.md                 # 当前活跃的 Skill 指令（v0.1.1 等效内容）
├── extension.json           # 当前清单（version 0.1.1）
├── references/
│   └── guide.md             # 扩展参考指南（精简版分析策略）
├── v0.1.0/                  # 上一版本存档
│   ├── SKILL.md
│   ├── extension.json       # version 0.1.0-dev
│   └── references/guide.md
└── v0.1.1/                  # 当前版本存档（与根目录内容等效）
    ├── SKILL.md
    ├── extension.json
    └── references/guide.md
```

## 4. 程序入口

不适用（无执行入口）。Skill 的"入口"是 DSH 宿主在会话中通过 skill catalog 加载 `SKILL.md`，并由 Agent 在匹配场景时调用。

## 5. 系统架构

本项目是纯声明式指令集，架构层级扁平：

- **宿主（DSH）** → 暴露 Skill catalog 与工具集
- **Skill（SKILL.md）** → 定义分析流程（8 Phase）、输出格式、安全边界
- **参考指南（references/guide.md）** → 补充核心目标与策略
- **Agent** → 按 Skill 指令驱动文件读取、搜索与报告生成

无 Frontend/Backend 分离、无进程模型、无数据持久化。

## 6. 核心模块

- **分析流程（Phases 1–8）**：从工作区发现到结论/风险/未知事项
- **核心原则**：证据优先、先读再判、先广后深、明确不确定性、默认只读
- **输出模板**：15 节结构化报告 + 12 条完成标准
- **安全边界**：默认只读，明确列出不应执行的操作

## 7. 依赖关系

- **运行时依赖**：DeepSeek Harness（Agent、文件读取、搜索、Git 查询工具）
- **内部依赖**：无（Skill 自包含）
- **外部服务**：无

## 8. 数据与状态

- 仅读取工作区文件与 Git 信息（如存在仓库）
- 无状态存储、无配置项、无环境变量、无端口

## 9. 构建与运行

- 无构建系统、无安装脚本、无 start/dev/test 命令
- "运行"= DSH 宿主加载 Skill 并由 Agent 执行指令
- 无 CI/CD 配置文件（未见 .github/、.gitlab-ci.yml 等）

## 10. 测试体系

无测试框架、无测试目录、无测试脚本、无覆盖率配置。

## 11. 部署与发布

无部署管线。版本通过目录快照（v0.1.0 / v0.1.1）和 `extension.json` 中的 `version` 字段管理；`extension.json` 声明 `type: "skill"`，表明其交付方式是 DSH Skill 注册。

## 12. 关键发现

### Finding 1：当前 SKILL.md 等效于 v0.1.1，根目录即"最新版"
**Evidence**：根目录 `SKILL.md`、`extension.json`（version 0.1.1）与 `v0.1.1/` 下内容一致；`v0.1.0/` 为旧版（version 0.1.0-dev）。
**Confidence**：High

### Finding 2：v0.1.1 的 references/guide.md 较 v0.1.0 更精简
**Evidence**：diff 显示 v0.1.1 删除了"总体分析策略"章节与部分示例路径，改为更短的"核心目标"表述。
**Confidence**：High

### Finding 3：项目本身无代码、无构建、无测试、无部署
**Evidence**：文件列表中无 .ts/.js 源码、无 package.json、无 Dockerfile、无 CI 配置。
**Confidence**：High

## 13. 技术风险

- **风险 1**：版本管理依赖目录快照而非 Git/变更集，难以追踪差异与回滚。
  **Evidence**：v0.1.0 / v0.1.1 为平行目录，无 Git 仓库（`git status` 报错）。
  **Confidence**：High

- **风险 2**：SKILL.md 与 v0.1.1/SKILL.md 存在冗余同步，未来可能出现根目录与版本目录内容不一致。
  **Evidence**：两者当前等效，但无同步机制或构建校验。
  **Confidence**：Medium

## 14. 待确认事项

1. 项目是否计划接入 DSH 的正式 Plugin/Skill 注册机制（目前仅有 `extension.json` 声明，无注册代码）？
2. v0.1.0 → v0.1.1 的具体变更动机（仅能从 guide.md 推断"加入输出预算考量"）？
3. 是否需要为 Skill 增加测试或验证用例（当前完全缺失）？
4. 根目录与 v0.1.1 的冗余是否 intentional（设计为"当前版 + 历史存档"）？

## 15. 建议继续调查

如果需要进一步理解该项目，下一步最值得调查：

- **DSH 宿主对该 Skill 的实际加载行为**（`cordis_inspect_list` / `cordis_inspect_self` 确认 Skill 在宿主中的注册状态）
- **Skill 的调用上下文**（在当前会话中是否已被激活、是否注册为可用 Skill）
- **版本管理策略**（是否应引入 Git 或变更集替代目录快照）

---

分析范围：`/Volumes/柯影数智/研发部/skill/project-analyst`（不含子目录深层代码，项目本身无源码）。

> 注意：这是"当前项目"（即 project-analyst Skill 自身）的分析，而不是对某个外部代码仓库的分析。如果您的本意是分析另一个项目，请提供该项目的路径或仓库。
