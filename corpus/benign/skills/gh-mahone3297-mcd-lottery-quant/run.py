# -*- coding: utf-8 -*-
"""积分抽奖量化占卜 —— 命令行入口。

    python run.py                         用内置样例数据出报告（不用 Token，不联网）
    python run.py --live                  连真实麦当劳 MCP（需环境变量 MCD_MCP_TOKEN）
    python run.py --json                  输出 JSON，方便给网页或脚本用
    python run.py --tools                 列出 MCP 服务端有哪些工具（排查用）

报告全程只读：不会替你抽奖，也不会替你下单。
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from datetime import date, datetime

from mcd_quant import engine, live, report, sample
from mcd_quant.client import McpError


def _inner_list(raw):
    """MCP 响应的外层是 {"success":..,"data":[..]}，这里把数组掏出来。"""
    if isinstance(raw, dict) and isinstance(raw.get("data"), list):
        return raw["data"]
    if isinstance(raw, list):
        return raw
    return []


def _prizes_of(raw) -> list[dict]:
    if isinstance(raw, dict):
        d = raw.get("data")
        if isinstance(d, dict):
            return [p for p in (d.get("prizes") or []) if isinstance(p, dict)]
    return []


def _snapshot_dict(snap: report.Snapshot) -> dict:
    """给 JSON 输出用。dataclasses.asdict 拿不到 @property，这里补全统计字段。"""
    d = dataclasses.asdict(snap)
    v = snap.verdict
    d["verdict"].update({
        "prize_count": len(v.rows),
        "win": v.win,
        "lose": v.lose,
        "unknown": v.unknown,
        "best_yuan": v.best_yuan,
        "draws_affordable": v.draws_affordable,
    })
    return d


def build(source: str, token: str, day: str) -> report.Snapshot:
    """收集数据 → 算 → 拼成一份可以渲染的报告。"""
    errors: dict = {}

    if source == "live":
        raw, errors = live.fetch(token)
        lottery = engine.lottery_from_raw(raw.get("lottery"))
        redeem = engine.redeem_items(_inner_list(raw.get("mall")))
        account = engine.account_from_raw(raw.get("account"))
        campaigns = live.campaigns_today(raw.get("campaigns"), day)
        prizes = _prizes_of(raw.get("prizes"))
    else:
        lottery = engine.lottery_from_raw(sample.LOTTERY)
        redeem = engine.redeem_items(sample.MALL)
        account = engine.account_from_raw(sample.ACCOUNT)
        campaigns = list(sample.CAMPAIGNS_TODAY)
        prizes = list(sample.MY_PRIZES)

    if lottery is None or lottery.cost_points <= 0:
        raise McpError("没拿到可用的抽奖活动信息，无法继续。")

    verdict = engine.evaluate(lottery, redeem, account.get("available", 0.0))
    if verdict is None:
        raise McpError("积分商城没有可用的兑换数据，算不出「1 积分值多少钱」。")

    advice = engine.compare(verdict)
    mood = engine.mood(verdict, advice, account, campaigns)

    return report.Snapshot(
        day=day,
        source=source,
        lottery=lottery,
        verdict=verdict,
        advice=advice,
        mood=mood,
        account=account,
        campaigns=campaigns,
        my_prizes=prizes,
        redeem=redeem,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        errors=errors,
    )


def resolve_token(cli_token) -> str:
    """按「命令行 --token → 环境变量 MCD_MCP_TOKEN」的顺序取，剥掉手滑带的引号/空格。

    Windows 上 `set MCD_MCP_TOKEN="abc"` 会把引号一起塞进值里，所以这里统一剥一层。
    """
    raw = cli_token if cli_token is not None else os.environ.get("MCD_MCP_TOKEN", "")
    return (raw or "").strip().strip('"').strip("'").strip()


def token_help() -> str:
    """没拿到 Token 时，把「我看到了什么 + 你该敲什么」一次讲清。"""
    if "MCD_MCP_TOKEN" not in os.environ:
        seen = "环境变量 MCD_MCP_TOKEN —— 没有设置"
    elif not (os.environ.get("MCD_MCP_TOKEN") or "").strip():
        seen = "环境变量 MCD_MCP_TOKEN —— 设置了，但值是空的"
    else:
        seen = "环境变量 MCD_MCP_TOKEN —— 有值，但剥掉引号/空格后是空的"

    return f"""[出错] 没拿到 MCP Token，连不上真实的麦当劳 MCP。

  我实际看到的：
    · {seen}
    · 命令行 --token —— 没有传

  下面三条选一条（把「你的Token」换成你自己的）：

    cmd.exe             set MCD_MCP_TOKEN=你的Token
    PowerShell          $env:MCD_MCP_TOKEN="你的Token"
    Git Bash / macOS    export MCD_MCP_TOKEN=你的Token

  最省事的办法 —— 直接把 Token 写在命令行上，跟当前是哪个 shell 无关：

    python run.py --live --token 你的Token

  两个高频坑：
    1) PowerShell 和 Git Bash 里的 `set MCD_MCP_TOKEN=xxx` 不会设置环境变量
       （只有 cmd.exe 认这个写法）。它就静静地把这行吃掉，不报错，
       看着像设置成功了，其实什么都没发生 —— 多半就是这个原因。
    2) cmd 里等号两边不能有空格（会变成名字带空格的变量）；
       值也不用加引号，加了会被当成 Token 的一部分。
"""


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="run.py",
        description="积分抽奖量化占卜：算清 1 积分值多少钱、抽一次亏不亏、该抽还是该换。",
    )
    parser.add_argument("--live", action="store_true", help="连真实麦当劳 MCP（需 MCD_MCP_TOKEN）")
    parser.add_argument("--token", default=None, help="MCP Token；不给就读环境变量 MCD_MCP_TOKEN")
    parser.add_argument("--date", default=date.today().isoformat(), help="报告日期 YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--tools", action="store_true", help="列出服务端有哪些 MCP 工具")
    args = parser.parse_args(argv)

    token = resolve_token(args.token)
    if (args.live or args.tools) and not token:
        print(token_help(), file=sys.stderr)
        return 2

    try:
        if args.tools:
            for tool in live.list_tools(token):
                print(f"- {tool.get('name')}: {(tool.get('description') or '')[:60]}")
            return 0

        snap = build("live" if args.live else "sample", token, args.date)

        if args.json:
            print(json.dumps(_snapshot_dict(snap), ensure_ascii=False, indent=2))
        else:
            print(report.render(snap))
        return 0
    except McpError as exc:
        print(f"[出错] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
