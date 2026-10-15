#!/usr/bin/env python3
"""Numerical tests of effect.py: typed prices with hand-computed answers, the hand null, the same-hours trap,
a planted effect of known size, calibration on no-effect series, determinism and the refusal paths.
The fixture helpers here (make_exp, run, clock_events, synth_csv) are also used by test_sweep.py."""
from __future__ import annotations

import contextlib, hashlib, io, json, math, os, random, shlex, shutil, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import _kit as k
import effect, fills, synth

DAY0 = 1609718400  # 2021-01-04T00:00:00Z, a Monday
FAR = 4102444800   # a split after every bar: the whole file is development


def near(a, b, tol=1e-5):
    return abs(a - b) <= tol


def next_runs(line, script):
    """True when a NEXT: line is a python3 command for `script` with --exp, whatever quoting the paths needed
    (a skill folder whose path holds a space is quoted, so a plain substring test is wrong)."""
    argv = shlex.split(line[6:]) if line.startswith("NEXT: python3 ") else []
    return len(argv) > 3 and os.path.basename(argv[1]) == script and "--exp" in argv[2:]


def run(mod, argv):
    """Call mod.main(argv) in this process; returns (exit code, stdout, stderr)."""
    out, err, code = io.StringIO(), io.StringIO(), 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            mod.main(argv)
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


def write_bars(path, t0, bar_seconds, day_opens, nan_from=None):
    """Typed bars: day_opens[d][i] is the open of bar i of day d (bar stamps t0 + 86400 d + bar_seconds i, in ms).
    Each close is the next open of the same day; rows at or after nan_from carry the text NaN as prices."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("open_time,open,high,low,close,volume\n")
        for d, opens in enumerate(day_opens):
            for i, o in enumerate(opens):
                ts, c = t0 + 86400 * d + bar_seconds * i, opens[min(i + 1, len(opens) - 1)]
                px = "NaN,NaN,NaN,NaN" if nan_from is not None and ts >= nan_from else f"{o},{max(o, c)},{min(o, c)},{c}"
                f.write(f"{ts * 1000},{px},1\n")
    return path


def synth_csv(path, split=None, **kw):
    """Seeded synthetic bars from tests/synth.py; with split, every row at or after it gets NaN prices."""
    synth.generate(path, **kw)
    if split is not None:
        lines = open(path, encoding="utf-8").read().splitlines()
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(l if i == 0 or int(l.split(",")[0]) < split * 1000 else l.split(",")[0] + ",NaN,NaN,NaN,NaN,1"
                              for i, l in enumerate(lines)) + "\n")
    return path


def clock_events(first_day, days, hhmm_seconds, side=1, before=FAR, hold=3600, pset=0):
    """Hand-made events.py output: one event per UTC day at a fixed UTC second of the day, kept if it ends before `before`."""
    ts = [first_day + 86400 * d + hhmm_seconds for d in range(days)]
    return [(t, side, pset) for t in ts if t + hold < before]


def make_exp(root, name, csv_path, bar_seconds, events, side="long", hold=60, cells=None, split=FAR, null=None,
             min_days=3, costs=(5, 1), causality="by construction", effect_gate=None):
    """An experiment folder as declare.py freeze + events.py would leave it (spec section 5), written by hand."""
    exp = os.path.join(root, name)
    os.makedirs(os.path.join(exp, "results"))
    decl = {"schema": 1, "kind": "clock",
            "idea": {"hypothesis": "test", "reason": None, "instrument": "SYN", "venue": "none", "side": side,
                     "event": {"local_time": "14:00", "zone": "UTC", "days": "all", "skip_dates_file": None},
                     "trade": {"hold_minutes": hold, "stop_bp": None, "target_bp": None}, "params": {}, "grid": {},
                     "prior_looks": {"text": "none", "variants_seen": 0}},
            "costs": {"fee_bp_per_fill": costs[0], "half_spread_bp_per_fill": costs[1], "source": "test"},
            "data": {"path": csv_path, "columns": {"ts": "open_time", "open": "open", "high": "high", "low": "low", "close": "close",
                                                   "volume": "volume"}, "ts_unit": "ms", "ts_zone": "UTC", "stamp": "open",
                     "bar_seconds": bar_seconds, "first_utc": None, "last_utc": None},
            "method": {"split": {"dev_fraction": 0.6667, "date_utc": None},
                       "null": {"pool": "same-day-other-times", "draws": 199, "seed": 1, "alpha": 0.05, **(null or {})},
                       "gates": {"dsr_min": 0.95, "oos_psr_min": 0.95, "min_event_days": min_days, "max_dropped_event_share": 0.02},
                       "cost_tiers": [0.5, 1.0, 2.0], "replay_probes": 200, "next_if_go": "x", "next_if_no_go": "y"}}
    cells = cells or [{"index": 0, "pset": 0, "hold_minutes": hold, "stop_bp": None, "target_bp": None, "params": {}}]
    lock = {"schema": 1, "decl_sha256": k.canonical_sha256(decl), "frozen_utc": "2026-01-01T00:00:00Z",
            "data": {"bytes": os.path.getsize(csv_path), "sha256": hashlib.sha256(open(csv_path, "rb").read()).hexdigest(), "first_utc": DAY0, "last_utc": DAY0},
            "split_utc": split, "cells": cells, "primary_cell": 0, "cells_declared": len(cells), "variants_seen": 0,
            "amend_penalty": 0, "N": len(cells), "history": []}
    for fname, doc in (("declarations.json", decl), ("declarations.lock", lock)):
        with open(os.path.join(exp, fname), "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1)
    if events is not None:
        effect.write_csv(exp, "events_dev.csv", effect.EVENT_COLUMNS, [
            {"pset": p, "segment": "dev", "day": k.utc_day(t), "decision_ts": t, "entry_ts": t, "side": s} for t, s, p in events])
        k.write_result(exp, "events.json", {"kind": "clock", "causality": causality, "events": {"0": len(events)}}, 0, script="events")
    if effect_gate is not None:
        k.write_result(exp, "effect_dev.json", {"gate": {"pass": effect_gate}, "enough_days": True}, 0 if effect_gate else 1, script="effect")
    return exp


def result(exp, name):
    return k.read_json(os.path.join(exp, "results", name))


def bars_of(csv_path, bar_seconds):
    """Load a whole CSV with the kit's own loader (no lock needed for the segment 'all')."""
    return k.load_bars({"data": {"path": csv_path, "columns": {"ts": "open_time", "open": "open", "high": "high", "low": "low",
                        "close": "close", "volume": "volume"}, "ts_unit": "ms", "ts_zone": "UTC", "stamp": "open", "bar_seconds": bar_seconds}}, None, "all")


# Six days of hourly bars 12:00..17:00; entry at the 14:00 open (100.00), exit at the 15:00 open.
EXITS = [100.10, 99.95, 100.20, 100.00, 100.15, 100.05]   # gross +10, -5, +20, 0, +15, +5 bp
SIX = [[100.2 + 0.05 * d, 99.9, 100.0, x, 100.1 - 0.03 * d, 100.3] for d, x in enumerate(EXITS)]


def test_typed_table(tmp):
    path = write_bars(os.path.join(tmp, "six.csv"), DAY0 + 12 * 3600, 3600, SIX)
    exp = make_exp(tmp, "six", path, 3600, clock_events(DAY0, 6, 14 * 3600))
    code, out, err = run(effect, ["--exp", exp])
    r, lines = result(exp, "effect_dev.json"), out.strip().splitlines()
    g = r["gross"]
    assert code == 1 and r["exit_code"] == 1 and r["script"] == "effect", (code, err)
    assert near(g["mean_bp"], 7.5) and near(g["sd_bp"], 9.354143) and near(g["t"], 1.963961) and near(g["median_bp"], 7.5), g
    assert near(g["upper95_bp"], 13.781390) and near(r["hit_rate"], 4 / 5) and near(r["tie_rate"], 1 / 6), r
    assert near(r["break_even_cost_bp"], 7.5) and near(r["cost_round_trip_bp"], 12.0) and r["event_days"] == r["trades"] == r["events"] == 6
    assert [t["tier"] for t in r["net_by_tier"]] == [0.5, 1.0, 2.0]
    assert all(near(t["mean_bp"], m) for t, m in zip(r["net_by_tier"], (1.5, -4.5, -16.5))) and near(r["net_by_tier"][1]["t"], -1.178377)
    assert r["by_year"] == [{"year": 2021, "days": 6, "gross_mean_bp": g["mean_bp"], "net_mean_bp": r["net_by_tier"][1]["mean_bp"]}]
    assert r["gate"]["pass"] is False and r["gate"]["net_mean_positive"] is False and "12.00 bp" in r["gate"]["reason"]
    assert r["decl_sha256"] == k.read_json(os.path.join(exp, "declarations.lock"))["decl_sha256"]
    assert r["null"]["pool"] == "same-day-other-times" and r["null"]["m"] == 199 and r["null"]["days_excluded"] == 0
    assert near(r["null"]["statistic_bp"], -4.5) and r["null"]["p"] == (r["null"]["b"] + 1) / 200 and r["placebo"] is None
    assert lines[-3].startswith("CHARACTERISATION GATE: FAIL (") and lines[-2].startswith("RESULT: ") and len(lines) <= 45
    assert next_runs(lines[-1], "verdict.py"), lines[-1]
    # the net line: one cell's per-day Sharpe and PSR against zero, printed so that nobody has to derive them by hand
    n = r["net"]
    assert near(n["mean_bp"], -4.5) and near(n["sd_bp"], 9.354143) and near(n["sharpe"], -4.5 / 9.354143) and near(n["t"], -1.178377), n
    assert near(n["psr0"], k.psr(n["sharpe"], 6, *k.skew_kurt([-2.0, -17.0, 8.0, -12.0, 3.0, -7.0])), 1e-6) and 0 < n["psr0"] < 0.5
    assert sum("net Sharpe per event day at the declared cost -0.4811 (not annualised)   PSR(0) " in l and "n = 6" in l for l in lines) == 1
    raw = open(os.path.join(exp, "results", "trades_raw_dev.csv"), encoding="utf-8").read().splitlines()
    assert raw[0] == ",".join(fills.TRADE_COLUMNS) and len(raw) == 7 and raw[1].startswith("raw,2021-01-04,1,"), raw[:2]
    code, out, _ = run(effect, ["--exp", exp, "--json"])
    assert code == 1 and json.loads(out)["gross"]["mean_bp"] == g["mean_bp"] and json.loads(out)["NEXT"].startswith("python3 ")
    short = make_exp(tmp, "six_short", path, 3600, clock_events(DAY0, 6, 14 * 3600, side=-1), side="short")
    assert run(effect, ["--exp", short])[0] == 1
    s = result(short, "effect_dev.json")
    assert near(s["gross"]["mean_bp"], -7.5) and near(s["gross"]["t"], -1.963961) and near(s["hit_rate"], 1 / 5), s["gross"]


def test_summarise_and_p():
    tr = lambda day, g: {"day": day, "gross_bp": g, "net_bp": g - 2.0}
    s = effect.summarise([tr("2021-01-04", 10.0), tr("2021-01-04", 30.0), tr("2021-01-05", -20.0)], 2.0)
    assert s["event_days"] == 2 and s["trades"] == 3 and near(s["gross"]["mean_bp"], 10.0) and near(s["net_by_tier"][1]["mean_bp"], 7.0), s
    assert near(s["break_even_cost_bp"], 20 / 3)   # per trade, while the means above are per event day
    s = effect.summarise([tr(f"2021-01-0{i + 4}", g) for i, g in enumerate([5.0, 0.0, 0.0, -5.0, 5.0])], 2.0)
    assert near(s["tie_rate"], 0.4) and near(s["hit_rate"], 2 / 3), s
    assert near(effect.p_value(0, 999), 0.001, 1e-12) and near(effect.p_value(49, 999), 0.050, 1e-12) and effect.p_value(999, 999) == 1.0


def hand_bars(bar_seconds, opens):
    b = k.Bars(bar_seconds)
    for i, o in enumerate(opens):
        c = opens[min(i + 1, len(opens) - 1)]
        b.ts.append(DAY0 + bar_seconds * i); b.open.append(o); b.high.append(max(o, c)); b.low.append(min(o, c)); b.close.append(c); b.volume.append(1.0)
    return b


def test_hand_null():
    b, cell = hand_bars(3600, [100.0, 101.0, 101.0, 102.0, 102.0]), {"index": 0, "hold_minutes": 60}
    spec = {"pool": "same-day-other-times", "draws": 3000, "seed": 1}
    gen = effect.RandomEntries(b, [(DAY0 + 2 * 3600, 1)], "same-day-other-times", 3600)
    net = effect.net_at(b, cell, 0.0)
    assert gen.cands == [[0, 1, 3]] and near(net(0, 1), 100.0) and net(1, 1) == 0.0 and near(net(2, 1), 99.0099, 1e-4) and net(4, 1) is None
    trades, _ = fills.build_trades(b, [{"entry_ts": DAY0 + 2 * 3600, "side": 1}], cell, 0.0)
    null, bad = effect.random_entry_null(b, trades, cell, 0.0, spec)
    assert bad is None and 0.30 <= null["b"] / null["m"] <= 0.37 and null["m"] == 3000, null   # exact value 1/3
    trades, _ = fills.build_trades(b, [{"entry_ts": DAY0 + 3600, "side": 1}], cell, 0.0)
    null, _ = effect.random_entry_null(b, trades, cell, 0.0, spec)
    assert null["b"] == null["m"] and null["p"] == 1.0, null                                   # every alternative is >= 0
    # exclusion: a 60-minute hold at 13:30 on a full day of one-minute bars
    day = hand_bars(60, [100.0] * 1500)
    c = set(effect.RandomEntries(day, [(DAY0 + 13 * 3600 + 1800, 1)], "same-day-other-times", 3600).cands[0])
    minute = lambda hh, mm: hh * 60 + mm
    assert not any(j in c for j in range(minute(12, 31), minute(14, 30))) and minute(12, 30) in c and minute(14, 30) in c
    assert min(c) == 0 and max(c) == 1439 and len(c) == 1440 - 119
    # a hold of a whole day has no alternative: the day is excluded and the null is degenerate
    gen = effect.RandomEntries(day, [(DAY0, 1)], "same-day-other-times", 86400)
    assert gen.cands == [None] and len(gen.excluded) == 1
    # same-year pool: any bar of the year with an exit bar, including ones that overlap the event
    gen = effect.RandomEntries(b, [(DAY0 + 2 * 3600, 1)], "same-year-any-time", 3600)
    assert gen.cands == [range(0, 5)] and {gen.draw(__import__("random").Random(s))[0] for s in range(60)} == {0, 1, 2, 3}


def test_planted_trap_and_determinism(tmp):
    split, evs = DAY0 + 100 * 86400, clock_events(DAY0, 150, 14 * 3600, before=DAY0 + 100 * 86400)
    kw = dict(days=150, bar_seconds=3600, seed=11)
    planted = synth_csv(os.path.join(tmp, "planted.csv"), split=split, effect_bp=30.0, **kw)   # out-of-sample rows are NaN text
    exp = make_exp(tmp, "planted", planted, 3600, evs, split=split, min_days=50, null={"draws": 499})
    code, out, err = run(effect, ["--exp", exp])
    r = result(exp, "effect_dev.json")
    se = r["gross"]["sd_bp"] / 10
    assert code == 0 and r["event_days"] == 100 and r["enough_days"] and r["gate"]["pass"], (code, err)
    assert abs(r["gross"]["mean_bp"] - 30.0) < 3 * se < 12 and abs(r["null"]["excess_bp"] - 30.0) < 3 * se, (r["gross"], r["null"])
    assert r["null"]["p"] == 1 / 500 and r["null"]["b"] == 0 and near(r["net_by_tier"][1]["mean_bp"], r["gross"]["mean_bp"] - 12.0, 1e-9)
    assert "CHARACTERISATION GATE: PASS" in out and next_runs(out.splitlines()[-1], "sweep.py") and r["placebo"] is None
    code2, _, _ = run(effect, ["--exp", exp])
    again = result(exp, "effect_dev.json")
    assert code2 == 0 and {**again, "created_utc": 0} == {**r, "created_utc": 0}                # same seed: identical
    other = make_exp(tmp, "planted_seed2", planted, 3600, evs, split=split, min_days=50, null={"draws": 499, "seed": 2})
    assert run(effect, ["--exp", other])[0] == 0
    r2 = result(other, "effect_dev.json")
    assert r2["null"]["null_mean_bp"] != r["null"]["null_mean_bp"] and r2["gross"] == r["gross"]
    year = make_exp(tmp, "planted_year_pool", planted, 3600, evs, split=split, min_days=50, null={"pool": "same-year-any-time"})
    assert run(effect, ["--exp", year])[0] == 0 and result(year, "effect_dev.json")["null"]["p"] == 1 / 200
    assert run(effect, ["--exp", make_exp(tmp, "bad_pool", planted, 3600, evs, split=split, null={"pool": "same-hours"})])[0] == 2
    # the clock-time trap: the same +30 bp in EVERY hour is a drift, and the null must contain it
    drift = synth_csv(os.path.join(tmp, "drift.csv"), split=split, drift_bp_per_hour=30.0, **kw)
    exp = make_exp(tmp, "drift", drift, 3600, evs, split=split, min_days=50, null={"draws": 499})
    code, out, _ = run(effect, ["--exp", exp])
    r = result(exp, "effect_dev.json")
    assert code == 1 and r["null"]["p"] > 0.05 and r["gate"]["net_mean_positive"] and not r["gate"]["null_p_ok"], r["null"]
    assert abs(r["null"]["null_mean_bp"] - r["null"]["statistic_bp"]) < 3 * se and "random entries" in r["gate"]["reason"]
    # zero edge: the gate fails on the cost
    zero = synth_csv(os.path.join(tmp, "zero.csv"), split=split, **kw)
    exp = make_exp(tmp, "zero", zero, 3600, evs, split=split, min_days=50)
    assert run(effect, ["--exp", exp])[0] == 1 and result(exp, "effect_dev.json")["gate"]["pass"] is False
    # weekday-only clock idea: the weekend placebo is reported
    dj = os.path.join(exp, "declarations.json")
    decl = k.read_json(dj)
    decl["idea"]["event"]["days"] = "weekdays"
    lock = k.read_json(os.path.join(exp, "declarations.lock"))
    lock["decl_sha256"] = k.canonical_sha256(decl)
    for path, doc in ((dj, decl), (os.path.join(exp, "declarations.lock"), lock)):
        json.dump(doc, open(path, "w", encoding="utf-8"))
    k.write_result(exp, "events.json", {"kind": "clock", "causality": "by construction"}, 0, script="events")
    assert run(effect, ["--exp", exp])[0] == 1 and result(exp, "effect_dev.json")["placebo"]["days"] == 28   # 14 weekends in 100 days


def test_calibration(tmp):
    """200 seeded no-effect datasets, 60 days of hourly bars, 199 draws: p <= 0.05 in 2% to 9% of them."""
    path, cell, hits = os.path.join(tmp, "cal.csv"), {"index": 0, "hold_minutes": 60}, 0
    for seed in range(200):
        synth.generate(path, days=60, bar_seconds=3600, seed=1000 + seed)
        b = bars_of(path, 3600)
        trades, _ = fills.build_trades(b, [{"entry_ts": t, "side": 1} for t, _, _ in clock_events(DAY0, 60, 14 * 3600)], cell, 12.0)
        null, bad = effect.random_entry_null(b, trades, cell, 12.0, {"pool": "same-day-other-times", "draws": 199, "seed": 1})
        assert bad is None and len(trades) == 60
        hits += null["p"] <= 0.05
    assert 4 <= hits <= 18, f"false-positive rate {hits}/200 is outside the 2% to 9% band"
    return hits


def test_volatile_event_hour():
    """A no-effect series whose event hour is three times as volatile as the rest. Counting draws alone passes far
    too often (the real mean scatters more than any draw); the gate's p, the larger of the two, stays near 5%."""
    cell, by_draws, by_gate, N = {"index": 0, "hold_minutes": 60}, 0, 0, 150
    for seed in range(N):
        rng, price, opens = random.Random(5000 + seed), 100.0, []
        for i in range(60 * 24 + 1):
            opens.append(price)
            price *= math.exp(rng.gauss(0.0, 0.0030 * (3.0 if i % 24 == 14 else 1.0)))
        b = hand_bars(3600, opens)
        trades, _ = fills.build_trades(b, [{"entry_ts": DAY0 + 86400 * d + 14 * 3600, "side": 1} for d in range(60)], cell, 0.0)
        null, bad = effect.random_entry_null(b, trades, cell, 0.0, {"pool": "same-day-other-times", "draws": 199, "seed": 1})
        assert bad is None and null["p"] == max(null["p_draws"], null["p_adjusted"]) and null["event_se_bp"] > 0, null
        by_draws += null["p_draws"] <= 0.05
        by_gate += null["p"] <= 0.05
    assert by_draws >= 2 * by_gate and by_draws >= 0.15 * N, f"draws alone passed {by_draws}/{N}: the trap this test is about is gone"
    assert by_gate <= 0.10 * N, f"gate false-positive rate {by_gate}/{N} is above 10% on a volatile event hour"
    return by_draws, by_gate


def test_refusals(tmp):
    path, evs = write_bars(os.path.join(tmp, "r.csv"), DAY0 + 12 * 3600, 3600, SIX), clock_events(DAY0, 6, 14 * 3600)
    def refused(name, **kw):
        exp = make_exp(tmp, name, path, 3600, kw.pop("events", evs), **kw)
        return exp, (lambda: run(effect, ["--exp", exp]))
    exp, go = refused("no_lock")
    os.remove(os.path.join(exp, "declarations.lock"))
    code, out, err = go()
    assert code == 3 and "not frozen" in err and err.startswith("ERROR: ") and "EXPECTED: " in err and "TRY: " in err and out == ""
    exp, go = refused("edited")
    decl = k.read_json(os.path.join(exp, "declarations.json"))
    decl["idea"]["trade"]["hold_minutes"] = 120
    json.dump(decl, open(os.path.join(exp, "declarations.json"), "w", encoding="utf-8"))
    code, _, err = go()
    assert code == 3 and "changed since the freeze" in err and not os.path.exists(os.path.join(exp, "results", "effect_dev.json"))
    assert refused("no_events", events=None)[1]()[0] == 3
    code, _, err = refused("replay_fail", causality="FAIL: 3 differences in 200 probes")[1]()
    assert code == 3 and "causality" in err
    exp, go = refused("stale")
    k.write_result(exp, "events.json", {"causality": "by construction"}, 0, script="events", decl_sha256="f" * 64)
    assert go()[0] == 3
    assert refused("two_days", events=evs[:2])[1]()[0] == 2                      # fewer than 3 event days
    flat = write_bars(os.path.join(tmp, "flat.csv"), DAY0 + 12 * 3600, 3600, [[100.0] * 6] * 6)
    code, _, err = run(effect, ["--exp", make_exp(tmp, "flat", flat, 3600, evs)])
    assert code == 2 and "DEGENERATE NULL" in err, err
    code, _, err = run(effect, ["--exp", make_exp(tmp, "long_hold", path, 3600, evs, hold=24 * 60)])
    assert code == 2                                                             # no exit bar a day later: no trades at all
    code, out, _ = run(effect, ["--help"])
    assert code == 0 and "--exp" in out and "--oos" not in out
    # a data file changed after the freeze is refused here too, with the same words as every other step
    grown = write_bars(os.path.join(tmp, "grown.csv"), DAY0 + 12 * 3600, 3600, SIX)
    exp = make_exp(tmp, "grown", grown, 3600, evs)
    with open(grown, "a", encoding="utf-8") as f:
        f.write(f"{(DAY0 + 30 * 86400) * 1000},100,100,100,100,1\n")
    code, _, err = run(effect, ["--exp", exp])
    assert code == 3 and "the data file changed since the freeze" in err and "declare.py amend" in err and not os.path.exists(os.path.join(exp, "results", "effect_dev.json"))


def main():
    tmp = tempfile.mkdtemp(prefix="stt_effect_")
    try:
        test_typed_table(tmp)
        test_summarise_and_p()
        test_hand_null()
        test_planted_trap_and_determinism(tmp)
        test_refusals(tmp)
        test_volatile_event_hour()
        return test_calibration(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    print(f"test_effect.py: all assertions passed; calibration {main()}/200 at p <= 0.05")
