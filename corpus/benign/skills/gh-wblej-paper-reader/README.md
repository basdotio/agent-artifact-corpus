# paper-reader

> 批判性论文精读与文献发现的 Claude Code 技能，共 4 个模式。
> A Claude Code skill for critical paper reading and literature discovery. 4 modes.

[中文](#中文) | [English](#english)

---

## 中文

### 这是什么

`paper-reader` 是一个 [Agent Skill](https://code.claude.com/docs/en/skills)，把「读论文」拆成四个可切换的模式：从批判性读懂一篇、快速筛选一批、发现该读什么，到跨篇合成写综述。

它的设计目标不是「帮你总结论文」，而是**逼出可核查的评价**：每条判断都要锚定原文位置，标注置信度，给出严重度，并在存在合理分歧时留出异议空间。

### 四个模式

| 模式 | 什么时候用 | 做什么 | 需要联网检索 |
|------|-----------|--------|-------------|
| **deep-read**（默认） | 手上有一篇重要论文，要批判性读懂并找启发 | 6 阶段流程：评估边界声明 → 全文通读 → 图表解读 → A 组质量审视 → B 组个人价值评估 → 严重问题汇总 → 导出 Obsidian Markdown | 否 |
| **quick-scan** | 一批论文待筛选，判断哪些值得精读 | 每篇 4 维速判（核心主张 / 方法严谨性 / 新颖性 / 行动引导），对话内表格，不落盘 | 否 |
| **recommend** | 不知道该读什么 | 澄清需求 → 构建检索策略 → 检索 → 筛选 5-8 篇 → 逐篇给出推荐理由 → 可衔接 deep-read | 是 |
| **lit-review** | 已有论文集，要写综述 | 逐篇 deep-read → 聚类 → 离群检测 → 五模块合成（Timeline / Schools / Consensus / Controversies / Gaps）→ 导出 Excel | 是（补漏） |

模式由关键词自动路由。命中多个或语义模糊时，技能会强制询问你选哪个模式，不自行猜测。

**deep-read 的评估维度**

- A 组（论文质量，编辑/审稿人视角）：1 核心主张、2 证据链与逻辑骨架、2.5 实验结果叙事线、3 方法严谨性（6 项系统清单）、4 新颖性（方法/概念/发现/资源四个子项）、5 隐藏假设与替代解释、6 过度宣称检测、7a 科学重要性、7b 领域推进
- B 组（对你的价值）：8 方法可迁移性、9 概念启发、10 资源可用性、11 空白揭示、12 行动引导（可行性 / 预期收益 / 时间成本三轴优先级）

**可信度机制（所有模式通用）**

| 机制 | 做法 |
|------|------|
| 证据锚定 | 每条评价引用原文具体位置（图号、页码、段落），禁止「样本量偏小」这类空泛判断 |
| 置信度标记 | `[HIGH]` 原文可查 / `[MEDIUM]` 有间接证据的推断 / `[LOW]` 领域知识推测，且必须声明「推测」 |
| 适用性分诊 | 每个维度先标记 `[applicable]` / `[not applicable]` / `[not assessable]`，材料不足时如实说不可评估 |
| 严重度与解决方案测试 | `[MAJOR]`（影响核心结论）必须附「需要什么证据才能消除此顾虑」，`[MINOR]` 只标注 |
| 异议空间 | 存在合理分歧时补「另一视角」段落，主动暴露分歧而非单边定论 |
| 图表三源对照 | 逐图比对「视觉所见 / 图注声明 / 正文描述」，不一致处标记 `[DISCREPANCY-MAJOR/MINOR]` |

### 安装

技能就是本仓库根目录，克隆到 Claude Code 的技能目录即可，无需构建。

```bash
# macOS / Linux
git clone https://github.com/WbleJ/Paper-reader.git ~/.claude/skills/paper-reader
```

```powershell
# Windows PowerShell
git clone https://github.com/WbleJ/Paper-reader.git $env:USERPROFILE\.claude\skills\paper-reader
```

只想让某个项目用到，就克隆到该项目的 `.claude/skills/paper-reader`。

安装后无需注册，Claude Code 启动时自动加载。两种触发方式：

- 自然语言：「帮我精读这篇论文」「快速扫一下这几篇」「这个方向有什么值得读的」「帮我梳理这几篇写综述」
- 显式调用：`/paper-reader`

### 配置

技能目录下的 `config.json` 有三个字段，默认全空，首次使用时技能会问你并写回：

| 字段 | 用途 | 为空时的行为 |
|------|------|-------------|
| `export_dir` | deep-read 导出 Markdown 的目标目录 | 首次导出前询问（建议填 Obsidian 库内的文件夹） |
| `user_system` | B 组「方法可迁移性」「行动引导」针对的研究体系（菌株/细胞/领域） | 首次 deep-read 前询问 |
| `default_mode` | 固定默认模式 | `null` 等同于 deep-read |

### 依赖

**Python 包**（仅 lit-review 的 Excel 导出需要）

```bash
pip install openpyxl
```

**配套技能（可选）**

recommend 与 lit-review 需要文献检索能力。技能会按下列优先级调用，缺失时自动降级，全部缺失则用宿主环境的 WebSearch 兜底并说明数据源。这些技能不随本仓库分发：

| 技能 | 用途 |
|------|------|
| `nature-academic-search` | 首选检索（多源协调 + MeSH 策略） |
| `wos-search` | Web of Science 检索（需已登录机构账号） |
| `paper-search-mcp` | 多源检索与 PDF 下载（开源项目 [OPENAGS/paper-search-mcp](https://github.com/openags/paper-search-mcp)） |
| `nature-statistics` | 方法严谨性的统计深度审计（可选增强） |
| `nature-reviewer` | 高价值论文的投稿级审查（可选增强） |

### 文件结构

```
paper-reader/
├── SKILL.md                              # 主文件：模式路由、deep-read 全流程、各模式说明
├── config.json                           # 用户配置（export_dir / user_system / default_mode）
├── README.md
├── LICENSE
└── references/
    ├── evaluation-framework.md           # 评价规范：适用性分诊、严重度、解决方案测试、证据锚定
    ├── figure-interpretation.md          # 图表解读协议：逐图格式、三源对照、差异判定
    ├── results-narrative.md              # 实验结果叙事线：故事弧线、步骤推演表、可复现性清单
    ├── methodological-rigor-checklist.md # 方法严谨性 6 项检查清单
    └── export-spec.md                    # 导出格式规范：frontmatter 字段、章节排序
```

`references/` 按需加载，不预加载进上下文。

### 致谢

本技能的设计借鉴了以下同为 Claude Code 技能的方法论，未复制其文本内容：

- `nature-reviewer` 的问题分类（concern taxonomy）思路，用于方法严谨性清单的严重度划分
- `nature-statistics` 的统计报告清单结构
- `nature-reader` 的模式定位区分（翻译对照 vs 批判理解）
- `paper-analyzer` 的多篇合成维度设计

技能机制基于 Claude Code 的 Agent Skills 体系。

### 已知限制

- **图表解读依赖模型视觉能力**。PHASE 2 需要客户端能直接读取 PDF 页面（Claude Code CLI / 桌面端 / VS Code 扩展均可）；用纯文本模型时该阶段会退化为仅读图注。
- **输出语言以中文为主**，引用的原文保留原语言。英文论文可以正常处理，但生成的笔记默认是中文。
- **检索质量取决于所配数据源**。WoS 需要机构账号，未配置时检索会走到 WebSearch。
- 图表条带强度等视觉判断不做密度定量，输出中会明确声明这一点。

### 许可

[MIT](LICENSE)

---

## English

### What is this

`paper-reader` is an [Agent Skill](https://code.claude.com/docs/en/skills) that splits paper reading into four switchable modes: critical reading of a single paper, fast triage of a batch, literature discovery, and cross-paper synthesis for a review.

The goal is not summarization but **auditable evaluation**: every judgment is anchored to a location in the paper, tagged with a confidence level, given a severity label, and paired with a dissenting view when a reasonable disagreement exists.

### The 4 modes

| Mode | When to use it | What it does | Needs search |
|------|---------------|--------------|--------------|
| **deep-read** (default) | You have one important paper to read critically | 6 phases: assessment boundary → full read → figure interpretation → quality review (Group A) → personal relevance (Group B) → major-issue roundup → export Markdown | No |
| **quick-scan** | You have a batch and want to know which are worth a deep read | 4 dimensions per paper (core claim / rigor / novelty / action), in-chat table, no file output | No |
| **recommend** | You don't know what to read | Clarify → build search strategy → search → pick 5-8 papers → explain why each is recommended → hand off to deep-read | Yes |
| **lit-review** | You have a set of papers and want to write a review | Per-paper deep-read → clustering → outlier detection → 5-module synthesis (Timeline / Schools / Consensus / Controversies / Gaps) → export Excel | Yes (gap filling) |

Mode routing is keyword-driven. If several modes match, the skill asks you to choose rather than guess.

**Credibility mechanisms (all modes)**

- **Evidence anchoring**: every claim cites a location (figure, page, paragraph). Vague verdicts like "small sample size" are rejected.
- **Confidence tags**: `[HIGH]` explicit in the paper, `[MEDIUM]` inferred from indirect evidence, `[LOW]` domain-knowledge speculation that must be labeled as such.
- **Applicability triage**: each dimension is marked `[applicable]`, `[not applicable]`, or `[not assessable]`.
- **Severity plus resolution test**: every `[MAJOR]` finding must state what evidence would remove the concern.
- **Dissent space**: a "another view" paragraph when a reasonable disagreement exists.
- **Three-source figure check**: what the figure visually shows vs. its caption vs. the body text, with `[DISCREPANCY-MAJOR/MINOR]` tags for mismatches.

### Installation

The repository root *is* the skill. Clone it into your skills directory; nothing to build.

```bash
git clone https://github.com/WbleJ/Paper-reader.git ~/.claude/skills/paper-reader
```

```powershell
# Windows PowerShell
git clone https://github.com/WbleJ/Paper-reader.git $env:USERPROFILE\.claude\skills\paper-reader
```

For project-scoped use, clone into `<project>/.claude/skills/paper-reader` instead. Claude Code loads it at startup; trigger it in natural language or with `/paper-reader`.

### Configuration

`config.json` in the skill directory holds three fields, all empty by default; the skill asks on first use and writes the answers back.

| Field | Purpose | When empty |
|-------|---------|-----------|
| `export_dir` | Where deep-read exports Markdown | Ask before the first export |
| `user_system` | The research system (strain / cell / field) used for transferability and action items | Ask before the first deep-read |
| `default_mode` | Pin a default mode | `null` means deep-read |

### Dependencies

`pip install openpyxl` for lit-review's Excel export.

Search-capable companion skills are optional and are **not** bundled. The skill calls them in priority order and degrades gracefully: `nature-academic-search` → `wos-search` → `paper-search-mcp` → the host's built-in WebSearch. Two optional enhancement skills, `nature-statistics` (statistics audit) and `nature-reviewer` (submission-grade review), are skipped silently when absent.

### Notes and limitations

- Figure interpretation relies on the model reading PDF pages visually. With a text-only model that phase degrades to captions only.
- Output language is primarily Chinese, with quoted source text kept in its original language.
- Search quality depends on the configured data sources; Web of Science requires an institutional login.
- Gel band intensities are described visually, not densitometrically, and the output says so.

### Acknowledgements

The design draws on the methodology of several sibling Claude Code skills, with no text copied from them: the concern-taxonomy idea from `nature-reviewer`, the statistics-reporting checklist from `nature-statistics`, the mode-boundary framing from `nature-reader`, and the multi-paper synthesis dimensions from `paper-analyzer`.

### License

[MIT](LICENSE)
