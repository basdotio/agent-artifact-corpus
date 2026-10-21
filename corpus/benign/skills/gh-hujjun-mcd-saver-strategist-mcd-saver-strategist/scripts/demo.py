#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦门省钱精算师 · 场景演示 (离线可跑, 无需 Token)

把 7 个真实点餐场景一次性跑给你看:
    1. 单人 · 想吃巨无霸套餐, 怎么最便宜
    2. 预算硬约束: 25 元以内能吃到什么
    3. 减脂期: 800 大卡以内还要便宜
    4. 三人拼单: 总价与人均
    5. 麦乐送外送: 配送费计入总价
    6. 券体检: 手里 8 张券, 哪张是真便宜
    7. 凑单: 加一个小东西, 反而更省钱

运行:  python demo.py            # 全部场景
       python demo.py 6          # 只看第 6 个场景
"""

from __future__ import annotations

import copy
import os
import sys
import unicodedata

from optimizer import (
    audit_coupons,
    format_audit,
    format_gap,
    format_pareto,
    format_report,
    load_json,
    optimize,
    suggest_gap,
)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "sample_data")
SYM = "¥"


def _load():
    return (load_json(os.path.join(DATA, "menu.json")),
            load_json(os.path.join(DATA, "coupons.json")))


def _width(text: str) -> int:
    """中文占两格, 用等宽字符数对齐方框。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _width(text))


def _head(no: int, title: str, sub: str = "") -> None:
    print()
    print("╔" + "═" * 62 + "╗")
    print("║ " + _pad(f"场景 {no} · {title}", 60) + "║")
    if sub:
        print("║ " + _pad(sub, 60) + "║")
    print("╚" + "═" * 62 + "╝")


def _brief(plan: dict) -> str:
    return " + ".join(it["name"] for it in plan["items"])


def main(argv) -> int:
    only = argv[1] if len(argv) > 1 else None
    menu, coupons = _load()

    def want(n: int) -> bool:
        return only is None or str(n) == str(only)

    if want(1):
        _head(1, "单人 · 想吃巨无霸套餐", "用户: 巨无霸 + 薯条 + 可乐, 怎么最便宜")
        req = {"wants": ["巨无霸", "薯条", "可乐"], "max_items": 4, "allow_extras": True}
        r = optimize(copy.deepcopy(menu), coupons, req)
        b = r["plans"][0]
        print(f"  直选原价 {SYM}{r['baseline']['total']:.2f}  →  "
              f"最优到手价 {SYM}{b['total']:.2f}   省 {SYM}{b['coupon_saving']:.2f}"
              f" ({b['saving_pct']*100:.0f}%)")
        print(f"  怎么点: {_brief(b)}")
        print(f"  用券:   {'、'.join(c['title'] for c in b['coupons'])}")
        print(f"  热量:   {b['calories']} kcal   共评估 {r['plan_pool_size']} 个方案")

    if want(2):
        _head(2, "预算硬约束", "用户: 25 块钱在麦当劳能吃到什么")
        req = {"wants": ["汉堡", "小食"], "budget": 25.0, "max_items": 4, "allow_extras": True}
        r = optimize(copy.deepcopy(menu), coupons, req)
        print(f"  预算 {SYM}25.00 内, 按到手价从低到高:")
        for i, p in enumerate(r["plans"][:3], 1):
            left = 25.0 - p["total"]
            print(f"    {i}. {SYM}{p['total']:>5.2f}  {p['calories']:>5} kcal  "
                  f"剩 {SYM}{left:>5.2f}   {_brief(p)}")
        print(f"  共 {r['plan_pool_size']} 个方案落在预算内 —— 预算不是越紧越省, "
              f"而是把'能吃到什么'筛出来")

    if want(3):
        _head(3, "减脂期 · 热量与价格双约束", "用户: 800 大卡以内, 还要便宜")
        req = {"wants": ["汉堡", "饮料"], "max_calories": 800, "max_items": 3,
               "allow_extras": True, "objective": "lightest"}
        r = optimize(copy.deepcopy(menu), coupons, req)
        b = r["plans"][0]
        print(f"  最低卡方案: {SYM}{b['total']:.2f} / {b['calories']} kcal   {_brief(b)}")
        print(f"  选型说明:   {r['objective_reason']}")
        no_bundle = {"coupons": [c for c in coupons["coupons"] if c["type"] != "bundle_price"]}
        r2 = optimize(copy.deepcopy(menu), no_bundle,
                      dict(req, objective="cheapest"))
        print("  假如手里没有 1+1 券, 价格与热量的权衡就出现了:")
        print(format_pareto(r2["pareto"], SYM))
        print("  → 前沿上的点都是'不可被支配'的: 想更省, 就得多吃热量。")

    if want(4):
        _head(4, "三人拼单", "用户: 3 个人各要一份巨无霸套餐")
        req = {"wants": ["巨无霸", "薯条", "可乐"], "max_items": 4,
               "allow_extras": True, "party_size": 3}
        r = optimize(copy.deepcopy(menu), coupons, req)
        b = r["plans"][0]
        print(f"  单份 {SYM}{b['unit_total']:.2f}  →  3 份总价 {SYM}{b['total']:.2f}"
              f"   人均 {SYM}{b['per_person']:.2f}")
        print("  注意: 优惠只计一次 (券按单用), 不随份数放大 —— 宁可少报, 不报假低价")

    if want(5):
        _head(5, "麦乐送外送", "用户: 外送到家, 预算 60, 含配送费")
        req = {"wants": ["巨无霸", "薯条", "可乐"], "max_items": 4, "allow_extras": True,
               "dining_mode": "delivery", "delivery_fee": 9.0, "budget": 60.0}
        r = optimize(copy.deepcopy(menu), coupons, req)
        b = r["plans"][0]
        print(f"  到手价 {SYM}{b['total']:.2f} (含配送费 {SYM}{b['delivery_fee']:.2f})   {_brief(b)}")
        print(f"  外送场景已自动剔除「仅到店」的门店券, 券池比到店少一张")

    if want(6):
        _head(6, "券体检 · 哪张券是真便宜", "同样的菜, 8 张券逐个体检")
        req = {"wants": ["巨无霸", "薯条", "可乐"], "max_items": 4, "allow_extras": True}
        rows = audit_coupons(copy.deepcopy(menu), coupons, req)
        print(format_audit(rows, SYM))
        print()
        print("  读法: 「名义」是券上写的大字, 「实际省」是真的能省, "
              "两者之间的差额就是兑现率的分母与分子。")
        print("  🪤 标记的券单看都在省钱, 但用了它就吃不到更划算的组合 —— 机会成本最高的一类。")

    if want(7):
        _head(7, "凑单 · 加一个小东西反而更省", "用户: 巨无霸 + 薯条, 手里只有一张「满 45 减 12」")
        thin = {"coupons": [{"id": "T45", "type": "threshold", "title": "满 45 减 12",
                             "min_spend": 45.0, "discount": 12.0, "stackable": True}]}
        # max_items=2: 只点想吃的两件, 不自动加购 —— 让凑单建议来回答"要不要加"
        req = {"wants": ["巨无霸", "薯条"], "max_items": 2, "allow_extras": True}
        r = optimize(copy.deepcopy(menu), thin, req)
        b = r["plans"][0]
        print(f"  当前方案: {SYM}{b['total']:.2f}   {_brief(b)}   (未触发满减)")
        g = r["gap"]["threshold"]
        if g:
            print(f"  凑单建议: {g['text']}")
            if g["verdict"] == "worth":
                print("  → 净变化为负: 加购花的钱 < 多减的钱, 这件东西等于白送还倒找钱")
            elif g["verdict"] == "even":
                print("  → 净变化为零: 花的钱一分不涨, 白得一份")
            else:
                print("  → 净变化为正: 为凑门槛多买的东西其实是自己掏钱, 别被门槛牵着走")
        else:
            print("  当前方案已用上最优券, 没有更划算的凑单空间。")

    print()
    print("─" * 64)
    print("以上全部由 optimizer.py 计算, 可用 `python selftest.py` 复现验证 (46 项断言)。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
