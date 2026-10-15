#!/usr/bin/env python3
"""Numerical tests of sweep.py: a three-cell grid typed by hand, the no-trade cell, the grid null on planted and
no-effect series, the refusal paths, and the out-of-sample look that can be taken once."""
from __future__ import annotations

import json, os, shutil, sys, tempfile, types

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import _kit as k
import effect, fills, sweep, synth
import test_effect as fx
from test_effect import DAY0, near, run, result

# Three days of 5-minute bars from 13:00 UTC; entry at bar 4 (open 100.00), exits 1, 2 and 3 bars later.
TYPED = [[99.8, 100.1, 99.9, 100.2, 100.0, 100.10, 100.30, 100.20, 100.0, 99.9, 100.1, 100.2, 100.0, 100.1],   # gross +10 +30 +20
         [100.1, 99.9, 100.2, 99.8, 100.0, 100.05, 99.90, 100.40, 100.1, 100.0, 99.8, 100.1, 100.2],           # gross  +5 -10 +40
         [100.0, 100.3, 99.7, 100.1, 100.0, 100.20, 100.20, 99.90, 100.0, 100.2, 99.9, 100.1, 100.0]]          # gross +20 +20 -10
NET = [[8.0, 3.0, 18.0], [28.0, -12.0, 18.0], [18.0, 38.0, -12.0]]   # per cell, per day, after the 2 bp round trip
ENTRY = 13 * 3600 + 4 * 300


def cell(i, hold, stop=None, target=None, pset=0):
    return {"index": i, "pset": pset, "hold_minutes": hold, "stop_bp": stop, "target_bp": target, "params": {}}


def typed_exp(tmp, name, holds, **kw):
    path = os.path.join(tmp, "typed.csv")
    if not os.path.exists(path):
        fx.write_bars(path, DAY0 + 13 * 3600, 300, TYPED)
    kw.setdefault("effect_gate", True)
    return fx.make_exp(tmp, name, path, 300, fx.clock_events(DAY0, 3, ENTRY), hold=holds[0], costs=(0.5, 0.5),
                       cells=[cell(i, h) for i, h in enumerate(holds)], **kw)


def csv_rows(exp, name):
    lines = open(os.path.join(exp, "results", name), encoding="utf-8").read().splitlines()
    return lines[0], [dict(zip(lines[0].split(","), l.split(","))) for l in lines[1:]]


def test_three_cells(tmp):
    assert sum(len(d) for d in TYPED) == 40
    exp = typed_exp(tmp, "three", [5, 10, 15])
    code, out, err = run(sweep, ["--exp", exp])
    s, (head, rows) = result(exp, "sweep.json"), csv_rows(exp, "grid.csv")
    assert head == ",".join(sweep.GRID_COLUMNS) and [r["cell"] for r in rows] == ["0", "1", "2"] and [r["hold_minutes"] for r in rows] == ["5", "10", "15"]
    for r, net in zip(rows, NET):
        assert near(float(r["net_mean_bp"]), sum(net) / 3, 1e-6) and near(float(r["gross_mean_bp"]), sum(net) / 3 + 2, 1e-6), r
        assert near(float(r["sharpe"]), k.sharpe(net), 1e-6) and near(float(r["net_sd_bp"]), k.sd(net), 1e-6) and near(float(r["t"]), k.tstat(net), 1e-6)
        assert r["trades"] == r["event_days"] == "3" and r["ties"] == "0" and r["flag"] == "" and r["params"] == "{}"
    # the criterion is the per-day Sharpe (1.27, 0.54, 0.58), not the mean (9.67, 11.33, 14.67): cell 0 is chosen
    assert s["chosen_cell"] == 0 and [r["chosen"] for r in rows] == ["1", "0", "0"] and [r["primary"] for r in rows] == ["1", "0", "0"]
    assert s["cells_declared"] == s["cells_run"] == s["net_positive_cells"] == 3 and "Sharpe" in s["selection_rule"]
    g = s["grid_null"]
    assert g["m"] == g["draws_used"] == g["draws_declared"] == 199 and g["p"] == (g["b"] + 1) / 200 and near(g["real_best_sharpe"], k.sharpe(NET[0]), 1e-6)
    assert code == (0 if g["p"] <= 0.05 else 1) == s["exit_code"] and s["script"] == "sweep", (code, err)
    head, daily = csv_rows(exp, "grid_daily.csv")
    assert head == "day,c0,c1,c2" and [d["day"] for d in daily] == ["2021-01-04", "2021-01-05", "2021-01-06"]
    assert all(near(float(d[f"c{i}"]), NET[i][j], 1e-6) for j, d in enumerate(daily) for i in range(3))
    for i in range(3):
        head, tr = csv_rows(exp, f"trades_c{i}_dev.csv")
        assert head == ",".join(fills.TRADE_COLUMNS) and len(tr) == 3 and {t["cell"] for t in tr} == {str(i)} and tr[0]["exit_reason"] == "time"
    lines = out.strip().splitlines()
    assert "cells declared 3   cells run 3   cells net-positive 3 of 3" in out and "chosen cell: 0" in out and len(lines) <= 45
    assert lines[-2].startswith("RESULT: ") and fx.next_runs(lines[-1], "deflate.py")
    again = (run(sweep, ["--exp", exp, "--json"])[1], run(sweep, ["--exp", exp, "--json"])[1])
    strip = lambda text: {**json.loads(text), "created_utc": 0}
    assert strip(again[0]) == strip(again[1]) == {**s, "created_utc": 0, "RESULT": lines[-2][8:], "NEXT": lines[-1][6:]}
    # a tie in Sharpe goes to the lower index: two identical cells
    rows2, _, _, chosen = sweep.run_cells(fx.bars_of(os.path.join(tmp, "typed.csv"), 300), [cell(0, 10), cell(1, 10), cell(2, 5)],
                                          {0: [{"entry_ts": DAY0 + 86400 * d + ENTRY, "side": 1} for d in range(3)]}, 2.0, 3)
    assert rows2[0]["sharpe"] == rows2[1]["sharpe"] < rows2[2]["sharpe"] and chosen == 2 and rows2[2]["chosen"] == 1
    assert sweep.run_cells(fx.bars_of(os.path.join(tmp, "typed.csv"), 300), [cell(0, 10), cell(1, 10)],
                           {0: [{"entry_ts": DAY0 + 86400 * d + ENTRY, "side": 1} for d in range(3)]}, 2.0, 3)[3] == 0


def test_shapes_and_refusals(tmp):
    exp = typed_exp(tmp, "no_trades", [5, 600])                       # no bar exists 600 minutes after any entry
    code, out, err = run(sweep, ["--exp", exp])
    s, (_, rows) = result(exp, "sweep.json"), csv_rows(exp, "grid.csv")
    assert code in (0, 1) and s["cells_declared"] == s["cells_run"] == len(rows) == 2 and s["chosen_cell"] == 0, err
    assert rows[1]["flag"] == "no trades" and rows[1]["trades"] == "0" and rows[1]["sharpe"] == rows[1]["net_mean_bp"] == "" and "no trades" in out
    assert csv_rows(exp, "trades_c1_dev.csv")[1] == [] and s["net_positive_cells"] == 1
    exp = typed_exp(tmp, "one", [5])
    code, out, _ = run(sweep, ["--exp", exp])
    s = result(exp, "sweep.json")
    assert code == 0 and s["grid_null"] is None and s["chosen_cell"] == 0 and len(csv_rows(exp, "grid.csv")[1]) == 1 and "grid null: not run" in out
    exp = typed_exp(tmp, "too_few", [5, 10], min_days=4)             # no cell reaches the declared minimum of event days
    code, out, _ = run(sweep, ["--exp", exp])
    assert code == 1 and result(exp, "sweep.json")["chosen_cell"] is None and len(csv_rows(exp, "grid.csv")[1]) == 2 and "verdict.py" in out.splitlines()[-1]
    # refusals
    exp = typed_exp(tmp, "no_effect", [5, 10])
    os.remove(os.path.join(exp, "results", "effect_dev.json"))
    code, out, err = run(sweep, ["--exp", exp])
    assert code == 3 and out == "" and err.startswith("ERROR: ") and not os.path.exists(os.path.join(exp, "results", "grid.csv"))
    code, _, err = run(sweep, ["--exp", typed_exp(tmp, "gate_false", [5, 10], effect_gate=False)])
    assert code == 3 and "the characterisation gate did not pass: the sweep is not run; next is verdict.py" in err
    exp = typed_exp(tmp, "few_days", [5, 10])
    k.write_result(exp, "effect_dev.json", {"gate": {"pass": True}, "enough_days": False}, 1, script="effect")
    assert run(sweep, ["--exp", exp])[0] == 3
    exp = typed_exp(tmp, "edited", [5, 10])
    decl = k.read_json(os.path.join(exp, "declarations.json"))
    decl["idea"]["grid"] = {"trade.hold_minutes": [5]}
    json.dump(decl, open(os.path.join(exp, "declarations.json"), "w", encoding="utf-8"))
    code, _, err = run(sweep, ["--exp", exp])
    assert code == 3 and "changed since the freeze" in err
    exp = typed_exp(tmp, "lock_cells", [5, 10])                      # a cell dropped from the lock by hand: rows would differ
    lock = k.read_json(os.path.join(exp, "declarations.lock"))
    lock["cells"] = lock["cells"][:1]
    json.dump(lock, open(os.path.join(exp, "declarations.lock"), "w", encoding="utf-8"))
    assert run(sweep, ["--exp", exp])[0] == 3
    exp = typed_exp(tmp, "undeclared", [5, 10])                      # there is no way to name, add or drop a cell
    for extra in (["--cell", "1"], ["--hold-minutes", "15"], ["--cells", "0"], ["--only", "0"]):
        assert run(sweep, ["--exp", exp] + extra)[0] == 2 and not os.path.exists(os.path.join(exp, "results", "grid.csv"))
    grown = fx.write_bars(os.path.join(tmp, "grown.csv"), DAY0 + 13 * 3600, 300, TYPED)   # the data file changed after the freeze
    exp = fx.make_exp(tmp, "grown", grown, 300, fx.clock_events(DAY0, 3, ENTRY), hold=5, costs=(0.5, 0.5), cells=[cell(0, 5), cell(1, 10)], effect_gate=True)
    with open(grown, "a", encoding="utf-8") as f:
        f.write(f"{(DAY0 + 30 * 86400) * 1000},100,100,100,100,1\n")
    code, _, err = run(sweep, ["--exp", exp])
    assert code == 3 and "the data file changed since the freeze" in err and not os.path.exists(os.path.join(exp, "results", "grid.csv"))
    exp = typed_exp(tmp, "stale", [5, 10])
    k.write_result(exp, "effect_dev.json", {"gate": {"pass": True}, "enough_days": True}, 0, script="effect", decl_sha256="e" * 64)
    assert run(sweep, ["--exp", exp])[0] == 3


NINE = [cell(3 * i + j, h, stop=s) for i, h in enumerate((60, 120, 180)) for j, s in enumerate((20, 40, 80))]


def fake_events(calls):
    """Stand-in for events.py (another file of the skill): one event per UTC day at 14:00, plus one BEFORE the split
    that sweep.py must not trade."""
    mod = types.ModuleType("events")
    def build_events(decl, lock, bars, segment, pset):
        calls.append((segment, pset, bars.ts[0]))
        days = sorted({t // 86400 for t in bars.ts if t >= lock["split_utc"]})
        ts = [lock["split_utc"] - 86400 + 14 * 3600] + [d * 86400 + 14 * 3600 for d in days]
        return [{"pset": pset, "segment": "oos", "day": k.utc_day(t), "decision_ts": t, "entry_ts": t, "side": 1} for t in ts], {}
    mod.build_events = build_events
    return mod


def test_planted_and_oos(tmp):
    split = DAY0 + 100 * 86400
    evs = fx.clock_events(DAY0, 150, 14 * 3600, before=split, hold=180 * 60)
    kw = dict(days=150, bar_seconds=3600, seed=11, effect_bp=30.0)
    nan = fx.synth_csv(os.path.join(tmp, "planted_nan.csv"), split=split, **kw)     # development never parses these rows
    exp = fx.make_exp(tmp, "dev_nan", nan, 3600, evs, split=split, min_days=50, cells=NINE[:2], effect_gate=True)
    assert run(sweep, ["--exp", exp])[0] == 0
    exp = fx.make_exp(tmp, "dev_year_pool", nan, 3600, evs, split=split, min_days=50, cells=[cell(0, 60, stop=40), cell(1, 120, stop=40)], effect_gate=True, null={"pool": "same-year-any-time"})
    assert run(sweep, ["--exp", exp])[0] == 0 and result(exp, "sweep.json")["grid_null"]["p"] == 1 / 200
    real = fx.synth_csv(os.path.join(tmp, "planted.csv"), **kw)
    exp = fx.make_exp(tmp, "planted", real, 3600, evs, split=split, min_days=50, cells=NINE, effect_gate=True)
    res, oos_path = os.path.join(exp, "results"), os.path.join(exp, "results", "oos.json")
    k.write_result(exp, "sweep.json", {"chosen_cell": 0, "grid_null": {"p": 0.001}}, 0, script="sweep")
    code, _, err = run(sweep, ["--exp", exp, "--oos"])
    assert code == 3 and "deflate.json" in err                                      # --oos before deflate.py
    k.write_result(exp, "deflate.json", {"cell": 0, "pass": True}, 0, script="deflate")
    k.write_result(exp, "sweep.json", {"chosen_cell": 0, "grid_null": {"p": 0.5}}, 1, script="sweep")
    code, out, _ = run(sweep, ["--exp", exp, "--oos"])                               # grid null above alpha
    assert code == 1 and "development gates not met: out-of-sample stays unopened" in out and not os.path.exists(oos_path)
    code, out, err = run(sweep, ["--exp", exp])                                      # the real development sweep, 9 cells
    s, (_, rows) = result(exp, "sweep.json"), csv_rows(exp, "grid.csv")
    g, chosen = s["grid_null"], s["chosen_cell"]
    assert code == 0 and len(rows) == 9 and g["p"] == 1 / 200 and g["b"] == 0 and g["z"] > 3, (code, err, g)
    assert float(rows[chosen]["sharpe"]) == max(float(r["sharpe"]) for r in rows) and s["net_positive_cells"] == 9 and rows[chosen]["event_days"] == "100"
    k.write_result(exp, "deflate.json", {"cell": chosen, "pass": False}, 1, script="deflate")
    code, out, _ = run(sweep, ["--exp", exp, "--oos"])                               # development did not pass
    assert code == 1 and out.strip().splitlines()[-2] == "RESULT: development gates not met: out-of-sample stays unopened"
    assert not os.path.exists(oos_path) and not any("oos" in f for f in os.listdir(res)) and "verdict.py" in out.splitlines()[-1]
    k.write_result(exp, "deflate.json", {"cell": chosen, "pass": True}, 0, script="deflate")
    calls, saved = [], sys.modules.get("events")
    sys.modules["events"] = fake_events(calls)
    try:
        code, out, err = run(sweep, ["--exp", exp, "--oos"])
        o, first = result(exp, "oos.json"), open(oos_path, "rb").read()
        assert code == 0 and o["cell"] == chosen == result(exp, "sweep.json")["chosen_cell"] and o["exit_code"] == 0, (code, err)
        assert calls == [("oos", 0, split - 30 * 86400)] and o["events"] == o["trades"] == o["event_days"] == 50 and o["enough_days"]
        head, tr = csv_rows(exp, f"trades_c{chosen}_oos.csv")
        assert len(tr) == 50 and min(int(t["entry_ts"]) for t in tr) >= split and tr[0]["day"] == k.utc_day(split)   # no development bar
        assert csv_rows(exp, "events_oos.csv")[0] == ",".join(effect.EVENT_COLUMNS) and len(csv_rows(exp, "events_oos.csv")[1]) == 50
        x = [sum(float(t["net_bp"]) for t in tr if t["day"] == d) for d in sorted({t["day"] for t in tr})]
        assert near(o["net_mean_bp"], k.mean(x), 1e-9) and near(o["sharpe"], k.sharpe(x), 1e-9) and near(o["t"], k.tstat(x), 1e-9)
        assert near(o["psr0"], k.psr(k.sharpe(x), 50, *k.skew_kurt(x)), 1e-9) and o["psr0"] >= 0.95 and o["net_mean_bp"] > 0
        assert o["gate"] == {"net_mean_positive": True, "psr_ok": True, "null_p_ok": True, "pass": True} and o["null"]["p"] == 1 / 200
        assert o["null"]["pool"] == "same-day-other-times" and o["by_year"][0]["days"] == 50 and o["opened_utc"].endswith("Z")
        assert fx.next_runs(out.strip().splitlines()[-1], "verdict.py")
        # figures a user asks for, printed by the script: the gross mean and the break-even cost of the unseen segment
        gross = [sum(float(t["gross_bp"]) for t in tr if t["day"] == d) for d in sorted({t["day"] for t in tr})]
        assert near(o["gross_mean_bp"], k.mean(gross), 1e-9) and near(o["break_even_cost_bp"], k.mean([float(t["gross_bp"]) for t in tr]), 1e-9)
        assert near(o["gross_mean_bp"] - o["cost_round_trip_bp"], o["net_mean_bp"], 1e-9) and "break-even round-trip cost" in out and "n/a bp" not in out
        assert "stop 20 bp, no target" in out or "no stop, no target" in out or "stop 40 bp, no target" in out or "stop 80 bp, no target" in out
        assert k.read_json(os.path.join(exp, "declarations.lock"))["oos_opened_utc"] == o["opened_utc"]   # the look is recorded in the lock
        code, out, err = run(sweep, ["--exp", exp, "--oos"])                         # the second look is refused
        assert code == 3 and "out-of-sample was already opened on " + o["opened_utc"] in err and "read once" in err and out == ""
        assert open(oos_path, "rb").read() == first and len(calls) == 1
        os.rename(oos_path, oos_path + ".moved")                                     # moving the result away does not buy a second look
        code, out, err = run(sweep, ["--exp", exp, "--oos"])
        assert code == 3 and "results/oos.json is gone" in err and o["opened_utc"] in err and out == "" and len(calls) == 1
        assert not os.path.exists(oos_path)
        os.rename(oos_path + ".moved", oos_path)
    finally:
        sys.modules.pop("events", None)
        if saved is not None:
            sys.modules["events"] = saved


def test_grid_null_calibration(tmp):
    """9 cells on 100 seeded no-effect series (60 days of hourly bars), 199 draws: p <= 0.05 in at most 10 of them."""
    path, hits = os.path.join(tmp, "cal.csv"), 0
    spec, costs = {"pool": "same-day-other-times", "draws": 199, "seed": 1}, {"fee_bp_per_fill": 5, "half_spread_bp_per_fill": 1}
    for seed in range(100):
        synth.generate(path, days=60, bar_seconds=3600, seed=5000 + seed)
        bars = fx.bars_of(path, 3600)
        by_pset = {0: [{"entry_ts": t, "side": 1} for t, _, _ in fx.clock_events(DAY0, 59, 14 * 3600)]}
        rows, _, _, chosen = sweep.run_cells(bars, NINE, by_pset, costs, 30)
        g = sweep.grid_null(bars, NINE, by_pset, costs, spec, 30, rows[chosen]["sharpe"], [r["trades"] for r in rows])
        hits += g["p"] <= 0.05
    assert hits <= 10, f"grid null rejects {hits}/100 no-effect series"
    return hits


def main():
    tmp = tempfile.mkdtemp(prefix="stt_sweep_")
    try:
        test_three_cells(tmp)
        test_shapes_and_refusals(tmp)
        test_planted_and_oos(tmp)
        return test_grid_null_calibration(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    print(f"test_sweep.py: all assertions passed; grid null calibration {main()}/100 at p <= 0.05")
