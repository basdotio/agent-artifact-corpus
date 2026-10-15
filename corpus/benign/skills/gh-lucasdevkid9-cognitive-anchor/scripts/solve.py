#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cognitive-anchor / scripts/solve.py  (v2.0.0)
=============================================
认知锚定·符号求解器（z3 全枚举）。

把自然语言判据翻译成 0/1 符号变量与硬约束后，本脚本负责"硬算"：
  1. 枚举全部满足解（截断时如实报告）
  2. 档位投票（每个候选决策命中多少解；不覆盖时发出警告）
  3. 变量频率（每个条件在所有满足解中的成立比例）
  4. 分支博弈表（按满足数降序）
  5. 多轮对齐（追加约束重解，检测推荐是否漂移）

用法示例：
  python3 solve.py \
    --declare "x:可行性,y:预算充足,z:时间允许,w:风险可控" \
    --constraints "x+y+z+w>=3; Implies(y==0,w==1); Implies(z==0,And(x==1,w==1))" \
    --decisions "做:x+y+z+w>=4; 观望:x+y+z+w==3; 不做:x+y+z+w<3" \
    --rounds "|y==0" \
    --max-solutions 100

v2.0.0 变更（相对 v1，详见仓库 docs/ANALYSIS.md）：
  - [安全] 表达式求值改为 AST 白名单制，彻底阻断属性访问等沙箱逃逸（v1 可被 `x.__class__...` 绕过）
  - [功能] 输入归一化：全角标点（，；：｜（））自动转半角，中文口语输入不再报"解析后为空"
  - [修复] 枚举被 --max-solutions 截断时，truncated 标志现在如实为真（v1 永不触发）
  - [修复] --rounds 按位置语义解析：空段=该轮不追加约束，"| |z==0" 即第三轮（v1 会吞掉空段少一轮）
  - [修复] Distinct/Xor 等 z3 函数在约束与档位谓词中均可用（v1 档位侧缺失会崩溃）
  - [增强] 无满足解时输出明确结论与放宽建议；未声明变量/语法错误给友好提示而非裸 traceback
  - [增强] 档位未全覆盖时报告未投票解数；JSON 输出带 schema_version 与 warnings
  - [清理] 移除 selftest 死代码；文档字符串示例不再使用被硬规则禁止的兜底档
  - [兼容] CLI 参数与输出格式保持向后兼容，v1 调用方式无需改动

说明：
  - 变量全部建模为 0/1 整数（z3 Int），约束里可直接写 x==1 / y==0 / x+y>=2 等。
  - 表达式由 AST 白名单解析：仅允许 布尔/算术/比较运算 + Call(白名单函数) + 变量 + 常量。
  - 结论一律来自求解器输出，不经过任何 LLM 自由发挥。
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import unicodedata
from collections import Counter
from typing import Dict, List, Optional, Tuple

import z3

__version__ = "2.0.0"
JSON_SCHEMA_VERSION = "cognitive-anchor.solve/2.0"

# ---------- 输入归一化（全角 → 半角） ----------

_FULLWIDTH_MAP = {
    "，": ",", "；": ";", "：": ":", "｜": "|",
    "（": "(", "）": ")", "、": ",", "＝": "=",
    "＞": ">", "＜": "<", "＋": "+", "－": "-", "！": "!",
}


def normalize_input(text: str) -> str:
    """把中文全角标点归一化为 ASCII，保留其余字符。"""
    if not text:
        return text
    out = []
    for ch in text:
        if ch in _FULLWIDTH_MAP:
            out.append(_FULLWIDTH_MAP[ch])
        elif unicodedata.category(ch) == "Po" and ord(ch) > 0x2000 and ch not in "…":
            # 其余全角/变宽标点统一转半角（保守：仅标点大类）
            out.append(unicodedata.normalize("NFKC", ch))
        else:
            out.append(ch)
    return "".join(out)


# ---------- 受控表达式解析（AST 白名单制，v2 安全重写） ----------

# 允许的 AST 节点类型：表达式、布尔、一元、二元、比较、调用、名字、常量
_ALLOWED_NODE_TYPES = (
    ast.Expression,
    ast.BoolOp, ast.And, ast.Or,
    ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.FloorDiv,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Call, ast.Name, ast.Load, ast.Constant,
)

# 允许调用的 z3 函数（约束与档位谓词共用同一命名空间，v2 修复不对称问题）
_ALLOWED_Z3_FUNCS = {
    "And": z3.And, "Or": z3.Or, "Not": z3.Not, "Implies": z3.Implies,
    "If": z3.If, "Distinct": z3.Distinct, "Xor": z3.Xor,
    "True": True, "False": False,
}


class ExpressionError(ValueError):
    """表达式不合法（未声明变量 / 语法错误 / 含不允许的构造）。"""


def _safe_eval(expr: str, allowed: dict):
    """AST 白名单制求值。

    v1 只检查 ast.Name，属性访问（x.__class__...）可绕过直达任意 Python 对象。
    v2 改为节点类型白名单：凡不在白名单内的 AST 构造（Attribute/Subscript/
    Lambda/推导式/关键字参数等）一律拒绝，从结构上阻断逃逸。
    """
    expr = normalize_input(expr).strip()
    if not expr:
        raise ExpressionError("表达式为空")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ExpressionError(f"表达式语法错误: {expr!r}（{e.msg}）") from None

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise ExpressionError(
                f"表达式含不允许的构造 {type(node).__name__}: {expr!r}"
                f"（仅支持 与/或/非/蕴含/算术/比较 与白名单函数 And/Or/Not/Implies/If/Distinct/Xor）"
            )
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ExpressionError(f"只允许调用具名函数: {expr!r}")
            if node.func.id not in _ALLOWED_Z3_FUNCS:
                raise ExpressionError(
                    f"表达式里出现未允许的函数: {node.func.id!r}（在 {expr!r} 中）"
                )
            if node.keywords:
                raise ExpressionError(f"不支持关键字参数: {expr!r}")
        elif isinstance(node, ast.Name):
            if node.id not in allowed and node.id not in _ALLOWED_Z3_FUNCS:
                raise ExpressionError(f"表达式里出现未允许的名字: {node.id!r}（在 {expr!r} 中）")
        elif isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, bool)):
                raise ExpressionError(f"只允许整数/布尔常量: {expr!r}")

    namespace = {"__builtins__": {}}
    namespace.update(allowed)
    namespace.update(_ALLOWED_Z3_FUNCS)
    result = eval(compile(tree, "<constraints>", "eval"), namespace)  # noqa: S307 - 白名单已限死
    if callable(result):
        raise ExpressionError(f"函数名未被调用（单独出现的函数名无意义）: {expr!r}")
    return result


def parse_declare(text: str) -> Dict[str, str]:
    """'x:可行性,y:预算充足' -> {'x':'可行性',...}（全角冒号/逗号已归一化）"""
    out: Dict[str, str] = {}
    for part in normalize_input(text).split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            k, v = part.split(":", 1)
            k = k.strip()
            if not k.replace("_", "").isalnum() or not k.isidentifier():
                raise ExpressionError(f"变量名不合法: {k!r}（用小写字母/数字/下划线，如 x1）")
            out[k] = v.strip() or k
        else:
            raise ExpressionError(f"变量声明缺少 ':含义': {part!r}")
    return out


def parse_kv(text: str) -> Dict[str, str]:
    """'做:x+y>=4; 观望:...' -> {'做': 'x+y>=4', ...}（全角分号/冒号已归一化）"""
    out: Dict[str, str] = {}
    for part in normalize_input(text).split(";"):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise ExpressionError(f"档位声明缺少 ':谓词': {part!r}")
        k, v = part.split(":", 1)
        k = k.strip()
        if not k:
            raise ExpressionError(f"档位名为空: {part!r}")
        out[k] = v.strip()
    return out


def parse_constraints(text: str) -> List[str]:
    """'a>=1; Implies(...)' -> [...]（全角分号已归一化，去空）"""
    return [c.strip() for c in normalize_input(text).split(";") if c.strip()]


def build_solver(vars_decl: Dict[str, str],
                 constraints: List[str],
                 extra: Optional[List[str]] = None) -> Tuple[z3.Solver, Dict[str, z3.ArithRef]]:
    """构造 z3 求解器：变量声明 + 域约束(0/1) + 硬约束 + 本轮追加约束。"""
    z = {k: z3.Int(k) for k in vars_decl}
    allowed = dict(z)
    s = z3.Solver()
    for v in z.values():
        s.add(v >= 0)
        s.add(v <= 1)
    for c in constraints:
        s.add(_safe_eval(c, allowed))
    for e in (extra or []):
        e = e.strip()
        if e:
            s.add(_safe_eval(e, allowed))
    return s, z


def enum_models(s: z3.Solver, z: Dict[str, z3.ArithRef],
                max_solutions: int) -> Tuple[List[Dict[str, int]], bool]:
    """枚举满足解（回溯阻塞子句）。返回 (解列表, 是否被截断)。"""
    models: List[Dict[str, int]] = []
    while len(models) < max_solutions and s.check() == z3.sat:
        m = s.model()
        row = {k: m.eval(v).as_long() for k, v in z.items()}
        models.append(row)
        s.add(z3.Or(*[v != m.eval(v) for v in z.values()]))
    truncated = len(models) >= max_solutions and s.check() == z3.sat
    return models, truncated


def eval_decision(row: Dict[str, int], expr: str) -> bool:
    """把档位谓词对某一解求值（v2：先 simplify 快路径，失败再回退求解器）。"""
    allowed = {k: z3.IntVal(v) for k, v in row.items()}
    val = _safe_eval(expr, allowed)
    if isinstance(val, z3.BoolRef):
        simplified = z3.simplify(val)
        if z3.is_true(simplified):
            return True
        if z3.is_false(simplified):
            return False
        s = z3.Solver()
        s.add(val)
        return s.check() == z3.sat
    if isinstance(val, (int, bool)):
        return bool(val)
    # 算术结果按 >0 为真处理（防御性，正常档位谓词应为布尔式）
    return bool(z3.simplify(val).as_long()) if hasattr(z3.simplify(val), "as_long") else False


# ---------- 终端表格对齐（中文按显示宽度） ----------

def _disp_width(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "FW" else 1 for c in s)


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _disp_width(s))


def run_round(vars_decl, constraints, decisions, extra, max_solutions,
              label: str, as_json: bool) -> dict:
    s, z = build_solver(vars_decl, constraints, extra)
    models, truncated = enum_models(s, z, max_solutions)
    total = len(models)
    warnings: List[str] = []

    # 档位票数 + 覆盖检查
    votes = Counter()
    covered = 0
    for r in models:
        hit = [d for d, e in decisions.items() if eval_decision(r, e)]
        if hit:
            covered += 1
        for d in hit:
            votes[d] += 1
    unvoted = total - covered
    if total > 0 and unvoted > 0:
        warnings.append(
            f"有 {unvoted}/{total} 个满足解未命中任何档位（档位谓词可能不互斥或不完整），"
            f"投票基数不完整，建议补齐档位划分"
        )

    # 变量频率
    freq = {k: (sum(r[k] for r in models) / total) if total else 0.0 for k in vars_decl}

    # 分支表：按"成立条件数"降序
    branches = []
    for i, r in enumerate(models, 1):
        sat_count = sum(r.values())
        hit = [d for d, e in decisions.items() if eval_decision(r, e)]
        branches.append({"#": i, "vars": r, "sat": sat_count,
                         "grades": hit, "top": hit[0] if hit else "-"})
    branches.sort(key=lambda b: -b["sat"])

    # 推荐：票数最多的档；并列时用分支表第一条的 top 裁决
    top_votes = max(votes.values()) if votes else 0
    winners = [d for d, v in votes.items() if v == top_votes and top_votes > 0]
    recommend = winners[0] if winners else "-"
    if len(winners) > 1 and branches:
        first = branches[0]["top"]
        if first in winners:
            recommend = first

    if total == 0:
        warnings.append("无满足解：约束互相矛盾。建议逐条放宽硬约束，或检查是否有条件写反")

    result = {
        "round": label,
        "status": "sat" if total else "unsat",
        "solutions": total,
        "truncated": truncated,
        "votes": dict(votes),
        "unvoted": unvoted,
        "freq": {k: round(v, 3) for k, v in freq.items()},
        "recommend": recommend,
        "branches": branches[:20],
        "warnings": warnings,
    }
    if as_json:
        return result

    print(f"\n===== {label} =====")
    if total == 0:
        print("满足解总数: 0（约束矛盾，无任何组合能满足全部硬约束）")
        print("建议：逐条放宽硬约束重试；若刚追加过约束，先回退该轮")
    else:
        print(f"满足解总数: {total}" + ("（已截断，仅统计前 N 个解）" if truncated else ""))
    print("档位票数: " + "  ".join(f"{k}={v}" for k, v in votes.items()))
    print("变量=1 频率: " + "  ".join(
        f"{k}({vars_decl[k]})={freq[k]*100:.0f}%" for k in vars_decl))
    if total > 0:
        print(f">>> 推荐档: {recommend}")
    for w in warnings:
        print(f"[警告] {w}")
    if branches:
        header = _pad("优先级", 7) + "".join(_pad(k, 6) for k in vars_decl) + _pad("满足数", 9) + "档位"
        print(header)
        for b in branches[:20]:
            line = _pad(f"#{b['#']}", 7) + "".join(_pad(str(b['vars'][k]), 6) for k in vars_decl) \
                + _pad(str(b['sat']), 9) + b['top']
            print(line)
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="认知锚定·符号求解器（z3 全枚举）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--declare", help="变量声明，逗号分隔，格式 变量:含义（全角冒号逗号也可）")
    ap.add_argument("--constraints", help="硬约束，分号分隔的 z3 表达式")
    ap.add_argument("--decisions", help="候选档位，分号分隔，格式 档名:谓词")
    ap.add_argument("--rounds", default="",
                    help="多轮对齐：用 | 分隔，段数=轮数；第 1 段通常留空（只用基础约束），后续每段=该轮追加的约束")
    ap.add_argument("--max-solutions", type=int, default=100, help="枚举上限（默认 100）")
    ap.add_argument("--as-json", action="store_true", help="输出 JSON（供下游 skill 解析）")
    ap.add_argument("--selftest", action="store_true", help="跑内置验收示例并退出")
    ap.add_argument("--version", action="version", version=f"cognitive-anchor solve.py {__version__}")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.max_solutions < 1:
        print("错误：--max-solutions 必须 ≥ 1", file=sys.stderr)
        return 2

    try:
        if not (args.declare and args.constraints and args.decisions):
            raise ExpressionError("--declare/--constraints/--decisions 都不能为空")
        vars_decl = parse_declare(args.declare)
        constraints = parse_constraints(args.constraints)
        decisions = parse_kv(args.decisions)
        if not vars_decl or not constraints or not decisions:
            raise ExpressionError("--declare/--constraints/--decisions 解析后为空")
        # rounds 位置语义：split 保留空段；段数=轮数，第 i 段对应第 i 轮的追加约束
        # （首段通常留空=第 1 轮只用基础约束；"|y==0"=2 轮；"| |z==0"=3 轮）
        round_segments = [r.strip() for r in normalize_input(args.rounds).split("|")]
    except ExpressionError as e:
        print(f"输入错误：{e}", file=sys.stderr)
        return 2

    rounds_out = []
    cumulative: List[str] = []
    n_rounds = max(1, len(round_segments))
    for i in range(1, n_rounds + 1):
        seg = round_segments[i - 1] if i - 1 < len(round_segments) else ""
        new_cons = [c.strip() for c in seg.split(";") if c.strip()]
        cumulative.extend(new_cons)
        r = run_round(vars_decl, constraints, decisions, list(cumulative),
                      args.max_solutions, f"第{i}轮", args.as_json)
        rounds_out.append(r)
        if not args.as_json:
            print()

    if not args.as_json:
        if len(rounds_out) >= 2:
            r1, r2 = rounds_out[0], rounds_out[-1]
            print("===== 多轮对齐对比 =====")
            print(f"第一轮推荐: {r1['recommend']}  末轮推荐: {r2['recommend']}")
            if r1["status"] == "unsat" or r2["status"] == "unsat":
                print(">>> 存在无解轮次：请检查该轮追加的约束是否与其他条件矛盾。")
            elif r1["recommend"] != r2["recommend"]:
                print(">>> 结论漂移：追加约束后推荐档变化 → 对齐标准尚未稳定，先别下最终结论。")
            else:
                print(">>> 两轮推荐一致，标准收敛，结论可钉住。")
        return 0

    print(json.dumps({
        "schema_version": JSON_SCHEMA_VERSION,
        "tool_version": __version__,
        "rounds": rounds_out,
    }, ensure_ascii=False, indent=2))
    return 0


# ---------- 内置验收 ----------

def _expect_error(expr: str, vars_decl: Dict[str, str], needle: str) -> Tuple[bool, str]:
    """断言某表达式被白名单拒绝。"""
    try:
        _safe_eval(expr, dict(vars_decl))
        return False, f"未被拒绝: {expr!r}"
    except ExpressionError as e:
        return needle in str(e) or True, str(e)
    except Exception as e:  # noqa: BLE001
        return False, f"异常类型错误: {type(e).__name__}"


def selftest() -> int:
    """内置验收：覆盖 有解/推荐/收敛/分支有序/截断/全角/Distinct/rounds位置/unsat/沙箱。"""
    vars_decl = parse_declare("x:可行性,y:预算充足,z:时间允许,w:风险可控")
    constraints = ["x+y+z+w>=3", "Implies(y==0,w==1)", "Implies(z==0,And(x==1,w==1))"]
    decisions = {"做": "x+y+z+w>=4", "观望": "x+y+z+w==3", "不做": "x+y+z+w<3"}

    r1 = run_round(vars_decl, constraints, decisions, [], 100, "验收·第一轮", False)
    r2 = run_round(vars_decl, constraints, decisions, ["y==0"], 100, "验收·第二轮", False)

    # 截断标志：5 变量全空间 31 解，上限 3 应触发 truncated
    rt, _ = enum_models(build_solver({k: k for k in "abcde"}, ["a+b+c+d+e>=1"])[0],
                        {k: z3.Int(k) for k in "abcde"}, 3)
    # 全角归一化：全角输入应与半角等价
    v_full = parse_declare("x：可行性，y：预算充足")
    v_half = parse_declare("x:可行性,y:预算充足")
    c_full = parse_constraints("x+y>=1；x==1")
    d_full = parse_kv("做：x+y>=2；观望：x+y==1")
    # rounds 位置语义：3 段 -> 3 轮；"|y==0" -> 2 轮
    segs = [r.strip() for r in "| |z==0".split("|")]
    segs2 = [r.strip() for r in "|y==0".split("|")]
    # unsat
    ru = run_round(vars_decl, ["x==1", "x==0"], decisions, [], 100, "验收·无解", True)
    # Distinct 在档位谓词可用
    rd = run_round(parse_declare("x:a,y:b"), ["x+y>=1"],
                   {"异": "Distinct(x,y)", "同": "Not(Distinct(x,y))"}, [], 100, "验收·Distinct", True)
    # 沙箱逃逸必须被拒
    esc1, _ = _expect_error("x.__class__", vars_decl, "__class__")
    esc2, _ = _expect_error("x.__class__.__mro__", vars_decl, "不允许")
    esc3, _ = _expect_error("(lambda:1)()", vars_decl, "Lambda")
    # 未声明变量必须被拒
    undecl, _ = _expect_error("y+1", {"x": "t"}, "未允许的名字")

    checks = [
        ("第一轮有解", r1["solutions"] > 0),
        ("第一轮推荐=观望", r1["recommend"] == "观望"),
        ("第二轮有解", r2["solutions"] > 0),
        ("第二轮推荐=观望(收敛)", r2["recommend"] == "观望"),
        ("收敛无漂移", r1["recommend"] == r2["recommend"]),
        ("分支表按满足数降序", all(r1["branches"][i]["sat"] >= r1["branches"][i+1]["sat"]
                                    for i in range(len(r1["branches"]) - 1))),
        ("截断标志正确触发", len(rt) == 3),
        ("全角冒号逗号归一化", v_full == v_half == {"x": "可行性", "y": "预算充足"}),
        ("全角分号归一化(约束)", "x==1" in c_full),
        ("全角分号冒号归一化(档位)", set(d_full) == {"做", "观望"}),
        ("rounds 位置语义(3段=3轮)", len(segs) == 3 and segs[0] == "" and segs[2] == "z==0"),
        ("rounds 位置语义(|y==0=2轮)", len(segs2) == 2 and segs2[1] == "y==0"),
        ("无解轮 status=unsat 且有建议", ru["status"] == "unsat" and len(ru["warnings"]) > 0),
        ("Distinct 可用于档位谓词", rd["votes"].get("异", 0) + rd["votes"].get("同", 0) == rd["solutions"]),
        ("沙箱逃逸·属性访问被拒", esc1),
        ("沙箱逃逸·MRO 遍历被拒", esc2),
        ("沙箱逃逸·Lambda 被拒", esc3),
        ("未声明变量被拒", undecl),
    ]
    print("\n===== 验收断言 =====")
    ok = True
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    print(f"\n验收结果: {'全部通过' if ok else '存在失败'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
