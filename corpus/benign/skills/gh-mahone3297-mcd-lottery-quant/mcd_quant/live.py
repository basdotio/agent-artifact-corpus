# -*- coding: utf-8 -*-
"""连真实麦当劳 MCP，把需要的几样数据抓回来。

**只调用只读工具** —— 这份清单是硬约束，任何时候都不往里加会花钱的接口：

    draw-lottery         抽奖（花积分）
    create-order         下单（花钱）
    mall-create-order    积分商城下单
    party-order-create   派对下单

单个工具失败只会让那一段降级（用内置样例顶上），不会整盘崩。
"""

from __future__ import annotations

import re

from .client import McdMcpClient

# 只读工具白名单。要改这个元组，先在 tests 里过一遍合规检查。
READ_ONLY_TOOLS = (
    "query-lottery-info",
    "query-my-account",
    "query-my-prizes",
    "mall-points-products",
    "campaign-calendar",
)

_CALLS = (
    ("lottery", "query-lottery-info", {}),
    ("account", "query-my-account", {}),
    ("prizes", "query-my-prizes", {"pageNum": "1", "pageSize": "50"}),
    ("mall", "mall-points-products", {}),
    ("campaigns", "campaign-calendar", {}),
)


def fetch(token: str) -> tuple[dict, dict]:
    """抓齐数据。返回 (数据字典, 错误字典)。"""
    client = McdMcpClient(token)
    client.initialize()
    raw: dict = {}
    errors: dict = {}
    for key, tool, args in _CALLS:
        try:
            raw[key] = client.call_tool_json(tool, args)
        except Exception as exc:  # 单个工具失败 → 降级，不中断
            raw[key] = None
            errors[tool] = str(exc)
    return raw, errors


def list_tools(token: str) -> list[dict]:
    """列出服务端提供哪些工具（排查用）。"""
    client = McdMcpClient(token)
    client.initialize()
    return client.list_tools()


# ---------------------------------------------------------------------- #
# 活动日历返回的是 Markdown，不是 JSON，得单独拆
# ---------------------------------------------------------------------- #

_TODAY_RE = re.compile(r"^#+\s*\d{4}年\d{1,2}月\d{1,2}日\s*今日\s*$", re.M)
_TITLE_RE = re.compile(r"\*\*活动标题\*\*[：:]\s*(.+)")
_NEXT_SEC_RE = re.compile(r"^#{2,4}\s", re.M)


def campaigns_today(raw, day: str = "") -> list[str]:
    """从活动日历的 Markdown 里，挑出「今天」那一节的活动标题。"""
    if isinstance(raw, dict):
        raw = raw.get("text") or raw.get("data") or ""
    if not isinstance(raw, str) or not raw:
        return []

    m = _TODAY_RE.search(raw)
    chunk = raw[m.end():] if m else raw
    nxt = _NEXT_SEC_RE.search(chunk)
    if nxt:
        chunk = chunk[:nxt.start()]
    return [t.strip() for t in _TITLE_RE.findall(chunk)]
