#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
常备件体检 —— 扫一遍投标常备件目录，报每件材料的状态

用法：
    python3 check_standing.py <常备件目录> [--asof 2026-11-16]

它只做一件事：**告诉你哪件材料可能过期了、哪件根本没找到。**

⚠️ 一条必须说清的局限：
   脚本用的是**文件修改时间（mtime）**，不是材料的**开具日期**。
   两者经常不一致 —— 从税务局导出一份完税证明、存到盘里、隔两个月又动过一次，
   mtime 就是后一次的时间，而材料本身可能早就过了招标文件要求的时效。
   **所以脚本报「✅ 在时效内」，只能说明"文件不旧"，不能说明"材料合规"。**
   真正的时效判据在材料内容上（查询日期、所属期），必须打开看。

配套：read_tender.py 读招标文件，本脚本读你自己的存货。两者都不写任何东西。
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

# ── 常备件定义 ────────────────────────────────────────────────────
# 每件：显示名 → (匹配关键词, 时效天数, 是否必备, 说明)
#   时效天数 = None 表示没有通用时效（以招标文件为准）
#   匹配关键词之间是"或"的关系，命中文件名即算这件材料存在
ITEMS = [
    # ── A 档：按次，时效由招标文件规定 ──
    ('信用中国查询截图', ['信用中国', '信用查询', '失信查询'], 7, True,
     '绝大多数招标文件要求"查询日期距投标截止日不超过 7 日"，也有 15/30 日的，以文件为准'),
    ('无重大违法记录声明/承诺函', ['无重大违法', '违法记录', '承诺函', '声明函'], None, True,
     '格式必须与招标文件指定措辞一字不差'),

    # ── B 档：按月 ──
    ('完税证明', ['完税', '纳税证明', '税收完税'], 90, True,
     '招标文件多要求"近 3 个月"或"近 6 个月"'),
    ('社保缴纳证明', ['社保', '社会保险', '参保'], 90, True,
     '需能体现参保人数 —— 有的标会拿它对律师名册核人数'),

    # ── C 档：按季／按年 ──
    ('律师事务所执业许可证', ['执业许可证', '律所执业许可'], None, True,
     '副本的年检结论页必须复印进去'),
    ('营业执照', ['营业执照'], None, True, '年度报告公示后更新'),
    ('律师名册', ['律师名册', '执业律师名册', '人员名册'], None, True,
     '名册人数须与执业证复印件、社保参保人数三者对得上'),
    ('财务审计报告/财务报表', ['审计报告', '财务报表', '资产负债表'], 400, False,
     '上半年投标交上年度；别把两年前的当最新的'),
    ('荣誉证书', ['荣誉', '优秀律师', '优秀律师事务所'], None, False,
     '按省级/全国级、律所/个人分好，评分表按级别给分'),

    # ── E 档：制度类 ──
    ('保密管理制度', ['保密'], None, False, '每年复核一次；写三页能执行的，好过十页抄来的'),
    ('档案管理制度', ['档案'], None, False, '归档时限、保存期限、销毁流程是否写清'),
    ('利益冲突审查制度', ['利益冲突', '冲突审查'], None, False, '审查流程与回避机制是否具体'),
    ('收费管理制度', ['收费管理', '收费标准'], None, False, '与现行收费标准是否一致'),
    ('应急预案/投诉处理机制', ['应急预案', '投诉处理'], None, False,
     '多数律所最弱的一项 —— 也是少数能在别人都不重视处拿分的地方'),
]

SKIP_DIRS = {'.git', '__pycache__', '.venv', 'node_modules'}


def collect_files(root):
    """列出目录下所有文件（跳过隐藏目录与缓存目录）。"""
    out = []
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS or part.startswith('.') for part in p.parts):
            continue
        out.append(p)
    return out


def age_days(path, asof):
    """返回文件有多"旧"（天）。负数表示修改时间晚于基准日。"""
    mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime)
    return (asof - mtime).days


def judge(days, limit):
    # 负数：文件修改时间比基准日还晚。多半是机器时钟不对，或者文件是从
    # 时钟走快的机器拷过来的。这种情况**不能报"在时效内"** ——
    # 它连"这份文件是不是这次要用的那份"都还没确认，报绿灯是骗人。
    if days < 0:
        return '⚠️ 时间异常'
    if limit is None:
        # 没有通用时效，不等于永远有效。超过一年的提醒复核一次 ——
        # 免得"以招标文件为准"变成"永远不用管"。
        return '💡 建议复核' if days > 365 else '—'
    if days <= limit:
        return '✅ 在时效内'
    if days <= limit * 1.5:
        return '⚠️ 已超期（接近临界，赶紧重取）'
    return '❌ 已超期'


def main():
    ap = argparse.ArgumentParser(description='投标常备件体检')
    ap.add_argument('root', help='常备件目录')
    ap.add_argument('--asof', help='以哪一天为准算天数，默认今天（YYYY-MM-DD）')
    ap.add_argument('--limit', type=float, default=1.0,
                    help='时效系数：0.5 表示按要求的半数天数就预警，默认 1.0')
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f'❌ 目录不存在：{root}')

    if args.asof:
        try:
            asof = datetime.datetime.strptime(args.asof, '%Y-%m-%d')
        except ValueError:
            raise SystemExit('❌ --asof 格式应为 YYYY-MM-DD')
    else:
        asof = datetime.datetime.now()

    files = collect_files(root)
    print(f'📂 {root}')
    print(f'   共 {len(files)} 个文件；以 {asof:%Y-%m-%d} 为基准日\n')

    missing, expiring, ok = [], [], []

    for name, keys, limit, required, note in ITEMS:
        hit = None
        for f in sorted(files):
            if any(k in f.name for k in keys):
                # 同一件材料有多份时取最新的
                if hit is None or f.stat().st_mtime > hit.stat().st_mtime:
                    hit = f
        if hit is None:
            flag = '❌ 未找到' if required else '⚠️ 未找到'
            (missing if required else expiring).append((name, None, None, note))
            print(f'  {flag:12} {name}')
            print(f'               └ {note}')
            continue

        days = age_days(hit, asof)
        eff = limit * args.limit if limit else None
        verdict = judge(days, eff)
        rel = hit.relative_to(root)
        when = f'{days} 天前' if days >= 0 else f'比基准日晚 {-days} 天'
        print(f'  {verdict:12} {name}  （{when}，{rel}）')
        if limit:
            print(f'               └ 招标文件常见要求：{limit} 天。{note}')
        else:
            print(f'               └ 无通用时效，以招标文件为准。{note}')
        if days < 0:
            print('               └ ⚠️ 文件修改时间晚于基准日，多半是时钟或复制问题，'
                  '请人工确认这份是不是这次要用的')
            expiring.append((name, days, eff, note))
        elif limit and eff and days > eff:
            expiring.append((name, days, eff, note))
        elif limit is None and days > 365:
            print(f'               └ 💡 已超过一年没动过，建议打开复核一次内容是否仍现行')
            expiring.append((name, days, eff, note))
        elif required:
            ok.append(name)

    print('\n' + '─' * 62)
    print('小结：')
    if ok:
        print(f'  ✅ 必备件中 {len(ok)} 件未发现时效问题（但见下方声明）')
    if expiring:
        print(f'  ⚠️ {len(expiring)} 件需要处理：')
        for name, days, eff, _ in expiring:
            when = f'{days} 天前' if days is not None else '未找到'
            print(f'     · {name} —— {when}')
    if missing:
        print(f'  ❌ {len(missing)} 件必备材料没有找到：')
        for name, _, _, _ in missing:
            print(f'     · {name}')
    print('─' * 62)
    print()
    print('⚠️ 两点必须自己确认，脚本给不了答案：')
    print('   1. 上面用的是**文件修改时间**，不是材料的**开具日期**。')
    print('      报「在时效内」只说明文件不旧，不等于材料合规 —— 打开看内容上的日期。')
    print('   2. 本清单是通用常备件。**招标文件"投标文件的组成"一节要什么，以它为准。**')
    print('      两者的差集，才是这次投标要补的东西。')


if __name__ == '__main__':
    sys.exit(main())
