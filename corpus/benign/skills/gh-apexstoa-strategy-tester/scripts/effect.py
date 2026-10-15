#!/usr/bin/env python3
"""Step 4 of strategy-tester: the raw effect of the declared event, before any exit logic.

Development segment only (this script has no way to read out-of-sample rows). It takes the primary
cell with its time exit alone, sums returns per event day (the day is the unit of evidence), shows
the cost tiers and the break-even cost, and compares the event with random entries:
  same-day-other-times  the same trade started at other times of the SAME days, never overlapping
                        the event's own window, so an effect tied to the clock is not in its own null
  same-year-any-time    the same number of trades started anywhere in the same calendar year
p = (b + 1) / (m + 1). The gate is: net mean at the declared cost > 0 AND null p <= alpha.

  python3 effect.py --exp EXP [--json]       exit 0 pass, 1 gate failed, 2 bad input, 3 refused
"""
from __future__ import annotations

import argparse, bisect, calendar, csv, math, os, random, shlex, sys, time
from datetime import date, timedelta

sys.dont_write_bytecode = True  # nothing is ever written into the skill folder
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _kit, fills

EVENT_COLUMNS = ["pset", "segment", "day", "decision_ts", "entry_ts", "side"]
POOLS = ("same-day-other-times", "same-year-any-time")
NULL_KEYS = ("statistic_bp", "null_mean_bp", "null_sd_bp", "null_p95_bp", "excess_bp", "z", "b", "m", "p_draws",
             "event_se_bp", "p_adjusted", "p")

def p_value(b, m) -> float:
    """p = (b + 1) / (m + 1): b draws at or above the real statistic out of m draws (never zero)."""
    return (b + 1) / (m + 1)

def cmd(script, exp, extra="") -> str:
    """The exact command line of another script of this skill for the same experiment folder."""
    return f"python3 {shlex.quote(os.path.join(HERE, script))} --exp {shlex.quote(os.path.abspath(exp))}{extra}"

def read_events(exp, name, pset=None) -> list:
    """Rows of EXP/results/<name> (events_*.csv) as dicts with integer pset, decision_ts, entry_ts, side."""
    path = _kit.require(exp, name)
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = [{**r, **{k: int(r[k]) for k in ("pset", "decision_ts", "entry_ts", "side")}} for r in csv.DictReader(f)]
    except (KeyError, ValueError, TypeError, OSError) as e:
        _kit.die(2, f"results/{name} cannot be read ({e})", "the columns " + ",".join(EVENT_COLUMNS), "run events.py again")
    return [r for r in rows if pset is None or r["pset"] == pset]

def write_csv(exp, name, columns, rows):
    """Write EXP/results/<name> with the given columns; None becomes an empty field."""
    os.makedirs(os.path.join(exp, "results"), exist_ok=True)
    with open(os.path.join(exp, "results", name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(columns)
        w.writerows([r.get(c) for c in columns] for r in rows)

def by_year(trades) -> list:
    """Per calendar year of the entry day: event days, mean gross and mean net bp per event day."""
    days, gross = _kit.day_sums(trades, "gross_bp")
    net = _kit.day_sums(trades, "net_bp")[1]
    return [{"year": int(y), "days": sum(d[:4] == y for d in days),
             "gross_mean_bp": _kit.mean([g for d, g in zip(days, gross) if d[:4] == y]),
             "net_mean_bp": _kit.mean([x for d, x in zip(days, net) if d[:4] == y])} for y in sorted({d[:4] for d in days})]

def summarise(trades, cost, tiers=(0.5, 1.0, 2.0)) -> dict:
    """The raw-effect table from trade dicts (day, gross_bp, net_bp): everything is taken over per-day sums
    except the hit and tie rates (per trade, exact zeros dropped from the hit rate) and the break-even cost."""
    days, g = _kit.day_sums(trades, "gross_bp")
    count = {d: 0 for d in days}
    for t in trades:
        count[t["day"]] += 1
    raw, D = [t["gross_bp"] for t in trades], len(days)
    wins, losses = sum(r > 0 for r in raw), sum(r < 0 for r in raw)
    tier_rows = []
    for tier in tiers:
        x = [gd - cost * tier * count[d] for d, gd in zip(days, g)]
        tier_rows.append({"tier": tier, "cost_bp": cost * tier, "mean_bp": _kit.mean(x), "t": _kit.tstat(x)})
    return {"trades": len(trades), "event_days": D,
            "gross": {"mean_bp": _kit.mean(g), "median_bp": _kit.median(g), "sd_bp": _kit.sd(g), "t": _kit.tstat(g),
                      "upper95_bp": _kit.mean(g) + _kit.Z95 * _kit.sd(g) / math.sqrt(D) if D else 0.0},
            "hit_rate": wins / (wins + losses) if wins + losses else None,
            "tie_rate": (len(raw) - wins - losses) / len(raw) if raw else None,
            "cost_round_trip_bp": cost, "break_even_cost_bp": _kit.mean(raw), "net_by_tier": tier_rows,
            "by_year": by_year(trades), "lag1_autocorr": _kit.lag1_autocorr(_kit.day_sums(trades, "net_bp")[1])}

class RandomEntries:
    """Where a random entry may start, for each real entry (entry_ts, side). cands[k] is the list (or range) of
    bar indices for entry k, or None when its day has no alternative (the day is then in `excluded`).
    lo = first bar index that may be used (the first out-of-sample bar when that segment is being read)."""

    def __init__(self, bars, entries, pool, hold_seconds, lo=0):
        ts, self.bars, self.hold, self.cands, self.excluded, days = bars.ts, bars, hold_seconds, [], set(), {}
        if pool not in POOLS:
            _kit.die(2, f"unknown null pool {pool!r}", " or ".join(POOLS), "set method.null.pool through declare.py")
        for e, _side in entries:
            if pool == POOLS[0]:
                d0 = e - e % 86400
                if d0 not in days:  # bars of that UTC day whose own exit bar exists, computed once per day
                    a, b = max(lo, bisect.bisect_left(ts, d0)), bisect.bisect_left(ts, d0 + 86400)
                    days[d0] = [j for j in range(a, b) if bars.index_at(ts[j] + hold_seconds) is not None]
                c = [j for j in days[d0] if ts[j] + hold_seconds <= e or ts[j] >= e + hold_seconds]
                if not c:
                    self.excluded.add(d0)
            else:  # same-year-any-time
                y = time.gmtime(e).tm_year
                c = range(max(lo, bisect.bisect_left(ts, calendar.timegm((y, 1, 1, 0, 0, 0)))),
                          bisect.bisect_left(ts, calendar.timegm((y + 1, 1, 1, 0, 0, 0))))
            self.cands.append(c)
        self.cands = [None if e - e % 86400 in self.excluded else c for (e, _s), c in zip(entries, self.cands)]

    def draw(self, rng) -> list:
        """One random set: a bar index per real entry (None for an excluded day, or when 100 tries found no
        bar with an exit bar). Uniform over the candidates."""
        out, ts = [], self.bars.ts
        for c in self.cands:
            j = None
            for _ in range(100 if c else 0):
                j = c[int(rng.random() * len(c))]
                if isinstance(c, list) or self.bars.index_at(ts[j] + self.hold) is not None:
                    break
                j = None
            out.append(j)
        return out

def net_at(bars, cell, cost, time_exit_only=False):
    """net(j, side): net bp of the cell's trade entered at bar j (None when it cannot be completed), remembered."""
    hold, memo = int(round(cell["hold_minutes"] * 60)), {}
    stop, target = (None, None) if time_exit_only else (cell.get("stop_bp"), cell.get("target_bp"))
    def net(j, side):
        key = (j, side)
        if key not in memo:
            tr = fills.simulate(bars, j, side, hold, stop, target)
            memo[key] = None if tr is None else tr["gross_bp"] - cost
        return memo[key]
    return net

def random_entry_null(bars, trades, cell, cost, method_null, lo=0, time_exit_only=False):
    """The random-entry null for one cell. Statistic S = sum of net trade returns / D, with D (event days of the
    real trades that have an alternative) fixed for every draw. Returns (null dict, None), or (dict, reason)
    when the null is degenerate: more than 5% of days without an alternative, or no spread."""
    pool, draws, seed = method_null["pool"], int(method_null["draws"]), int(method_null["seed"])
    gen = RandomEntries(bars, [(t["entry_ts"], t["side"]) for t in trades], pool, int(round(cell["hold_minutes"] * 60)), lo)
    keep = [t for t, c in zip(trades, gen.cands) if c is not None]
    out = {"pool": pool, "draws": draws, "seed": seed, **{k: None for k in NULL_KEYS}, "days_excluded": len(gen.excluded)}
    D = len({t["day"] for t in keep})
    if not keep or len(gen.excluded) > 0.05 * len({t["day"] for t in trades}):
        return out, f"{len(gen.excluded)} event days have no other start time on the same day (hold too long for this pool)"
    net, sides, rng = net_at(bars, cell, cost, time_exit_only), [t["side"] for t in trades], random.Random(seed)
    real = math.fsum(t["net_bp"] for t in keep) / D
    stats = [math.fsum(net(j, s) for j, s in zip(gen.draw(rng), sides) if j is not None) / D for _ in range(draws)]
    b, mu, sd = sum(s >= real for s in stats), _kit.mean(stats), _kit.sd(stats)
    # The draws take the event window to be as volatile as the times they sample. When it is more volatile (a
    # session open, a data release) the real mean scatters more widely than any draw, and counting draws alone
    # passes too often. So a second p uses the event days' OWN spread: (real - null mean) / (sd of the event
    # days' net returns / sqrt(D)), one-sided normal. The gate uses the LARGER of the two.
    by_day = {}
    for t in keep:
        by_day[t["day"]] = by_day.get(t["day"], 0.0) + t["net_bp"]
    se = _kit.sd(list(by_day.values())) / math.sqrt(D) if D > 1 else 0.0
    p_draws = p_value(b, draws)
    p_adj = 1.0 - _kit.Phi((real - mu) / se) if se > 0 else None
    out.update(statistic_bp=real, null_mean_bp=mu, null_sd_bp=sd, null_p95_bp=sorted(stats)[math.ceil(0.95 * draws) - 1],
               excess_bp=real - mu, z=(real - mu) / sd if sd > 0 else None, b=b, m=draws, p_draws=p_draws,
               event_se_bp=se, p_adjusted=p_adj, p=p_draws if p_adj is None else max(p_draws, p_adj))
    return out, (None if sd > 0 else "every random entry gave the same result (no spread)")

def weekend_placebo(decl, bars, cell):
    """Clock ideas declared on weekdays only: the same clock rule on Saturdays and Sundays. Reported, never gated."""
    ev, days = decl["idea"]["event"], decl["idea"]["event"].get("days")
    if decl.get("kind") != "clock" or not (days == "weekdays" or (isinstance(days, list) and days and max(days) < 5)):
        return None
    side, evs, d = (-1 if decl["idea"]["side"] == "short" else 1), [], date.fromisoformat(_kit.utc_day(bars.ts[0]))
    while d <= date.fromisoformat(_kit.utc_day(bars.ts[-1])):
        if d.weekday() >= 5:
            evs.append({"entry_ts": _kit.local_to_utc(d, ev["local_time"], ev["zone"]), "side": side})
        d += timedelta(days=1)
    g = _kit.day_sums(fills.build_trades(bars, evs, cell, 0.0, time_exit_only=True, label="placebo")[0], "gross_bp")[1]
    return {"days": len(g), "gross_mean_bp": _kit.mean(g), "t": _kit.tstat(g)} if len(g) >= 2 else None

def net_line(x) -> dict:
    """Net per-event-day figures of one cell: mean, sd, per-day Sharpe (never annualised), t and PSR against zero
    (None when the series has no spread or the moments do not allow it). No trial count enters here."""
    sd, (skew, kurt) = _kit.sd(x), _kit.skew_kurt(x)
    try:
        psr0 = _kit.psr(_kit.sharpe(x), len(x), skew, kurt) if sd > 0 and len(x) >= 3 else None
    except (ValueError, ZeroDivisionError):
        psr0 = None
    return {"mean_bp": _kit.mean(x), "sd_bp": sd, "sharpe": _kit.sharpe(x) if sd > 0 else None,
            "t": _kit.tstat(x) if sd > 0 else None, "psr0": psr0}

def check_fresh(doc, lock, name):
    """Exit 3 when a result file was made under other declarations than the frozen ones."""
    if doc.get("decl_sha256") != lock.get("decl_sha256"):
        _kit.die(3, f"results/{name} was made under different declarations", "results of the current freeze",
                 "run declare.py status --exp EXP and follow its NEXT: line")

def main(argv=None):
    ap = argparse.ArgumentParser(description="Raw effect on development data only: per-day table, cost tiers, break-even cost, null, gate.")
    ap.add_argument("--exp", required=True, help="experiment folder holding declarations.json and its lock")
    ap.add_argument("--json", action="store_true", help="print the result JSON instead of the text summary")
    a = ap.parse_args(argv)
    decl, lock = _kit.load_decl(a.exp)
    ej = _kit.require(a.exp, "events.json", "causality")
    check_fresh(ej, lock, "events.json")
    if "FAIL" in str(ej["causality"]) or ej.get("exit_code") not in (0, None):
        _kit.die(3, f"events.py did not pass (causality: {ej['causality']}; exit code {ej.get('exit_code')})",
                 "an events.json with exit_code 0 and a non-failing causality", cmd("verdict.py", a.exp))
    _kit.check_data(decl, lock)
    cell, mth = _kit.cells(lock)[lock["primary_cell"]], decl["method"]
    cost = fills.round_trip_cost_bp(decl["costs"]["fee_bp_per_fill"], decl["costs"]["half_spread_bp_per_fill"])
    events = read_events(a.exp, "events_dev.csv", cell["pset"])
    bars = _kit.load_bars(decl, lock, "dev")
    trades, counts = fills.build_trades(bars, events, cell, cost, time_exit_only=True, label="raw")
    out = {"cell": cell["index"], "events": len(events), **summarise(trades, cost, mth.get("cost_tiers") or (0.5, 1.0, 2.0))}
    D, g = out["event_days"], out["gross"]
    out.update(skipped_overlap=counts["skipped_overlap"], dropped_missing_exit=counts["dropped_missing_exit"],
               enough_days=D >= mth["gates"]["min_event_days"])
    if D < 3:
        _kit.die(2, f"only {D} event days with a completed trade on development data", "at least 3 event days",
                 "check results/events.json: the events and the data do not meet")
    null, degenerate = random_entry_null(bars, trades, cell, cost, mth["null"], time_exit_only=True)
    if degenerate:
        _kit.die(2, f"DEGENERATE NULL: {degenerate}", "random entries that differ from one another",
                 "check the data for flat prices, or declare a hold well under one day for the same-day pool")
    if g["sd_bp"] == 0:
        _kit.die(2, "zero variance: every event day has the same return", "returns that vary from day to day", "check the data file")
    net1 = net_line(_kit.day_sums(trades, "net_bp")[1])  # tier 1, whatever tiers are declared
    out["net"] = net1
    alpha, flags, why = mth["null"]["alpha"], [], []
    if abs(g["t"]) > 20:
        flags.append(f"SUSPICIOUS: |t| = {abs(g['t']):.1f} is above 20; reproduce three trades by hand")
    if out["hit_rate"] is not None and out["hit_rate"] > 0.90 and len(trades) >= 50:
        flags.append(f"SUSPICIOUS: hit rate {out['hit_rate']:.2f} on {len(trades)} trades; check for look-ahead")
    if cost == 0:
        flags.append("SUSPICIOUS: the declared round-trip cost is 0 bp")
    pos, p_ok = net1["mean_bp"] > 0, null["p"] <= alpha
    if not pos:
        why.append(f"net mean {net1['mean_bp']:+.2f} bp per event day is not above zero at the declared round-trip cost of "
                   f"{cost:.2f} bp; break-even cost {out['break_even_cost_bp']:.2f} bp")
    if not p_ok:
        why.append(f"null p = {null['p']:.4f} is above {alpha:g}: no better than random entries ({null['pool']})")
    reason = "; ".join(why) or f"net mean {net1['mean_bp']:+.2f} bp is above zero at the declared cost and null p = {null['p']:.4f} <= {alpha:g}"
    out.update(null=null, placebo=weekend_placebo(decl, bars, cell), flags=flags,
               gate={"net_mean_positive": pos, "null_p_ok": p_ok, "pass": pos and p_ok, "reason": reason})
    code = 0 if out["gate"]["pass"] and out["enough_days"] else 1
    write_csv(a.exp, "trades_raw_dev.csv", fills.TRADE_COLUMNS, trades)
    res = _kit.write_result(a.exp, "effect_dev.json", out, code, script="effect")
    f2, hit, pl = (lambda v: f"{v:+.2f}"), out["hit_rate"], out["placebo"]
    L = [f"RAW EFFECT, development only: cell {cell['index']}, {decl['idea']['side']}, hold {cell['hold_minutes']:g} min, time exit (stop and target not applied here)",
         f"events {len(events)}   trades {len(trades)}   skipped for overlap {counts['skipped_overlap']}   dropped, no exit bar {counts['dropped_missing_exit']}   event days D = {D}",
         f"gross per event day   mean {f2(g['mean_bp'])} bp   median {f2(g['median_bp'])}   sd {g['sd_bp']:.2f}   t {f2(g['t'])}   one-sided 95% upper bound {f2(g['upper95_bp'])}",
         f"hit rate {'n/a' if hit is None else format(hit, '.3f')} (per trade, exact zeros dropped)   tie rate {out['tie_rate']:.3f}",
         f"round-trip cost {cost:.2f} bp   break-even round-trip cost {out['break_even_cost_bp']:.2f} bp (gross mean per trade)"]
    L += [f"net at {r['tier']:g}x cost ({r['cost_bp']:.2f} bp)   mean {f2(r['mean_bp'])} bp   t {f2(r['t'])}" for r in out["net_by_tier"]]
    L.append(f"net Sharpe per event day at the declared cost {'n/a' if net1['sharpe'] is None else format(net1['sharpe'], '+.4f')} (not annualised)   "
             f"PSR(0) {'n/a' if net1['psr0'] is None else format(net1['psr0'], '.4f')}   n = {D}   (this one cell only: N and DSR exist after the sweep)")
    L += [f"  {r['year']}: {r['days']} days   gross {f2(r['gross_mean_bp'])} bp   net {f2(r['net_mean_bp'])} bp" for r in out["by_year"][:12]]
    L += [f"lag-1 autocorrelation of the daily net returns {out['lag1_autocorr']:+.3f}",
          f"random-entry null ({null['pool']}, {null['m']} draws, seed {null['seed']}, {null['days_excluded']} days excluded)",
          f"  event {f2(null['statistic_bp'])} bp   null mean {f2(null['null_mean_bp'])}   null sd {null['null_sd_bp']:.2f}   null 95th pct {f2(null['null_p95_bp'])}",
          f"  excess {f2(null['excess_bp'])} bp   z {f2(null['z'])}   p from draws = ({null['b']} + 1) / ({null['m']} + 1) = {null['p_draws']:.4f}",
          f"  p adjusted for the event window's own spread = {'n/a' if null['p_adjusted'] is None else format(null['p_adjusted'], '.4f')}"
          f"   null p (the larger of the two, used by the gate) = {null['p']:.4f}"]
    if pl:
        L.append(f"weekend placebo (same clock rule, Saturdays and Sundays; not gated): {pl['days']} days   gross mean {f2(pl['gross_mean_bp'])} bp   t {f2(pl['t'])}")
    L += flags
    if not out["enough_days"]:
        L.append(f"WARNING: {D} event days, below the declared minimum of {mth['gates']['min_event_days']}")
    L.append("CHARACTERISATION GATE: PASS" if out["gate"]["pass"] else f"CHARACTERISATION GATE: FAIL ({reason})")
    if code == 0:
        result, nxt = f"gate passed: net {f2(net1['mean_bp'])} bp per event day over {D} days, null p = {null['p']:.4f}", cmd("sweep.py", a.exp)
    elif out["gate"]["pass"]:
        result, nxt = f"gate passed but only {D} event days against {mth['gates']['min_event_days']} declared: the sweep is not run", cmd("verdict.py", a.exp)
    else:
        result, nxt = f"gate failed: {reason}", cmd("verdict.py", a.exp)
    _kit.finish(res, result, nxt, code, a.json, L)

if __name__ == "__main__":
    _kit.guard(main)
