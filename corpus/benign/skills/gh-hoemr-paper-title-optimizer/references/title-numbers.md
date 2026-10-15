# 标题里的数字：实证规则（L1 补充）

数据源：papercopilot/paperlists 收录的五个顶会录用标题（ICLR 2025 / NeurIPS 2024 /
ICML 2024 / ACL 2025 / CVPR 2024，剔除 Reject/Withdraw/Desk Reject 后共
**16,677 篇**）。分析脚本 `scripts/title-stats.mjs` 可在任何年份的 JSON 上复跑；
快照存 `references/title-numbers-stats.json`。

## 先说反直觉的总图景

**定量数字在录用标题里是稀缺动作，不是默认动作。**

| venue | 录用篇数 | 含任何数字* | 含定量数字** | 百分比数量 |
|---|---|---|---|---|
| ICLR 2025 | 3,703 | 6.5% | 2.6% | 0 |
| NeurIPS 2024 | 4,562 | 7.2% | 2.2% | 2 |
| ICML 2024 | 2,610 | 2.9% | 2.1% | 0 |
| ACL 2025 | 3,086 | 4.1% | 1.8% | 1 |
| CVPR 2024 | 2,716 | 18.3% | 2.8% | 0 |

\* 含型号/标识符里的数字（3D、LLaMA-2、Qwen3-4B、ResNet-50）。
\*\* 标题里真的出现量化 claim：倍数 / 百分比 / 增量 / 计数 / 规模 / 拼写数词。

换句话说：**97% 的录用标题不带定量数字**。写数字是差异化手段——用对地方才有
价值，默认去写反而是噪声。

## 什么时候带（三个信号）

1. **数字本身就是论点**（quantization 到 1.99 bits、codebook 扩到 100,000、
   dataset 有 1 trillion tokens）。数字是贡献时不用犹豫。
2. **量级大到值得当卖点**（1000x speed、15x reduction、1 million FPS）。
   注意全是**整数倍/整数大数**。
3. **档次越高的论文越常带**：定量数字率 Oral/Award 明显高于 Poster——
   ICLR 2025 Oral 4.2% vs Poster 2.4%；ICML 2024 Oral 4.2% vs Poster 1.8%；
   ACL 2025 Award 5.3% vs 全体 1.8%。带数字论文的引用中位数也更高
   （NeurIPS 5 vs 2、ICML 9 vs 4、CVPR 13 vs 10）。
   **但这是选择效应**：结果强才敢写数字，不是写数字就能变强——见下「诚实边界」。

## 怎么带（幸存者写法清单）

16,677 篇里真正带了定量数字的写法，全部落在这些形态：

- **整数大数 / 量级词**：`over 500 Real-World Tasks`、`1 million FPS`、
  `10 Million Context Length`、`1 Hour of Data`、`100,000` codebook
- **整数倍**：`15x Reduction`、`1000x Speed`、`10x`
- **拼写数词**（约占 1.3–2.0%，稳定存在）：`One-Shot`、`Two-Layer`、
  `Three Complementary Inductive Biases`、`One Step`
- **整数百分比**（极罕见，五大会合计 3 例，全是标志性量级）：
  `64% Better Than GPT-4o`、`99% Utilization`、`0.1% Data`
- **名句化用**（CVPR 常见梗）：`A Picture is Worth More Than 77 Text Tokens`、
  `A Pedestrian is Worth One Prompt`
- **位置**：多数 venue 的数字更常出现在**冒号后**（副标题是免费数字位）；
  ACL 例外，爱把数字放主标题做梗（`7 Points to Tsinghua but 10 Points to ?`）
- **长度**：带定量数字的标题中位 10–11 词，与不带（9–10 词）几乎一样——
  数字不构成加长理由

**小数在标题里的生存状况**：两位小数 **0 例**；一位小数百分比 1 例
（`0.1% Data Makes Segment Anything Slim`——0.1 本身是标志性量级，不是精度展示）；
一位小数倍数接近 0（`1.99 bits` 是唯一出名的两位小数，且数字即论点）。

**结论：`48.6% less memory` 这种精度展示违背顶会惯例。** 换算成读者脑内的数：
- 48.6% → `half the memory`（从"占用降为 51.4%"的角度这是保守舍入）
- 1.443× → `1.4×`（一位小数倍数勉强可接受）或整数百分比 `40% faster`
- 4.20–9.61 points → `up to 9.6 points` 或 `5+ points`
- 精确值留在摘要第 4–5 句（那里是数字句的主场），标题只留人读的量级

## 诚实边界（引用本节结论时必须带的话）

1. **相关≠因果**：带数字论文引用更高，主要证据指向"强结果才敢写数字"
   的选择效应。本 skill 不承诺"加数字提升引用"。
2. **文献背景**：Jamali & Nikzad 2011（Scientometrics 88:653）发现数字标题的
   下载与引用高于均值（PLOS 综合，非 CS 顶会）；Lewison & Hartley 2005 与
   Hartley 2007 发现冒号对引用无显著影响——所以冒号副标题的价值在检索入口，
   不在引用收益。KDD 2024 GEO 论文的 +30%/+40% 是 AI 搜索可见度指标，
   不是引用率。
3. **学科差异**：CVPR 的"含数字 18.3%"主要由 3D/型号驱动（视觉社区习惯），
   不能跨领域套用。本节数据限五大会 2024–2025 的录用集。
4. 舍入方向纪律：把精确值换算成量级词时，**朝证据的保守侧舍入**
   （48.6% lower memory → "half the memory" 成立的唯一理由是"占用降到 51.4%"
   这个视角；若换算后反而显得更强，就不许换算，宁可不带数字）。

## 与其他层的关系

- L1（`title-patterns.md`）的数字规则以本节为准
- L2（`layer2-coverage.md`）：数字句是摘要的可引用锚点（摘要里要精确，
  标题里要人读），两层不冲突——精确值给摘要，量级给标题
- L3（`layer3-terms.md`）：本节的 `title-word-pool.csv` 是顶会标题高频词种子池，
  给副标题选词参考；它统计的是"录用标题用词分布"，与 term-pool.csv 的
  arXiv 年量是两种数据，不要互相填列

## 复跑

```bash
node scripts/title-stats.mjs --out references/title-numbers-stats.json \
  <paperlists-venue-year>.json...
```

数据更新流程：每年新数据放出来后重跑一次，检查「百分比几乎绝迹」「整数倍/
量级词为主」的结论是否仍然成立；若失效，改的是本文件而不是脚本。
