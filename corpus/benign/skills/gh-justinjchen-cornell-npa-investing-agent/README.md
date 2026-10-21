<div align="center">

<img src=".github/social-preview.png" alt="NPA-Investing-Agent 封面：不良资产投资智能体知识库" width="100%">

# 🏦 NPA-Investing-Agent

**不良资产投资智能体知识库 · 实战手册**

*把六本不良资产专著的智慧，压缩成 46 章可调用、可检索、可执行的投资技能*

[![Chapters](https://img.shields.io/badge/章节-46%20章-1f4e79?style=flat-square)](chapters/)
[![Sections](https://img.shields.io/badge/篇章-7%20大篇-c8963c?style=flat-square)](#-内容地图)
[![Usage](https://img.shields.io/badge/用途-智能体技能%20%2B%20人工手册-2e7d32?style=flat-square)](#-快速开始)
[![Website](https://img.shields.io/badge/🌐_在线浏览-GitHub_Pages-1565c0?style=flat-square)](https://justinjchen-cornell.github.io/NPA-Investing-Agent/)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Justinjchen-Cornell/NPA-Investing-Agent?style=flat-square&color=e6b800)](https://github.com/Justinjchen-Cornell/NPA-Investing-Agent/stargazers)

</div>

---

## 📖 这是什么

一个面向**不良资产（NPA / Distressed Assets）投资全流程**的开源知识库——从行业认知、尽职调查、估值定价，到收购交易、投后管理、处置盘活、法律实务与司法案例，按 **46 章主题化重组**，横跨 220 万字原著语料。

**双重身份**：

- 🤖 **智能体技能** — 克隆到 `~/.claude/skills/` 后，Claude Code / Copilot 等 AI 智能体可直接检索调用（按主题、按章节）；
- 📚 **人工手册** — 直接浏览章节文件；[`cheatsheet.md`](cheatsheet.md) 是放在手边的 12 张决策工具表。

> 📄 全部内容为**提炼总结**（不含原书文本），每章均含：核心思想 / 核心框架 / 关键概念 / 思维模型 / 反模式 / 实操示例 / 要点回顾。

## ✨ 亮点

| | |
|---|---|
| 🎯 **拿来即用** | 47 个命名框架、30+ 可复用模式、12 张速查决策表 |
| ⚖️ **中国实务** | AMC 生态、司法解释谱系、18 般处置武艺、25 个真实判例精析 |
| 🌏 **国际视角** | 惠特曼五大真相、NAMA 估值走廊、凯马特破产博弈全解剖 |
| 🔍 **对抗思维** | 逃废债识别、责任穿透五连、互保联保拆解、拒执罪压力阶梯 |
| 📐 **决策工具** | 六层分析法、价格链倒推、估值四因素、四栏过账法 |

## 🗺️ 内容地图

<table>
<tr><td width="50%">

**① 行业认知**（ch01–06）
不良资产本质与四次扩展 · 违约成因 · 市场格局 · 参与主体 · AMC 使命与全牌照 · 大不良与机构救助

**② 收购与尽调**（ch07–13）
尽调八法 · 收购流程与定价 · 资产包实战案例 · 评估与拍卖 · 三方博弈

**③ 惠特曼投资理论**（ch14–22）
市场环境 · 理论基础 · **五大真相** · 自愿交换 · 破产法框架 · 重组流程 · 估值与风险 · GMAC/凯马特案例

**④ 投后管理与处置盘活**（ch23–33）

</td><td width="50%">

24 列资产台账 · 债务重组 · 债转股 · 证券化 · 债权转让 · 以物抵债/公证/仲裁 · 诉讼清收 · 保全工具箱 · **责任穿透** · 清算追责 · 盘活重组

**⑤ 法律实务精要**（ch34–41）
司法解释谱系 · 非金业务 · 债的更新 · 股+债 · 担保措施 · 类担保 · 争议解决 · 法律方法论

**⑥ 案例精析**（ch42–44）
程序篇 10 案 · 实体篇 15 案

**⑦ 政策与监管**（ch45–46）
监管办法要点 · 核心司法解释速览

</td></tr>
</table>

## 🚀 快速开始

**方式一：作为智能体技能（推荐）**

```bash
git clone https://github.com/Justinjchen-Cornell/NPA-Investing-Agent.git ~/.claude/skills/npa-investing
```

重启会话后即可使用：

```
用 npa-investing 分析这个资产包      → 加载核心框架
npa-investing 关于债转股             → 定位并讲解相关章节
npa-investing ch18                   → 读取"五大真相"全章
```

**方式二：在线浏览**

👉 **[打开网页版](https://justinjchen-cornell.github.io/NPA-Investing-Agent/)** —— 七大篇章 46 章全文在线阅读

**方式三：本地手册**

直接浏览 [`chapters/`](chapters/) 目录，或从速查表开始：[`cheatsheet.md`](cheatsheet.md)

## 🧭 场景速查（从哪开始读）

| 你的场景 | 从这里开始 |
|---|---|
| 评估资产包准备报价 | `ch10` → `ch11` → `ch13` → 速查表·报价决策盘 |
| 尽调不知从何下手 | `ch07` → `ch08` → `ch09` |
| 拿到债权先做什么 | `ch23` → `ch29` → 速查表·投前体检 |
| 设计重组方案 | `ch24` → `ch36`（担保存续）→ 速查表·条款清单 |
| 债务人想金蝉脱壳 | `ch30` → `ch31` → `ch43` |
| 企业想债转股 | `ch25` → `ch37` |
| 学习投资理论 | `ch15` → `ch18` → `ch19` → `ch22` |
| 法务审合同/项目 | `ch40` → `ch41` → `ch38`/`ch39` |
| 查某条司法解释 | `ch46` → `ch34` |

## 📁 目录结构

```
npa-investing/
├── SKILL.md            # 智能体技能入口（核心框架 + 46 章索引 + 主题索引）
├── chapters/           # 46 章正文
│   ├── ch01-不良资产的本质与分类.md
│   ├── ...
│   └── ch46-不良资产核心司法解释速览.md
├── glossary.md         # 术语表（100+ 条目）
├── patterns.md         # 模式库（30+ 可复用模式）
├── cheatsheet.md       # 速查决策表（12 张工具卡）
├── docs/               # GitHub Pages 在线网页
└── README.md
```

## 📚 数据来源

本库为学习研究用途的**提炼总结**，基于以下六本著作的研读：

| # | 著作 | 作者 |
|---|---|---|
| 1 | 《一本书读懂不良资产》 | 石佳华 |
| 2 | 《不良资产投资：理论与方法》（Distress Investing 中译版） | 马丁·J.惠特曼 / 费尔南多·迪茨 |
| 3 | 《掘金之旅：金融不良资产处置十八般武艺》 | 蔡春雷 |
| 4 | 《掘金之旅：投资金融不良资产疑难案例精析》 | 蔡春雷 / 邵雷雷 |
| 5 | 《特殊机会投资之道——金融资产管理公司法律实务精要》 | 中国东方资产管理股份有限公司 |
| 6 | 《不良资产经营管理》 | 戚桂林 / 郭玉春 / 曾惠东 |

## 📄 许可证

本项目采用 [CC BY 4.0](LICENSE)（署名 4.0 国际）许可协议：可自由复制、分发与改编（包括商业用途），仅需注明出处。原书版权归各作者与出版社所有，本库仅含提炼总结。

## ⚠️ 免责声明

- 内容为读书提炼与框架整理，**不构成任何投资建议或法律意见**；
- 涉及法律条文的部分以**现行有效法律及当地司法实践**为准（民法典时代部分旧规已更新）；
- 实战应用请结合项目具体情况并咨询专业顾问。

---

<div align="center">

**⭐ 如果这个项目对你有帮助，欢迎 Star 支持**

*读万卷书，行万里路——在不良资产的世界里，认知即杠杆。*

</div>
