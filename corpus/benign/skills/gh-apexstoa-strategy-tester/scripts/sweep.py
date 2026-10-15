#!/usr/bin/env python3
"""Step 5 of strategy-tester: every declared cell on development data, then (--oos) the one
out-of-sample look at the chosen cell.

The cells come from the frozen lock and from nowhere else: no flag adds, removes or selects one,
and every cell is written to results/grid.csv whether it looks good or not. The chosen cell is the
one with the highest net per-day Sharpe (never annualised) among cells with the declared minimum of
event days. With more than one cell the grid null asks how good the BEST cell looks on random
entries: each draw runs every cell on one random set of entries and keeps the best Sharpe.

  python3 sweep.py --exp EXP [--json]          development: every declared cell
  python3 sweep.py --exp EXP --oos [--json]    out-of-sample, chosen cell only, readable ONCE
Exit 0 done, 1 a declared gate failed, 2 bad input, 3 refused (order, lock, or a second look).
"""
from __future__ import annotations

import argparse, inspect, json, math, os, random, sys

sys.dont_write_bytecode = True  # nothing is ever written into the skill folder
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _kit, fills, effect

GRID_COLUMNS = ["cell", "pset", "hold_minutes", "stop_bp", "target_bp", "params", "trades", "event_days", "gross_mean_bp",
                "net_mean_bp", "net_sd_bp", "sharpe", "t", "ties", "primary", "chosen", "flag"]
RULE = "highest development net per-day Sharpe among cells with at least {} event days; ties go to the lower index"

def run_cells(bars, cells, events_by_pset, costs, min_days, primary=0):
    """Run every cell. Returns (rows, trades_by_cell, daily, chosen): rows are grid.csv dicts in cell order,
    daily[i] maps day -> net bp of cell i, chosen is a cell index or None when no cell has min_days event days."""
    rows, all_trades, daily, chosen = [], [], [], None
    for c in cells:
        trades, _ = fills.build_trades(bars, events_by_pset.get(c["pset"], []), c, costs)
        days, net = _kit.day_sums(trades, "net_bp")
        D, sd = len(days), _kit.sd(net)
        row = {"cell": c["index"], "pset": c["pset"], "hold_minutes": c["hold_minutes"], "stop_bp": c.get("stop_bp"),
               "target_bp": c.get("target_bp"), "params": json.dumps(c.get("params") or {}, sort_keys=True, separators=(",", ":")),
               "trades": len(trades), "event_days": D, "gross_mean_bp": None, "net_mean_bp": None, "net_sd_bp": None,
               "sharpe": None, "t": None, "ties": None, "primary": int(c["index"] == primary), "chosen": 0, "flag": "no trades"}
        if trades:
            row.update(gross_mean_bp=_kit.mean(_kit.day_sums(trades, "gross_bp")[1]), net_mean_bp=_kit.mean(net),
                       ties=sum(t["exit_reason"] == "tie" for t in trades),
                       flag="zero variance" if sd == 0 else "" if D >= min_days else f"fewer than {min_days} event days")
            if sd > 0:
                row.update(net_sd_bp=sd, sharpe=_kit.sharpe(net), t=_kit.tstat(net))
        if row["flag"] == "" and (chosen is None or row["sharpe"] > rows[chosen]["sharpe"]):
            chosen = len(rows)
        rows.append(row); all_trades.append(trades); daily.append(dict(zip(days, net)))
    if chosen is not None:
        rows[chosen]["chosen"] = 1
    return rows, all_trades, daily, chosen

def grid_null(bars, cells, events_by_pset, costs, method_null, min_days, real_best, trades_per_cell, lo=0):
    """Max-statistic random-entry null over the whole grid. Each draw: one random entry per real event (same pool
    as effect.py, alternatives measured against the longest declared hold), every cell run on those entries, the
    best per-day Sharpe among cells with min_days kept. p = (b + 1) / (m + 1) against the real best."""
    cost = fills.round_trip_cost_bp(costs["fee_bp_per_fill"], costs["half_spread_bp_per_fill"])
    declared, bs, day_of = int(method_null["draws"]), bars.bar_seconds, bars.ts
    work = sum(n * (max(1, int(c["hold_minutes"] * 60 // bs)) if c.get("stop_bp") is not None or c.get("target_bp") is not None else 1)
               for c, n in zip(cells, trades_per_cell))
    used = min(declared, max(199, int(1e8 // max(work, 1))))
    hold = max(int(round(c["hold_minutes"] * 60)) for c, n in zip(cells, trades_per_cell) if n)  # cells that trade at all
    gens = {p: effect.RandomEntries(bars, [(e["entry_ts"], e["side"]) for e in evs], method_null["pool"], hold, lo)
            for p, evs in sorted(events_by_pset.items())}
    sides, nets = {p: [e["side"] for e in evs] for p, evs in events_by_pset.items()}, [effect.net_at(bars, c, cost) for c in cells]
    rng, stats = random.Random(int(method_null["seed"])), []
    for _ in range(used):
        picks, best = {p: g.draw(rng) for p, g in gens.items()}, None
        for c, net in zip(cells, nets):
            acc = {}
            for j, s in zip(picks.get(c["pset"], ()), sides.get(c["pset"], ())):
                r = None if j is None else net(j, s)
                if r is not None:
                    d = day_of[j] // 86400
                    acc[d] = acc.get(d, 0.0) + r
            v = list(acc.values())
            sd = _kit.sd(v) if len(v) >= min_days else 0.0
            if sd > 0 and (best is None or _kit.mean(v) / sd > best):
                best = _kit.mean(v) / sd
        stats.append(best)
    ok, excluded = [s for s in stats if s is not None], sum(len(g.excluded) for g in gens.values())
    b, mu, sd = sum(s is None or s >= real_best for s in stats), _kit.mean(ok), _kit.sd(ok)  # a draw with no usable cell counts against
    if sd == 0 or excluded > 0.05 * len({e["entry_ts"] // 86400 for evs in events_by_pset.values() for e in evs}):
        _kit.die(2, f"DEGENERATE NULL: the grid null has no spread or {excluded} event days have no other start time",
                 "random entries that differ from one another", "check the data, or declare holds well under one day for the same-day pool")
    return {"draws_declared": declared, "draws_used": used, "real_best_sharpe": real_best, "null_mean": mu, "null_sd": sd,
            "null_p95": sorted(ok)[math.ceil(0.95 * len(ok)) - 1], "z": (real_best - mu) / sd, "b": b, "m": used, "p": effect.p_value(b, used),
            "days_excluded": excluded}

def development(a, decl, lock):
    eff = _kit.require(a.exp, "effect_dev.json")
    effect.check_fresh(eff, lock, "effect_dev.json")
    _kit.check_data(decl, lock)
    if not (eff.get("gate") or {}).get("pass") or not eff.get("enough_days"):
        _kit.die(3, "the characterisation gate did not pass: the sweep is not run; next is verdict.py",
                 "effect_dev.json with gate.pass true and enough event days", effect.cmd("verdict.py", a.exp))
    cells, mth = _kit.cells(lock), decl["method"]
    if len(cells) != lock.get("cells_declared") or [c.get("index") for c in cells] != list(range(len(cells))):
        _kit.die(3, f"the lock lists {len(cells)} cells but declares {lock.get('cells_declared')}", "a lock written by declare.py",
                 "restore declarations.lock; every declared cell is run and reported")
    events, bars = effect.read_events(a.exp, "events_dev.csv"), _kit.load_bars(decl, lock, "dev")
    by_pset = {p: [e for e in events if e["pset"] == p] for p in sorted({c["pset"] for c in cells})}
    min_days, alpha = mth["gates"]["min_event_days"], mth["null"]["alpha"]
    rows, trades, daily, chosen = run_cells(bars, cells, by_pset, decl["costs"], min_days, lock["primary_cell"])
    null = None
    if len(cells) > 1 and chosen is not None:
        null = grid_null(bars, cells, by_pset, decl["costs"], mth["null"], min_days, rows[chosen]["sharpe"], [r["trades"] for r in rows])
    positive = sum(1 for r in rows if r["net_mean_bp"] is not None and r["net_mean_bp"] > 0)
    code = 1 if chosen is None or (null is not None and null["p"] > alpha) else 0
    effect.write_csv(a.exp, "grid.csv", GRID_COLUMNS, rows)
    effect.write_csv(a.exp, "grid_daily.csv", ["day"] + [f"c{c['index']}" for c in cells],
                     [{"day": d, **{f"c{i}": x.get(d) for i, x in enumerate(daily)}} for d in sorted(set().union(*daily))])
    for c, t in zip(cells, trades):
        effect.write_csv(a.exp, f"trades_c{c['index']}_dev.csv", fills.TRADE_COLUMNS, t)
    res = _kit.write_result(a.exp, "sweep.json", {"cells_declared": len(cells), "cells_run": len(rows), "net_positive_cells": positive,
                            "chosen_cell": chosen, "selection_rule": RULE.format(min_days), "grid_null": null}, code, script="sweep")
    num = lambda v, spec="+.2f": "" if v is None else format(v, spec)
    L = ["THE DECLARED GRID, development only (net of the declared cost, per event day, Sharpe not annualised)",
         f"cells declared {len(cells)}   cells run {len(rows)}   cells net-positive {positive} of {len(cells)}",
         "cell  hold_min  stop_bp  target_bp  trades  days  gross_bp  net_bp  net_sd  sharpe       t  ties  note"]
    for r in rows[:30]:
        note = " ".join(x for x in ("primary" * r["primary"], "CHOSEN" * r["chosen"], r["flag"], r["params"] if r["params"] != "{}" else "") if x)
        L.append(f"{r['cell']:>4}  {r['hold_minutes']:>8g}  {num(r['stop_bp'], 'g'):>7}  {num(r['target_bp'], 'g'):>9}  {r['trades']:>6}  {r['event_days']:>4}  "
                 f"{num(r['gross_mean_bp']):>8}  {num(r['net_mean_bp']):>6}  {num(r['net_sd_bp'], '.2f'):>6}  {num(r['sharpe'], '+.4f'):>6}  {num(r['t']):>6}  {num(r['ties'], 'd'):>4}  {note}")
    if len(rows) > 30:
        L.append(f"... {len(rows) - 30} more cells: every row is in {os.path.join(a.exp, 'results', 'grid.csv')}")
    L.append(f"chosen cell: {'none' if chosen is None else chosen} ({RULE.format(min_days)})")
    if null is None:
        L.append("grid null: not run (one declared cell)" if len(cells) == 1 else "grid null: not run (no cell qualifies)")
    else:
        cut = "" if null["draws_used"] == null["draws_declared"] else f", reduced from the declared {null['draws_declared']} to bound the run time"
        L.append(f"grid null ({mth['null']['pool']}, {null['draws_used']} draws{cut}): real best Sharpe {null['real_best_sharpe']:+.4f}   null mean {num(null['null_mean'], '+.4f')}   "
                 f"null sd {num(null['null_sd'], '.4f')}   z {num(null['z'])}   p = ({null['b']} + 1) / ({null['m']} + 1) = {null['p']:.4f}")
    if chosen is None:
        result, nxt = f"no declared cell has {min_days} event days: nothing can be chosen", effect.cmd("verdict.py", a.exp)
    else:
        tail = "" if null is None else f"; grid null p = {null['p']:.4f}" + ("" if code == 0 else f", above {alpha:g}: out-of-sample will stay unopened")
        result = f"{len(rows)} of {len(cells)} declared cells run, {positive} net-positive; chosen cell {chosen}, Sharpe {rows[chosen]['sharpe']:+.4f}{tail}"
        nxt = effect.cmd("deflate.py", a.exp)
    _kit.finish(res, result, nxt, code, a.json, L)

def out_of_sample(a, decl, lock):
    path, lock_path = os.path.join(a.exp, "results", "oos.json"), os.path.join(a.exp, "declarations.lock")
    def refuse_if_opened():
        mark = (_kit.read_json(lock_path) or {}).get("oos_opened_utc")  # written below, before the result file
        if mark and not os.path.exists(path):
            _kit.die(3, f"out-of-sample was already opened on {mark} (recorded in declarations.lock) and results/oos.json is gone; it is read once",
                     "the results/oos.json of that one look, where it was written", "put results/oos.json back, then run verdict.py; "
                     "without it this experiment cannot be finished and any further test is a new experiment on new data")
        if mark or os.path.exists(path):
            when = mark or (_kit.read_json(path) or {}).get("opened_utc")
            _kit.die(3, f"out-of-sample was already opened on {when}; it is read once", "one out-of-sample look per frozen declaration",
                     effect.cmd("verdict.py", a.exp) + "  (any change now is a new experiment on new data)")
    refuse_if_opened()
    sw, df = _kit.require(a.exp, "sweep.json"), _kit.require(a.exp, "deflate.json")
    _kit.check_data(decl, lock)
    effect.check_fresh(sw, lock, "sweep.json"); effect.check_fresh(df, lock, "deflate.json")
    mth, chosen, gn = decl["method"], sw.get("chosen_cell"), sw.get("grid_null")
    alpha, min_days = mth["null"]["alpha"], mth["gates"]["min_event_days"]
    if chosen is not None and df.get("cell") not in (None, chosen):
        _kit.die(3, f"deflate.json is about cell {df.get('cell')} but the chosen cell is {chosen}", "deflate.py run after sweep.py", effect.cmd("deflate.py", a.exp))
    if chosen is None or df.get("pass") is not True or (gn is not None and (gn.get("p") is None or gn["p"] > alpha)):
        _kit.finish({"script": "sweep", "decl_sha256": lock["decl_sha256"], "created_utc": _kit.utc_iso(), "exit_code": 1, "opened": False},
                    "development gates not met: out-of-sample stays unopened", effect.cmd("verdict.py", a.exp), 1, a.json,
                    [f"deflate.json pass: {df.get('pass')}   grid null p: {'not run' if gn is None else gn.get('p')} (alpha {alpha:g})"])
    try:
        import events as events_py
    except ImportError as e:
        _kit.die(2, f"events.py of this skill cannot be imported ({e})", "the skill folder as shipped", "restore the scripts folder")
    cell, opened = _kit.cells(lock)[chosen], _kit.utc_iso()
    cost = fills.round_trip_cost_bp(decl["costs"]["fee_bp_per_fill"], decl["costs"]["half_spread_bp_per_fill"])
    bars = _kit.load_bars(decl, lock, "oos")
    extra = {"exp": a.exp} if "exp" in inspect.signature(events_py.build_events).parameters else {}
    evs = [e for e in events_py.build_events(decl, lock, bars, "oos", cell["pset"], **extra)[0] if int(e["entry_ts"]) >= lock["split_utc"]]
    evs = [{"pset": cell["pset"], "segment": "oos", "day": _kit.utc_day(int(e["entry_ts"])), "decision_ts": int(e.get("decision_ts", e["entry_ts"])),
            "entry_ts": int(e["entry_ts"]), "side": int(e["side"])} for e in evs]
    trades, _ = fills.build_trades(bars, evs, cell, cost)
    days, x = _kit.day_sums(trades, "net_bp")
    gross = _kit.day_sums(trades, "gross_bp")[1]
    D, sd, (skew, kurt) = len(days), _kit.sd(x), _kit.skew_kurt(x)
    try:
        psr0 = _kit.psr(_kit.sharpe(x), D, skew, kurt) if sd > 0 else None
    except (ValueError, ZeroDivisionError):
        psr0 = None
    null, degenerate = effect.random_entry_null(bars, trades, cell, cost, mth["null"], lo=bars.first_oos_index)
    gate = {"net_mean_positive": D > 0 and _kit.mean(x) > 0, "psr_ok": psr0 is not None and psr0 >= mth["gates"]["oos_psr_min"],
            "null_p_ok": not degenerate and null["p"] is not None and null["p"] <= alpha}
    gate["pass"] = all(gate.values())
    out = {"cell": chosen, "opened_utc": opened, "events": len(evs), "trades": len(trades), "event_days": D, "enough_days": D >= min_days,
           "gross_mean_bp": _kit.mean(gross) if D else None, "cost_round_trip_bp": cost,
           "break_even_cost_bp": _kit.mean([t["gross_bp"] for t in trades]) if trades else None,
           "net_mean_bp": _kit.mean(x) if D else None, "net_sd_bp": sd if D > 1 else None, "sharpe": _kit.sharpe(x) if sd > 0 else None,
           "t": _kit.tstat(x) if sd > 0 else None, "skew": skew, "kurt": kurt, "psr0": psr0, "null": null, "by_year": effect.by_year(trades), "gate": gate}
    code = 0 if gate["pass"] else 1
    refuse_if_opened()
    now = _kit.read_json(lock_path) or {}
    if now.get("decl_sha256") != lock["decl_sha256"]:
        _kit.die(3, "declarations.lock changed while out-of-sample was being read", "the lock as frozen", "run declare.py status --exp EXP")
    now["oos_opened_utc"] = opened  # the look is recorded in the lock first: moving oos.json away does not buy a second one
    with open(lock_path + ".tmp", "w", encoding="utf-8") as f:
        f.write(json.dumps(now, indent=1) + "\n")
    os.replace(lock_path + ".tmp", lock_path)
    effect.write_csv(a.exp, "events_oos.csv", effect.EVENT_COLUMNS, evs)
    effect.write_csv(a.exp, f"trades_c{chosen}_oos.csv", fills.TRADE_COLUMNS, trades)
    res = _kit.write_result(a.exp, "oos.json", out, code, script="sweep")
    num = lambda v, spec="+.2f": "n/a" if v is None else format(v, spec)
    dist = lambda k, word: f"no {word}" if cell.get(k) is None else f"{word} {cell[k]:g} bp"
    L = [f"OUT-OF-SAMPLE, the one look: cell {chosen}, hold {cell['hold_minutes']:g} min, {dist('stop_bp', 'stop')}, {dist('target_bp', 'target')}; opened {opened}",
         f"events {len(evs)}   trades {len(trades)}   event days D = {D} (declared minimum {min_days})",
         f"gross per event day   mean {num(out['gross_mean_bp'])} bp   round-trip cost {cost:.2f} bp   break-even round-trip cost {num(out['break_even_cost_bp'])} bp (gross mean per trade)",
         f"net per event day   mean {num(out['net_mean_bp'])} bp   sd {num(out['net_sd_bp'], '.2f')}   Sharpe {num(out['sharpe'], '+.4f')}   t {num(out['t'])}   skew {skew:+.2f}   kurtosis {kurt:.2f}",
         f"PSR(0) {num(psr0, '.4f')} (required {mth['gates']['oos_psr_min']:g})",
         f"random-entry null ({null['pool']}, out-of-sample bars only): null mean {num(null['null_mean_bp'])}   excess {num(null['excess_bp'])} bp   z {num(null['z'])}   p {num(null['p'], '.4f')}"
         + (f"   DEGENERATE NULL: {degenerate}" if degenerate else "")]
    L += [f"  {r['year']}: {r['days']} days   net {r['net_mean_bp']:+.2f} bp" for r in out["by_year"][:12]]
    if not out["enough_days"]:
        L.append(f"WARNING: {D} event days, below the declared minimum of {min_days}")
    L.append("out-of-sample gate: " + ("PASS" if gate["pass"] else "not met (" + ", ".join(k for k, v in gate.items() if not v and k != "pass") + ")"))
    _kit.finish(res, f"out-of-sample {'held' if gate['pass'] else 'did not meet the gate'}: net {num(out['net_mean_bp'])} bp over {D} event days, PSR(0) {num(psr0, '.4f')}, "
                f"null p {num(null['p'], '.4f')}; this segment is now used", effect.cmd("verdict.py", a.exp), code, a.json, L)

def main(argv=None):
    ap = argparse.ArgumentParser(description="Run every declared cell on development data; with --oos, read the out-of-sample "
                                 "segment once for the chosen cell. Cells come only from the frozen lock.")
    ap.add_argument("--exp", required=True, help="experiment folder holding declarations.json and its lock")
    ap.add_argument("--oos", action="store_true", help="the one out-of-sample look (needs sweep.json and deflate.json)")
    ap.add_argument("--json", action="store_true", help="print the result JSON instead of the text summary")
    a = ap.parse_args(argv)
    decl, lock = _kit.load_decl(a.exp)
    (out_of_sample if a.oos else development)(a, decl, lock)

if __name__ == "__main__":
    _kit.guard(main)
