# cognitive-anchor · 认知锚定·符号求解器

> 把「多条件权衡、结论反复摇摆」的决策翻译成 0/1 符号变量与硬约束，用 z3 全枚举**硬算**结论——不让 LLM 猜。
> A z3-backed symbolic decision anchor: translate multi-criteria trade-offs into 0/1 variables and hard constraints, enumerate all satisfying models, and let the solver — not the LLM — decide.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Version](https://img.shields.io/badge/skill-v2.0.0-blue.svg)
![z3](https://img.shields.io/badge/solver-z3--solver-green.svg)

## 它解决什么问题

多条件决策（做不做、买不买、选 A 还是 B）时，LLM 凭"语感"给结论，用户一改条件就摇摆、还无法复核。cognitive-anchor 把判据符号化后交给 z3 求解器：

- **全枚举**：列出所有满足硬约束的组合，一个不漏
- **档位投票**：每个候选决策命中多少解，票数即结论
- **分支博弈表**：所有组合按"成立条件数"排序，看清每个分支
- **多轮对齐**：每轮新增约束重解，推荐档变了就报警"标准未稳"
- **可复现**：同一输入永远同一输出，推理链可回放、可复核

## 快速开始

```bash
pip install z3-solver

python3 scripts/solve.py \
  --declare "x:可行性,y:预算充足,z:时间允许,w:风险可控" \
  --constraints "x+y+z+w>=3; Implies(y==0,w==1); Implies(z==0,And(x==1,w==1))" \
  --decisions "做:x+y+z+w>=4; 观望:x+y+z+w==3; 不做:x+y+z+w<3" \
  --rounds "|y==0"
```

输出示例：

```
===== 第1轮 =====
满足解总数: 6
档位票数: 做=1  观望=3  不做=2
变量=1 频率: x(可行性)=100%  y(预算充足)=50%  z(时间允许)=83%  w(风险可控)=100%
>>> 推荐档: 观望
优先级 x     y     z     w     满足数   档位
#1     1     1     1     1     4        做
...
===== 多轮对齐对比 =====
第一轮推荐: 观望  末轮推荐: 观望
>>> 两轮推荐一致，标准收敛，结论可钉住。
```

更多参数（`--as-json` / `--max-solutions` / `--selftest`）见 [SKILL.md](SKILL.md)。

## 仓库结构

```
cognitive-anchor/
├── SKILL.md                    # Skill 定义（触发词 / 工作流 / 硬规则 / 输出格式）
├── references/
│   └── format.md               # 翻译层语法手册（变量/约束/档位/多轮书写规范）
├── scripts/
│   └── solve.py                # z3 全枚举求解器（v2.0.0，AST 白名单沙箱）
├── docs/
│   └── ANALYSIS.md             # v1 缺陷深度分析 + v2.0 修复对照
├── legacy/                     # v1 原始版本存档
├── requirements.txt
├── LICENSE                     # MIT
└── README.md
```

## 作为 Agent Skill 使用

本仓库本身即一个 [Claude/Agent Skill](https://code.claude.com/docs/zh-CN/skills)：把 `cognitive-anchor/` 目录放入技能的 skills 目录（如 `~/.claude/skills/`），agent 遇到「多条件权衡」「结论摇摆」「别猜，算给我看」「帮我钉住结论」等触发场景即会自动调用。`SKILL.md` 的 frontmatter 含完整触发词列表。

## v2.0.0 亮点（相对 v1）

| 类别 | 变更 |
| --- | --- |
| 安全 | 表达式求值从"仅查变量名"升级为 **AST 节点白名单**，属性访问 / Lambda / 下标等沙箱逃逸路径全部阻断（v1 实测可被 `x.__class__...` 绕过） |
| 中文输入 | **全角标点自动归一化**（`：，；｜（）`），用户口语化粘贴不再报"解析后为空" |
| 正确性 | 修复截断标志永不触发、rounds 空段被吞导致轮次错乱、`Distinct` 在档位侧缺失三处缺陷 |
| 体验 | 无解时给出明确结论与放宽建议；未声明变量/语法错误给友好提示；档位未全覆盖时报告未投票解数 |
| 工程 | JSON 输出带 `schema_version` + `warnings`；selftest 从 6 项扩到 **18 项断言**；补齐 README / LICENSE / requirements |

详细缺陷清单与修复对照见 [docs/ANALYSIS.md](docs/ANALYSIS.md)。

## 安全设计

- 用户提供的表达式**永不直接 exec**：AST 白名单只放行布尔/算术/比较运算 + 8 个白名单 z3 函数（And/Or/Not/Implies/If/Distinct/Xor + True/False）+ 变量 + 整数常量
- 求解过程纯本地 z3，无网络调用、无外部 LLM API
- 结论必须来自求解器输出（SKILL.md 硬规则第 1 条），LLM 只做解释

## License

MIT © 2026 cognitive-anchor contributors. 见 [LICENSE](LICENSE)。

---

<details>
<summary>English summary</summary>

A z3-based symbolic solver skill for multi-criteria decisions. It translates natural-language criteria into 0/1 integer variables and hard constraints, enumerates all satisfying models, votes candidate decisions, and detects recommendation drift across constraint rounds. v2.0 hardens expression evaluation with an AST whitelist (blocking sandbox escapes present in v1), normalizes full-width CJK punctuation, and fixes truncation/rounding/coverage bugs. MIT licensed.
</details>
