---
name: harness-prompt-design
description: 编写 system prompt、agent 提示词、工具描述和工具参数 schema 的风格规范，提炼自生产级 agent harness 的线上 system prompt 与工具定义。凡是要新写或修改任何交付给 LLM 的文本都必须使用：system prompt、兜底/判定/知识库等指令文案、工具描述、工具参数描述。当用户要求"写/改/优化某个 prompt"、"新增工具"、"写工具描述"，或任务涉及 app/agents/、app/utils/ 下的 prompt 模板文本时，即使没有明说"风格规范"，也应触发此 skill。
disable-model-invocation: true
---

# Harness Prompt 设计规范

从生产级 agent harness 的线上 system prompt 与工具定义中提炼的风格指南。适用三类对象：system prompt、工具描述、工具参数 schema。

## 完整范例（先看这个）

- `references/examples-system-prompt.md` — 一个生产级编码 agent 的完整 system prompt（身份块 + 正文块全文），开头有结构导读
- `references/examples-system-prompt.zh.md` — 上述范例的中文对照版，附机制注释（`file_path:line_number` 跳转、they/them 代词、`[[]]` 记忆互链）；阅读辅助用，风格基准仍是英文原文
- `references/examples-tool-prompts.md` — 四个复杂度递进的完整工具范例 + 三个专项片段，原文及要点批注

写新 prompt 前先扫一遍对应范例，建立对"成品长什么样"的直觉，再用下方原则检查自己的产出。

## 核心原则（三类对象通用）

### 1. 一句话定位，先钉身份

第一句定义"是什么、边界在哪"。system prompt 开头是身份句与角色句；工具描述第一句是动词开头的一句话功能定义——模型在选择工具时只扫首句，首句之外的内容都要等被选中后才被细读。

### 2. 枚举用 bullet，行为准则用紧凑散文

事实、能力清单、环境信息用 bullet；行为准则写成连贯短段，靠分号并列与破折号推进，不拆成碎片 bullet。编号列表只用于真正有序的流程。

### 3. 强词省用，全文一处为标定

IMPORTANT / NEVER / ONLY 只留给安全与授权门控这类真正不可妥协的规则。标定参照：范例 system prompt 全文只有一个 IMPORTANT（安全段）。所有规则都"重要"等于都不重要。

### 4. 负向禁令必配正向替代

"adjust, don't retry verbatim"、"don't also run it yourself — wait for the result"——禁令紧跟该做什么，模型才不会卡住。单纯禁止留下的是空白，不是约束。

### 5. 具体胜过抽象

数字、精确名称、引号原文替代模糊词："max 12 chars"、"1-5 words"、`"select:Read,Edit,Grep"`、超时单位写毫秒。不写"适当的""尽量简洁"。

### 6. 理由融进同一子句

用破折号把"为什么"焊在规则后面，不另起一句："Reference code as `file_path:line_number` — it's clickable."。模型知道原因后能在边界情况自行判断，比死板指令稳。

### 7. 对照收缩选择空间

"When to use"永远配反方向的对照："For a single-fact lookup where you already know the file, symbol, or value, search directly."。指名替代工具，给一句话理由。

### 8. 前置条件与失败行为前置

"or the call will fail"、"returns an error rather than content"——会失败的条件写在调用前，失败语义写清。从结果可信性还能推导省力规则："Do NOT re-read a file you just edited to verify — Edit/Write would have errored if the change failed."

### 9. 点名禁止可预测的臆造行为

模型必然倾向编造的东西（未到达的异步结果、看不到的界面状态）逐条点名："Never fabricate or predict a pending agent's results — the notification is never something you write yourself; if the user asks before it arrives, say it's still running."。禁臆造的同时必须给"此时该说什么"。

### 10. 高成本动作需显式授权门控

高成本/高风险工具开头用 ONLY + 枚举全部合法授权形式 + 明确排除推断授权 + 教模型告知用户跳过方式。与 system prompt 侧的"approval in one context doesn't extend to the next"是同一主题。

## System Prompt

详见 `references/system-prompts.md`。要点：

- **双块结构**：身份一句话独立成块；角色句 + 安全政策 + 全部节放正文块；两块各自带 cache 标记
- **分节顺序**：机制说明→ 会话指引→ 记忆→ 环境→ 上下文管理
- **动态内容隔离**：环境信息、git 状态等每会话变化的内容放尾部独立节或独立注入，保护正文块的前缀缓存
- **Memory 子系统**：格式用 frontmatter 代码块钉死，四类记忆各一段，索引与正文分离

完整范例见 `references/examples-system-prompt.md`。

## 工具描述与参数 Schema

详见 `references/tool-prompts.md`（原则 + 第 9 节参数 schema 描述原文）。要点：

- **首句承担选择摘要**：单一 description 形态下第一句就是选工具的全部依据，用法展开放在首句之后
- **按复杂度伸缩**：简单工具一句话 + 几条规则；复杂工具 `##` 子节分章（When to use / Usage notes / 示例）
- **委托与异步纪律**：委托后不重复做、后台通知不可预测、结果要转述
- **工具间交互约束**：用法受另一工具状态约束时写明去向
- **软硬标定**："This is a guideline, not a hard limit"——数字约束声明是硬边界还是指导线
- **schema 描述写全**：默认值、边界值、跨参数依赖、UI 语义、字段受众、inline 示例

完整范例见 `references/examples-tool-prompts.md`。

## 交付前自查

- [ ] 首句能否独立承担"这是什么、何时用"的判断？
- [ ] 行为准则是否写成了紧凑散文而非碎片 bullet？
- [ ] 强词是否只出现在安全与授权门控上？
- [ ] 每条禁令是否跟了替代方案或理由？
- [ ] 模糊词是否都换成了数字、名称、引号原文？
- [ ] 工具选择场景是否有反方向对照与替代工具点名？
- [ ] 会失败的前置条件是否写在调用前、失败语义是否写清？
- [ ] 模型会臆造的东西是否点名禁止并给了"此时该说什么"？
- [ ] 高成本动作是否枚举了授权形式并排除推断授权？
- [ ] 动态内容是否与静态内容分离？
