#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cognitive-anchor / scripts/solve.py
====================================
认知锚定·符号求解器（z3 全枚举）。

把自然语言判据翻译成 0/1 符号变量与硬约束后，本脚本负责"硬算"：
  1. 枚举全部满足解
  2. 档位投票（每个候选决策命中多少解）
  3. 变量频率（每个条件在所有满足解中的成立比例）
  4. 分支博弈表（按满足数降序）
  5. 多轮对齐（追加约束重解，检测推荐是否漂移）

用法示例：
  python3 solve.py \
    --declare "x:可行性,y:预算充足,z:时间允许,w:风险可控" \
    --constraints "x+y+z+w>=3; Implies(y==0,w==1); Implies(z==0,And(x==1,w==1))" \
    --decisions "做:x+y+z+w>=4; 观望:x+y+z+w==3; 不做:True" \
    --rounds "|y==0" \
    --max-solutions 50

说明：
  - 变量全部建模为 0/1 整数（z3 Int），约束里可直接写 x==1 / y==0 / x+y>=2 等。
  - 表达式由受控 eval 解析：只允许 z3 函数(And/Or/Not/Implies/If) + 变量 + 算术/比较。
  - 结论一律来自求解器输出，不经过任何 LLM 自由发挥。
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from typing import Dict, List, Optional, Tuple

import z3

# ---------- 受控表达式解析 ----------

def _safe_eval(expr: str, allowed: dict):
    """在只含 z3 API 与变量的命名空间里 eval，禁止 __builtins__。"""
    tree = ast.parse(expr.strip(), mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in allowed:
            raise ValueError(f"表达式里出现未允许的名字: {node.id!r}（在 {expr!r} 中）")
    return eval(compile(tree, "<constraints>", "eval"), {"__builtins__": {}}, allowed)


def parse_declare(text: str) -> Dict[str, str]:
    """'x:可行性,y:预算充足' -> {'x':'可行性',...}"""
    out = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
        else:
            out[part.strip()] = part.strip()
    return out


def build_solver(vars_decl: Dict[str, str],
                 constraints: List[str],
                 decisions: Dict[str, str],
                 extra: Optional[List[str]] = None) -> Tuple[z3.Solver, Dict[str, z3.ArithRef]]:
    """构造 z3 求解器：变量声明 + 域约束(0/1) + 硬约束 + 本轮追加约束。"""
    z = {k: z3.Int(k) for k in vars_decl}
    allowed = dict(z)
    allowed.update({
        "And": z3.And, "Or": z3.Or, "Not": z3.Not, "Implies": z3.Implies,
        "If": z3.If, "Distinct": z3.Distinct,
        "True": True, "False": False,
    })
    s = z3.Solver()
    for k, v in z.items():
        s.add(v >= 0)
        s.add(v <= 1)
    for c in constraints:
        c = c.strip()
        if c:
            s.add(_safe_eval(c, allowed))
    for e in (extra or []):
        e = e.strip()
        if e:
            s.add(_safe_eval(e, allowed))
    return s, z


def enum_models(s: z3.Solver, z: Dict[str, z3.ArithRef],
                max_solutions: int) -> List[Dict[str, int]]:
    """枚举全部满足解（带回溯阻塞子句）。"""
    models: List[Dict[str, int]] = []
    while len(models) < max_solutions and s.check() == z3.sat:
        m = s.model()
        row = {k: m.eval(v).as_long() for k, v in z.items()}
        models.append(row)
        s.add(z3.Or(*[v != m.eval(v) for v in z.values()]))
    return models


def eval_decision(row: Dict[str, int], expr: str, z: Dict[str, z3.ArithRef]) -> bool:
    """把档位谓词对某一解求值（解是整数，构建 Bool 后 eval）。"""
    allowed = {k: z3.IntVal(v) for k, v in row.items()}
    allowed.update({
        "And": z3.And, "Or": z3.Or, "Not": z3.Not, "Implies": z3.Implies,
        "If": z3.If, "True": True, "False": False,
    })
    val = _safe_eval(expr, allowed)
    if isinstance(val, z3.BoolRef):
        s = z3.Solver()
        s.add(val)
        return s.check() == z3.sat
    return bool(val)


def run_round(vars_decl, constraints, decisions, extra, max_solutions,
              label: str, as_json: bool) -> dict:
    s, z = build_solver(vars_decl, constraints, decisions, extra)
    models = enum_models(s, z, max_solutions)
    total = len(models)

    # 档位票数
    votes = Counter()
    for dname, dexpr in decisions.items():
        votes[dname] = sum(1 for r in models if eval_decision(r, dexpr, z))

    # 变量频率
    freq = {}
    for k in vars_decl:
        freq[k] = (sum(r[k] for r in models) / total) if total else 0.0

    # 分支表：按"成立条件数"降序
    branches = []
    for i, r in enumerate(models, 1):
        sat_count = sum(r.values())
        hit = [d for d, e in decisions.items() if eval_decision(r, e, z)]
        branches.append({"#": i, "vars": r, "sat": sat_count,
                         "grades": hit, "top": hit[0] if hit else "-"})
    branches.sort(key=lambda b: -b["sat"])

    # 推荐：票数最多的档；并列时用票数 + 分支表第一条的 top 裁决
    top_votes = max(votes.values()) if votes else 0
    winners = [d for d, v in votes.items() if v == top_votes and top_votes > 0]
    recommend = winners[0] if winners else "-"
    if len(winners) > 1 and branches:
        first = branches[0]["top"]
        if first in winners:
            recommend = first

    result = {
        "round": label, "solutions": total, "votes": dict(votes),
        "freq": {k: round(v, 3) for k, v in freq.items()},
        "recommend": recommend, "branches": branches[:max_solutions],
        "truncated": total > max_solutions,
    }
    if as_json:
        return result

    print(f"\n===== {label} =====")
    print(f"满足解总数: {total}" + ("（已截断）" if result["truncated"] else ""))
    print(f"档位票数: " + "  ".join(f"{k}={v}" for k, v in votes.items()))
    print(f"变量=1 频率: " + "  ".join(f"{k}({vars_decl[k]})={freq[k]*100:.0f}%" for k, v in vars_decl.items()))
    print(f">>> 推荐档: {recommend}")
    if branches:
        print(f"{'优先级':<6}" + "".join(f"{k:<4}" for k in vars_decl) + f"{'满足数':<7}{'档位':<8}")
        for b in branches[:20]:
            line = f"#{b['#']:<5}" + "".join(f"{b['vars'][k]:<4}" for k in vars_decl) + f"{b['sat']:<7}{b['top']:<8}"
            print(line)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description="认知锚定·符号求解器（z3 全枚举）")
    ap.add_argument("--declare", help="变量声明，逗号分隔，格式 变量:含义")
    ap.add_argument("--constraints", help="硬约束，分号分隔的 z3 表达式")
    ap.add_argument("--decisions", help="候选档位，分号分隔，格式 档名:谓词")
    ap.add_argument("--rounds", default="", help="多轮对齐：每轮追加约束，用 | 分隔；空表示无追加")
    ap.add_argument("--max-solutions", type=int, default=100, help="枚举上限")
    ap.add_argument("--as-json", action="store_true", help="输出 JSON（供下游 skill 解析）")
    ap.add_argument("--selftest", action="store_true", help="跑内置验收示例并退出")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if not (args.declare and args.constraints and args.decisions):
        print("错误：--declare/--constraints/--decisions 都不能为空", file=sys.stderr)
        return 2

    vars_decl = parse_declare(args.declare)
    constraints = [c.strip() for c in args.constraints.split(";") if c.strip()]
    decisions = {}
    for part in args.decisions.split(";"):
        part = part.strip()
        if ":" in part:
            n, e = part.split(":", 1)
            decisions[n.strip()] = e.strip()
    rounds = [r.strip() for r in args.rounds.split("|") if r.strip() != ""]

    if not vars_decl or not constraints or not decisions:
        print("错误：--declare/--constraints/--decisions 解析后为空", file=sys.stderr)
        return 2

    rounds_out = []
    cumulative: List[str] = []
    for i, extra in enumerate([None] + rounds, 1):
        label = f"第{i}轮"
        if extra:
            cumulative.append(extra)
        r = run_round(vars_decl, constraints, decisions, cumulative, args.max_solutions,
                      label, args.as_json)
        rounds_out.append(r)
        if not args.as_json:
            print()

    if not args.as_json:
        if len(rounds_out) >= 2:
            r1, r2 = rounds_out[0], rounds_out[-1]
            print("===== 多轮对齐对比 =====")
            print(f"第一轮推荐: {r1['recommend']}  末轮推荐: {r2['recommend']}")
            if r1["recommend"] != r2["recommend"]:
                print(">>> 结论漂移：追加约束后推荐档变化 → 对齐标准尚未稳定，先别下最终结论。")
            else:
                print(">>> 两轮推荐一致，标准收敛，结论可钉住。")
        return 0

    print(json.dumps(rounds_out, ensure_ascii=False, indent=2))
    return 0


def selftest() -> int:
    """内置验收：跑一个 4 变量 3 约束两轮示例，断言关键结果。"""
    args = [
        "--declare", "x:可行性,y:预算充足,z:时间允许,w:风险可控",
        "--constraints", "x+y+z+w>=3; Implies(Not(y),w); Implies(Not(z),And(x,w))",
        "--decisions", "做:x+y+z+w>=4; 观望:x+y+z+w==3; 不做:True",
        "--rounds", "y==0",
        "--max-solutions", "100",
    ]
    vars_decl = parse_declare("x:可行性,y:预算充足,z:时间允许,w:风险可控")
    constraints = ["x+y+z+w>=3", "Implies(y==0,w==1)", "Implies(z==0,And(x==1,w==1))"]
    decisions = {"做": "x+y+z+w>=4", "观望": "x+y+z+w==3", "不做": "x+y+z+w<3"}
    r1 = run_round(vars_decl, constraints, decisions, [], 100, "验收·第一轮", False)
    r2 = run_round(vars_decl, constraints, decisions, ["y==0"], 100, "验收·第二轮", False)
    ok = True
    checks = [
        ("第一轮有解", r1["solutions"] > 0),
        ("第一轮推荐=观望", r1["recommend"] == "观望"),
        ("第二轮有解", r2["solutions"] > 0),
        ("第二轮推荐=观望(收敛)", r2["recommend"] == "观望"),
        ("收敛无漂移", r1["recommend"] == r2["recommend"]),
        ("分支表按满足数降序", all(r1["branches"][i]["sat"] >= r1["branches"][i+1]["sat"]
                                     for i in range(len(r1["branches"])-1))),
    ]
    print("\n===== 验收断言 =====")
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    print(f"\n验收结果: {'全部通过' if ok else '存在失败'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
