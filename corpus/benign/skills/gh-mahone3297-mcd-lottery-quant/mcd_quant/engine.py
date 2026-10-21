# -*- coding: utf-8 -*-
"""核心计算：1 积分值多少钱、抽一次亏不亏、该抽还是该换。

本文件只做算术 —— 不联网、不打印、不依赖任何第三方库。
所有结论都能用真实 MCP 字段复现。

三个前提，先摆明（不玩玄学）：

1. 积分商城返回「商品名 + 所需积分」，商品名里基本都带售价
   （例如「6.9元可乐麦炫酷」= 50 积分）→ 1 积分值多少钱可以直接算出来，
   而且是用麦当劳自己的标价算的，不是我们瞎猜的。

2. 抽奖接口**不返回中奖概率**，只返回奖品清单。
   → 所以本工具不编概率、不算「平均收益」，只算两件确定的事：
       保本线（花掉的积分如果拿去兑换值多少钱）
       上限  （奖池里最值钱那件值多少钱）
     只要「上限」打不过「兑换」，抽奖就没有理由。

3. 折扣券一律不估价。省多少钱取决于你点什么，估出来是骗人。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

# ---------------------------------------------------------------------- #
# 解析
# ---------------------------------------------------------------------- #

_YUAN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*元")
_POINT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*积分")
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

TAG_WIN = "赚"
TAG_LOSE = "亏"
TAG_UNKNOWN = "看用法"

KIND_CASH = "定值券"
KIND_DISCOUNT = "折扣券"
KIND_POINTS = "积分奖"


def guess_yuan(name: str) -> float | None:
    """从商品名里抠出金额：'6.9元可乐麦炫酷' -> 6.9。抠不到返回 None。"""
    m = _YUAN_RE.search(name or "")
    return float(m.group(1)) if m else None


def parse_date(text: str) -> datetime | None:
    try:
        return datetime.strptime((text or "").strip(), _DATE_FMT)
    except (ValueError, TypeError):
        return None


def to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------- #
# 积分商城 —— 全项目的价值锚
# ---------------------------------------------------------------------- #

@dataclass(frozen=True)
class RedeemItem:
    """积分商城里能用积分换的一件东西。"""

    name: str
    points: int
    yuan: float | None = None      # 这件东西值多少钱（从名字里读出来）
    cat: str = ""
    end_time: str = ""

    @property
    def yuan_per_point(self) -> float | None:
        """换这件东西，1 个积分能换来多少钱。"""
        if not self.yuan or self.points <= 0:
            return None
        return self.yuan / self.points


@dataclass(frozen=True)
class PointRate:
    """1 积分大概值多少钱 —— 由积分商城的可换商品算出来。"""

    median: float
    best: float
    worst: float
    best_item: str
    worst_item: str
    samples: int

    def text(self) -> str:
        return f"1 积分 ≈ {self.median:.4f} 元"


def point_rate(items: list[RedeemItem]) -> PointRate | None:
    """算出 1 积分值多少钱。取中位数当基准，避免被极端商品带跑。"""
    pairs = sorted((i.yuan_per_point, i.name) for i in items if i.yuan_per_point)
    if not pairs:
        return None
    rates = [r for r, _ in pairs]
    n = len(rates)
    mid = rates[n // 2] if n % 2 else (rates[n // 2 - 1] + rates[n // 2]) / 2.0
    return PointRate(
        median=mid,
        best=pairs[-1][0],
        worst=pairs[0][0],
        best_item=pairs[-1][1],
        worst_item=pairs[0][1],
        samples=n,
    )


def usable_items(items: list[RedeemItem], now: datetime | None = None) -> list[RedeemItem]:
    """只留现在真的能换的：有积分门槛、有标价、还在有效期内。"""
    now = now or datetime.now()
    out = []
    for it in items:
        if it.points <= 0 or not it.yuan:
            continue
        end = parse_date(it.end_time)
        if end and end < now:
            continue
        out.append(it)
    return out


# ---------------------------------------------------------------------- #
# 抽奖
# ---------------------------------------------------------------------- #

@dataclass(frozen=True)
class Lottery:
    """当前这场积分抽奖。"""

    name: str
    cost_points: int
    end_time: str = ""
    prizes: tuple[str, ...] = ()

    @property
    def prize_count(self) -> int:
        return len(self.prizes)


@dataclass
class PrizeRow:
    """奖池里的一件奖品，估完价之后的形态。"""

    name: str
    kind: str
    yuan: float | None
    tag: str

    @property
    def yuan_text(self) -> str:
        if self.yuan is None:
            return "省多少看你怎么点，没法估"
        return f"{self.yuan:.2f} 元"


def classify_prize(name: str, rate: PointRate, break_even: float) -> PrizeRow:
    """给一件奖品估价，并判断它值不值这一次的积分。

    顺序很重要：先看名字里有没有「X元」这种直接标价，
    再看是不是「X积分」这种积分奖，剩下的都当折扣券处理。
    """
    yuan = guess_yuan(name)
    if yuan is not None:
        kind = KIND_CASH
    else:
        m = _POINT_RE.search(name or "")
        if m:
            yuan = float(m.group(1)) * rate.median
            kind = KIND_POINTS
        else:
            kind = KIND_DISCOUNT
            yuan = None

    if yuan is None:
        tag = TAG_UNKNOWN
    elif yuan >= break_even:
        tag = TAG_WIN
    else:
        tag = TAG_LOSE
    return PrizeRow(name=name, kind=kind, yuan=yuan, tag=tag)


@dataclass
class Verdict:
    """抽一次亏不亏 —— 保本线 + 奖池逐件估价。"""

    cost_points: int
    rate: PointRate
    break_even: float
    rows: list[PrizeRow] = field(default_factory=list)
    points: float = 0.0

    @property
    def win(self) -> int:
        return sum(1 for r in self.rows if r.tag == TAG_WIN)

    @property
    def lose(self) -> int:
        return sum(1 for r in self.rows if r.tag == TAG_LOSE)

    @property
    def unknown(self) -> int:
        return sum(1 for r in self.rows if r.tag == TAG_UNKNOWN)

    @property
    def best_yuan(self) -> float | None:
        vals = [r.yuan for r in self.rows if r.yuan is not None]
        return max(vals) if vals else None

    @property
    def draws_affordable(self) -> int:
        return int(self.points // self.cost_points) if self.cost_points > 0 else 0


def evaluate(
    lottery: Lottery,
    redeem_items: list[RedeemItem],
    points: float,
    now: datetime | None = None,
) -> Verdict | None:
    """主计算：把所有东西拼成一份可读的结论。"""
    usable = usable_items(redeem_items, now)
    rate = point_rate(usable)
    if rate is None or lottery.cost_points <= 0:
        return None

    break_even = lottery.cost_points * rate.median
    rows = [classify_prize(n, rate, break_even) for n in lottery.prizes]
    # 能定价的排前面，金额从高到低；估不了价的（折扣券）排在最后
    rows.sort(key=lambda r: (r.yuan is None, -(r.yuan or 0.0)))

    return Verdict(
        cost_points=lottery.cost_points,
        rate=rate,
        break_even=break_even,
        rows=rows,
        points=points,
    )


# ---------------------------------------------------------------------- #
# 该抽还是该换
# ---------------------------------------------------------------------- #

@dataclass
class Advice:
    """同一笔积分，抽奖划算还是兑换划算。"""

    draw_best_rate: float | None   # 抽奖上限：最值钱的奖品 ÷ 一次消耗
    redeem_best_rate: float        # 兑换最好档
    winner: str                    # 抽 / 换 / 差不多
    reason: str


def compare(v: Verdict) -> Advice:
    """比一比：抽奖的「天花板」打不打得过兑换的「最好档」。

    用天花板对比是刻意的 —— 抽奖没有概率，
    但如果连天花板都输，那就没什么好犹豫的了。
    """
    redeem_best = v.rate.best
    draw_best = (v.best_yuan / v.cost_points) if v.best_yuan else None

    if draw_best is None or redeem_best <= 0:
        return Advice(
            draw_best_rate=draw_best,
            redeem_best_rate=redeem_best,
            winner="换",
            reason="奖池里没有能定价的奖品，没法比。稳妥起见，去兑换。",
        )

    ratio = draw_best / redeem_best
    if ratio >= 1.05:
        winner = "抽"
        reason = (
            f"抽奖上限 {draw_best:.4f} 元/分，高出兑换最好档 "
            f"{redeem_best:.4f} 元/分，能博一把。"
        )
    elif ratio <= 0.95:
        winner = "换"
        reason = (
            f"抽奖就算抽到最值钱的，也只有 {draw_best:.4f} 元/分，"
            f"还不如直接兑换的 {redeem_best:.4f} 元/分。"
        )
    else:
        winner = "差不多"
        reason = (
            f"抽奖上限 {draw_best:.4f} 元/分，和兑换最好档 "
            f"{redeem_best:.4f} 元/分基本持平。"
        )
    return Advice(draw_best, redeem_best, winner, reason)


# ---------------------------------------------------------------------- #
# 今天适合抽吗
# ---------------------------------------------------------------------- #

@dataclass
class Mood:
    headline: str          # 宜抽 / 不宜抽 / 随意
    lines: list[str] = field(default_factory=list)


def mood(v: Verdict, adv: Advice, account: dict, campaigns: list[str]) -> Mood:
    """把上面算出来的东西翻译成一句人话。"""
    lines: list[str] = []

    if v.points < v.cost_points:
        lines.append(f"积分只有 {v.points:g}，不够抽一次（要 {v.cost_points}），先去攒分吧。")
    else:
        lines.append(f"积分 {v.points:g}，够抽 {v.draws_affordable} 次。")

    expiring = to_float(account.get("expiring"))
    if expiring > 0:
        lines.append(f"注意有 {expiring:g} 积分即将过期，过期就白扔了，优先花掉。")

    if campaigns:
        lines.append(f"今天有 {len(campaigns)} 项活动在跑，但不影响上面的比价结论。")

    lines.append(adv.reason)

    headline = {"抽": "宜抽", "换": "不宜抽"}.get(adv.winner, "随意")
    return Mood(headline=headline, lines=lines)


# ---------------------------------------------------------------------- #
# 把 MCP 原样响应转成上面这些结构
# live 模式和内置样例共用同一套转换 —— 两边跑出来必须一模一样
# ---------------------------------------------------------------------- #

def account_from_raw(raw) -> dict:
    """积分账户：接口外层是 {"data":{...}}，字段是 camelCase。"""
    d = raw if isinstance(raw, dict) else {}
    if isinstance(d.get("data"), dict):
        d = d["data"]
    return {
        "available": to_float(d.get("availablePoint")),
        "accumulative": to_float(d.get("accumulativePoint")),
        "expired": to_float(d.get("expiredPoint")),
        "expiring": to_float(d.get("currentMouthExpirePoint")),
        "used": to_float(d.get("usedPoint")),
    }


def redeem_items(rows) -> list[RedeemItem]:
    """积分商城商品数组 → RedeemItem。只要 status=2（上架）的。"""
    if not isinstance(rows, list):
        return []
    out = []
    for it in rows:
        if not isinstance(it, dict):
            continue
        if str(it.get("status", "")) != "2":
            continue
        name = str(it.get("spuName", ""))
        out.append(
            RedeemItem(
                name=name,
                points=int(to_float(it.get("point"))),
                yuan=guess_yuan(name),
                cat=str(it.get("catName", "")),
                end_time=str(it.get("downTime", "")),
            )
        )
    return out


def lottery_from_raw(raw) -> Lottery | None:
    """抽奖活动：拿不到 activityName 就当没取到。"""
    if not isinstance(raw, dict):
        return None
    d = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    if not isinstance(d, dict) or not d.get("activityName"):
        return None
    prizes = tuple(
        str(p.get("name", "")) for p in (d.get("prizes") or []) if isinstance(p, dict)
    )
    return Lottery(
        name=str(d.get("activityName", "")),
        cost_points=int(to_float(d.get("drawPoint"))),
        end_time=str(d.get("endTime", "")),
        prizes=prizes,
    )
