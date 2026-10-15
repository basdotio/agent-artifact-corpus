# cognitive-anchor v1 深度分析报告 & v2.0 修复对照

> 分析对象：`legacy/`（v1 原始版本，SKILL.md + references/format.md + scripts/solve.py，共约 18KB）
> 方法：全部缺陷经**实证复现**后记录（非静态阅读推断），复现命令见各项说明。
> 结论先行：**v1 的"符号化 + z3 全枚举"架构设计正确且有新意；缺陷集中在表达式沙箱可逃逸（安全级）、中文输入容错、以及若干"文档承诺了但代码没做到"的一致性漏洞。**

---

## 1. 架构总览

| 层 | 文件 | 职责 | 完成度 |
| --- | --- | --- | --- |
| Skill 定义 | SKILL.md | 触发词、六步工作流、硬规则、输出格式 | ★★★★ |
| 翻译层规范 | references/format.md | 变量/约束/档位/多轮书写语法 | ★★★★ |
| 求解层 | scripts/solve.py | z3 全枚举、档位投票、分支表、多轮对齐、selftest | ★★★☆ |

v1 selftest 基线：6 项断言全 PASS（有解 / 推荐正确 / 收敛 / 分支有序）——**基线是健康的**，问题都在基线覆盖不到的地方。

## 2. 缺陷清单（全部经实证复现）

### P0 — 安全（1 项）

1. **`_safe_eval` 沙箱可逃逸（RCE 级）**
   AST 检查只遍历 `ast.Name` 节点，**属性访问 `ast.Attribute` 完全不在检查范围**。
   实证：`--constraints "x.__class__.__name__=='ArithRef'"` 被正常求值并产出解——说明可达任意 Python 对象属性（`__class__.__mro__.__subclasses__()` 等经典逃逸路径均开放）。
   一个定位是"安全求值用户表达式"的函数，实为任意代码执行入口。

### P0 — 功能性（中文场景致命，2 项）

2. **全角标点直接拒服**
   中文用户高频输入 `x：可行性，y：预算充足`（全角冒号/逗号）、`；`（全角分号）、`｜`（全角竖线）。
   实证：全角输入 → "错误：--declare/--constraints/--decisions 解析后为空"。v1 零容错。
3. **截断标志永不触发（结论可信度事故）**
   `truncated: total > max_solutions`，而 `total = len(models)` 已被 `max_solutions` 封顶——该条件恒为 False。
   实证：5 变量 31 个解、`--max-solutions 5` → 输出"满足解总数: 5"且**无任何截断提示**。用户以为看到了全量，实际票数只是前 5 个解的统计。这与 skill"可复现推理链"的核心承诺直接冲突。

### P1 — 一致性 / 健壮性（6 项）

4. **rounds 位置语义被破坏**：`[r for r in split("|") if r.strip()]` 把空段全部丢弃。实证 `"| |z==0"`（文档示例的第 3 轮写法）只产出 2 轮——空段无法表达"该轮不追加"。
5. **`Distinct` 命名空间不对称**：`build_solver` 的 allowed 表有 `Distinct`，`eval_decision` 的没有。实证档位谓词写 `Distinct(x,y)` 直接 `ValueError` 崩溃——同一函数两侧一能一不能，无任何文档说明。
6. **无解输出隐晦**：实证矛盾约束 → "满足解总数: 0 / 推荐档: -"，无解释、无建议，用户无法行动。
7. **错误路径裸 traceback**：档位谓词引用未声明变量时直接抛栈，而非友好错误 + 退出码。
8. **档位不全覆盖静默丢票**：无覆盖检查，部分满足解不命中任何档时无任何提示。
9. **文档自相矛盾（反模式示范）**：solve.py 文档字符串示例用 `不做:True` 兜底档——正是 SKILL.md 硬规则与 format.md 明令禁止的反模式；selftest 里还有一段从未执行的死代码 `args = [...]`，其中同时包含 `不做:True` 和 `Implies(Not(y),w)`（format.md"注意"节点名禁止的 `Not(y)` 写法）。**规范文档禁止的写法，在代码示例里被示范**，agent 学习时会被带偏。

### P2 — 工程化（4 项）

10. 无 README / LICENSE / requirements.txt（开源三件套缺失）
11. 分支表 `f"{k:<4}"` 按字符数填充，中文变量名显示宽度为 2，表格错位
12. JSON 输出无 schema 版本号，下游无法校验结构演进
13. selftest 仅 6 项断言，不覆盖上述任何缺陷场景（所以它们能一直活着）

## 3. v2.0 修复对照表

| # | 缺陷 | v2.0 修复 | 验证 |
| --- | --- | --- | --- |
| 1 | 沙箱逃逸 | AST **节点类型白名单**（Expression/BoolOp/UnaryOp/BinOp/Compare/Call/Name/Constant）；Call 仅限白名单函数且禁关键字参数；常量仅int/bool；对"裸函数名"结果兜底拦截 | selftest 3 项逃逸断言全 PASS |
| 2 | 全角拒服 | `normalize_input()`：`：，；｜（）＝＞＜＋－` → ASCII，其余全角标点 NFKC 归一化 | selftest 3 项归一化断言 + 全角端到端回归 |
| 3 | 截断标志 | 枚举结束后再探一次 solver：仍 sat 即 `truncated=True`，输出明示"仅统计前 N 个解" | selftest 截断断言 + 回归 |
| 4 | rounds 语义 | 段数=轮数、按位置对应；`"|y==0"`=2 轮，`"| |z==0"`=3 轮，空段=该轮不追加 | selftest 2 项位置断言 + 回归 1（恰好 2 轮） |
| 5 | Distinct 不对称 | 约束与档位共用同一命名空间（And/Or/Not/Implies/If/Distinct/Xor） | selftest Distinct 档位断言 |
| 6 | 无解隐晦 | `status: unsat` + 明示"约束矛盾" + 放宽建议 + 多轮对比时指出矛盾轮次 | selftest unsat 断言 + 回归 3 |
| 7 | 裸 traceback | 全部输入错误收敛为 `ExpressionError` → stderr 友好提示 + exit 2 | 回归（错误路径） |
| 8 | 覆盖静默 | 统计未投票解数，超 0 即 [警告] 并说明"投票基数不完整" | 代码路径 + 输出示例 |
| 9 | 反模式示范 | 文档字符串示例改为合规档位；selftest 死代码整体移除 | 人工审查 |
| 10 | 开源三件套 | README.md（中英）/ LICENSE（MIT）/ requirements.txt | 仓库文件 |
| 11 | 表格错位 | `unicodedata.east_asian_width` 按显示宽度填充 | 输出目视 |
| 12 | JSON 无版本 | 顶层 `schema_version: cognitive-anchor.solve/2.0` + `tool_version` + 每轮 `warnings` | 回归 5 |
| 13 | 断言覆盖窄 | selftest 6 → **18 项**：新增沙箱×3、全角×3、rounds×2、截断、unsat、Distinct、未声明变量 | `--selftest` 全 PASS |

## 4. 保留清单（v1 原样继承）

符号化翻译协议（变量/约束/档位三层语法）、z3 全枚举 + 阻塞子句、档位投票与并列裁决规则、分支表降序、多轮累积与漂移检测、六步工作流、硬规则 1–5、输出格式模板、翻译层边界诚实声明、扩展点诚实声明——**架构与协议零改动**，v2.0 是 v1 的超集，v1 的调用方式无需修改。

## 5. 参考说明

v2.0 的安全重写参考了 Python AST 白名单求值的通用实践（受限 eval 模式）；工程化补齐参考了主流开源 Skill 仓库的组织方式。求解器核心（z3 枚举 + 档位投票 + 分支表）为 v1 原创设计，未引入外部规范。
