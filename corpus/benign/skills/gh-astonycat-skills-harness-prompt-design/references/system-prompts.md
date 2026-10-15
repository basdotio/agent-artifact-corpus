# System Prompt 风格详解

来源：一个生产级编码 agent harness 的线上 system prompt（全文见 `examples-system-prompt.md`）。

## 目录

1. [块结构与缓存](#1-块结构与缓存)
2. [开篇：身份、角色与安全](#2-开篇身份角色与安全)
3. [行为准则的散文形态](#3-行为准则的散文形态)
4. [语气标定](#4-语气标定)
5. [分节顺序](#5-分节顺序)
6. [机制段：教机制，不堆规则](#6-机制段教机制不堆规则)
7. [Memory 子系统](#7-memory-子系统)
8. [动态段](#8-动态段)

## 1. 块结构与缓存

system prompt 以 text block 数组下发，每个 block 自带 cache 标记：

- **块 1（身份块）**：一句话，几乎永不变，缓存命中率最高
- **块 2（正文块）**：角色句 + 安全政策 + 全部节，随版本迭代变化

每会话变化的内容（环境信息、git 状态、会话内注入）不放正文块——放尾部独立节或独立的 system-reminder 消息，正文块的前缀缓存才能跨会话复用。

## 2. 开篇：身份、角色与安全

两个 block 各一句：

> "You are Claude Code, Anthropic's official CLI for Claude."（身份：是什么）
>
> "You are an interactive agent that helps users with software engineering tasks."（角色：干什么）

安全政策紧随角色句，用"协助面 + 拒绝面"配对：

> "Assist with authorized security testing, defensive security, CTF challenges, and educational contexts. Refuse requests for destructive techniques, DoS attacks, mass targeting, supply chain compromise, or detection evasion for malicious purposes. Dual-use security tools (C2 frameworks, credential testing, exploit development) require clear authorization context: pentesting engagements, CTF competitions, security research, or defensive use cases."

先说帮什么，再说拒什么；拒绝清单具体到攻击类型；双用途工具不一刀切，写明"需要什么授权上下文"。

## 3. 行为准则的散文形态

行为准则不逐条 bullet，写成连贯短段。三种句法反复出现：

- **机制事实 + 行为修正**："Tools run behind a user-selected permission mode; a denied call means the user declined it — adjust, don't retry verbatim."
- **分号并列三元组**（一个原则的三个分支）："if tests fail, say so with the output; if a step was skipped, say that; when something is done and verified, state it plainly without hedging."
- **负向排比 + 正向收束**："Do not re-derive facts already established in the conversation, re-litigate a decision the user has already made, or narrate options you will not pursue. If you are weighing a choice, give a recommendation, not an exhaustive survey."

时间与范围的限定写进规则本身："approval in one context doesn't extend to the next"、"it may be cached or indexed even if later deleted"——限定不写，规则就没有边界。

## 4. 语气标定

全文只有一个 IMPORTANT（安全段），其余规则靠措辞密度而非大写达成强调：短句、动词开头、破折号补理由。以此密度为标定——重要的事不需要喊，喊多了真正重要的那条会被稀释。

## 5. 分节顺序

1. 身份（块 1）
2. 角色 + 安全（块 2 开头）
3. `# Harness`：运行机制——输出可见性、权限模式、系统注入、hooks、并行调用、代码引用格式
4. `# Session-specific guidance`：会话级操作指引
5. `# Memory`：持久记忆子系统
6. `# Environment`：环境事实（动态）
7. `# Context management`：上下文压缩语义

工具使用、沟通风格、风险动作不独立成节——关键条目内联进 Harness 段的散文里，其余交给各工具自己的 description 承载。

## 6. 机制段：教机制，不堆规则

机制段回答"我在什么环境里运行"：输出怎么渲染、权限怎么生效、系统注入长什么样、hooks 是谁说的话。模型理解机制后自己推导行为，比堆行为规则省 token 且更稳。教用户侧功能时给出确切语法：`! <command>`、`/<skill-name>`。

## 7. Memory 子系统

- **格式钉死**：带 frontmatter 的 markdown 代码块，不留自由发挥空间
- **四类各一段**：是什么、何时存、怎么用；feedback/project 类追加 **Why:** / **How to apply:** 行
- **索引与正文分离**：MEMORY.md 只放一行指针，永远不装内容
- **显式排除清单**：代码结构、git 历史、本会话临时信息不存
- **链接语法宽容**："a `[[name]]` that doesn't match an existing memory yet is fine; it marks something worth writing later, not an error"
- **零示例**：格式已经用代码块钉死，示例不再增加信息

## 8. 动态段

环境信息用结构化 bullet + 精确值（model ID 加引号）；git 状态以独立消息注入并声明快照语义——"a snapshot in time, and will not update during the conversation"。动态内容必须自带时效声明，防止模型当实时数据用。
