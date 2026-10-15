#!/usr/bin/env python3
"""Trade simulation and costs for strategy-tester (library), plus a small cost calculator.

Fixed rules: market entry at the open of the entry bar; time exit at the open of the bar stamped
entry + hold, found by timestamp (no such bar: the trade is dropped, nothing is filled forward);
a stop never fills better than its level, a gap through it fills at the open, a target needs a
trade-through (a touch is not a fill), stop and target inside one bar count as the stop; one
position at a time; fee plus half-spread is charged on both fills of every trade.
Prices are the file's units, returns and costs are basis points (bp), times are UTC epoch seconds.

  python3 fills.py --fee-bp 5 --half-spread-bp 1 [--stop-bp 50] [--gross-bp 7.5] [--json]
"""
from __future__ import annotations

import argparse, json, os, sys

sys.dont_write_bytecode = True  # nothing is ever written into the skill folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _kit


def round_trip_cost_bp(fee_bp, half_spread_bp, tier=1.0) -> float:
    """Cost of one round trip in bp: 2 fills x (fee + half-spread) x tier."""
    return 2 * (fee_bp + half_spread_bp) * tier


def simulate(bars, entry_index, side, hold_seconds, stop_bp=None, target_bp=None):
    """One trade on a _kit.Bars. Enters at bars.open[entry_index]; side +1 long, -1 short; stop_bp and
    target_bp are distances from the entry price in bp (None = not used). Returns a dict with entry_ts,
    entry_px, exit_ts, exit_px, exit_reason (time|stop|stop_gap|target|tie) and gross_bp, or None when the
    exit bar does not exist (simulate.reason is then "exit bar missing"). exit_ts is the open time of the
    exit bar for time and stop_gap, and the end of the bar (open time + bar_seconds) for stop, target, tie."""
    ts, op = bars.ts, bars.open
    entry_ts, entry = ts[entry_index], op[entry_index]
    exit_index = bars.index_at(entry_ts + hold_seconds)
    if exit_index is None or exit_index <= entry_index:
        simulate.reason = "exit bar missing"
        return None
    exit_ts, exit_px, reason = ts[exit_index], op[exit_index], "time"
    if stop_bp is not None or target_bp is not None:
        hi, lo, cl = (bars.high, bars.low, bars.close) if side > 0 else (bars.low, bars.high, bars.close)
        # work in "signed" prices p * side so one set of long-side comparisons serves both sides
        S = side * (entry - side * entry * stop_bp / 1e4) if stop_bp is not None else None
        T = side * (entry + side * entry * target_bp / 1e4) if target_bp is not None else None
        for j in range(entry_index, exit_index):
            o, h, l, c = side * op[j], side * hi[j], side * lo[j], side * cl[j]
            hit = None
            if S is not None and j > entry_index and o <= S:
                hit = (o, "stop_gap", ts[j])
            elif S is not None and l <= S:
                hit = (min(S, c), "tie" if T is not None and h > T else "stop", ts[j] + bars.bar_seconds)
            elif T is not None and h > T:
                hit = (T, "target", ts[j] + bars.bar_seconds)
            if hit:
                exit_px, reason, exit_ts = side * hit[0], hit[1], hit[2]
                break
    return {"entry_ts": entry_ts, "entry_px": entry, "exit_ts": exit_ts, "exit_px": exit_px,
            "exit_reason": reason, "gross_bp": side * (exit_px / entry - 1) * 1e4}


def build_trades(bars, events, cell, costs, tier=1.0, time_exit_only=False, label=None):
    """Turn events into trades for one cell. events: dicts with entry_ts and side (+1/-1), any order; cell: a
    lock cell {index, hold_minutes, stop_bp, target_bp, ...}; costs: declarations 'costs' dict (fee_bp_per_fill,
    half_spread_bp_per_fill) or a number already meaning round-trip bp at tier 1. time_exit_only ignores the
    cell's stop and target; label overrides the 'cell' field. Returns (trades, counts): trades are dicts with
    the trades_*.csv columns cell, day, side, entry_ts, entry_px, exit_ts, exit_px, exit_reason, gross_bp,
    cost_bp, net_bp in entry order; counts = {skipped_overlap, dropped_missing_exit, dropped_missing_entry}."""
    if isinstance(costs, dict):
        cost = round_trip_cost_bp(costs["fee_bp_per_fill"], costs["half_spread_bp_per_fill"], tier)
    else:
        cost = float(costs) * tier
    hold = int(round(cell["hold_minutes"] * 60))
    stop, target = (None, None) if time_exit_only else (cell.get("stop_bp"), cell.get("target_bp"))
    name = cell.get("index") if label is None else label
    trades, counts, free_at = [], {"skipped_overlap": 0, "dropped_missing_exit": 0, "dropped_missing_entry": 0}, None
    for ev in sorted(events, key=lambda e: e["entry_ts"]):
        if free_at is not None and ev["entry_ts"] < free_at:
            counts["skipped_overlap"] += 1
            continue
        i = bars.index_at(ev["entry_ts"])
        tr = None if i is None else simulate(bars, i, int(ev["side"]), hold, stop, target)
        if tr is None:
            counts["dropped_missing_entry" if i is None else "dropped_missing_exit"] += 1
            continue
        free_at = tr["exit_ts"]
        trades.append({"cell": name, "day": _kit.utc_day(tr["entry_ts"]), "side": int(ev["side"]), **tr,
                       "cost_bp": cost, "net_bp": tr["gross_bp"] - cost})
    return trades, counts


TRADE_COLUMNS = ["cell", "day", "side", "entry_ts", "entry_px", "exit_ts", "exit_px", "exit_reason",
                 "gross_bp", "cost_bp", "net_bp"]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cost per fill, per round trip, in R, and net of a gross figure (all bp).")
    ap.add_argument("--fee-bp", type=float, required=True, help="fee per fill, bp of notional")
    ap.add_argument("--half-spread-bp", type=float, required=True, help="half the bid-ask spread per fill, bp")
    ap.add_argument("--stop-bp", type=float, help="stop distance in bp: prints the cost in R")
    ap.add_argument("--gross-bp", type=float, help="gross mean per trade in bp: prints net and break-even")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    a = ap.parse_args(argv)
    vals = [v for v in (a.fee_bp, a.half_spread_bp, a.stop_bp, a.gross_bp) if v is not None]
    if any(v != v or abs(v) == float("inf") for v in vals) or a.fee_bp < 0 or a.half_spread_bp < 0:
        _kit.die(2, "fee and half-spread must be finite numbers, zero or above", "for example --fee-bp 5 --half-spread-bp 1",
                 "give both as basis points per fill, from the venue's fee table and the quoted spread")
    if a.stop_bp is not None and a.stop_bp <= 0:
        _kit.die(2, "--stop-bp must be above zero", "a stop distance in bp, for example 50", "give the distance, not a price")
    rt = round_trip_cost_bp(a.fee_bp, a.half_spread_bp)
    out = {"cost_per_fill_bp": a.fee_bp + a.half_spread_bp, "round_trip_bp": rt,
           "round_trip_by_tier_bp": {str(t): round_trip_cost_bp(a.fee_bp, a.half_spread_bp, t) for t in (0.5, 1.0, 2.0)},
           "cost_in_R": None if a.stop_bp is None else rt / a.stop_bp,
           "gross_bp": a.gross_bp, "net_bp": None if a.gross_bp is None else a.gross_bp - rt,
           "break_even_cost_bp": a.gross_bp}
    lines = [f"cost per fill        {out['cost_per_fill_bp']:.2f} bp (fee {a.fee_bp:g} + half-spread {a.half_spread_bp:g})",
             f"round trip           {rt:.2f} bp (two fills); tiers 0.5x {rt * 0.5:.2f}, 2x {rt * 2:.2f}"]
    if a.stop_bp is not None:
        lines.append(f"cost in R            {out['cost_in_R']:.2f} R (round trip / stop of {a.stop_bp:g} bp)")
    if a.gross_bp is not None:
        lines += [f"net per trade        {out['net_bp']:.2f} bp (gross {a.gross_bp:g} - round trip {rt:.2f})",
                  f"break-even cost      {a.gross_bp:.2f} bp round trip: above this the gross figure is gone"]
    verdict = "" if a.gross_bp is None else f"; a gross {a.gross_bp:g} bp nets {out['net_bp']:.2f} bp"
    _kit.finish(out, f"round trip costs {rt:.2f} bp{verdict}",
                "put fee, half-spread and where they come from under costs in declarations.json", 0, a.json, lines)


if __name__ == "__main__":
    _kit.guard(main)
