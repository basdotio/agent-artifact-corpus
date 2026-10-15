#!/usr/bin/env python3
"""Seeded synthetic bars for the tests: noise with a known answer, no market rule in it.

A Gaussian random walk in log price (sd and drift given per hour, in bp), plus an optional planted
effect of --effect-bp spread evenly over the bars whose open falls in [event-utc, event-utc +
effect-minutes) on every day. High and low are drawn outside open and close. Writes the header
open_time,open,high,low,close,volume with millisecond UTC stamps of each bar's open.

  python3 tests/synth.py --out bars.csv [--days 400] [--bar-seconds 300] [--seed 7] [--effect-bp 0]
      [--event-utc 14:00] [--effect-minutes 60] [--drift-bp-per-hour 0] [--sd-bp-per-hour 30] [--start 2021-01-04]
"""
from __future__ import annotations

import argparse, calendar, math, random, sys


def generate(out, days=400, bar_seconds=300, seed=7, effect_bp=0.0, event_utc="14:00", effect_minutes=60,
             drift_bp_per_hour=0.0, sd_bp_per_hour=30.0, start="2021-01-04"):
    """Write `days` UTC days of bars to the CSV path `out`; returns the number of rows written.
    The same arguments always give the same bytes. Returns are in bp per hour; start is 'YYYY-MM-DD'."""
    rng = random.Random(seed)
    y, m, d = (int(p) for p in start.split("-"))
    t0 = calendar.timegm((y, m, d, 0, 0, 0))
    hh, mm = (int(p) for p in event_utc.split(":"))
    ev_start = hh * 3600 + mm * 60
    ev_end = ev_start + effect_minutes * 60
    per_day = 86400 // bar_seconds
    n_effect = sum(1 for k in range(per_day) if ev_start <= k * bar_seconds < ev_end) or 1
    frac = bar_seconds / 3600.0
    sd, drift = sd_bp_per_hour * math.sqrt(frac) / 1e4, drift_bp_per_hour * frac / 1e4
    logp, rows = math.log(100.0), 0
    with open(out, "w", newline="", encoding="utf-8") as f:
        f.write("open_time,open,high,low,close,volume\n")
        for i in range(days * per_day):
            sec = (i % per_day) * bar_seconds
            step = rng.gauss(0.0, sd) + drift
            if ev_start <= sec < ev_end:
                step += effect_bp / n_effect / 1e4
            o, logp = math.exp(logp), logp + step
            c = math.exp(logp)
            h = max(o, c) * (1 + abs(rng.gauss(0.0, sd)) / 2)
            l = min(o, c) * (1 - abs(rng.gauss(0.0, sd)) / 2)
            f.write(f"{(t0 + i * bar_seconds) * 1000},{o:.6f},{h:.6f},{l:.6f},{c:.6f},{rng.uniform(1, 100):.3f}\n")
            rows += 1
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write seeded synthetic bars (noise with an optional planted effect).")
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=int, default=400)
    ap.add_argument("--bar-seconds", type=int, default=300)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--effect-bp", type=float, default=0.0)
    ap.add_argument("--event-utc", default="14:00")
    ap.add_argument("--effect-minutes", type=int, default=60)
    ap.add_argument("--drift-bp-per-hour", type=float, default=0.0)
    ap.add_argument("--sd-bp-per-hour", type=float, default=30.0)
    ap.add_argument("--start", default="2021-01-04")
    a = ap.parse_args(argv)
    if a.days < 1 or a.bar_seconds < 1 or 86400 % a.bar_seconds:
        sys.stderr.write("ERROR: bad size\nEXPECTED: --days >= 1 and --bar-seconds dividing 86400\nTRY: --bar-seconds 300\n")
        sys.exit(2)
    rows = generate(a.out, a.days, a.bar_seconds, a.seed, a.effect_bp, a.event_utc, a.effect_minutes,
                    a.drift_bp_per_hour, a.sd_bp_per_hour, a.start)
    print(f"wrote {rows} bars of {a.bar_seconds} s to {a.out}")


if __name__ == "__main__":
    main()
