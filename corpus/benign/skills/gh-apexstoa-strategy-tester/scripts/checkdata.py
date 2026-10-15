#!/usr/bin/env python3
"""Data sanity check of a frozen experiment. Report-only: it never fills, clips, sorts or deletes a row.

  python3 checkdata.py --exp EXP [--json]

Reads the data file named in the declarations and writes results/data_check.json and, when bars are
missing, results/missing_bars.csv (gap_start_utc, gap_end_utc, bars_missing: the open times of the first
and last missing bar of each gap, UTC epoch seconds). A FAIL is a defect the later steps cannot work
around; a WARNING is for a person to look at. Rows outside data.first_utc .. data.last_utc are only
checked for a readable, ascending timestamp. Exits: 0 PASS (warnings allowed), 1 FAIL, 2 unreadable file
or missing column, 3 no lock or the file differs from the one frozen.
"""
from __future__ import annotations

import argparse, csv, hashlib, math, os, shlex, statistics, sys, time
from array import array
from collections import Counter

sys.dont_write_bytecode = True  # nothing is ever written into the skill folder
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _kit

SIGMAS, SHARE, SHOWN = 20.0, 0.05, 20  # flags for a person to look at; they change nothing in the data
OUTLIER_SHARE = 0.001  # extreme one-bar returns are a WARNING above this share of bars and a plain note below it:
                       # intraday prices have fat tails, and a warning that fires on every real file is not read


def scan(decl):
    """One pass over the data file; returns the counts and lists behind every check (see main for the keys)."""
    d = decl["data"]
    bs, unit, zone, cols = int(d["bar_seconds"]), d.get("ts_unit") or "s", d.get("ts_zone"), d.get("columns") or {}
    shift, lo, hi = (bs if d.get("stamp") == "close" else 0), _kit.to_epoch(d.get("first_utc")), _kit.to_epoch(d.get("last_utc"))
    r = {k: 0 for k in ("rows", "unreadable", "out_of_order", "dup_same", "dup_diff", "ohlc", "nonpos", "flat", "zero_vol",
                        "ties", "pairs", "outside")}
    lines = {k: [] for k in ("unreadable", "out_of_order", "dup_diff", "ohlc", "nonpos")}
    times, rets, ret_ts, gaps, diffs = array("q"), array("d"), array("q"), [], Counter()

    def note(kind, n):
        r[kind] += 1
        if len(lines[kind]) < 5:
            lines[kind].append(n)

    try:
        f = open(d["path"], newline="", encoding="utf-8-sig")
    except (OSError, TypeError) as e:
        _kit.die(2, f"data file cannot be opened ({e})", "the CSV named in data.path", "correct data.path through declare.py amend")
    with f:
        rd = csv.reader(f)
        names = [h.strip().lower() for h in next(rd, [])]
        idx = []
        for key in ("ts", "open", "high", "low", "close", "volume"):
            want = cols.get(key)
            if want is None and key == "volume":
                idx.append(-1)
            elif str(want).lower() not in names:
                _kit.die(2, f"column {want!r} ({key}) is not in the data header", f"one of {names}", "correct data.columns")
            else:
                idx.append(names.index(str(want).lower()))
        it, io_, ih, il, ic, iv = idx
        n, prev, last_t, last_px = 1, None, None, None
        try:
            for row in rd:
                n += 1
                if not row:
                    continue
                try:
                    t = _kit.parse_ts(row[it], unit, zone) - shift
                except (ValueError, IndexError, OverflowError):
                    note("unreadable", n)
                    continue
                if prev is not None and t < prev:
                    note("out_of_order", n)
                    prev = t
                    continue
                prev = t
                if (lo is not None and t < lo) or (hi is not None and t > hi):
                    r["outside"] += 1
                    continue
                try:
                    o, h, l, c = float(row[io_]), float(row[ih]), float(row[il]), float(row[ic])
                    v = float(row[iv]) if iv >= 0 and row[iv].strip() else 0.0
                    if not (math.isfinite(o) and math.isfinite(h) and math.isfinite(l) and math.isfinite(c)):
                        raise ValueError
                except (ValueError, IndexError):
                    note("unreadable", n)
                    continue
                if t == last_t:
                    if (o, h, l, c) == last_px:
                        r["dup_same"] += 1
                    else:
                        note("dup_diff", n)
                    continue
                if min(o, h, l, c) <= 0:
                    note("nonpos", n)
                elif l > min(o, c) or h < max(o, c) or l > h:
                    note("ohlc", n)
                if last_t is not None:
                    diffs[t - last_t] += 1
                    r["pairs"] += 1
                    r["ties"] += c == last_px[3]
                    if t - last_t > bs and len(gaps) < 200000:
                        gaps.append((last_t + bs, t - bs, (t - last_t) // bs - 1))
                    if t - last_t == bs and c > 0 and last_px[3] > 0:
                        rets.append(math.log(c / last_px[3]))
                        ret_ts.append(t)
                r["rows"] += 1
                r["flat"] += h == l
                r["zero_vol"] += v == 0
                times.append(t)
                last_t, last_px = t, (o, h, l, c)
        except (csv.Error, UnicodeDecodeError) as e:
            _kit.die(2, f"data file is not readable CSV text near line {n} ({e})", "a UTF-8 CSV", "export the bars again as plain CSV")
    by_year = Counter(time.gmtime(t).tm_year for t in times)
    r.update(lines=lines, times=times, rets=rets, ret_ts=ret_ts, gaps=gaps, diffs=diffs, has_volume=iv >= 0,
             by_year={str(y): k for y, k in sorted(by_year.items()) if k})
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description="Report-only data check of a frozen experiment: PASS or FAIL, with every defect listed.")
    ap.add_argument("--exp", required=True, help="the experiment folder")
    ap.add_argument("--json", action="store_true", help="print the result JSON instead of text")
    a = ap.parse_args(argv)
    decl, lock = _kit.load_decl(a.exp)
    d, sha = decl["data"], _kit.check_data(decl, lock)
    r, bs = scan(decl), int(d["bar_seconds"])
    times, rows, at = r["times"], r["rows"], lambda k: ", ".join(map(str, r["lines"][k]))
    first, last = (times[0], times[-1]) if rows else (None, None)
    modal = r["diffs"].most_common(1)[0][0] if r["diffs"] else None
    missing = max(0, (last - first) // bs + 1 - rows) if rows else 0
    largest = max((g[2] for g in r["gaps"]), default=0)
    share = lambda k: r[k] / rows if rows else 0.0
    fails, warns, notes, outliers = [], [], [], []
    if not rows:
        fails.append("zero rows: the file holds no readable bar inside the declared range")
    if r["unreadable"]:
        fails.append(f"{r['unreadable']} rows cannot be parsed (a timestamp or a price is not a finite number); first at line {at('unreadable')}")
    if r["out_of_order"]:
        fails.append(f"{r['out_of_order']} rows are out of time order; first at line {at('out_of_order')}")
    if r["dup_diff"]:
        fails.append(f"{r['dup_diff']} rows repeat an open time with different prices; first at line {at('dup_diff')}")
    if r["ohlc"]:
        fails.append(f"{r['ohlc']} rows break the bar rules (low <= open, close <= high); first at line {at('ohlc')}")
    if r["nonpos"]:
        fails.append(f"{r['nonpos']} rows hold a price at or below zero; first at line {at('nonpos')}")
    if modal is not None and modal != bs:
        fails.append(f"bars are {modal} s apart most often, but data.bar_seconds declares {bs}")
    if r["dup_same"]:
        warns.append(f"{r['dup_same']} identical duplicate rows (the later steps skip them)")
    if missing:
        warns.append(f"{missing} bars are missing in {len(r['gaps'])} gaps, the largest {largest} bars: an event or exit on a "
                     "missing bar is dropped and listed, never filled")
    if share("flat") > SHARE:
        warns.append(f"{share('flat'):.1%} of bars are flat (high equals low)")
    if r["has_volume"] and share("zero_vol") > SHARE:
        warns.append(f"{share('zero_vol'):.1%} of bars have zero volume")
    if len(r["rets"]) > 1:
        med = statistics.median(r["rets"])
        sigma = 1.4826 * statistics.median(abs(x - med) for x in r["rets"])
        if sigma > 0:
            hits = [(t, x) for t, x in zip(r["ret_ts"], r["rets"]) if abs(x - med) > SIGMAS * sigma]
            outliers = [{"ts": t, "return_bp": x * 1e4, "sigmas": abs(x - med) / sigma} for t, x in hits[:SHOWN]]
            if hits:
                part = len(hits) / len(r["rets"])
                msg = (f"{len(hits)} of {len(r['rets'])} one-bar returns ({part:.3%}) lie beyond {SIGMAS:g} robust sigmas (none is removed; "
                       f"the first {min(len(hits), SHOWN)} are under outliers in results/data_check.json); first at "
                       + ", ".join(_kit.utc_iso(t) for t, _ in hits[:3]))
                if part > OUTLIER_SHARE:
                    warns.append(msg)
                else:
                    notes.append("note: " + msg + f". A share at or below {OUTLIER_SHARE:.1%} is usual for intraday prices")
        else:
            notes.append("outlier check skipped: the median absolute deviation of one-bar returns is 0")
    if rows and last + bs > time.time():
        warns.append("the last bar's interval has not ended by this machine's clock: it may be incomplete")
    missing_events = None
    if decl.get("kind") == "clock" and rows and not fails:
        import events
        bars = _kit.Bars(bs)
        bars.ts = times
        missing_events = events.build_events(decl, lock, bars, "all", 0, exp=a.exp)[1]["dropped_missing_entry"]
        if missing_events:
            warns.append(f"{len(missing_events)} declared event times have no bar (events.py drops and lists them): "
                         + ", ".join(m["date"] for m in missing_events[:10]) + (" ..." if len(missing_events) > 10 else ""))
    gap_path = os.path.join(a.exp, "results", "missing_bars.csv")
    os.makedirs(os.path.dirname(gap_path), exist_ok=True)
    if r["gaps"]:
        with open(gap_path, "w", newline="", encoding="utf-8") as f:
            f.write("gap_start_utc,gap_end_utc,bars_missing\n" + "".join(f"{g[0]},{g[1]},{g[2]}\n" for g in r["gaps"]))
    elif os.path.exists(gap_path):
        os.remove(gap_path)
    code = 1 if fails else 0
    payload = {"rows": rows, "first_utc": first, "last_utc": last, "bar_seconds": modal if modal is not None else bs,
               "ts_unit": d.get("ts_unit"), "duplicates_identical": r["dup_same"], "duplicates_conflicting": r["dup_diff"],
               "out_of_order": r["out_of_order"], "missing_bars": missing, "largest_gap_bars": largest,
               "ohlc_violations": r["ohlc"], "nonpositive_prices": r["nonpos"], "flat_share": share("flat"),
               "zero_volume_share": share("zero_vol") if r["has_volume"] else None,
               "tie_rate": r["ties"] / r["pairs"] if r["pairs"] else 0.0, "outliers": outliers, "rows_by_year": r["by_year"],
               "fails": fails, "warns": warns, "result": "FAIL" if fails else "PASS", "notes": notes,
               "bar_seconds_declared": bs, "unreadable_rows": r["unreadable"], "rows_outside_declared_range": r["outside"],
               "gaps": len(r["gaps"]), "missing_event_bars": missing_events, "data_sha256": sha}
    out = _kit.write_result(a.exp, "data_check.json", payload, code, script="checkdata")
    iso = lambda t: "none" if t is None else _kit.utc_iso(t)
    text = [f"data: {rows} bars of {payload['bar_seconds']} s from {iso(first)} to {iso(last)}; by year: "
            + ", ".join(f"{y} {k}" for y, k in r["by_year"].items()),
            f"duplicates: {r['dup_same']} identical, {r['dup_diff']} conflicting; out of order {r['out_of_order']}; unreadable {r['unreadable']}",
            f"missing bars: {missing} (largest gap {largest} bars)" + (" -> results/missing_bars.csv" if r["gaps"] else ""),
            f"flat bars {share('flat'):.2%}; zero-volume bars " + (f"{share('zero_vol'):.2%}" if r["has_volume"] else "n/a")
            + f"; exactly-zero close-to-close returns {payload['tie_rate']:.2%}"]
    text += [f"  gap {iso(g[0])} to {iso(g[1])}: {g[2]} bars" for g in r["gaps"][:SHOWN]]
    text += [f"  ... {len(r['gaps']) - SHOWN} more gaps in results/missing_bars.csv"] if len(r["gaps"]) > SHOWN else []
    text += ["FAIL: " + x for x in fails] + ["WARNING: " + x for x in warns] + notes
    text.append("DATA CHECK: PASS" if not fails else f"DATA CHECK: FAIL ({len(fails)} problems)")
    q = shlex.quote
    nxt = f"python3 {q(os.path.join(HERE, 'events.py'))} --exp {q(os.path.abspath(a.exp))}" if not fails else (
        "show the user the FAIL lines and stop: nothing is repaired here; " + _kit.DATA_FIX.split("; ", 1)[1])
    result = f"the data passed with {len(warns)} warning(s)" if not fails else f"the data failed {len(fails)} check(s) and cannot be used as it is"
    _kit.finish(out, result, nxt, code, a.json, text)


if __name__ == "__main__":
    _kit.guard(main)
