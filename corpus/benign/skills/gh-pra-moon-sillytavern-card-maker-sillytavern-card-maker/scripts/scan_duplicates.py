#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_duplicates.py — 世界书赘述体检：行级精确查重 + 句级模糊查重（跨条目 / 条目内）

用法:
    python scripts/scan_duplicates.py <worldbook.json | 卡工程目录 | 成品卡.json>
                                      [--threshold 0.55] [--top 25]

输出:
    D. 条目字数排行（常驻 / 条件触发 分开）
    A. 跨条目精确重复（≥14 字的整行）
    B. 跨条目近义句（difflib 相似度 ≥ threshold）
    C. 条目内近义句

处理原则（读输出时用）:
    单一权威源 + 短指针——数值口径只留「变量更新规则」等权威条目，
    其余改「见『XXX』」；「咒语型」短指针是执行锚点，只压短不删；
    例子/味道句不删。只读不写。
"""

import json
import os
import re
import sys
from difflib import SequenceMatcher

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_entries(path):
    """支持三种输入：ST 世界书 json / 卡工程目录 / 成品卡 json。返回 {uid: {comment, content, constant, disable}}"""
    if os.path.isdir(path):
        path = os.path.join(path, "worldbook.json")
    if not os.path.isfile(path):
        raise SystemExit(f"找不到输入文件: {path}（需要 ST 世界书 json / 卡工程目录 / 成品卡 json）")
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    if "entries" in data and isinstance(data["entries"], dict):
        return {
            str(uid): {
                "comment": e.get("comment", ""),
                "content": e.get("content") or "",
                "constant": bool(e.get("constant")),
                "disable": bool(e.get("disable")),
            }
            for uid, e in data["entries"].items()
        }
    if "data" in data and "character_book" in data.get("data", {}):
        out = {}
        for i, e in enumerate(data["data"]["character_book"]["entries"]):
            out[str(e.get("id", i))] = {
                "comment": e.get("comment", ""),
                "content": e.get("content") or "",
                "constant": bool(e.get("constant")),
                "disable": not bool(e.get("enabled", True)),
            }
        return out
    raise SystemExit("无法识别的输入：需要 ST 世界书 json / 卡工程目录 / 成品卡 json")


def split_sentences(text):
    sents = []
    for s in re.split(r"[。；]", text.replace("\n", "。")):
        t = re.sub(r"^[\s\-【「]*", "", s.strip())
        if len(t) >= 16 and re.search(r"[\u4e00-\u9fff]", t):
            sents.append(t)
    return sents


def main():
    args = [a for a in sys.argv[1:]]
    path = args[0] if args and not args[0].startswith("--") else "."
    threshold = 0.55
    top = 25
    if "--threshold" in args:
        threshold = float(args[args.index("--threshold") + 1])
    if "--top" in args:
        top = int(args[args.index("--top") + 1])

    entries = load_entries(path)
    print(f"[输入] {path}（{len(entries)} 个条目）\n")

    # ---------- D. 体量排行
    const_rows, cond_rows = [], []
    for uid, e in entries.items():
        if e["disable"]:
            continue
        row = (len(e["content"]), uid, e["comment"])
        (const_rows if e["constant"] else cond_rows).append(row)
    const_total = sum(r[0] for r in const_rows)
    print(f"== D. 条目字数排行（常驻 {len(const_rows)} 条，合计 {const_total} 字）==")
    for size, uid, comment in sorted(const_rows, reverse=True):
        print(f"{size:>6}  uid={uid:<4} {comment}")
    print(f"\n-- 条件触发 {len(cond_rows)} 条 --")
    for size, uid, comment in sorted(cond_rows, reverse=True):
        print(f"{size:>6}  uid={uid:<4} {comment}")
    print()

    # ---------- A. 行级精确重复
    lines = []
    for uid, e in entries.items():
        if e["disable"]:
            continue
        for ln in e["content"].split("\n"):
            t = ln.strip().lstrip("-").strip()
            if len(t) >= 14:
                lines.append((uid, t))
    seen = {}
    for uid, t in lines:
        seen.setdefault(t, []).append(uid)
    print("== A. 跨条目精确重复（≥14 字整行）==")
    found = 0
    for t, uids in seen.items():
        if len(set(uids)) >= 2:
            found += 1
            print(f"  [{', '.join(sorted(set(uids), key=lambda x: int(x) if x.isdigit() else 0))}] {t[:80]}")
    if not found:
        print("  （无）")
    print()

    # ---------- B. 跨条目近义句
    sents = []
    for uid, e in entries.items():
        if e["disable"]:
            continue
        for s in split_sentences(e["content"]):
            sents.append((uid, s))
    pairs = []
    for i in range(len(sents)):
        for j in range(i + 1, len(sents)):
            u1, s1 = sents[i]
            u2, s2 = sents[j]
            if u1 == u2:
                continue
            r = SequenceMatcher(None, s1, s2).ratio()
            if r >= threshold:
                pairs.append((r, u1, s1, u2, s2))
    pairs.sort(reverse=True)
    print(f"== B. 跨条目近义句（相似度 ≥ {threshold}）==")
    shown, keys = 0, set()
    for r, u1, s1, u2, s2 in pairs:
        key = (min(u1, u2), max(u1, u2), s1[:12])
        if key in keys:
            continue
        keys.add(key)
        print(f"--- {r:.2f} [uid {u1} ↔ {u2}]")
        print(f"    A({u1}): {s1[:90]}")
        print(f"    B({u2}): {s2[:90]}")
        shown += 1
        if shown >= top:
            break
    if not shown:
        print("  （无）")
    print()

    # ---------- C. 条目内近义句
    print("== C. 条目内近义句 ==")
    shown = 0
    for uid, e in entries.items():
        if e["disable"]:
            continue
        ss = split_sentences(e["content"])
        for i in range(len(ss)):
            for j in range(i + 1, len(ss)):
                if len(ss[i]) < 20:
                    continue
                r = SequenceMatcher(None, ss[i], ss[j]).ratio()
                if r >= max(threshold, 0.6):
                    print(f"--- uid={uid} ({e['comment'][:16]}) sim={r:.2f}")
                    print(f"    A: {ss[i][:88]}")
                    print(f"    B: {ss[j][:88]}")
                    shown += 1
                    if shown >= top:
                        break
            if shown >= top:
                break
        if shown >= top:
            break
    if not shown:
        print("  （无）")


if __name__ == "__main__":
    main()
