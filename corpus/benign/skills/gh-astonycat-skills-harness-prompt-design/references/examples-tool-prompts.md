# 完整范例：工具描述与参数 Schema

四个复杂度递进的完整范例 + 三个专项片段，原文来自生产级编码 agent harness 的线上工具定义。写工具描述/schema 时对照。

## 目录

1. [Write：最简（一句话 + 分工边界）](#1-write最简一句话--分工边界)
2. [Read：能力枚举与失败语义](#2-read能力枚举与失败语义)
3. [Agent：委托与异步纪律](#3-agent委托与异步纪律)
4. [AskUserQuestion：schema 密集型](#4-askuserquestionschema-密集型)
5. [专项：Bash 的执行环境与 description 字段规范](#5-专项bash-的执行环境与-description-字段规范)
6. [专项：Skill 的触发优先级与命名空间](#6-专项skill-的触发优先级与命名空间)
7. [专项：ToolSearch 的延迟加载协议](#7-专项toolsearch-的延迟加载协议)

---

## 1. Write：最简（一句话 + 分工边界）

5 行内完成定位、使用时机、前置失败、与近邻工具的分工。

**description 全文：**

```
Writes a file to the local filesystem, overwriting if it exists. Use when: creating a new file, or fully replacing one you've already Read. Overwriting an existing file you haven't Read will fail. For partial changes, use Edit instead.
```

要点：

- 首句 = 功能定义 + 覆盖语义
- "Use when:" 直接列两种合法场景，不多写
- 前置条件与失败后果同句："you haven't Read will fail"
- 最后一句话把另一半场景让给 Edit——简单工具靠分工句防误用，不靠展开规则

同级别的 Edit 把约束写得更细，句式一样：前置条件带后果（"You must Read the file in this conversation before editing, or the call will fail."）、精确匹配规则（"`old_string` must match the file exactly, including indentation, and be unique — the edit fails otherwise. Strip the Read line prefix (line number + tab) before matching."）、替代出路（"`replace_all: true` replaces every occurrence instead."）。

## 2. Read：能力枚举与失败语义

一句话定位 → 能力 bullet → 失败语义 → 省力规则。

**description 全文：**

```
Reads a file from the local filesystem.
- `file_path` must be an absolute path
- Reads up to 2000 lines by default. When you already know which part of the file you need, only read that part. This can be important for larger files.
- Results are returned using cat -n format, with line numbers starting at 1
- Reads images (PNG, JPG, …) and presents them visually. Reads PDFs via the `pages` parameter (e.g. "1-5", max 20 pages/request; required for PDFs over 10 pages). Reads Jupyter notebooks (.ipynb) as cells with outputs.
- Reading a directory, a missing file, or an empty file returns an error or system reminder rather than content.
- Do NOT re-read a file you just edited to verify — Edit/Write would have errored if the change failed, and the harness tracks file state for you.
```

要点：

- 数字边界全显式：2000 行、20 页/request、超 10 页必须带 pages
- 失败语义写清输入错了会发生什么："returns an error or system reminder rather than content"
- 最后一条是省力规则：从"Edit/Write 失败会报错"这一可信性推导出"不必重读验证"，理由用破折号给出

## 3. Agent：委托与异步纪律

复杂工具的形态：定位段 + `## When to use` 章节；参数语义（优先级、授权、弃用）下沉到 schema 描述。

**description 全文：**

```
Launch a new agent to handle complex, multi-step tasks. Each agent type has specific capabilities and tools available to it. Available agent types are listed in <system-reminder> messages in the conversation. When using the Agent tool, specify a subagent_type to select an agent: `"fork"` forks yourself (the fork inherits your full conversation context and always runs on your model — a `model` override is ignored); any other type — or omitting it — starts a fresh agent (general-purpose by default).

## When to use

Reach for this when the task matches an available agent type, when you have independent work to run in parallel, or when answering would mean reading across several files — delegate it and you keep the conclusion, not the file dumps. For a single-fact lookup where you already know the file, symbol, or value, search directly. Once you've delegated a search, don't also run it yourself — wait for the result.

A fork runs in the background and keeps its tool output out of your context. If you are the fork, execute directly — don't re-delegate. Subagents run in the background; you'll be notified when one completes. Never fabricate or predict a pending agent's results — the notification is never something you write yourself; if the user asks before it arrives, say it's still running.

- The agent's final report is not shown to the user — relay what matters.
- Use SendMessage with the agent's ID or name to continue a previously spawned agent with its context intact; a new Agent call starts fresh (except subagent_type: "fork", which inherits your context).
- Each agent type's model, reasoning effort, and tools come from its definition (`.claude/agents/*.md` frontmatter or SDK `agents`).
- `isolation: "worktree"` gives the agent its own git worktree (auto-cleaned if unchanged).
```

**schema 描述：**

```
description: A short (3-5 word) description of the task
prompt: The task for the agent to perform
subagent_type: The type of specialized agent to use for this task
model: Optional model override for this agent. Takes precedence over the agent definition's model frontmatter and the configured default subagent model. If omitted, uses the agent definition's model, else the default (inherits from the parent unless a default subagent model is configured). Ignored for subagent_type: "fork" — forks always inherit the parent model.
effort: Reasoning effort for this agent. Set this ONLY when the user, or instructions such as CLAUDE.md or a skill, explicitly ask that this agent or delegated work run at a specific effort level, never on your own judgment; otherwise omit it and the agent runs at its usual effort. Ignored for subagent_type: "fork": a fork runs at your own effort.
name: Name for the spawned agent. Makes it addressable via SendMessage({to: name}) while running.
team_name: Deprecated; ignored. The session has a single implicit team.
mode: Deprecated; ignored. Subagents inherit the parent session's permission mode; agent-definition frontmatter may override it.
isolation: Isolation mode. "worktree" creates a temporary git worktree so the agent works on an isolated copy of the repo. "remote" launches the agent in a remote cloud environment (always runs in background; availability is gated).
```

要点：

- 参数语义用对照句式讲清：`"fork"` 分号一侧、其他类型另一侧，特殊行为（model 覆盖被忽略）括号内直接说
- When to use 三连条件 + 一个具体反例（single-fact lookup）收窄空间
- 委托四件事齐全：不重复（don't also run it yourself）、后台语义（you'll be notified）、防臆造（Never fabricate — 附"该说什么"）、转述义务（relay what matters）
- 角色自觉条款："If you are the fork, execute directly — don't re-delegate."——针对子 agent 读到自身描述的场景
- 定义来源指针给到具体路径（`.claude/agents/*.md` frontmatter）
- model 的优先级链一句话讲全：override > agent 定义 frontmatter > 默认（默认=继承父会话），例外用 "Ignored for subagent_type: ..." 收尾——跨参数依赖写成字段描述的固定尾句
- effort 是授权门控下沉到参数级的样本：默认不填，要填必须有用户或指令的明确要求（"never on your own judgment"）——授权门控不只用于整个工具，粒度可以细到单个字段
- 弃用参数不删除、显式声明："Deprecated; ignored." + 一句现状解释（"The session has a single implicit team."）——字段为兼容保留，新行为写进解释里
- name 的描述写的是副作用："Makes it addressable via SendMessage({to: name}) while running."——一个参数同时是另一个工具的寻址键，工具间交互约束进 schema

## 4. AskUserQuestion：schema 密集型

机制复杂、参数多，描述管用法，schema 描述承载 UI 语义与示例。

**description 要点（节选）：**

```
Use this tool only when you are blocked on a decision that is genuinely the user's to make: one you cannot resolve from the request, the code, or sensible defaults.
- Users will always be able to select "Other" to provide custom text input
- Use multiSelect: true to allow multiple answers to be selected for a question
- If you recommend an option, make that the first option in the list and add "(Recommended)" at the end of the label

Plan mode note: To switch into plan mode, use EnterPlanMode (not this tool). Once in plan mode, use this tool to clarify requirements or choose between approaches BEFORE finalizing your plan. Do NOT use this tool to ask "Is my plan ready?", "Should I proceed?", or otherwise reference "the plan" in questions — the user cannot see the plan until you call ExitPlanMode for approval.

Preview feature: Use the optional `preview` field on options when presenting concrete artifacts that users need to visually compare:
- ASCII mockups of UI layouts and components
- Code snippets showing different implementations
- Diagram variations
- Configuration examples
Preview content is rendered as markdown in a monospace box. Multi-line text with newlines is supported. When any option has a preview, the UI switches to a side-by-side layout with a vertical option list on the left and preview on the right. Do not use previews for simple preference questions where labels and descriptions suffice. Note: previews are not supported for single-select questions (not multiSelect).

Reserve this for decisions where the user's answer changes what you do next — not for choices with a conventional default or facts you can verify in the codebase yourself. In those cases pick the obvious option, mention it in your response, and proceed.
```

**schema 描述（节选）：**

```
question: "The complete question to ask the user. Should be clear, specific, and end with a question mark. Example: 'Which library should we use for date formatting?' If multiSelect is true, phrase it accordingly, e.g. 'Which features do you want to enable?'"
header: "Very short label displayed as a chip/tag (max 12 chars). Examples: 'Auth method', 'Library', 'Approach'."
label: "The display text for this option that the user will see and select. Should be concise (1-5 words) and clearly describe the choice."
preview: "Optional preview content rendered when this option is focused. Use for mockups, code snippets, or visual comparisons that help users compare options. See the tool description for the expected content format."
multiSelect: "Set to true to allow the user to select multiple options instead of just one. Use when choices are not mutually exclusive."
```

要点：

- 开头就把工具收缩到最窄场景："blocked on a decision that is genuinely the user's to make"
- 工具间交互约束显式：与 EnterPlanMode 的分工、"the user cannot see the plan until you call ExitPlanMode"——用机制事实解释为什么不能那样问
- 反问句式点名禁止："Do NOT use this tool to ask 'Is my plan ready?', 'Should I proceed?'"——直接引号引用会出问题的问法
- schema 描述带 UI 语义："displayed as a chip/tag (max 12 chars)"——写渲染形态而非只写数据含义
- 示例嵌进字段描述：question 给正例问句、multiSelect 为 true 时给对应改写
- UI 约定写进描述：推荐选项放第一个并加 "(Recommended)"
- 实验性功能用段前缀显式标记（"Preview feature:"），用途限定为"concrete artifacts that users need to visually compare"并四类枚举——不是所有选项都配 preview
- 渲染机制与 UI 布局变化写明（monospace box、side-by-side 布局切换）——模型由此知道用户屏幕上长什么样；新功能的反向收缩同步给："Do not use previews for simple preference questions where labels and descriptions suffice."
- description 与 schema 分工：内容格式细节（四类用途、渲染方式）在 description，字段描述只写触发时机（"rendered when this option is focused"）并指回去（"See the tool description for the expected content format."）——一处定义、一处引用，不重复

## 5. 专项：Bash 的执行环境与 description 字段规范

**description 全文：**

```
Executes a bash command and returns its output.
- Working directory persists between calls, but prefer absolute paths — `cd` in a compound command can trigger a permission prompt. Shell state (env vars, functions) does not persist; the shell is initialized from the user's profile.
- Command output is displayed to you, not reliably to the user.
- `timeout` is in milliseconds: default 120000, max 600000 for a foreground command.
- `run_in_background` runs the command detached: it keeps running across turns and re-invokes you when it exits. No `&` needed.

# Git
- Interactive flags (`-i`, e.g. `git rebase -i`, `git add -i`) are not supported in this environment.
- Use the `gh` CLI for GitHub operations (PRs, issues, API).
- Commit or push only when the user asks. If on the default branch, branch first.
- End git commit messages and PR bodies with the attribution lines given in the conversation's system-reminder, when one is present.
```

`description` 参数（用户在权限框里读的那句话）自带一套写作规范：

```
Clear, concise description of what this command does in active voice. Never use words like "complex" or "risk" in the description - just describe what it does. Say what the command does in plain words: do not echo the command's text, its flags, or file paths - the user reads this description, often without seeing the command. For simple commands (git, npm, standard CLI tools), keep it brief (5-10 words):
- ls → "List files in current directory"
- git status → "Show working tree status"
- npm install → "Install package dependencies"
For commands that are harder to parse at a glance (piped commands, obscure flags, etc.), add enough context to clarify what it does:
- find . -name "*.tmp" -exec rm {} \; → "Find and delete all .tmp files recursively"
- git reset --hard origin/main → "Discard all local changes and match remote main"
- curl -s url | jq '.data[]' → "Fetch JSON from URL and extract data array elements"
```

要点：

- 持久与不持久分开写准：工作目录跨调用持久（"Working directory persists between calls"）、shell 状态不持久（"Shell state (env vars, functions) does not persist"）——半持久环境把边界写清；"prefer absolute paths" 顺手给出理由（`cd` 触发权限弹窗）
- 输出受众声明："Command output is displayed to you, not reliably to the user"——"not reliably" 比不显示更准确，兼防模型假设用户已看到命令输出
- 后台模式一句话三性质："detached: it keeps running across turns and re-invokes you when it exits. No `&` needed."——生命周期（跨 turn）+ 回调机制（exits 时唤起）+ 禁用 shell 习惯（不用 `&`）
- `# Git` 子节按主题聚拢环境专属规则：环境限制（交互 flag 不支持）、替代工具点名（`gh`）、授权纪律（"Commit or push only when the user asks. If on the default branch, branch first."）、动态内容来源指引（attribution lines 在 system-reminder 里，"when one is present" 兜住不存在的情形）
- `description` 参数的受众与阅读场景写明："the user reads this description, often without seeing the command"——由此推导出禁令（不复述命令文本/flag/路径）
- 禁词表给具体词："complex"、"risk"
- 示例按两档给：简单命令 5-10 词；难一眼看懂的（管道、冷门 flag）展开说
- 示例格式统一用 `命令 → "描述"` 箭头式

## 6. 专项：Skill 的触发优先级与命名空间

**description 全文：**

```
Invoke a skill. A skill is a packaged set of instructions the user or project has set up for a particular kind of task (deploy steps, a review checklist, a repo-specific workflow). Available skills appear in a system-reminder listing with one-line descriptions. When the task at hand is one a listed skill covers, call this tool first — the skill's instructions load into the turn for you to follow in place of your default approach; some skills instead run in a subagent and return the finished result. A skill that runs in the background returns only the agent's name — its result arrives later as a task notification, so don't wait on it or invoke it again in the meantime. Users may also ask for one by name (`/<name>`, or "slash command"); that's a request to invoke it.
- `skill`: exact name from the listing, no leading slash. Plugin skills use `plugin:skill`. Directory-scoped skills are listed with a path prefix (`apps/web:deploy`); when both scoped and unscoped variants of a name exist, pick the one whose directory contains the files you're working on (most specific wins; unscoped otherwise).
- `args`: optional arguments to pass through. Only names from the listing (or that the user typed explicitly) are valid. Built-in CLI commands (`/help`, `/clear`, …) aren't skills. If a `<command-name>` block is already present this turn, the skill is loaded — follow it directly rather than calling again.
```

**schema 描述：**

```
skill: The name of a skill from the available-skills list. Do not guess names.
args: Optional arguments for the skill
```

要点：

- 触发优先级一句话三合一："call this tool first — the skill's instructions load into the turn for you to follow in place of your default approach"——优先级、加载机制、与默认方法的替换关系
- 三种执行形态分别写明：载入当轮（load into the turn）/ 子 agent 执行返回成品 / 后台只返回名字——同一工具不同时序，各自的行为指令不同
- 后台形态与 Agent 的异步纪律同族："returns only the agent's name — its result arrives later as a task notification, so don't wait on it or invoke it again in the meantime"——防等待、防重复调用
- 命名空间三层（裸名 / `plugin:skill` / 路径前缀作用域），冲突消解一句收口："most specific wins; unscoped otherwise"
- 合法值收窄到两个来源（listing、用户显式输入），反例排除内置命令："Built-in CLI commands (`/help`, `/clear`, …) aren't skills."
- 幂等守卫：用会话内可见标记判断已加载——"If a `<command-name>` block is already present this turn, the skill is loaded — follow it directly rather than calling again."
- 用户显式点名即授权："Users may also ask for one by name (`/<name>`, or "slash command"); that's a request to invoke it."——把用户口语映射到工具调用

## 7. 专项：ToolSearch 的延迟加载协议

```
Fetches full schema definitions for deferred tools so they can be called.

Deferred tools appear by name in <system-reminder> messages. Until fetched, only the name is known — there is no parameter schema, so the tool cannot be invoked. This tool takes a query, matches it against the deferred tool list, and returns the matched tools' complete JSONSchema definitions inside a <functions> block. Once a tool's schema appears in that result, it is callable exactly like any tool defined at the top of the prompt.

Result format: each matched tool appears as one <function>{"description": "...", "name": "...", "parameters": {...}}</function> line inside the <functions> block — the same encoding as the tool list at the top of this prompt.

Query forms:
- "select:Read,Edit,Grep" — fetch these exact tools by name
- "notebook jupyter" — keyword search, up to max_results best matches
- "+slack send" — require "slack" in the name, rank by remaining terms
```

schema：

```
query: Query to find deferred tools. Use "select:<tool_name>" for direct selection, or keywords to search.
max_results: Maximum number of results to return (default: 5)
```

要点：

- **机制三段论**：名字可见但 schema 不可见（不能调用）→ 取回后与顶部工具完全同权 → 结果格式与顶部工具列表同一编码（"the same encoding as the tool list at the top of this prompt"，模型无需学第二种编码）
- **Query forms 三形态枚举**：精确选择（select:）/ 关键词（max_results 截断）/ `+` 前缀必含——进阶形态（`+`）只在描述教，schema 只留两种主形态
- 首句以目的收尾（"so they can be called"），一句话讲清这个工具为什么存在
- schema 的 required 含 max_results 但同时带 default: 5——序列化产物形态，仿写时按"可选 + 默认值进描述"处理
- **换行结构**（源码核实）：定位句 → 空行 → 机制段一整段（段内零换行）→ 空行 → Result format 段 → 空行 → Query forms 一项一行；源码用 PROMPT_HEAD + hint + PROMPT_TAIL 拼装，hint 随 feature flag 在 system-reminder / available-deferred-tools 两种载体措辞间切换
