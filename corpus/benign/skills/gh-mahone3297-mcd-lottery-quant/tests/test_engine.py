# -*- coding: utf-8 -*-
"""引擎单测 —— 全部用真实抓下来的样例数据，不联网、不花钱。

跑法：
    python tests/test_engine.py
"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcd_quant import client, engine, live, report, sample

import run  # 仓库根目录的入口，sys.path 上面已插好

# 样例数据抓取当天，固定住，测试才能复现
NOW = datetime(2026, 10, 9, 15, 0, 0)


class TestParse(unittest.TestCase):
    def test_guess_yuan(self):
        self.assertEqual(engine.guess_yuan("6.9元可乐麦炫酷"), 6.9)
        self.assertEqual(engine.guess_yuan("下单立减3元券"), 3.0)
        self.assertEqual(engine.guess_yuan("22.9元2份麦辣鸡腿堡"), 22.9)

    def test_guess_yuan_none(self):
        # 折扣券、积分奖、纯文字 —— 都不该抠出金额
        self.assertIsNone(engine.guess_yuan("麦旋风5折券"))
        self.assertIsNone(engine.guess_yuan("30积分"))
        self.assertIsNone(engine.guess_yuan("麦麦脆汁鸡两件套"))
        self.assertIsNone(engine.guess_yuan(""))


class TestRedeem(unittest.TestCase):
    def setUp(self):
        self.items = engine.redeem_items(sample.MALL)

    def test_build_from_raw(self):
        self.assertEqual(len(self.items), len(sample.MALL))
        fifty = [i for i in self.items if i.points == 50]
        self.assertEqual(len(fifty), 4)

    def test_usable_filters_out_expired_and_unpriced(self):
        usable = engine.usable_items(self.items, NOW)
        names = {i.name for i in usable}
        self.assertIn("6.9元可乐麦炫酷", names)
        # 2026-06-24 就下架了
        self.assertNotIn("5.9元香芋派/菠萝派任选", names)
        # 积分门槛是 0（这些是花钱买的派对），不是积分兑换
        self.assertNotIn("麦当劳亲子读书会", names)
        # 实物奖品没标价，算不出每积分值多少
        self.assertNotIn("罗技键鼠套装", names)

    def test_point_rate(self):
        rate = engine.point_rate(engine.usable_items(self.items, NOW))
        self.assertIsNotNone(rate)
        self.assertEqual(rate.samples, 7)
        self.assertAlmostEqual(rate.median, 0.0545, places=4)
        self.assertAlmostEqual(rate.best, 0.138, places=4)
        self.assertEqual(rate.best_item, "6.9元香芋派/菠萝派任选")

    def test_point_rate_empty(self):
        self.assertIsNone(engine.point_rate([]))


class TestPrizeClassify(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        items = engine.redeem_items(sample.MALL)
        cls.rate = engine.point_rate(engine.usable_items(items, NOW))
        cls.break_even = 24 * cls.rate.median  # 1.308

    def test_cash_prize_wins(self):
        row = engine.classify_prize("下单立减3元券", self.rate, self.break_even)
        self.assertEqual(row.kind, engine.KIND_CASH)
        self.assertEqual(row.tag, engine.TAG_WIN)

    def test_cash_prize_loses(self):
        row = engine.classify_prize("下单立减1元券", self.rate, self.break_even)
        self.assertEqual(row.kind, engine.KIND_CASH)
        self.assertEqual(row.tag, engine.TAG_LOSE)

    def test_points_prize(self):
        row = engine.classify_prize("30积分", self.rate, self.break_even)
        self.assertEqual(row.kind, engine.KIND_POINTS)
        self.assertAlmostEqual(row.yuan, 30 * self.rate.median, places=6)

    def test_discount_prize_never_priced(self):
        row = engine.classify_prize("麦旋风5折券", self.rate, self.break_even)
        self.assertEqual(row.kind, engine.KIND_DISCOUNT)
        self.assertIsNone(row.yuan)
        self.assertEqual(row.tag, engine.TAG_UNKNOWN)


class TestVerdict(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lottery = engine.lottery_from_raw(sample.LOTTERY)
        cls.redeem = engine.redeem_items(sample.MALL)
        cls.account = engine.account_from_raw(sample.ACCOUNT)
        cls.v = engine.evaluate(cls.lottery, cls.redeem, cls.account["available"], now=NOW)

    def test_lottery_from_raw(self):
        self.assertEqual(self.lottery.name, "麦麦积分抽奖")
        self.assertEqual(self.lottery.cost_points, 24)
        self.assertEqual(self.lottery.prize_count, 10)

    def test_account_from_raw(self):
        self.assertEqual(self.account["available"], 0)
        self.assertAlmostEqual(self.account["accumulative"], 267.1, places=1)
        self.assertAlmostEqual(self.account["expired"], 267.1, places=1)

    def test_break_even(self):
        self.assertAlmostEqual(self.v.break_even, 24 * 0.0545, places=4)

    def test_counts(self):
        self.assertEqual(self.v.win, 3)      # 3元券、2元券、30积分
        self.assertEqual(self.v.lose, 1)     # 1元券
        self.assertEqual(self.v.unknown, 6)  # 6 张折扣券
        self.assertEqual(len(self.v.rows), 10)

    def test_best_is_capped_by_cash_coupon(self):
        self.assertAlmostEqual(self.v.best_yuan, 3.0, places=6)

    def test_rows_sorted_priced_first(self):
        priced = [r for r in self.v.rows if r.yuan is not None]
        self.assertEqual(priced, sorted(priced, key=lambda r: -r.yuan))
        self.assertTrue(all(r.yuan is None for r in self.v.rows[len(priced):]))

    def test_not_enough_points(self):
        self.assertEqual(self.v.draws_affordable, 0)

    def test_evaluate_degrades_on_empty_mall(self):
        self.assertIsNone(engine.evaluate(self.lottery, [], 100, now=NOW))


class TestAdvice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lottery = engine.lottery_from_raw(sample.LOTTERY)
        redeem = engine.redeem_items(sample.MALL)
        cls.v = engine.evaluate(lottery, redeem, 0, now=NOW)
        cls.adv = engine.compare(cls.v)

    def test_draw_ceiling(self):
        # 最值钱的是 3 元券 → 3 / 24 = 0.125 元/分
        self.assertAlmostEqual(self.adv.draw_best_rate, 0.125, places=6)

    def test_redeem_ceiling(self):
        self.assertAlmostEqual(self.adv.redeem_best_rate, 0.138, places=4)

    def test_winner_is_redeem(self):
        self.assertEqual(self.adv.winner, "换")

    def test_mood_headline(self):
        m = engine.mood(self.v, self.adv, engine.account_from_raw(sample.ACCOUNT), sample.CAMPAIGNS_TODAY)
        self.assertEqual(m.headline, "不宜抽")
        self.assertTrue(any("不够" in ln for ln in m.lines))


class TestReport(unittest.TestCase):
    def test_render_contains_key_sections(self):
        snap = _snapshot()
        text = report.render(snap)
        for expected in [
            "积分抽奖量化占卜",
            "1 积分到底值多少钱",
            "抽一次，亏不亏",
            "该抽，还是该换",
            "我的积分",
            "今天适合抽吗",
            "不公开中奖概率",
            "全程只读",
        ]:
            self.assertIn(expected, text)

    def test_render_lists_every_prize(self):
        text = report.render(_snapshot())
        for name in sample.LOTTERY["prizes"]:
            self.assertIn(name["name"], text)

    def test_no_ascii_emoji_leak(self):
        # 纯中文报告，别混进 emoji
        text = report.render(_snapshot())
        self.assertNotIn("🔮", text)


def _snapshot() -> report.Snapshot:
    lottery = engine.lottery_from_raw(sample.LOTTERY)
    redeem = engine.redeem_items(sample.MALL)
    account = engine.account_from_raw(sample.ACCOUNT)
    v = engine.evaluate(lottery, redeem, account["available"], now=NOW)
    adv = engine.compare(v)
    m = engine.mood(v, adv, account, sample.CAMPAIGNS_TODAY)
    return report.Snapshot(
        day="2026-10-09",
        source="sample",
        lottery=lottery,
        verdict=v,
        advice=adv,
        mood=m,
        account=account,
        campaigns=list(sample.CAMPAIGNS_TODAY),
        my_prizes=[],
        redeem=redeem,
    )


class TestSafety(unittest.TestCase):
    """合规底线：这个项目永远不碰会花钱的接口。"""

    BANNED = {"draw-lottery", "create-order", "mall-create-order", "party-order-create"}

    def test_whitelist_excludes_money_spending(self):
        self.assertEqual(self.BANNED & set(live.READ_ONLY_TOOLS), set())

    def test_every_call_is_in_whitelist(self):
        used = {tool for _, tool, _ in live._CALLS}
        self.assertTrue(used <= set(live.READ_ONLY_TOOLS))

    def test_no_call_looks_like_a_purchase(self):
        for _, tool, _ in live._CALLS:
            self.assertNotIn("create", tool)
            self.assertNotIn("draw", tool)


class TestResponseParsing(unittest.TestCase):
    """真实响应外面包了一层给人看的 Markdown 说明，解析必须能穿透。

    这是踩过的坑：直接 json.loads 会失败，然后整份报告降级成样例数据。
    """

    WRAPPED = """# API Response Information

Below is the response from an API call. To help you understand the data, I've provided:

1. A detailed description of all fields in the response structure
2. The complete API response

## Response Structure

- **data**: 抽奖活动信息
  - **data.drawPoint**: 单次所需积分 (Type: string)

## Original Response

{"success":true,"code":200,"data":{"activityName":"麦麦积分抽奖","drawPoint":"24","prizes":[{"name":"30积分"}]}}
"""

    def test_unwraps_original_response(self):
        got = client.extract_json(self.WRAPPED)
        self.assertIsInstance(got, dict)
        self.assertEqual(got["data"]["drawPoint"], "24")

    def test_plain_json_passthrough(self):
        self.assertEqual(client.extract_json('{"a": 1}'), {"a": 1})

    def test_fenced_json(self):
        self.assertEqual(client.extract_json('说明\n```json\n{"a": 2}\n```\n尾巴'), {"a": 2})

    def test_markdown_returns_as_text(self):
        md = "### 当前时间：2026-10-09\n#### 2026年10月9日 今日\n-   **活动标题**：测试活动\n"
        self.assertEqual(client.extract_json(md), md.strip())

    def test_content_blocks(self):
        got = client.extract_json({"content": [{"type": "text", "text": self.WRAPPED}]})
        self.assertEqual(got["data"]["activityName"], "麦麦积分抽奖")

    def test_braces_inside_strings_do_not_break_scan(self):
        text = '## Original Response\n\n{"note":"用 {花括号} 试试","n":1}'
        self.assertEqual(client.extract_json(text)["n"], 1)

    def test_scan_skips_array_before_object(self):
        text = '## Original Response\n\n[1, 2]\n{"n": 9}'
        self.assertEqual(client.extract_json(text), [1, 2])


class TestCampaignParsing(unittest.TestCase):
    MD = """### 当前时间：2026-10-09 15:50:28

### 活动列表：

#### 2026年10月8日 往期回顾

-   **活动标题**：昨天的活动
    **活动内容介绍**：xxx

#### 2026年10月9日 今日

-   **活动标题**：今天的活动一
    **活动内容介绍**：yyy

-   **活动标题**：今天的活动二
    **活动内容介绍**：zzz

#### 2026年10月10日

-   **活动标题**：明天的活动
    **活动内容介绍**：www
"""

    def test_picks_today_only(self):
        self.assertEqual(live.campaigns_today(self.MD), ["今天的活动一", "今天的活动二"])

    def test_empty_input(self):
        self.assertEqual(live.campaigns_today(None), [])
        self.assertEqual(live.campaigns_today(""), [])


class TestTokenResolution(unittest.TestCase):
    """Token 取值的容错。

    踩过的坑：Windows 上 `set MCD_MCP_TOKEN="abc"` 会把引号一起存进去，
    PowerShell / Git Bash 里的 `set X=Y` 则根本不设置环境变量（不报错，静默失败）。
    这里保证「引号/空格/换行」都不会把好 Token 弄丢。
    """

    def setUp(self):
        self._saved = os.environ.get("MCD_MCP_TOKEN")
        os.environ.pop("MCD_MCP_TOKEN", None)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("MCD_MCP_TOKEN", None)
        else:
            os.environ["MCD_MCP_TOKEN"] = self._saved

    def test_cli_wins_over_env(self):
        os.environ["MCD_MCP_TOKEN"] = "from-env"
        self.assertEqual(run.resolve_token("from-cli"), "from-cli")

    def test_reads_env_when_cli_missing(self):
        os.environ["MCD_MCP_TOKEN"] = "from-env"
        self.assertEqual(run.resolve_token(None), "from-env")

    def test_strips_quotes_whitespace_and_newline(self):
        for raw in ('  "abc123"  ', "'abc123'", "abc123\r\n", ' "abc123" '):
            self.assertEqual(run.resolve_token(raw), "abc123", raw)

    def test_empty_cases_return_empty(self):
        for raw in (None, "", "   ", '""', "''", "\n"):
            self.assertEqual(run.resolve_token(raw), "", repr(raw))

    def test_powershell_style_set_does_not_leak(self):
        """PowerShell/Git Bash 的 `set X=Y` 不设环境变量 —— 取到就是空，不能瞎猜。"""
        self.assertEqual(run.resolve_token(None), "")

    def test_help_mentions_missing_env(self):
        text = run.token_help()
        self.assertIn("没有设置", text)
        self.assertIn("PowerShell", text)

    def test_help_mentions_blank_env(self):
        os.environ["MCD_MCP_TOKEN"] = "   "
        self.assertIn("值是空的", run.token_help())

    def test_cli_without_token_exits_2_and_hints(self):
        import contextlib
        import io

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = run.main(["--live"])
        self.assertEqual(code, 2)
        self.assertIn("--token", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
