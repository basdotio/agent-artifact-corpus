# 摘要句级结构（L1 + L2）

## 为什么摘要要按句设计

你的摘要在同时服务两个目标：

- **A**：整段 title+abstract 被向量化成一个文档，参与召回
- **B**：模型生成答案时，从里面**整句 lift 出来**当引用

关键词堆砌能让 A 好看，但它会把句子拆碎，B 直接崩。而 embedding 是语义的
不是词面的，所以 A 本来就不需要堆词。**按 B 写，A 自动拿到。**

KDD 2024 那篇（GEO 原始论文）实测：引述 ~+40%、统计 ~+30%、来源 ~+28%、
流畅易读 +15-30%，**唯一实测有害的是关键词堆砌**。这不是本 skill 的推测，
是论文结论。

## 句子位次表

| 句 | 作用 | 写法要求 |
|---|---|---|
| 1 | 现象层问题描述 | 用社区会用的词，**不是**你的内部叫法。交代失效/瓶颈现象 |
| 2 | 术语映射 | "We study X, which Y literature calls A and Z community calls B" |
| 3 | 方法 + 产物命名 | 定义缩写。禁止出现未定义黑话 |
| 4-5 | 结果 + 数字 | 平均值 + 最优值 + 评测范围 + 代价 |
| 6 | 对比/边界 | "Unlike prior work assuming P, we find Q degrades when R" |
| 7 | 资源 + 读者动作 | 代码/数据/评测框架的获取方式 |

第 1-2 句是**通向外部社区的入口**，也是最常被 lift 的位置，优先打磨。

## 句型优先级

**① 量化句** — KDD 那条 +30% 的结论就在这。
> We show X improves Y by 19.3 points on 6 benchmarks.

`"many users struggle with X"` 这种没有任何锚点，不可引用。
具体到 `58.5%` 而不是 `about 60%`，数字带单位和小数点会增加被摘出的完整性。

**② 对比句** — 因为用户 query 本身经常带对比结构（"X vs Y"、"does X actually
work"），命中率高。
> Unlike prior work that assumes a fixed decomposition depth, GQR infers depth from query structure.

**③ 映射句** — 覆盖多个词汇空间，一句顶一句。
> This problem is studied as feature superposition in interpretability work and as polysemanticity in the safety community.

**④ 边界句** — 诚实写清代价和失效条件，反而提升可信度。
> At 1.4x inference cost, and degrades by only 2.1 points when the depth predictor is wrong.

## 自足性检查

每一句单独拎出来，脱离上下文还能读懂吗？

- 禁止代词指代前句：`This approach` → `GQR`
- 禁止裸缩写：`the model` → `the 7B decomposition model`
- 禁止需要读者回看才知道主语的从句
- 长句拆成短句，但别拆成碎片（"它能做 A。也能做 B。"这种反而不可引用）

## 摘要里不要写什么

- **背景铺陈** — 属于 Introduction
- **相关工作综述** — 属于 Related Work
- **投稿模板套话** — "In this paper, we present..." 这类句子不携带任何信息

这三类挤占的是最贵的引用位。摘要的预算应该全部花在"可被单独摘出的事实"上。

## 篇幅

按目标会议的要求来（NeurIPS 150-250，ACL 150-200，部分期刊 300）。
要放 3-5 个可引用句，通常 150 词够用；赶字数时优先砍第 1 句的修饰成分，
不要砍数字句。

## 写完的自检

1. 逐句问：这句能脱离上下文被 AI 整句引用吗？
2. 逐句问：这句话里的每个数字我能在正文指到出处吗？
3. 前 100 词里有几个可验证的事实点？少于 3 个就该补
4. 有没有句子是在介绍"我们要做什么"而不是"我们发现了什么"？有就改
