# -*- coding: utf-8 -*-
"""把算出来的数字，打印成一眼能看懂的中文报告。

这里只管排版和措辞，不做任何计算。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .engine import (
    TAG_LOSE,
    TAG_UNKNOWN,
    TAG_WIN,
    Advice,
    Lottery,
    Mood,
    RedeemItem,
    Verdict,
    to_float,
)
from .sample import CAPTURED_AT

WIDTH = 66

_MARK = {TAG_WIN: "[赚]", TAG_LOSE: "[亏]", TAG_UNKNOWN: "[?]"}

_NAME_COL = 30


def _w(s: str) -> int:
    """字符串在终端里占几列（中日韩字符按 2 列算）。"""
    return sum(2 if ord(c) > 0x2E7F else 1 for c in s)


def _pad(s: str, n: int) -> str:
    return s + " " * max(0, n - _w(s))


def _rule(ch: str = "-") -> str:
    return ch * WIDTH


@dataclass
class Snapshot:
    """一次报告要用到的全部输入。"""

    day: str
    source: str                    # "live" / "sample"
    lottery: Lottery
    verdict: Verdict
    advice: Advice
    mood: Mood
    account: dict
    campaigns: list[str]
    my_prizes: list[dict]
    redeem: list[RedeemItem]
    generated_at: str = ""
    errors: dict = field(default_factory=dict)

    @property
    def source_text(self) -> str:
        if self.source == "live":
            return "麦当劳 MCP 实时数据（只读）"
        return f"内置样例（{CAPTURED_AT} 真实抓取，未联网）"


# ---------------------------------------------------------------------- #
# 各段落
# ---------------------------------------------------------------------- #

def _sec_rate(v: Verdict) -> str:
    r = v.rate
    return "\n".join([
        "",
        "【一】1 积分到底值多少钱？",
        "",
        f"  拿积分商城里现在还能换的 {r.samples} 件东西算，每件都标着售价和积分：",
        "",
        f"    最划算   {_pad(r.best_item, _NAME_COL)} 1 分 = {r.best:.4f} 元",
        f"    最差     {_pad(r.worst_item, _NAME_COL)} 1 分 = {r.worst:.4f} 元",
        "",
        f"  取中间档当基准：{r.text()}",
    ])


def _sec_verdict(v: Verdict, lottery: Lottery) -> str:
    lines = [
        "",
        "【二】抽一次，亏不亏？",
        "",
        f"  活动：{lottery.name}　一次 {v.cost_points} 积分　奖池 {len(v.rows)} 件",
        "",
        f"  这 {v.cost_points} 积分如果直接拿去兑换，值 {v.break_even:.2f} 元。",
        f"  → 所以抽出来的东西，至少值 {v.break_even:.2f} 元才算不亏。",
        "",
        "  奖池逐件估价：",
        "",
    ]
    for row in v.rows:
        lines.append(f"    {_MARK[row.tag]} {_pad(row.name, _NAME_COL)} {row.yuan_text}")
    lines.append("")
    lines.append(f"  数一下：赚 {v.win} 件、亏 {v.lose} 件、看用法 {v.unknown} 件。")
    return "\n".join(lines)


def _sec_compare(v: Verdict, adv: Advice) -> str:
    lines = ["", "【三】该抽，还是该换？", ""]
    if adv.draw_best_rate is not None and v.best_yuan is not None:
        top = max((r for r in v.rows if r.yuan is not None), key=lambda r: r.yuan)
        lines.append(
            f"  抽奖（最好情况）抽到「{top.name}」"
            f"　{v.best_yuan:.2f} ÷ {v.cost_points} = {adv.draw_best_rate:.4f} 元/分"
        )
    else:
        lines.append("  抽奖（最好情况）奖池里没有能定价的奖品，比不了")
    lines.append(
        f"  兑换（最好档）  「{v.rate.best_item}」"
        f"　{v.rate.best:.4f} 元/分"
    )
    lines.append("")
    lines.append(f"  → 结论：{adv.winner}。")
    lines.append(f"    {adv.reason}")
    return "\n".join(lines)


def _sec_account(account: dict, v: Verdict) -> str:
    parts = [f"可用 {to_float(account.get('available')):g} 分"]
    acc = to_float(account.get("accumulative"))
    if acc:
        parts.append(f"累计 {acc:g} 分")
    exp = to_float(account.get("expired"))
    if exp:
        parts.append(f"已过期 {exp:g} 分")
    soon = to_float(account.get("expiring"))
    if soon:
        parts.append(f"即将过期 {soon:g} 分")

    lines = ["", "【四】我的积分", "", "  " + " · ".join(parts)]
    avail = to_float(account.get("available"))
    if avail >= v.cost_points:
        lines.append(f"  抽一次要 {v.cost_points} 分 —— 够，最多能抽 {v.draws_affordable} 次。")
    else:
        lines.append(f"  抽一次要 {v.cost_points} 分 —— 现在不够，还差 {v.cost_points - avail:g} 分。")
    return "\n".join(lines)


def _sec_mood(m: Mood) -> str:
    lines = ["", "【五】今天适合抽吗？", "", f"  {m.headline}"]
    lines.extend(f"  · {ln}" for ln in m.lines)
    return "\n".join(lines)


# ---------------------------------------------------------------------- #
# 主入口
# ---------------------------------------------------------------------- #

def render(snap: Snapshot) -> str:
    v = snap.verdict
    blocks = [
        _rule("="),
        f"  积分抽奖量化占卜 · {snap.day}",
        f"  数据来源：{snap.source_text}",
        _rule("="),
        _sec_rate(v),
        _sec_verdict(v, snap.lottery),
        _sec_compare(v, snap.advice),
        _sec_account(snap.account, v),
        _sec_mood(snap.mood),
    ]

    if snap.errors:
        blocks.append("")
        blocks.append("【提示】以下工具没取到数据，已用内置样例顶上：")
        for key, err in snap.errors.items():
            blocks.append(f"  - {key}: {err}")

    blocks.extend([
        "",
        _rule("="),
        "  两点说明：",
        "  1. 抽奖接口不公开中奖概率，所以本工具不估算「平均能抽到多少」，",
        "     只算两件确定的事 —— 保本线、奖池上限。折扣券一律不估价。",
        "  2. 全程只读：不会替你抽奖，也不会替你下单。",
        _rule("="),
    ])
    return "\n".join(blocks)
