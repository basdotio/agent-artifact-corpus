#!/usr/bin/env python3
"""Numerical tests of fills.py on bars typed by hand: entry 100.00, fee 5 + half-spread 1 per fill."""
from __future__ import annotations

import json, os, subprocess, sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import _kit as k
import fills

T0, COSTS = 1704205800, {"fee_bp_per_fill": 5, "half_spread_bp_per_fill": 1, "source": "test"}   # 2024-01-02T14:30Z
QUIET = (100.0, 100.05, 99.95, 100.0)


def bars(rows, skip=()):
    """One-minute Bars from (open, high, low, close) rows; bar i is stamped T0 + 60 i; indices in `skip` are absent."""
    b = k.Bars(60)
    for i, (o, h, l, c) in enumerate(rows):
        if i not in skip:
            b.ts.append(T0 + 60 * i); b.open.append(o); b.high.append(h); b.low.append(l); b.close.append(c); b.volume.append(1.0)
    return b


def near(a, b, tol=1e-9):
    return abs(a - b) <= tol


def one(second, side=1, stop=None, target=None, exit_open=100.5):
    """Entry at bar 0 (open 100), `second` is bar 1, a quiet bar 2, time exit at the open of bar 3."""
    return fills.simulate(bars([QUIET, second, QUIET, (exit_open, exit_open + 0.1, exit_open - 0.1, exit_open)]), 0, side, 180, stop, target)


def check(trade, reason, px, gross, exit_ts):
    assert trade["exit_reason"] == reason and near(trade["exit_px"], px) and near(trade["gross_bp"], gross), trade
    assert trade["entry_px"] == 100.0 and trade["entry_ts"] == T0 and trade["exit_ts"] == exit_ts, trade


def test_simulate():
    check(one(QUIET), "time", 100.5, 50.0, T0 + 180)
    check(one(QUIET, side=-1), "time", 100.5, -50.0, T0 + 180)
    # long: target 100 bp = 101.00, stop 50 bp = 99.50; an exit inside bar 1 is stamped at the end of bar 1
    check(one((100.0, 101.2, 100.1, 101.1), target=100), "target", 101.0, 100.0, T0 + 120)
    check(one((100.0, 101.0, 100.1, 100.9), target=100), "time", 100.5, 50.0, T0 + 180)        # a touch is not a fill
    check(one((100.0, 100.1, 99.2, 99.3), stop=50), "stop", 99.3, -70.0, T0 + 120)
    check(one((100.0, 100.1, 99.4, 99.8), stop=50), "stop", 99.5, -50.0, T0 + 120)
    check(one((100.0, 100.1, 99.5, 99.9), stop=50), "stop", 99.5, -50.0, T0 + 120)             # a touch of the stop fills
    check(one((99.0, 99.3, 98.9, 99.2), stop=50), "stop_gap", 99.0, -100.0, T0 + 60)
    check(one((100.0, 101.2, 99.4, 100.9), stop=50, target=100), "tie", 99.5, -50.0, T0 + 120)
    check(one((100.0, 101.2, 100.1, 101.1), stop=50, target=100), "target", 101.0, 100.0, T0 + 120)
    check(one((100.0, 100.4, 99.8, 100.2), stop=50, target=100), "time", 100.5, 50.0, T0 + 180)
    # short mirror: stop 100.50, target 99.00
    check(one((100.0, 100.8, 99.9, 100.7), side=-1, stop=50), "stop", 100.7, -70.0, T0 + 120)
    check(one((100.0, 100.6, 99.9, 100.2), side=-1, stop=50), "stop", 100.5, -50.0, T0 + 120)
    check(one((101.0, 101.1, 100.8, 100.9), side=-1, stop=50), "stop_gap", 101.0, -100.0, T0 + 60)
    check(one((100.0, 100.6, 98.8, 99.1), side=-1, stop=50, target=100), "tie", 100.5, -50.0, T0 + 120)
    check(one((100.0, 100.1, 98.8, 98.9), side=-1, target=100), "target", 99.0, 100.0, T0 + 120)
    check(one((100.0, 100.1, 99.0, 99.2), side=-1, target=100), "time", 100.5, -50.0, T0 + 180)  # touch only
    # the entry bar is scanned for stop and target, but the gap rule starts at the next bar
    b = bars([(100.0, 100.1, 99.4, 99.9), QUIET, QUIET, QUIET])
    check(fills.simulate(b, 0, 1, 180, 50, None), "stop", 99.5, -50.0, T0 + 60)
    b = bars([(99.0, 100.3, 98.9, 100.0), QUIET, QUIET, QUIET])        # entry 99.00, stop 98.505: low 98.9 holds
    assert fills.simulate(b, 0, 1, 180, 50, None)["exit_reason"] == "time"
    # the exit bar itself is never scanned; a bar missing inside the scan is skipped; a missing exit bar drops the trade
    b = bars([QUIET, QUIET, QUIET, (100.5, 102.0, 98.0, 100.0)])
    check(fills.simulate(b, 0, 1, 180, 50, 100), "time", 100.5, 50.0, T0 + 180)
    b = bars([QUIET, (100.0, 101.5, 100.0, 101.4), QUIET, (100.5, 100.6, 100.4, 100.5)], skip={1})
    check(fills.simulate(b, 0, 1, 180, None, 100), "time", 100.5, 50.0, T0 + 180)
    b = bars([QUIET, QUIET, QUIET, QUIET, QUIET], skip={3})
    assert fills.simulate(b, 0, 1, 180) is None and fills.simulate.reason == "exit bar missing"
    assert fills.simulate(b, 0, 1, 240)["exit_ts"] == T0 + 240 and fills.simulate(b, 3, 1, 600) is None


def test_build_trades():
    assert fills.round_trip_cost_bp(5, 1) == 12 and fills.round_trip_cost_bp(5, 1, 0.5) == 6 and fills.round_trip_cost_bp(5, 1, 2) == 24
    rows = [QUIET] * 3 + [(100.5, 100.6, 100.4, 100.5)] + [QUIET] * 6
    b, cell = bars(rows), {"index": 4, "pset": 0, "hold_minutes": 3, "stop_bp": None, "target_bp": None, "params": {}}
    ev = lambda i, side=1: {"pset": 0, "segment": "dev", "day": "2024-01-02", "decision_ts": T0 + 60 * i, "entry_ts": T0 + 60 * i, "side": side}
    trades, counts = fills.build_trades(b, [ev(0)], cell, COSTS)
    assert counts == {"skipped_overlap": 0, "dropped_missing_exit": 0, "dropped_missing_entry": 0}
    t = trades[0]
    assert list(t) == fills.TRADE_COLUMNS and t["cell"] == 4 and t["day"] == "2024-01-02" and t["side"] == 1
    assert near(t["gross_bp"], 50.0) and t["cost_bp"] == 12.0 and near(t["net_bp"], 38.0) and t["exit_reason"] == "time"
    t = fills.build_trades(b, [ev(0, -1)], cell, COSTS)[0][0]
    assert near(t["gross_bp"], -50.0) and near(t["net_bp"], -62.0) and t["side"] == -1
    for tier, cost in ((0.5, 6.0), (2.0, 24.0)):
        t = fills.build_trades(b, [ev(0)], cell, COSTS, tier)[0][0]
        assert t["cost_bp"] == cost and near(t["net_bp"], 50.0 - cost)
    assert fills.build_trades(b, [ev(0)], cell, 12.0, label="raw")[0][0]["cell"] == "raw"
    # two events inside one hold: one trade; an event at the exact exit time is taken (given in any order)
    trades, counts = fills.build_trades(b, [ev(3), ev(1), ev(0)], cell, COSTS)
    assert [x["entry_ts"] for x in trades] == [T0, T0 + 180] and counts["skipped_overlap"] == 1
    assert near(trades[1]["gross_bp"], (100.0 / 100.5 - 1) * 1e4) and near(k.day_sums(trades)[1][0], 50.0 - 49.75124378109453 - 24.0, 1e-6)
    # missing exit bar: dropped and counted, and the position is free for the next event
    b2 = bars(rows, skip={3})
    trades, counts = fills.build_trades(b2, [ev(0), ev(1)], cell, COSTS)
    assert counts["dropped_missing_exit"] == 1 and [x["entry_ts"] for x in trades] == [T0 + 60]
    assert fills.build_trades(b2, [ev(3)], cell, COSTS) == ([], {"skipped_overlap": 0, "dropped_missing_exit": 0, "dropped_missing_entry": 1})
    # stop charged like any other trade; after a stop inside bar 1 an event at bar 2 is free to enter
    rows = [QUIET, (100.0, 100.1, 99.2, 99.3), QUIET, QUIET, QUIET, QUIET, QUIET]
    stopped = dict(cell, stop_bp=50, target_bp=100)
    trades, counts = fills.build_trades(bars(rows), [ev(0), ev(1), ev(2)], stopped, COSTS)
    assert [(x["exit_reason"], x["entry_ts"]) for x in trades] == [("stop", T0), ("time", T0 + 120)] and counts["skipped_overlap"] == 1
    assert near(trades[0]["gross_bp"], -70.0) and near(trades[0]["net_bp"], -82.0)
    raw = fills.build_trades(bars(rows), [ev(0)], stopped, COSTS, time_exit_only=True)[0][0]
    assert raw["exit_reason"] == "time" and near(raw["gross_bp"], 0.0) and near(raw["net_bp"], -12.0)


def test_cli():
    def run(*args):
        r = subprocess.run([sys.executable, "-B", os.path.join(os.path.dirname(HERE), "fills.py"), *args], capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr
    code, out, _ = run("--fee-bp", "5", "--half-spread-bp", "1", "--stop-bp", "50", "--gross-bp", "7.5")
    assert code == 0 and "6.00 bp" in out and "12.00 bp" in out and "0.24 R" in out and "-4.50 bp" in out and "7.50 bp" in out
    assert out.splitlines()[-2].startswith("RESULT: ") and out.splitlines()[-1].startswith("NEXT: ")
    code, out, _ = run("--fee-bp", "5", "--half-spread-bp", "1", "--stop-bp", "30", "--gross-bp", "7.5", "--json")
    doc = json.loads(out)
    assert code == 0 and doc["cost_per_fill_bp"] == 6 and doc["round_trip_bp"] == 12 and near(doc["cost_in_R"], 0.4)
    assert doc["net_bp"] == -4.5 and doc["break_even_cost_bp"] == 7.5 and doc["round_trip_by_tier_bp"] == {"0.5": 6, "1.0": 12, "2.0": 24}
    for args in (("--fee-bp", "-1", "--half-spread-bp", "1"), ("--fee-bp", "5", "--half-spread-bp", "-0.5"),
                 ("--fee-bp", "nan", "--half-spread-bp", "1"), ("--fee-bp", "5", "--half-spread-bp", "1", "--stop-bp", "0"), ("--fee-bp", "5")):
        code, out, err = run(*args)
        assert code == 2 and "Traceback" not in err and out == "", (args, code, err)
    assert run("--fee-bp", "-1", "--half-spread-bp", "1")[2].splitlines()[0].startswith("ERROR: ")
    assert run("--help")[0] == 0


def main():
    test_simulate()
    test_build_trades()
    test_cli()


if __name__ == "__main__":
    main()
    print("test_fills: all assertions passed")
