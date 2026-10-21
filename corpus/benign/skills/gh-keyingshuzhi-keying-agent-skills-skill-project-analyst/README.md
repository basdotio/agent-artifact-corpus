# Project Analyst

> 系统化分析陌生的软件项目或代码仓库。

## 用途

当用户需要理解以下事项时使用本 Skill：

- 项目用途
- 技术栈
- 目录结构
- 程序入口
- 系统架构
- 核心模块
- 依赖关系
- 数据与状态
- 构建运行方式
- 测试部署体系
- 技术风险
- 待确认事项

## 交付内容

| 文件 | 说明 |
|---|---|
| `SKILL.md` | Skill 指令：分析流程（8 Phase）、核心原则、输出格式、安全边界 |
| `extension.json` | Skill 清单：name / version / type: "skill" |
| `references/guide.md` | 扩展参考指南 |
| `ANALYSIS_REPORT.md` | 设计决策与评估基线 |

## 版本

当前版本：`0.1.1`

## 分析流程

```text
Phase 1 — 工作区发现
Phase 2 — 项目与技术识别
Phase 3 — 项目结构分析
Phase 4 — 程序入口分析
Phase 5 — 架构分析
Phase 6 — 依赖、数据与状态分析
Phase 7 — 工程体系分析（构建/运行/测试/部署）
Phase 8 — 结论、风险与未知事项
```

## 核心原则

- **证据优先**：Finding → Evidence → Confidence
- **先读取，再判断**：不根据文件名或惯例下结论
- **先广后深**：全貌 → 高信息密度文件 → 关键模块 → 深入分析
- **明确表达不确定性**：无法确认的放入 Unknowns
- **默认只读**：不主动修改项目或环境

## 输出格式

15 节结构化报告：

1. 项目概览
2. 技术栈
3. 项目结构
4. 程序入口
5. 系统架构
6. 核心模块
7. 依赖关系
8. 数据与状态
9. 构建与运行
10. 测试体系
11. 部署与发布
12. 关键发现（Finding / Evidence / Confidence）
13. 技术风险
14. 待确认事项
15. 建议继续调查

## 使用方式

作为 **柯影智航（KoyingPilot）** 的 Skill 加载，由 Agent 在匹配场景时调用。

典型请求：

> 帮我快速了解一下这个项目。

> 分析一下当前项目的整体架构。

> 接手这个项目前先帮我分析一下。

## 与其他 Skill 的关系

```text
Project Analyst     → 理解项目（这个项目是怎么工作的？）
       ↓
Bug Investigator    → 调查故障（为什么坏了？）
       ↓
Coding Agent        → 实施修复（怎么把它修好？）
```

## License

MIT — 详见 [LICENSE](./LICENSE)。