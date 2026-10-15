# 工具描述与参数 Schema 风格详解

来源：生产级编码 agent harness 的线上工具定义（完整范例见 `examples-tool-prompts.md`）。

## 目录

1. [首句承担选择摘要](#1-首句承担选择摘要)
2. [按复杂度伸缩](#2-按复杂度伸缩)
3. [决策启发式与对照](#3-决策启发式与对照)
4. [委托与异步纪律](#4-委托与异步纪律)
5. [授权门控](#5-授权门控)
6. [工具间交互约束](#6-工具间交互约束)
7. [软硬标定与禁词](#7-软硬标定与禁词)
8. [参数 schema 描述](#8-参数-schema-描述)
9. [参数 schema 范例（input_schema 原文）](#9-参数-schema-范例input_schema-原文)

## 1. 首句承担选择摘要

单一 description 字段形态下没有独立的短摘要——第一句就是它。动词开头、一句话功能定义："Executes a bash command and returns its output."、"Performs exact string replacements in a file."。首句之后才是用法、机制、约束。判断标准：模型只读首句能否正确决定"用不用这个工具"。

## 2. 按复杂度伸缩

- **简单工具**（Write）：一句话定位 + Use when 两三条 + 与近邻工具的分工，5 行内
- **中等工具**（Read/Edit）：定位 → 能力 bullet → 前置约束 → 失败行为
- **复杂工具**（Agent/Workflow/AskUserQuestion）：`## When to use` / `## Usage notes` 分章，正文嵌 canonical 示例

复杂度跟参数数量和误用空间走，不跟功能重要性走。

## 3. 决策启发式与对照

工具选择写成启发式 + 对照，不是能力罗列：

> "Reach for this when the task matches an available agent type, when you have independent work to run in parallel, or when answering would mean reading across several files — delegate it and you keep the conclusion, not the file dumps. For a single-fact lookup where you already know the file, symbol, or value, search directly."

正反各一半：什么时候用（并列条件 + 收益），什么时候不用（具体反例）。替代工具点名并给一句话理由。

## 4. 委托与异步纪律

委托类工具必须写清四件事：

- **不重复**："Once you've delegated a search, don't also run it yourself — wait for the result."
- **后台语义**："Subagents run in the background; you'll be notified when one completes."
- **防臆造**："Never fabricate or predict a pending agent's results — the notification is never something you write yourself; if the user asks before it arrives, say it's still running."
- **转述义务**："The agent's final report is not shown to the user — relay what matters."

异步边界（模型看不到的东西）是臆造高发区，每条都要附"此时该说什么"。

## 5. 授权门控

高成本/高风险工具（大量 spawn 子 agent、花大钱、外发内容）的门控写法：

- 开头 ONLY："ONLY call this tool when the user has explicitly opted into..."
- 枚举全部合法授权形式：关键词、会话开关、用户原话、skill 指令、点名调用
- 给判例排除推断授权："The ask must be in the user's words — a task that would merely benefit from a workflow does not count."
- 关门也要留门："Mention they can ask for one with 'use a workflow' in a future message to skip the ask."

## 6. 工具间交互约束

一个工具的合法用法依赖另一个工具的状态时，写明去向：

> "To switch into plan mode, use EnterPlanMode (not this tool)."（AskUserQuestion）
>
> "Before writing a script, load the `workflow-authoring` skill."（Workflow）

不能假设模型同时读过两个工具的描述——约束写在受影响的那个工具里。

## 7. 软硬标定与禁词

- **数字约束声明软硬**："This is a guideline, not a hard limit — follow it unless the user's prompt calls for a different scale."
- **禁词表给具体词**："Never use words like 'complex' or 'risk'"
- **反例给具体反例句**，不只给原则

## 8. 参数 schema 描述

统一写法：

- **一句话功能定义**："The command to execute"、"The absolute path to the file to read"
- **默认值写进描述**："default 120000, max 600000"
- **边界值显式**："max 12 chars"、"1-5 words"
- **跨参数依赖**："Only provide if the file is too large to read at once"、"Not available in this build; leave unset"
- **UI/渲染语义**："Very short label displayed as a chip/tag (max 12 chars)"——参数描述不只说数据含义，还说它渲染出来长什么样
- **字段受众与消费方式**："Goes to telemetry and shown back to the user. 'watching CI run' beats 'waiting.'"——写清谁看、怎么被读
- **inline 示例分两档**：简单命令给 5-10 词示例；难一眼看懂的命令（管道、冷门 flag）给展开示例
- **枚举值逐个解释**：不只列 enum，每个值一句话说语义
- **单位写明**："timeout is in milliseconds"

## 9. 参数 schema 范例（input_schema 原文）

九个工具的 input_schema 原文（与编码 agent 工具集对应），写 schema 结构与字段描述时对照。

### Write：边界写进描述

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "file_path": { "description": "The absolute path to the file to write (must be absolute)", "type": "string" },
    "content": { "description": "The content to write to the file", "type": "string" }
  },
  "required": ["file_path", "content"],
  "additionalProperties": false
}
```

要点：约束直接写进字段描述（"must be absolute"），不依赖工具正文；content 无长度提示——正文已声明完整覆盖语义，字段不重复；required + additionalProperties: false 钉死封闭参数集。

### Edit：跨参数约束

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "file_path": { "description": "The absolute path to the file to modify", "type": "string" },
    "old_string": { "description": "The text to replace", "type": "string" },
    "new_string": { "description": "The text to replace it with (must be different from old_string)", "type": "string" },
    "replace_all": { "description": "Replace all occurrences of old_string (default false)", "type": "boolean", "default": false }
  },
  "required": ["file_path", "old_string", "new_string"],
  "additionalProperties": false
}
```

要点：参数间的约束放进字段描述（"must be different from old_string"）；默认值写进描述（"default false"）同时带 default 节点；replace_all 的语义靠指代 old_string 讲清，不重复定义。

### Read：条件提供模式

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "file_path": { "description": "The absolute path to the file to read", "type": "string" },
    "offset": { "description": "The line number to start reading from. Only provide if the file is too large to read at once", "type": "integer", "minimum": 0, "maximum": 9007199254740991 },
    "limit": { "description": "The number of lines to read. Only provide if the file is too large to read at once.", "type": "integer", "exclusiveMinimum": 0, "maximum": 9007199254740991 },
    "pages": { "description": "Page range for PDF files (e.g. \"1-5\", \"3\", \"10-20\"). Only applicable to PDF files. Maximum 20 pages per request.", "type": "string" }
  },
  "required": ["file_path"],
  "additionalProperties": false
}
```

要点：

- **条件提供**（"Only provide if…"）——告诉模型默认别填、什么场景才填；适用范围写明（"Only applicable to PDF files"），格式给 inline 示例（"1-5"、"3"、"10-20"）
- offset 允许 0、limit 从 1 起——边界语义用 minimum/exclusiveMinimum 区分，描述里不再重复
- 数值上限 9007199254740991 是 Number.MAX_SAFE_INTEGER 的序列化产物，仿写时照抄即可

### Bash：单位与上限

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "command": { "description": "The command to execute", "type": "string" },
    "timeout": { "description": "Optional timeout in milliseconds (max 600000 for a foreground command)", "type": "number" },
    "description": { "description": "Clear, concise description of what this command does in active voice. Never use words like \"complex\" or \"risk\" in the description - just describe what it does. Say what the command does in plain words: do not echo the command's text, its flags, or file paths - the user reads this description, often without seeing the command.\n\nFor simple commands (git, npm, standard CLI tools), keep it brief (5-10 words):\n- ls → \"List files in current directory\"\n- git status → \"Show working tree status\"\n- npm install → \"Install package dependencies\"\n\nFor commands that are harder to parse at a glance (piped commands, obscure flags, etc.), add enough context to clarify what it does:\n- find . -name \"*.tmp\" -exec rm {} \\; → \"Find and delete all .tmp files recursively\"\n- git reset --hard origin/main → \"Discard all local changes and match remote main\"\n- curl -s url | jq '.data[]' → \"Fetch JSON from URL and extract data array elements\"", "type": "string" },
    "run_in_background": { "description": "Set to true to run this command in the background.", "type": "boolean" },
    "dangerouslyDisableSandbox": { "description": "Set this to true to dangerously override sandbox mode and run commands without sandboxing.", "type": "boolean" }
  },
  "required": ["command"],
  "additionalProperties": false
}
```

要点：单位写明（milliseconds）、上限写明（max 600000）；布尔开关用 "Set to true to…" 句式，危险开关的措辞自带警示（dangerously）；description 字段自带两档示例与禁词表（受众声明→推导禁令→两档示例，全文见 examples-tool-prompts.md 专项 5）。

### Agent：enum / pattern / 弃用参数

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "description": { "description": "A short (3-5 word) description of the task", "type": "string" },
    "prompt": { "description": "The task for the agent to perform", "type": "string" },
    "subagent_type": { "description": "The type of specialized agent to use for this task", "type": "string" },
    "model": { "description": "Optional model override for this agent. Takes precedence over the agent definition's model frontmatter and the configured default subagent model. If omitted, uses the agent definition's model, else the default (inherits from the parent unless a default subagent model is configured). Ignored for subagent_type: \"fork\" — forks always inherit the parent model.", "type": "string", "enum": ["sonnet", "opus", "haiku", "fable"] },
    "effort": { "description": "Reasoning effort for this agent. Set this ONLY when the user, or instructions such as CLAUDE.md or a skill, explicitly ask that this agent or delegated work run at a specific effort level, never on your own judgment; otherwise omit it and the agent runs at its usual effort. Ignored for subagent_type: \"fork\": a fork runs at your own effort.", "type": "string", "enum": ["low", "medium", "high", "xhigh", "max"] },
    "name": { "description": "Name for the spawned agent. Makes it addressable via SendMessage({to: name}) while running.", "type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$" },
    "team_name": { "description": "Deprecated; ignored. The session has a single implicit team.", "type": "string" },
    "mode": { "description": "Deprecated; ignored. Subagents inherit the parent session's permission mode; agent-definition frontmatter may override it.", "type": "string", "enum": ["acceptEdits", "auto", "bypassPermissions", "default", "dontAsk", "plan"] },
    "isolation": { "description": "Isolation mode. \"worktree\" creates a temporary git worktree so the agent works on an isolated copy of the repo. \"remote\" launches the agent in a remote cloud environment (always runs in background; availability is gated).", "type": "string", "enum": ["worktree", "remote"] }
  },
  "required": ["description", "prompt"],
  "additionalProperties": false
}
```

要点：

- enum 与描述互相支撑：enum 钉死合法值，描述讲优先级链（override > agent 定义 > 默认继承）、授权纪律（effort：默认不填，要填需用户或指令明确要求）、例外（"Ignored for subagent_type: fork"）
- 弃用参数不删除："Deprecated; ignored." + 一句现状解释，字段为兼容保留
- name 的 pattern 直接可见（^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$），描述写的是副作用（SendMessage 寻址键）
- description（3-5 word）这类量词约束与 required 只保留最小集——prompt 之外的都可选

### Skill：防臆造

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "skill": { "description": "The name of a skill from the available-skills list. Do not guess names.", "type": "string" },
    "args": { "description": "Optional arguments to pass through", "type": "string" }
  },
  "required": ["skill"],
  "additionalProperties": false
}
```

要点：取值来源 + 防臆造禁令压进一行（"from the available-skills list. Do not guess names."）；命名空间规则（plugin:skill、路径前缀、no leading slash）在工具描述的参数 bullet 里教，schema 只留一句话。

### ToolSearch：查询形态示例

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "query": { "description": "Query to find deferred tools. Use \"select:<tool_name>\" for direct selection, or keywords to search.", "type": "string" },
    "max_results": { "description": "Maximum number of results to return (default: 5)", "type": "number", "default": 5 }
  },
  "required": ["query", "max_results"],
  "additionalProperties": false
}
```

要点：自由格式字段（query）给出确切的形态语法；默认值带括号（default: 5）；`+` 前缀必含等进阶形态由工具描述的 Query forms 承担，schema 只留两种主形态；required 含 max_results 但同时带 default: 5——序列化产物形态，仿写时按"可选 + 默认值进描述"处理。

### ListAgents：占位参数显式禁用

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "channel": { "description": "Not available in this build; leave unset.", "type": "string", "maxLength": 256 },
    "q": { "description": "Not available in this build; leave unset.", "type": "string", "maxLength": 256 }
  },
  "additionalProperties": false
}
```

要点：schema 为兼容保留字段、行为上关闭（"Not available in this build; leave unset."）——与 Agent 的 "Deprecated; ignored." 同族，一个面向未上线，一个面向已弃用；无 required——整个工具零必填参数。

### AskUserQuestion：嵌套 schema 与回填结构

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "questions": {
      "description": "Questions to ask the user (1-4 questions)",
      "type": "array",
      "minItems": 1,
      "maxItems": 4,
      "items": {
        "type": "object",
        "properties": {
          "question": { "description": "The complete question to ask the user. Should be clear, specific, and end with a question mark. Example: \"Which library should we use for date formatting?\" If multiSelect is true, phrase it accordingly, e.g. \"Which features do you want to enable?\"", "type": "string" },
          "header": { "description": "Very short label displayed as a chip/tag (max 12 chars). Examples: \"Auth method\", \"Library\", \"Approach\".", "type": "string" },
          "options": {
            "description": "The available choices for this question. Must have 2-4 options. Each option should be a distinct, mutually exclusive choice (unless multiSelect is enabled). There should be no 'Other' option, that will be provided automatically.",
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "items": {
              "type": "object",
              "properties": {
                "label": { "description": "The display text for this option that the user will see and select. Should be concise (1-5 words) and clearly describe the choice.", "type": "string" },
                "description": { "description": "Explanation of what this option means or what will happen if chosen. Useful for providing context on trade-offs or implications.", "type": "string" },
                "preview": { "description": "Optional preview content rendered when this option is focused. Use for mockups, code snippets, or visual comparisons that help users compare options. See the tool description for the expected content format.", "type": "string" }
              },
              "required": ["label", "description"],
              "additionalProperties": false
            }
          },
          "multiSelect": { "description": "Set to true to allow the user to select multiple options instead of just one. Use when choices are not mutually exclusive.", "type": "boolean", "default": false }
        },
        "required": ["question", "header", "options", "multiSelect"],
        "additionalProperties": false
      }
    },
    "answers": {
      "description": "User answers collected by the permission component",
      "type": "object",
      "propertyNames": { "type": "string" },
      "additionalProperties": { "type": "string" }
    },
    "annotations": {
      "description": "Optional per-question annotations from the user (e.g., notes on preview selections). Keyed by question text.",
      "type": "object",
      "propertyNames": { "type": "string" },
      "additionalProperties": {
        "type": "object",
        "properties": {
          "preview": { "description": "The preview content of the selected option, if the question used previews.", "type": "string" },
          "notes": { "description": "Free-text notes the user added to their selection.", "type": "string" }
        },
        "additionalProperties": false
      }
    },
    "metadata": {
      "description": "Optional metadata for tracking and analytics purposes. Not displayed to user.",
      "type": "object",
      "properties": {
        "source": { "description": "Optional identifier for the source of the question (e.g. \"remember\" for /remember command). Used for analytics tracking.", "type": "string" }
      },
      "additionalProperties": false
    }
  },
  "required": ["questions"],
  "additionalProperties": false
}
```

要点：

- **UI/渲染语义**进描述："displayed as a chip/tag"、"rendered when this option is focused"——写它长什么样，不只写数据含义
- **数字边界**双载体：描述里有（(1-4 questions)、(max 12 chars)、(2-4 options)、(1-5 words)），结构上也有（minItems/maxItems）——描述给模型读，约束给校验器用，不因有 schema 约束而省描述
- **示例嵌进字段**：question 给正例问句、multiSelect 为 true 时的对应改写、header 给三个例值
- **跨字段联动**：question 的描述里说明 multiSelect 为 true 时措辞要变；options 的描述排除重复造 Other（"that will be provided automatically"）
- **harness 回填字段**（answers/annotations）留在同一 schema 里并写明来源（"collected by the permission component"）——模型知道这些不是自己填的；propertyNames + additionalProperties 双约束表达"键是问题文本、值是字符串"的 map 语义
- **受众与用途**写明：metadata "Not displayed to user"、source "Used for analytics tracking"，给具体例值（"remember" for /remember command）
- 嵌套每层都带 required + additionalProperties: false——封闭性从顶层贯穿到叶子
