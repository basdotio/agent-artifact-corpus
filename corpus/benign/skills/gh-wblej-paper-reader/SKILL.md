---
name: paper-reader
version: 1.0.0
license: MIT
description: "Critical paper reading with divergent thinking. 4 modes — deep-read (批判理解+发散思维, 图表解读+实验结果叙事线, figure interpretation via vision), quick-scan (快速筛选, 4 dimensions), recommend (文献发现, WoS/PubMed→衔接deep-read), lit-review (跨篇综述合成+离群检测). Credibility: evidence anchoring + confidence markers [HIGH/MEDIUM/LOW] + dissent space + applicability triage + severity labels [MAJOR/MINOR] + resolution tests. Triggers: 解读, 分析一下, 帮我看看, 理解, 精读, 深度, 发散, 启发, 批判, analyze, read, deep read, understand, critique, interpret, 快速, 速览, 扫一下, 初筛, 过一遍, quick, scan, triage, skim, 推荐, 发现, 有什么值得读, 帮我找, 搜一下, recommend, discover, find papers, search for, 综述, 系统梳理, 跨篇, 对比, 合成, review, synthesize, systematic, compare."
---

# Paper Reader

论文批判性深度解读与文献发现。4个模式，从"读懂一篇论文"到"发现该读什么"到"写综述"。

## Mode Routing

**Step 0: 检测模式关键词 → 唯一命中直接进入，多命中/零命中/语义模糊 → 强制执行 AskUserQuestion 询问用户选择模式，禁止自行推断。**

| 模式 | 触发关键词（中文） | 触发关键词（English） | 核心任务 | 推荐/搜索 |
|------|------------------|---------------------|---------|----------|
| **deep-read**（默认） | 解读、分析一下、帮我看看、理解、精读、深度、发散、启发、批判 | analyze, read, deep read, understand, critique, interpret | 批判理解+发散思维 | ❌ |
| **quick-scan** | 快速、速览、扫一下、初筛、过一遍、哪些值得读 | quick, scan, triage, skim, which are worth | 4维快速判断是否值得精读 | ❌ |
| **recommend** | 推荐、发现、有什么值得读、帮我找、搜一下、不知道读什么 | recommend, discover, find papers, search for, what should I read | 从零发现论文→可衔接deep-read | ✅ |
| **lit-review** | 综述、系统梳理、跨篇、合成、写综述、literature review | review, synthesize, systematic, compare, literature review | 跨篇合成+补漏 | ✅（补全遗漏） |

**冲突示例**：
- "帮我分析并推荐文献" → 命中 deep-read + recommend → 询问用户
- "快速过一遍给个综述" → 命中 quick-scan + lit-review → 询问用户
- "看看这篇" → 模糊，无法确定模式 → 询问用户列出4个模式

## 配置（config.json）

本技能目录下的 `config.json` 存放用户配置，三个字段：

| 字段 | 用途 | 为空（默认）时的行为 |
|------|------|---------------------|
| `export_dir` | deep-read 导出 Markdown 的目标目录 | 首次导出前询问用户要存到哪个目录（建议 Obsidian 库内的文件夹），得到答案后写入 config.json，之后不再重复询问 |
| `user_system` | B 组「方法可迁移性」与「行动引导」评估所针对的研究体系（菌株/细胞/领域） | 首次 deep-read 前询问一次并写入 config.json |
| `default_mode` | 固定默认模式，`null` 等同于 deep-read | 保持 `null` |

若技能目录不可写（例如通过插件缓存安装），则在本次会话内记住用户的选择，并提示用户手动写入 `config.json`。

---

## Credibility Mechanisms（所有模式通用）

### 1. 证据锚定

每条评价必须引用原文具体位置。禁止空泛判断。

```
❌ 禁用: "样本量偏小"
✅ 要求: "[MEDIUM] 关键酶活实验仅n=2（Fig.3B，无error bar），
   发酵罐重复n=3但未报告生物学重复来源（Methods p.7段落2）。"
```

### 2. 置信度标记

每条维度强制标注：

| 标记 | 含义 |
|------|------|
| `[HIGH]` | 原文明确可查的事实 |
| `[MEDIUM]` | 合理推断，有间接证据 |
| `[LOW]` | 领域知识推测，原文未涉及 |

`[LOW]` 置信度的判断必须明确说是"推测"，不用确定语气。

### 3. 异议空间

关键判断后加"另一视角"段落：

```
"另一视角：如果作者的目标是工业应用而非机制研究，n=2的酶活初筛是可以接受的——
关键在于后续放大实验（Fig.4）的n=3数据是否可靠。"
```

不强制每条维度都有"另一视角"——仅在存在合理分歧时出现。

---

## Deep-Read Mode（默认模式）

**入口**：用户已有具体论文，需要深度批判理解和发散思维。

**工作流**（6 个 Phase）：

```
PHASE 0: 评估边界声明
  → 声明输入范围、可/不可评估维度、缺失材料
  → 识别论文类型（发现/机制研究、方法/工具、资源/数据集、综述）

PHASE 1: 全文通读
  → 使用 Read 工具逐页读取 PDF（利用 `pages` 参数分块处理长论文）
  → 提取所有图注、表注及其页码位置
  → 建立内部源映射：页码→章节→关键声明

PHASE 2: 图表解读 [NEW]
  → 对每个图表重新 Read 其所在页面（利用 vision 能力观察图表内容）
  → 逐图产出结构化解读：视觉描述 + 文本对照 + 差异标记
  → 详细协议见 → references/figure-interpretation.md

PHASE 3: A组审视 — 论文质量评价（9个维度）
  → 每个维度先标记适用性 [applicable / not applicable / not assessable]
  → 关键发现标注严重度 [MAJOR / MINOR]
  → MAJOR 项附带解决方案测试
  → 统一评价规范见 → references/evaluation-framework.md

PHASE 4: B组价值评估 — 个人相关性（第8-12维，不变）

PHASE 5: 严重问题汇总 [NEW]
  → 聚合所有 MAJOR 和 MINOR 发现
  → 提供解决方案测试汇总

PHASE 6: 导出 Obsidian Markdown
  → 格式规范见 → references/export-spec.md
```

---

### PHASE 0: 评估边界声明

在 deep-read 输出开头声明（格式详见 `references/evaluation-framework.md`）：
- 输入范围（PDF全文 / 仅摘要 / DOI解析 / …）
- 论文类型
- 可评估 vs 无法评估的维度
- 影响评估置信度的缺失材料

---

### PHASE 2: 图表解读 [NEW]

**核心创新**：不是裁剪搬运图片（那是 nature-reader 做的事），而是利用 Claude 阅读 PDF 时的 vision 能力"看"图并产出文字解读。

**三源对照**：每张图对比 (a) 视觉显示内容 (b) 图注声明 (c) 正文描述。三者不一致 → 产生差异标记 `[DISCREPANCY-MAJOR]` 或 `[DISCREPANCY-MINOR]`。

全部图表解读完成后输出「图表-文本一致性汇总表」。

**详细协议** → `references/figure-interpretation.md`（图表身份、视觉描述、文本对照、差异标记、图表类型特定指南、红线）

---

### PHASE 3: A组 — 论文质量审视（编辑/审稿人视角）

每个维度遵循统一规范（详见 `references/evaluation-framework.md`）：
- 开头标记适用性 `[applicable / not applicable / not assessable]`
- 标注置信度 `[HIGH/MEDIUM/LOW]` + 引用原文位置
- 关键发现标注严重度 `[MAJOR / MINOR]`，MAJOR 附带解决方案测试
- 存在合理分歧时添加"另一视角"

---

**1. 核心主张**
这篇论文用一个句子说做了什么？用你自己的话重述（不是翻译摘要）。

**2. 证据链与逻辑骨架**
从假设→实验→结论的完整链条。每一步的逻辑支撑是什么？**最脆弱的一环在哪？**
用编号列表呈现链条，标注每步的证据强度。

**2.5 实验结果叙事线 [NEW]**
→ 详细模板见 `references/results-narrative.md`

**目标**：让读者能独立复述这篇论文的实验故事——做了什么实验、为什么按这个顺序做、每一步得到了什么。

包含：
- **故事弧线**（≤200字叙事提炼）
- **实验步骤推演表**（步骤 | 科学问题 | 实验设计 | 关键结果[配图] | 作者解读 | 逻辑推进）
- **叙事逻辑图**（Mermaid 流程图或 ASCII 替代）
- **关键转折点**（预期 vs 发现 vs 实验方向改变）
- **可复现性检查清单**（菌株/试剂/质粒/数据/代码/统计的可用性）

**3. 方法严谨性 [UPGRADED]**
→ 系统检查清单见 `references/methodological-rigor-checklist.md`

替代原自由文本评价，逐项系统检查 6 个方面：
1. 对照设计（阳性/阴性/遗传学/条件对照）
2. 重复与样本量（生物学重复 vs 技术重复，n数）
3. 统计方法（检验选择、多重比较校正、效应量）
4. 菌株/试剂信息（基因型、质粒、引物、抗体货号）
5. 数据可获取性（GEO/SRA accession、代码 GitHub）
6. 实验方法细节（关键步骤的完整性和可追溯性）

每项标记适用性 + 严重度 + 解决方案测试。检测到统计方法后主动询问 nature-statistics 深度审计。

**4. 新颖性 [DEEPENED]**
分 4 个子项评价，**每个子项必须提供 ≥1 条证据引用**（原文具体位置或声明证据缺失）：
- **4a. 方法新颖性**：主张 + 证据 + 置信度
- **4b. 概念新颖性**：主张 + 证据 + 置信度
- **4c. 发现新颖性**：主张 + 证据 + 置信度
- **4d. 资源新颖性**：主张 + 证据（菌株ID/质粒名称/数据库URL）+ 置信度

若基于领域知识推断（非论文本身声明），标记 [LOW] 并说明推断依据。

**5. 隐藏假设与替代解释**
- 哪些前提作者默认成立但没有检验？
- 数据是否可能用另一种机制解释？作者排除了吗？

**6. 过度宣称检测**
具体指出**哪句话**超出了数据能支持的范围。引用原文中的结论句 + 解释为什么数据不完全支撑。

**7a. 科学重要性 [NEW]**
- 该工作是否具有突出的科学重要性？（独立于这篇论文做得好不好）
- 重要性是领域内部的（incremental）还是跨领域的（broad）？
- 如果结论成立，谁会关心？为什么？

**7b. 领域推进**（原 dim 7 重聚焦）
- 如果结论成立，领域向前走了多少？
- 增量式改进（砖）→ 明显推进 → 新范式/新基准（地震）
- 与 7a 的区分：7a 问"重不重要"，7b 问"推了多少"

---

### PHASE 4: B组 — 对用户的价值（个人相关性）

**8. 方法可迁移性**
这个方法能用到用户自己的体系吗（体系取自 `config.json` 的 `user_system`，未配置则先询问）？需要改什么？有什么障碍？

**9. 概念启发**
这篇论文是否改变了用户对某个问题的理解？重新框定了什么？

**10. 资源可用性**
有用户可以直接用的东西吗？菌株（是否可用/需要MTA?）、质粒（Addgene?）、数据（GEO/SRA accession?）、代码（GitHub?）、工具。

**11. 空白揭示**
这篇论文**没做什么**？那个空白是不是用户能做的切入点？
区分：技术空白（方法限制做不了）vs 视野空白（作者没想到）

**12. 行动引导（三轴优先级排序）**

每条行动建议用三轴评估：

| 轴 | 问题 | 取值 |
|----|------|------|
| 可行性 | 现有条件能做吗？ | 高/中/低 |
| 预期收益 | 做出来对课题推进多大？ | 高/中/低 |
| 时间成本 | 大概多久看到结果？ | 短(<2周)/中/长(>2月) |

输出格式：
```
📋 行动建议
1. 🔴 高优 — [类型] 具体行动描述。可行性X，预期收益X，时间X。
2. 🟡 中优 — ...
3. 🟢 低优/长期 — ...
```

---

### PHASE 5: 严重问题汇总 [NEW]

全部维度评估完成后，聚合所有 MAJOR 和 MINOR 发现：

```markdown
## 严重问题汇总

### MAJOR 发现（影响核心结论或可复现性）
1. [dim 3] 具体问题描述。解决方案：[具体方案]
2. ...

### MINOR 发现（呈现问题、局部缺陷）
1. [dim 4] 具体问题描述
2. ...
```

---

### Deep-Read 完成后

A+B组全部完成后，检查：
- 科研价值是否 ≥4★ 或行动引导中是否有🔴高优项
- 如有，主动询问一次：*"这篇对你课题价值较高。需要我用 nature-reviewer 做投稿级严格审查吗？它会暴露潜在致命缺陷——任何论文在这种审查下都会显得问题重重。"*
- 用户拒绝则跳过，不重复询问

### Deep-Read 导出

→ 完整格式规范见 `references/export-spec.md`

分析完成后，将完整结果导出为 Markdown 文件到 `config.json` 的 `export_dir`；该字段为空时先询问用户要存到哪里（见「配置」一节），写入后再导出。

**文件名格式**：`{第一作者}_{年份}_{关键词}_分析.md`

**YAML frontmatter**（新增字段均为可选，向后兼容）：
```yaml
---
title: "论文完整标题"
first_author: "Smith"
year: 2024
doi: "10.xxx/xxxx"
analysis_date: 2026-07-23
mode: deep-read
tags: [CRISPRi, metabolic engineering, strain engineering]
assessment_boundary: "全文评估"
figure_count: 6
figure_discrepancies: 1
major_concerns: 2
---
```

---

## Quick-Scan Mode

**入口**：用户有多篇论文待筛选，快速判断哪些值得精读。

**提取4个维度**（每篇简洁，1-3句话每个维度）：
1. 核心主张 — 一句话
2. 方法严谨性 — 最大亮点或最大缺陷
3. 新颖性 — 一句话判断
4. 行动引导 — "值得精读/可跳过/视需求而定" + 一句话理由

**输出**：对话内表格。不导出文件。

| # | 论文 | 核心主张 | 方法严谨性 | 新颖性 | 建议 |
|---|------|---------|-----------|--------|------|
| 1 | Zhang 2024 | ... | ... | ... | 值得精读 — ... |

---

## Recommend Mode

**入口**：用户不知道读什么，需要发现文献。

**流程**：
1. **澄清需求** — 如用户输入模糊（"帮我找点CRISPR的论文"），先问：具体方向？什么菌株体系？最近几年？
2. **构建检索策略** — 提取2-4个核心关键词（英文），构建 WoS/PubMed 查询
3. **执行检索** — 优先调用 `nature-academic-search`（多源协调+MeSH策略+T1-T2-T3回退路由）；不可用时依次降级到 `wos-search` → `paper-search-mcp` → 宿主环境的 WebSearch，并告知用户当前数据源（配套技能清单见 Dependencies 一节）
4. **筛选 5-8 篇** — 按引用量+期刊质量+时间+多样性筛选
5. **呈现推荐列表** — 每篇给出：标题、作者、年份、期刊、引用数、**推荐理由**（为什么这篇值得读？对你有什么用？）
6. **衔接 deep-read** — 询问"需要深入解读其中某篇吗？回复编号即可进入 deep-read"

**和 paper-search-mcp 的区别**：paper-search-mcp 是底层搜索工具（返回搜索结果），recommend 是策划服务——理解需求→筛选→解释为什么推荐→衔接深度阅读。不简单罗列搜索结果。

**和 lit-review 中 WoS 搜索的区别**：recommend 是从零发现（"我该读什么？"），lit-review 是补全遗漏（"我已有的这些论文之外还漏了什么？"）。

---

## Lit-Review Mode

**入口**：用户已有论文集 + 写综述意图。

**流程**：
1. **逐篇 deep-read**（A组7维，无需B组）— 每篇提取核心主张、方法、创新、局限性
2. **聚类** — 按 domain + method_keywords 计算相似度，分为同质簇/同域异法/边缘重叠/异质
3. **离群检测** — 识别远离主流簇的论文，标注离群原因
4. **跨篇合成**（5模块）：
   - **Timeline**：按年份排序的关键突破 → `year | breakthrough | paper_ref | solved | unsolved`
   - **Schools**：按方法流派分组 → `name | core | paper_refs | strength | weakness`
   - **Consensus**：已形成共识的结论 → `point | paper_refs`
   - **Controversies**：仍有争议的问题 → `issue | side_a | refs_a | side_b | refs_b`
   - **Gaps**：研究空白 → `gap | importance | why_unsolved`
5. **补漏搜索**（可选）— 识别合成后仍缺失的角度，优先用 `nature-academic-search` 检索补充文献
6. **导出** — Excel 默认（Sheet1逐篇分析 + Sheet2综述辅助），可选 Markdown/JSON

---

## 与其他 Skill 的边界

仅在对应技能已安装时才有意义；没装可整体跳过本节。

| 场景 | 用 paper-reader | 不用 |
|------|----------------|------|
| 批判理解+发散思维 | paper-reader deep-read | nature-reader |
| 中英对照翻译+图表定位 | nature-reader | paper-reader |
| 结构化12维度分析+写综述 | paper-analyzer | paper-reader lit-review |
| 单纯搜论文+下载PDF | paper-search-mcp | paper-reader recommend |
| 从零发现该读什么论文 | paper-reader recommend | paper-search-mcp |

**paper-reader lit-review vs paper-analyzer**：
- paper-reader lit-review：理解驱动，先深度读每篇再合成，偏"帮我理清这几篇的关系"
- paper-analyzer：分析驱动，12维度打分后聚类导出Excel，偏"我要写综述的素材整理"

---

## Integration with Nature Skills

以下 nature 系列 skill 均为可选配套，不随本仓库分发。检测到对应触发条件且技能已安装时主动建议调用；未安装则跳过相应提示，不阻塞主流程。

本 skill 专注批判理解和发散思维，以下方面 nature 系列 skill 更专业：

| 环节 | 触发条件 | 调用 | 关系说明 |
|------|---------|------|---------|
| deep-read "方法严谨性" | 论文含统计方法（t-test/ANOVA/回归/多重比较等） | `nature-statistics` | 主动询问：*"需要我对这篇论文的统计方法做深度审计吗？nature-statistics 可检测嵌套数据、多重比较校正缺失、样本量不足等问题。"* |
| deep-read 完成后 | 科研价值 ≥4★ 或 行动引导有🔴高优项 | `nature-reviewer` | 主动询问：*"这篇对你课题价值较高。需要我用 nature-reviewer 做投稿级严格审查吗？它会暴露潜在致命缺陷——任何论文在这种审查下都会显得问题重重。"* |
| recommend 模式 | 执行文献检索 | `nature-academic-search` | **默认优先调用**（多源协调+MeSH策略+他引判定）；不可用时降级到 `wos-search` → `paper-search-mcp` |

**原则**：nature skill 作为可选深度工具，不自动调用，不阻塞主流程。用户拒绝后不重复询问。

---

## Reference Files

Deep-read 模式的详细规范分布在 `references/` 目录中。以下文件按需加载：

| 文件 | 打开时机 |
|------|---------|
| [references/evaluation-framework.md](references/evaluation-framework.md) | 开始 A 组审视前 — 适用性分诊、严重度标签、解决方案测试、评估边界声明、置信度标记、证据锚定 |
| [references/figure-interpretation.md](references/figure-interpretation.md) | 执行 PHASE 2 图表解读 — 逐图输出格式、三源对照协议、差异标记规则、图表类型特定指南、红线 |
| [references/results-narrative.md](references/results-narrative.md) | 执行 dim 2.5 实验结果叙事线 — 故事弧线模板、实验步骤推演表、Mermaid 逻辑图、可复现性检查清单 |
| [references/methodological-rigor-checklist.md](references/methodological-rigor-checklist.md) | 执行 dim 3 方法严谨性 — 6项系统检查清单、适用性分诊、严重度判定、解决方案测试 |
| [references/export-spec.md](references/export-spec.md) | 执行 PHASE 6 导出 — frontmatter 字段、章节排序、向后兼容规则 |

---

## Dependencies

**Python 包**

```bash
pip install openpyxl  # lit-review 模式的 Excel 导出
```

**配套 skills（可选，缺失时自动降级）**

本技能的 recommend 与 lit-review 模式需要文献检索能力，会按优先级调用下列技能。这些技能不随本仓库分发，请按需自行准备；全部缺失时用宿主环境自带的 WebSearch 兜底，并在输出中说明数据源。

| 技能 | 用途 | 缺失时的行为 |
|------|------|-------------|
| `nature-academic-search` | recommend 首选检索（多源协调 + MeSH 策略） | 降级到下一项 |
| `wos-search` | Web of Science 检索（需已登录机构账号） | 降级到下一项 |
| `paper-search-mcp` | 多源检索与 PDF 下载（开源项目 OPENAGS/paper-search-mcp） | 降级到 WebSearch |
| `nature-statistics` | 方法严谨性的统计深度审计 | 跳过该提示 |
| `nature-reviewer` | 高价值论文的投稿级审查 | 跳过该提示 |

---

## Notes

- 使用 Read 工具读取 PDF（Claude Code 原生支持），长论文用 `pages` 参数分块读取
- **图表解读**：利用 Claude 阅读 PDF 页面时的 vision 能力直接观察图表内容，不需要外部图片处理工具
- 中英文论文均支持，输出语言以中文为主（引用的原文保留原语言）
- 行动引导中的「用户体系」取自 `config.json` 的 `user_system`（菌株/细胞/领域）。未配置时在首次 deep-read 前询问，不要默认任何具体物种
- `references/` 目录包含各模块的详细规范，按需加载而非全部预加载
