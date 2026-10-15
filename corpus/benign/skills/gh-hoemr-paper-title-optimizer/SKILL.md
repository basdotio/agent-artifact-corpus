---
name: paper-title-optimizer
description: |
  Rewrite an academic paper's title and abstract so the work is retrievable and
  citable inside AI answer engines (ChatGPT, Perplexity, Google AI Overviews) and
  literature indexes (arXiv, Semantic Scholar). Three layers: single-query
  citation quality, cross-community vocabulary coverage, and rising-term
  alignment behind a qualification gate. Produces a claim-to-evidence map, a
  query coverage matrix, a term table, and — when the paper is already public —
  a pre-change visibility baseline to measure against later.
  改论文标题和摘要 / 让论文被 AI 检索到 / 提升论文在 AI 搜索里的可见度。
  Trigger on: "优化我的论文标题", "摘要改写", "让 ChatGPT 引用我的论文",
  "论文标题太长/太空", "我的方法名要不要改", "abstract rewrite",
  "paper title optimization", "make my paper findable in AI search",
  "GEO for papers", "arXiv abstract SEO", "how do I get my paper cited by AI",
  "check if my method name is taken".
  Do NOT use for: full-manuscript rewriting (this skill only gives location-level
  pointers into the body), citation recommendation or related-work search (use
  deep-research), LaTeX/Word/PPT authoring (use docx/pptx), or papers whose
  results do not exist yet — there is nothing retrievable to optimize before the
  findings are real.
---

# Paper Title Optimizer

把已完成的论文改写成在 AI 检索管道里容易被召回、被整句引用的标题与摘要。
（方法学脉络来自 GEO——Generative Engine Optimization，KDD 2024；懂这个概念的用户说 "GEO for papers" 也能触发。）

## 不可协商的五条

写在最前面，因为它们决定产出能不能用：

1. **不新增事实** — 每个数字/名称/引用必须能在论文全文指到出处。找不到就写
   `[待补: ...]`，禁止估算或外推。见 `references/constraints.md`
2. **不抬高 claim 强度** — 只许把 claim 做得更具体，不许做得更强
3. **不挂无关热词** — 热词走闸门，详见 `references/layer3-terms.md`
4. **正文只给定位建议，不重写** — 位置 + 建议 + 理由，不是改好的段落
5. **没测到的就说没测到** — 绝不输出假的 0

违反任意一条造成的损害（学术诚信事故 / 被 AI 误引 / 工具失去可信度），
都大于优化收益。

## Inputs to collect

开工前先确认这些，缺了就问，别用假设硬上：

| 输入 | 必需 | 缺了会怎样 |
|---|---|---|
| `title` + `abstract` | ✅ | 无的改 |
| `paper_fulltext` | ✅ | 拿不到就无法做证据映射，整个价值主张塌掉 |
| `venue` | ✅ | 决定摘要字数上限和匿名要求 |
| `field` + `subfield` | ✅ | L2 模拟和 L3 选词都靠它 |
| `author_gloss` | ⭕ | 领域黑话 → 外部通用词的映射，拿到 L2 精度显著提升 |
| `query_logs` | ⭕ | 真实检索 query，优先于凭空构造 |
| `arxiv_id` / 已公开? | ⭕ | 决定 Stage 0 基线能不能做 |

论文尚未公开（没投/没挂 arXiv）时 Stage 0 无法进行——明确说明并跳过，
不要拿一篇还不存在的论文编基线。

## Procedure

### Stage 0 — 基线（只对已公开的论文做）

改写之前先量一次，否则改完之后无法判断变好还是变坏。

1. 按 `references/layer2-coverage.md` 的方法写 8-12 条 query，每条同时给
   `arxiv_query`（arXiv 检索式）。两个字段不能合成一个：AI 引擎吃自然语言，
   arXiv 走字面短语匹配——实跑发现把问句直接丢给 arXiv 返回恒为 0
2. 存成 `queries.json`，跑：
   ```bash
   node scripts/visibility-probe.mjs --queries queries.json \
     --title "<完整标题>" --arxiv-id <id> --engines arxiv --out baseline-before.json
   ```
3. 需要 AI 引擎数据时加 `--engines openai,perplexity`，但要先有
   `OPENAI_API_KEY` / `PERPLEXITY_API_KEY`。没有 key 脚本会输出 `skipped`
   并注明"这不是 0，是没测"——照原样转述，不要替它填数

真实结果要 3-9 个月才观测得到，基线是唯一的对照物。

### Stage 1 — 抽取证据（后面所有阶段的地基）

通读全文，产出一张表：每一条可量化的 claim → 正文位置（表号/节号/公式号）。

- 找不到位置 → 标 `unsupported`
- 论文里压根没写的数字 → 记为缺口，后面输出成 `[待补]`
- 记下方法名和缩写，下一步查撞名

这张表决定了你能改写出什么。跳过这一步直接改摘要，后面必然违反约束 1。

**撞名检查**（先做完再进 Stage 2）。方法缩写撞名的后果和措辞不在一个量级：
撞了会让 AI 把两篇论文混淆，把别人的结果安到你头上。用
`arxiv-trend.mjs --json "<缩写>"` 或 arXiv API 查一遍，结果直接给作者看。
处理办法见 `references/title-patterns.md`。作者自创缩写时这一步不能省。

### Stage 2 — 标题与摘要改写（L1）

读 `references/title-patterns.md`、`references/title-numbers.md` 和
`references/abstract-architecture.md`。

1. 生成 2-3 个标题变体，每个写清权衡（换了什么、代价是什么），让作者挑。
   数字用法按 `title-numbers.md` 的实证规则：默认不带（录用标题仅 1.8–2.8% 带
   定量数字），要带就带人读的量级，禁止小数精度展示
2. 摘要按句位次表重写：现象层 → 术语映射 → 方法命名 → 量化结果 → 对比/边界 → 资源
3. 每句过自足性检查：脱离上下文能读懂吗
4. 每条改写回填 Stage 1 的证据位置

### Stage 3 — 跨词汇覆盖（L2）

读 `references/layer2-coverage.md`。

站在门外写 8-12 条 query（不用论文里的任何术语），逐条对摘要找对应句，
产出命中/部分/缺失矩阵。缺失的按映射句 > 现象层改写 > 用途从句 > 副标题
的顺序补。**封顶三个词汇空间**——顶会审稿人在意社区归属，定位三栖本身扣分。

### Stage 4 — 术语闸门（L3）

读 `references/layer3-terms.md`。

1. 读 `references/term-pool.csv`。`collected_at` 超过 90 天 → 提示用户并回落到
   现场探针，别用旧数据做决策
2. 没有池子或需要新词时跑：
   ```bash
   node scripts/arxiv-trend.mjs --json "term one" "term two"
   ```
3. 四道闸门全过才能进摘要：真实关系（①跑其 benchmark ②反驳其结论
   ③其方法为 baseline ④同一问题）／上升期／未过气／数据已年化
4. 未通过的写进"不建议使用"表并说明原因，不要静默丢弃

`background` 状态的词作背景词用即可，别当钩子。

### Stage 5 — 正文定位建议

给 `位置 + 建议 + 理由` 三元组，不给改好的段落。典型产出：

- `§1 第 2 段`：首次出现术语 X 的地方加一句映射句，相邻社区才搜得到你
- `§4.1`：这里的 claim 可以量化成 N points，因为 Table 3 已有数据
- `Fig 2`：图注里的数字没在正文出现，正文无法引用它做锚点

### Stage 6 — 组装与交付

按 Output contract 输出。写文件的话，落到 `geo/<paper-slug>/`。

## Output contract

1. **新标题** — 2-3 个候选，各附权衡说明
2. **新摘要** — 标出词数
3. **可引用句清单** — 逐句标：是否自足 / 是否含数字 / 是否需外部上下文
4. **Claim→证据映射表** — 每条 claim 指向正文位置；`unsupported` 和
   `[待补]` 项标红
5. **L2 覆盖矩阵** — 外部 query / 目标社区 / 对应句 / 状态 / 建议补法
6. **L3 术语表** — 通过的（附挂载句式）+ 未通过的（附原因）
7. **正文定位建议** — 位置 / 建议 / 理由
8. **基线快照** — Stage 0 的结果；未做则写明"论文未公开，无法取基线"
9. **Overclaim 审计** — 逐条列出任何可能超出证据强度的表述

每条改动都附理由。作者要能向合作者和导师解释每一处，否则采纳率归零。

## Failure handling

- **全文缺失**：说明约束 1 无法满足，停下来要全文。降级做表层润色并明确
  标注"未经证据核验"，或干脆不做——不要假装能做
- **找不到数字**：输出 `[待补]`，不要填一个看起来合理的数
- **venue 不明**：问。摘要字数上限和匿名要求猜错会让整版作废
- **词池过期**：提示 + 现场探针，不要静默使用
- **探针报 skipped**：原样说"未测量"，不要用 0 顶替
- **目标必须靠抬高 claim 才能达成**：直接告诉作者"这篇需要补实验"，
  这是正确答案，不是失败
- **脚本报错**：先看 `--help`。别改脚本去迁就一次性的输入

## 对结果的诚实

这个 skill 提高的是"被检索和被引用的概率"，不是保证。真实效果要 3-9 个月
才观测得到，本 skill 不对结果背书。Stage 0 的代理指标（可引用句数、覆盖率、
overclaim 违例数）用来判断这一版改写是否达标，跨领域引用率才是最终指标。

## 未决（阈值与结论的校准状态）

这些是本 skill 自己声明的不确定处，改动前先读：

- **L3 状态阈值是启发式**（`--min-vol 30` / `--hot-vol 1000` / rising 需同比
  ≥2x）：来自少量实跑，未系统校准。边界 case 一律给数据不给结论，让作者判断
- **数字标题的引用优势是相关不是因果**：顶会数据里带定量数字的论文引用中位数
  更高，但主因是选择效应（结果强才敢写）。证据与规则见
  `references/title-numbers.md`，其结论基于 2024–2025 五大会录用集，需按年重跑
- **词池覆盖极薄**：`term-pool.csv` 目前是演示级种子（2 词），实际依赖现场探针。
  `title-word-pool.csv`（顶会标题高频词，由 `scripts/title-stats.mjs` 从
  papercopilot/paperlists 生成）同样只是 2024–2025 快照
- **探针脚本未在无 key 环境验证过 openai/perplexity 后端**：用前先 `--dry-run`
- **年化数值在年初（1–2 月）噪声极大**：当年折算比例过小时不下的结论不采信

## Examples

**输入**：一篇已挂 arXiv 的 CS 论文，提供全文 + 当前标题摘要 + 目标 NeurIPS。

**关键动作**：Stage 0 跑出 arxiv 基线（2/8 query 命中）→ Stage 1 抽出 14 条
可量化 claim，其中 2 条 unsupported → 标题给 3 个变体，推荐冒号副标题版
（理由：副标题能塞 benchmark 名和 synonym）→ 摘要重写为 6 句，前 100 词含
4 个可验证事实点 → L2 覆盖 10 条外部 query，3 条缺失，补 2 个映射句
→ L3 词池 90 天内命中，7 个词过闸（3 background + 4 rising），其中 1 个
`stale` 标为不建议使用 → Stage 5 给出 6 条正文定位建议 → 输出 9 项。

**不做的事**：不改正文段落、不编缺失的数字、不承诺提升多少引用。
