---
name: project-analyst
description: 系统化分析陌生的软件项目或代码仓库。当用户需要理解项目用途、技术栈、目录结构、程序入口、系统架构、核心模块、依赖关系、数据与状态、构建运行方式、测试部署体系、技术风险或待确认事项时使用。
---

# Project Analyst｜项目分析

## 目标

基于当前工作区中的真实文件、配置和代码证据，系统地理解并解释一个软件项目。

目标不是简单总结 README 或浏览少量文件，而是建立一个可靠的项目认知模型，使用户能够快速理解：

- 这个项目是做什么的；
- 使用了哪些主要技术；
- 项目如何组织；
- 程序从哪里启动；
- 核心模块如何协作；
- 数据和状态如何流动；
- 项目如何构建、运行、测试和部署；
- 当前能够确认哪些重要事实；
- 存在哪些有证据支持的风险；
- 哪些问题目前仍然无法确认。

本 Skill 主要负责：

理解 → 分析 → 解释 → 报告

默认不负责：

修改 → 修复 → 重构 → 实现

---

## 适用场景

当用户提出以下类型的需求时使用本 Skill：

- 分析这个项目；
- 帮我理解这个代码仓库；
- 看一下这个项目是什么架构；
- 这个项目是怎么运行的；
- 帮我梳理一下项目结构；
- 这个项目用了哪些技术；
- 核心模块有哪些；
- 接手这个项目前先帮我分析一下；
- 帮我做一个项目技术概览；
- 分析项目的构建、测试或部署方式。

如果用户表达的实际目标是“先理解项目，再进行后续开发”，也可以首先使用本 Skill 建立项目认知。

---

## 不适用场景

如果用户的主要目标是以下任务，不应将本 Skill 作为主要执行流程：

- 修复具体 Bug；
- 实现新功能；
- 修改代码；
- 重构模块；
- 部署项目；
- 执行性能优化；
- 执行完整安全审计；
- 删除或迁移数据；
- 修改系统环境。

项目分析可以作为这些工作的前置阶段，但本 Skill 本身应保持“项目理解与分析”的职责边界。

---

# 核心原则

## 1. 证据优先

重要结论必须尽可能由项目中的真实证据支持。

核心模式：

Finding → Evidence → Confidence

即：

结论 → 证据 → 置信度

不要把推测写成事实。

---

## 2. 先读取，再判断

不要仅根据：

- 文件名；
- 目录名；
- 项目名称；
- README 中的一句话；
- 常见项目惯例；

直接判断项目架构。

在形成重要结论之前，应检查相关配置、入口代码、核心模块或其他直接证据。

---

## 3. 先广后深

分析大型项目时遵循：

项目全貌
↓
高信息密度文件
↓
关键模块
↓
必要的深入分析

不要默认读取整个代码仓库。

优先确定哪些部分最值得分析，再进行针对性读取。

---

## 4. 明确表达不确定性

当证据不足时，不要自行补全缺失信息。

无法确认的内容应进入：

Unknowns / 待确认事项

而不是生成一个看似完整但没有证据支持的结论。

---

## 5. 默认只读

项目分析默认属于只读任务。

除非用户明确要求并且确有必要，否则不要修改项目、环境或系统状态。

---

# 分析流程

尽量按照以下阶段进行。

可以根据项目规模和类型调整每个阶段的分析深度，但不要无理由跳过关键阶段。

---

## Phase 1 — 工作区发现

首先确定分析对象和项目边界。

检查：

- 当前工作目录；
- Git 仓库边界；
- 顶层目录；
- Workspace / Monorepo 配置；
- README；
- 主要配置文件；
- 项目文档。

判断当前工作区属于：

- 单体应用；
- 前端应用；
- 后端服务；
- 桌面应用；
- CLI；
- Library / SDK；
- 移动应用；
- Monorepo；
- 多语言项目；
- 多服务系统；
- 其他类型。

不要默认当前目录就是完整项目边界。

---

## Phase 2 — 项目与技术识别

寻找能够直接说明技术体系的文件。

例如：

- package.json
- pnpm-workspace.yaml
- yarn.lock
- package-lock.json
- pyproject.toml
- requirements.txt
- uv.lock
- Cargo.toml
- go.mod
- pom.xml
- build.gradle
- Dockerfile
- docker-compose.*
- tsconfig.json
- 框架配置文件
- CI/CD 配置

尽可能确认：

- 主要编程语言；
- Framework；
- Runtime；
- Package Manager；
- Build System；
- 数据库；
- 基础设施；
- 仓库组织方式。

优先相信配置和源码证据，而不是目录名称。

---

## Phase 3 — 项目结构分析

建立项目目录和模块地图。

重点识别：

- applications；
- packages；
- libraries；
- services；
- shared modules；
- configuration；
- scripts；
- tests；
- documentation；
- generated code；
- vendor / third-party code。

重点分析影响项目实际运行和架构的目录。

对于以下内容通常降低优先级：

- node_modules；
- dist；
- build；
- coverage；
- cache；
- 临时文件；
- 编译产物；
- 大型生成文件。

除非它们与当前分析目标直接相关。

---

## Phase 4 — 程序入口分析

定位真正的执行入口。

根据项目类型寻找：

- 应用启动入口；
- Server Entry；
- Frontend Bootstrap；
- Electron Main；
- Electron Preload；
- Electron Renderer；
- CLI Entry；
- Worker；
- Background Service；
- API Router；
- Scheduled Job；
- Package Scripts。

不要只找到入口文件名称。

在合理范围内继续追踪启动路径，以解释：

程序从哪里启动
↓
初始化哪些组件
↓
加载哪些核心模块
↓
最终进入什么运行状态

---

## Phase 5 — 架构分析

根据实际代码建立系统架构模型。

重点分析：

- 系统主要层次；
- 模块职责；
- Component Boundary；
- Runtime Boundary；
- Process Boundary；
- Frontend / Backend Boundary；
- API；
- IPC / RPC；
- Service；
- Plugin / Extension；
- 数据流；
- 控制流；
- 核心抽象。

不要强行把项目归类为某种经典架构。

应该描述：

“代码实际表现出来的架构。”

必要时可以使用简单文本图表示关系。

例如：

Desktop
↓
Runtime
↓
Service
↓
Data Layer

但图中的关系必须有实际证据支持。

---

## Phase 6 — 依赖、数据与状态分析

不要机械罗列全部依赖。

重点寻找“对架构有意义的依赖”。

例如：

- 核心框架；
- Runtime 依赖；
- 数据库；
- AI Model Provider；
- 外部 API；
- 内部 Package；
- IPC / RPC Library；
- Plugin Framework；
- Storage；
- Authentication；
- State Management。

同时尽可能理解：

数据从哪里进入
↓
经过哪些模块
↓
在哪里处理
↓
在哪里保存
↓
最终输出到哪里

区分：

- 已确认的运行时依赖；
- 开发依赖；
- 可选依赖；
- 外部服务；
- 推测关系。

---

## Phase 7 — 工程体系分析

### 构建

检查：

- 安装方式；
- Build Command；
- Package Script；
- 编译过程；
- Bundling；
- Build Artifact；
- Release Script。

### 运行

检查：

- 启动命令；
- Runtime 要求；
- 环境变量；
- 服务依赖；
- 进程结构；
- 明确配置的端口。

不要因为某个端口是某框架的常见默认值，就将其作为项目事实。

### 测试

检查：

- 测试框架；
- Test Directory；
- Unit Test；
- Integration Test；
- E2E；
- Test Script；
- Coverage Configuration。

没有真实 Coverage 数据时，不要声称项目具有某个测试覆盖率。

### 部署

检查：

- Docker；
- CI/CD；
- Release Workflow；
- Packaging；
- Deployment Script；
- Deployment Documentation。

不要仅根据开发配置推断生产环境部署架构。

---

## Phase 8 — 结论、风险与未知事项

完成主要分析后，整理关键发现。

重要 Finding 使用统一格式：

### Finding

明确描述发现。

### Evidence

列出支持该结论的：

- 文件；
- 配置；
- 代码位置；
- 项目行为；
- 其他直接证据。

### Confidence

只使用：

- High
- Medium
- Low

定义：

**High**

存在多个直接证据，结论基本明确。

**Medium**

存在直接证据，但部分信息缺失。

**Low**

主要依赖间接证据或合理推断。

如果证据不足以支持 Low Confidence，则不要形成 Finding，应放入 Unknowns。

---

# 上下文管理

不要暴力读取整个项目。

推荐采用：

Repository Overview
↓
High-information Files
↓
Important Components
↓
Selected Deep Inspection

优先分析高信息密度文件，例如：

- README；
- Package Manifest；
- Workspace Configuration；
- Build Configuration；
- Entry Point；
- Router；
- Service Registration；
- Runtime Configuration；
- Database Configuration；
- Test Configuration；
- Deployment Configuration。

对于大型项目，应优先建立正确的高层模型，而不是追求读取所有文件。

---

# 工具使用规则

可以使用当前环境提供的：

- 文件读取；
- 文件搜索；
- 代码搜索；
- 符号定位；
- Git 信息查询；
- 安全的 Shell 查询；

辅助项目分析。

工具使用遵循：

必要 → 精确 → 最小化

优先使用针对性的文件读取和搜索，而不是执行大量宽泛命令。

执行 Shell 命令前，应先判断是否能够直接通过读取文件获得相同信息。

---

# 安全边界

Project Analyst 默认执行只读分析。

为了“理解项目”，不要主动执行：

- 修改源码；
- 删除文件；
- 移动文件；
- 安装依赖；
- 卸载依赖；
- git commit；
- git reset；
- 无必要的 branch switch；
- 修改系统配置；
- 修改凭据；
- 修改环境变量；
- 终止无关进程；
- 启停系统服务；
- 破坏性 Shell 命令。

如果深入分析确实需要可能改变项目或环境状态的操作，应先说明：

1. 为什么需要；
2. 会改变什么；
3. 存在什么风险；

然后等待用户明确确认。

拥有工具调用权限不等于拥有执行破坏性操作的权限。

---

# 输出格式

根据项目复杂度生成结构化报告。

推荐使用：

# 项目分析报告

## 1. 项目概览

说明项目是什么、主要用途是什么。

## 2. 技术栈

说明已经确认的语言、框架、Runtime、构建系统和重要基础设施。

## 3. 项目结构

说明关键目录及其职责。

## 4. 程序入口

说明主要程序入口和启动链路。

## 5. 系统架构

说明主要组件、边界、关系和运行模型。

## 6. 核心模块

说明关键模块及其职责。

## 7. 依赖关系

说明对架构有重要影响的内部和外部依赖。

## 8. 数据与状态

说明重要数据、状态、配置和数据流。

## 9. 构建与运行

说明项目如何安装、构建和启动。

## 10. 测试体系

说明已经确认的测试工具、测试类型和执行方式。

## 11. 部署与发布

说明已经确认的打包、发布和部署机制。

## 12. 关键发现

重要结论使用：

Finding / Evidence / Confidence

结构表达。

## 13. 技术风险

只列出有实际证据支持的风险。

不要为了填充报告而制造风险。

## 14. 待确认事项

列出当前项目证据不足以回答的重要问题。

## 15. 建议继续调查

指出如果需要进一步理解项目，下一步最值得分析的区域。

这里主要提供调查方向，不主动扩展为重构或开发计划。

---

# 完成标准

满足以下条件后，可以认为本轮项目分析完成：

1. 已确认项目边界；
2. 已识别主要技术栈；
3. 已理解关键目录；
4. 已定位主要程序入口；
5. 已形成合理的系统架构模型；
6. 已分析关键模块；
7. 已检查重要依赖；
8. 已分析构建与运行方式；
9. 已检查测试和部署体系；
10. 重要结论具有证据支持；
11. 无法确认的信息已经明确标记；
12. 最终报告能够帮助开发者快速建立项目整体认知。

对于大型项目，不要求穷尽所有代码。

优先保证：

正确性 > 完整性 > 分析数量