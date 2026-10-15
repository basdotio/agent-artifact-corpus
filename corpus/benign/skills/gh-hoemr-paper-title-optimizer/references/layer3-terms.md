# 热度对齐与术语闸门（L3）

## 先看清楚"热"的两种形态

它们是不同东西，混了会翻车：

| 状态 | 含义 | 正确用法 |
|---|---|---|
| `background` | 高频、增长平缓 | **入场券**，不是钩子。不写反而奇怪 |
| `rising` | 有体量 + 同比 ≥2x | **真正的钩子**，能把论文带进新流量池 |
| `peaked` | 量级仍高但已过峰 | 禁止使用 |
| `stale` | 连续下滑 | 禁止 retro-fit |

实跑对照（arXiv 年化发文量）：

- `chain of thought` 2022→2026: 51 → 433 → 978 → 2552 → **2823**，增长 1.6x，
  判定 `background`。已经默认化，不提才奇怪，但提它带你去不了新地方。
- `large language model agents`: 0 → 8 → 51 → 101 → **335**，增长 4.4x，
  判定 `rising`。这才是钩子。

**选热词的正确指标不是"哪个词大"，是"哪个词增长快 × 你和它有没有真实关系"。**

## 资格闸门

四道全过才允许进摘要。任一不过 → 标为"不建议使用"并写清原因，
**不静默丢弃**（作者有权知道我们考虑过什么）。

**① 真实关系**（四选一，一个都不沾就不许挂）

1. 在该术语命名的 benchmark 上做了实验
2. 你的结果反驳/推翻了一个该术语下的热门结论
3. 该术语的方法是你的 baseline
4. 你解决的问题就是它命名的那个问题

② ④ 性价比最高：它们天然产出对比句和映射句，正好是 L1 要的可引用句型。

**② 上升期** — `status == rising`。`background` 只能作背景词使用，
即"用了这个默认方法"而非"我把热点挂上去了"。

**③ 未过气** — 非 `peaked` / `stale`。过气词是坟场，今天挂明年看就是尸体。

**④ 数据已归一化** — 跨年比较必须年化。当年只有部分月份，raw count
必然低于去年，这是趋势分析最常见的误读。`arxiv-trend.mjs` 已内建年化。

## 词池接入

数据以文件形式接入，skill 代码不关心数据从哪来。

**schema** — `references/term-pool.csv`（vol 列按实际数据年份命名，示例为
2022–2026；解析时按列名读，不要按固定位置读）：

```csv
term,aliases,community,vol_2022,vol_2023,vol_2024,vol_2025,vol_2026_annualized,slope,status,evidence_source,collected_at
```

**加载顺序**

1. `references/term-pool.csv` 存在且 `collected_at` 在 90 天内 → 直接读
2. 不存在或过期 → 跑 `scripts/arxiv-trend.mjs` 现场探针取数
3. 过期时必须提示用户，不要静默用旧数据

第 3 条是刚需：这个领域迭代很快，半年前的词表等于闭眼开车。

**顶会录用标题词频池（已建成种子版）**：`references/title-word-pool.csv`
（由 `scripts/title-stats.mjs` 从 papercopilot/paperlists 的五大会录用标题生成，
统计口径见 `references/title-numbers.md`）。它是"录用标题用词分布"参考数据，
给副标题选词用；与 term-pool.csv 的 arXiv 年量是两种口径，不要互相填列。
每年新数据放出后重跑 `title-stats.mjs` 刷新。

## 挂载句式

过了闸门的词，按关系类型选句式：

| 关系 | 句式 |
|---|---|
| ① 跑过其 benchmark | `On <benchmark>, GQR improves ... by N points` |
| ② 反驳其结论 | `Contrary to <claim> in <community> work, we find ...` |
| ③ 其方法为 baseline | `Against <method>, which achieves A, GQR achieves B under C` |
| ④ 同一问题 | 见 `abstract-architecture.md` 的映射句 |

## 反面做法

- ❌ **挂无关热词**。这是最高风险操作：审稿人一眼看出，且精确命中 KDD 论文里
  唯一被证明有害的手法（关键词堆砌）
- ❌ **追过气词**。2022 年的当红词在 2026 年是尸体
- ❌ **不归一化就下结论**。2090 < 2547 看着像衰退，其实只是 9 个月 vs 12 个月
- ❌ **把发布量当搜索量**。arXiv 计数是"发表趋势"，不是"搜索量"。
  对论文场景前者更合适（引用你的是研究者，研究者翻文献库），但要清楚这是代理指标
- ❌ **用社交热度代替学术热度**。顶会录用标题的词频质量远高于社媒话题
