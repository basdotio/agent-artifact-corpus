#!/usr/bin/env python3
"""Numerical tests of _kit.py against hand-computed and published values. Plain asserts."""
from __future__ import annotations

import contextlib, datetime as dt, hashlib, io, json, math, os, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import _kit as k
import synth


def near(a, b, tol=1e-5):
    return abs(a - b) <= tol


def exits(code, fn, *args, **kw):
    """Run fn, require sys.exit(code), return what it wrote to stderr."""
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            fn(*args, **kw)
    except SystemExit as e:
        assert e.code == code, f"exit {e.code}, expected {code}: {err.getvalue()}"
        return err.getvalue()
    raise AssertionError(f"{fn.__name__} did not exit {code}")


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def test_hash_and_declarations(tmp):
    assert k.canonical_sha256({"b": 1, "a": [1, 2]}).startswith("94a786c3662bc7be")
    decl = {"schema": 1, "kind": "clock", "idea": {"side": "long", "trade": {"hold_minutes": 60}}}
    sha = k.canonical_sha256(decl)
    write(os.path.join(tmp, "declarations.json"), json.dumps(decl))
    assert "not frozen" in exits(3, k.load_decl, tmp)
    assert k.load_decl(tmp, need_lock=False) == (decl, None)
    write(os.path.join(tmp, "declarations.lock"), json.dumps({"decl_sha256": sha, "cells": [{"index": 0}]}))
    assert k.load_decl(tmp)[1]["decl_sha256"] == sha
    # key order and whitespace of the source file do not matter; one value does
    write(os.path.join(tmp, "declarations.json"),
          '{ "kind":"clock",\n\n  "idea": {"trade": {"hold_minutes": 60}, "side": "long"},   "schema": 1 }')
    assert k.load_decl(tmp)[0] == decl
    decl["idea"]["trade"]["hold_minutes"] = 61
    write(os.path.join(tmp, "declarations.json"), json.dumps(decl))
    assert "changed since the freeze" in exits(3, k.load_decl, tmp)
    assert k.load_decl(tmp, need_lock=False)[0] == decl
    assert k.cells({"cells": [{"index": 0}]}) == [{"index": 0}]
    assert "declarations.json" in exits(3, k.load_decl, os.path.join(tmp, "nowhere"))
    # results: header keys first, step-order guard, RESULT:/NEXT: as the last two lines
    out = k.write_result(tmp, "effect_dev.json", {"gate": {"pass": False}, "x": float("nan")}, 1, script="effect")
    assert list(out)[:4] == ["script", "decl_sha256", "created_utc", "exit_code"] and out["decl_sha256"] == sha
    assert out["x"] is None and len(out["created_utc"]) == 20 and out["created_utc"].endswith("Z")
    assert k.require(tmp, "effect_dev.json")["exit_code"] == 1
    assert k.require(tmp, "effect_dev.json", "gate.pass", False)["script"] == "effect"
    assert "gate.pass" in exits(3, k.require, tmp, "effect_dev.json", "gate.pass", True)
    exits(3, k.require, tmp, "effect_dev.json", "gate.missing")
    assert "out of order" in exits(3, k.require, tmp, "sweep.json")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exits(1, k.finish, out, "gate failed", "python3 verdict.py --exp EXP", 1, False, ["CHARACTERISATION GATE: FAIL (x)"])
    assert buf.getvalue().splitlines()[-2:] == ["RESULT: gate failed", "NEXT: python3 verdict.py --exp EXP"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exits(0, k.finish, out, "r", "n", 0, True)
    assert json.loads(buf.getvalue())["RESULT"] == "r"
    # guard: an exception nobody expected is three stderr lines and exit 2, never a traceback with exit 1; exits pass through
    def boom():
        return dict(["lookback", 20])
    text = exits(2, k.guard, boom)
    assert text.startswith("ERROR: ValueError: ") and "\nEXPECTED: " in text and "\nTRY: " in text and "Traceback" not in text and "test_kit.py line" in text
    exits(3, k.guard, lambda: k.die(3, "a", "b", "c"))
    assert k.guard(lambda: None) is None
    # check_data: one rule and one message for a data file that is not the frozen one
    data = os.path.join(tmp, "fingerprint.csv")
    write(data, "open_time,open\n1,2\n")
    raw = open(data, "rb").read()
    good = {"data": {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}}
    assert k.check_data({"data": {"path": data}}, good) == good["data"]["sha256"]
    write(data, "open_time,open\n1,3\n")                     # same size, other bytes
    text = exits(3, k.check_data, {"data": {"path": data}}, good)
    assert "changed since the freeze" in text and "declare.py amend" in text and "new experiment after" in text
    exits(2, k.check_data, {"data": {"path": os.path.join(tmp, "gone.csv")}}, good)
    # title: the instrument once, a long hypothesis cut at a word
    assert k.title("SYNTH", "A made-up instrument drifts up in the hour after 14:00 UTC, for no reason at all") == \
        "SYNTH, A made-up instrument drifts up in the hour after 14:00 UTC ..."
    assert k.title("BTC", "BTC rises") == "BTC rises" and k.title("BTC", "BTCUSDT rises") == "BTC, BTCUSDT rises" and k.title(None, None) == ", "
    assert exits(2, k.die, 2, "a", "b", "c") == "ERROR: a\nEXPECTED: b\nTRY: c\n"


def test_time():
    for text, unit in (("1700000000", "s"), ("1700000000000", "ms"), ("1700000000000000", "us"),
                       ("1700000000000000000", "ns"), ("2023-11-14T22:13:20+00:00", "iso"),
                       ("2023-11-14T22:13:20Z", "iso"), ("2023-11-15 03:43:20+05:30", "iso")):
        assert k.parse_ts(text, unit, "UTC") == 1700000000, text
        assert k.detect_ts_unit(text) == unit and k.parse_ts(text) == 1700000000
    assert k.parse_ts("2023-11-14T17:13:20", "iso", "America/New_York") == 1700000000
    assert k.parse_ts("1700000000000.0", "ms", "UTC") == 1700000000
    assert k.utc_iso(1700000000) == "2023-11-14T22:13:20Z" and k.utc_day(1700000000) == "2023-11-14"
    assert k.to_epoch("2023-11-14") == 1699920000 and k.to_epoch(None) is None and k.to_epoch(5) == 5
    for bad in (("abc", "s", "UTC"), ("nan", "ms", "UTC"), ("2023-13-40", "iso", "UTC"), ("2023-11-14T17:13:20", "iso", None)):
        try:
            k.parse_ts(*bad)
        except ValueError:
            continue
        raise AssertionError(f"parse_ts{bad} did not raise ValueError")
    ny = lambda d: k.utc_iso(k.local_to_utc(d, "09:30", "America/New_York"))[11:16]
    expected = {"2023-03-10": "14:30", "2023-03-13": "13:30", "2023-11-03": "13:30", "2023-11-06": "14:30"}
    assert {d: ny(d) for d in expected} == expected
    assert k.local_to_utc(dt.date(2023, 7, 1), "14:00", "UTC") == k.parse_ts("2023-07-01T14:00:00Z")
    counts, mismatches, day = {}, 0, dt.date(2007, 1, 1)
    have_zones = k.zone_rule("America/New_York") == "zoneinfo"
    try:
        while day <= dt.date(2035, 12, 31):
            k.FORCE_TZ_FALLBACK = False
            a = k.local_to_utc(day, "09:30", "America/New_York")
            k.FORCE_TZ_FALLBACK = True
            mismatches += a != k.local_to_utc(day, "09:30", "America/New_York")
            if day.year == 2024:
                counts[k.utc_iso(a)[11:16]] = counts.get(k.utc_iso(a)[11:16], 0) + 1
            day += dt.timedelta(days=1)
        assert counts == {"13:30": 238, "14:30": 128}, counts
        assert mismatches == 0, f"{mismatches} days differ between zoneinfo and the US fallback"
        assert k.zone_rule("America/New_York") == "built-in US fallback" and k.zone_rule("UTC") == "UTC"
        assert "Europe/Paris" in exits(2, k.local_to_utc, "2024-06-03", "09:00", "Europe/Paris")
        assert k.local_to_utc("2024-06-03", "09:00", "UTC") == 1717405200
    finally:
        k.FORCE_TZ_FALLBACK = False
    real, k.ZoneInfo = k.ZoneInfo, lambda zone: (_ for _ in ()).throw(KeyError(zone))  # a machine with no tz data
    try:
        assert ny("2023-03-13") == "13:30" and ny("2023-03-10") == "14:30"
        exits(2, k.parse_ts, "2023-11-14T17:13:20", "iso", "Europe/Paris")
    finally:
        k.ZoneInfo = real
    if have_zones:
        assert k.utc_iso(k.local_to_utc("2024-07-01", "09:00", "Europe/Paris"))[11:16] == "07:00"
    exits(2, k.local_to_utc, "2024-06-03", "09:00", "Mars/Olympus")


def test_statistics():
    for n, closed, exact, used in ((2, 0.519755, 0.564190, 0.564190), (3, 0.852804, 0.846284, 0.852804)):
        e = k.emax(n)
        assert near(e.closed, closed) and near(e.exact, exact) and near(e.used, used), (n, e)
    assert tuple(k.emax(1)) == (0.0, 0.0, 0.0) and tuple(k.emax(0)) == (0.0, 0.0, 0.0)
    assert near(k.emax(2).exact, 1 / math.sqrt(math.pi), 1e-9) and near(k.emax(3).exact, 1.5 / math.sqrt(math.pi), 1e-9)
    for n, used in ((9, 1.520778), (100, 2.530603), (600, 3.106921)):
        assert near(k.emax(n).used, used), n
    assert all(k.emax(n).closed >= k.emax(n).exact for n in range(3, 60))   # closed form is the larger from N = 3
    for n, need in ((1, 1.645), (2, 2.209), (6, 2.945), (9, 3.166)):       # development t needed for DSR 0.95
        assert near(k.emax(n).used + 1.645, need, 6e-4), n
    x = [10, -5, 20, 0, 15, 5]
    assert k.mean(x) == 7.5 and k.median(x) == 7.5 and near(k.sd(x), 9.354143)
    assert near(k.tstat(x), 1.963961) and near(k.sharpe(x), 0.801784)
    assert near(k.lag1_autocorr([1, 2, 3, 4, 5]), 0.4, 1e-12)
    assert k.sd([3.0]) == 0.0 and k.sharpe([2, 2, 2]) == 0.0 and k.tstat([2, 2, 2]) == 0.0 and k.mean([]) == 0.0
    sk, ku = k.skew_kurt([1, 2, 3, 4, 10])     # by hand: m 4, m2 10, m3 36, m4 278.8
    assert near(sk, 36 / 10 ** 1.5, 1e-12) and near(ku, 2.788, 1e-12) and k.skew_kurt([1, 1]) == (0.0, 3.0)
    trades = [{"day": "2024-01-02", "net_bp": 10.0, "gross_bp": 22.0}, {"day": "2024-01-03", "net_bp": -20.0, "gross_bp": -8.0},
              {"entry_ts": 1704207600, "net_bp": 30.0, "gross_bp": 42.0}]          # 2024-01-02T15:00Z
    assert k.day_sums(trades) == (["2024-01-02", "2024-01-03"], [40.0, -20.0])
    assert k.day_sums(trades, "gross_bp")[1] == [64.0, -8.0] and k.day_sums([]) == ([], [])
    # published vectors: Deflated Sharpe paper example, then the Sharpe-frontier PSR example
    sr, spread = 2.5 / math.sqrt(250), math.sqrt(1 / 500)
    assert near(sr, 0.158114, 1e-6) and near(spread * k.emax(100).used, 0.113172) and near(spread * k.emax(46).used, 0.100362)
    assert near(k.psr(sr, 1250, -3, 10, spread * k.emax(100).used), 0.900397)
    assert near(k.psr(sr, 1250, -3, 10, spread * k.emax(46).used), 0.950502)
    assert near(k.psr(sr, 1250, 0, 3, spread * k.emax(88).used), 0.950491)
    assert near(k.psr(0.036 / 0.079, 24, -2.448, 10.164), 0.9127, 5e-4)
    assert near(k.psr(0.036 / 0.079, 36, -2.448, 10.164), 0.9530, 5e-4)
    assert near(0.1 * k.emax(100).closed, 0.253060) and near(k.psr(0.08225, 400), 0.9495, 1e-4)
    assert near(k.min_trl(0.1), 272.907, 1e-3) and math.ceil(k.min_trl(0.13)) == 163 and k.min_trl(0.0) == math.inf
    assert near(k.Phi(k.Z95), 0.95, 1e-6) and near(k.PhiInv(0.95), k.Z95, 1e-6)


def test_bars(tmp):
    t0, path = 1685577600, os.path.join(tmp, "bars.csv")          # 2023-06-01T00:00Z, one-minute bars
    rows = ["open_time,open,high,low,close,volume,close_time,quote_volume"]
    for i in range(10):
        p = 100.0 + i
        rows.append(f"{(t0 + 60 * i) * 1000},{p},{p + 2},{p - 1},{p + 1},{5 + i},{(t0 + 60 * i) * 1000 + 59999},1")
    rows.insert(4, rows[3])                                        # an identical duplicate row is skipped
    oos = [f"{(t0 + 60 * i) * 1000},NaN,NaN,NaN,NaN,NaN,0,0" for i in range(10, 14)]
    write(path, "\n".join(rows + oos) + "\n")
    data = {"path": path, "ts_unit": "ms", "ts_zone": "UTC", "stamp": "open", "bar_seconds": 60, "first_utc": None, "last_utc": None,
            "columns": {"ts": "open_time", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}}
    lock = {"split_utc": t0 + 600}
    b = k.load_bars({"data": data}, lock, "dev")                   # never parses the NaN rows
    assert len(b) == 10 == b.first_oos_index and list(b.ts) == [t0 + 60 * i for i in range(10)]
    assert b.open[0] == 100.0 and b.high[9] == 111.0 and b.low[9] == 108.0 and b.close[3] == 104.0 and b.volume[2] == 7.0
    assert b.bar_seconds == 60 and b.index_at(t0 + 120) == 2 and b.index_at(t0 + 121) is None and b.index_at(t0 + 600) is None
    assert "checkdata.py" in exits(3, k.load_bars, {"data": data}, lock, "all")       # NaN prices are a FAIL
    assert "line 13" in exits(3, k.load_bars, {"data": data}, lock, "oos")
    b = k.load_bars({"data": dict(data, first_utc=t0 + 120, last_utc="2023-06-01T00:05:00Z")}, lock, "dev")
    assert list(b.ts) == [t0 + 60 * i for i in range(2, 6)]
    b = k.load_bars({"data": dict(data, stamp="close", columns=dict(data["columns"], volume=None))}, {"split_utc": t0 + 300}, "dev")
    assert b.ts[0] == t0 - 60 and len(b) == 6 and b.volume[0] == 0.0
    assert "'vol'" in exits(2, k.load_bars, {"data": dict(data, columns=dict(data["columns"], volume="vol"))}, lock, "dev")
    exits(2, k.load_bars, {"data": dict(data, path=path + ".missing")}, lock, "dev")
    exits(2, k.load_bars, {"data": data}, None, "dev")
    w = b.window(5, 3)                                             # closed bars 2, 3, 4 only
    assert w.close == (103.0, 104.0, 105.0) and len(w.ts) == 3 and w.close[-1] == b.close[4] and isinstance(w.open, tuple)
    for attempt in (lambda: w.close[3], lambda: w.bars, lambda: setattr(w, "close", 1), lambda: b.window(2, 3)):
        try:
            attempt()
        except (IndexError, AttributeError, ValueError):
            continue
        raise AssertionError("the window let something through")
    # out-of-sample: ISO stamps with an offset, 40 daily bars, split after day 35: lookback of 30 days is kept
    iso = os.path.join(tmp, "daily.csv")
    day0 = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
    write(iso, "Date,Open,High,Low,Close\n" + "".join(
        f"{(day0 + dt.timedelta(days=i)).isoformat()},{10 + i},{11 + i},{9 + i},{10.5 + i}\n" for i in range(40)))
    d2 = {"path": iso, "ts_unit": "iso", "ts_zone": None, "stamp": "open", "bar_seconds": 86400,
          "columns": {"ts": "date", "open": "open", "high": "high", "low": "low", "close": "close", "volume": None}}
    split = int(day0.timestamp()) + 35 * 86400
    b = k.load_bars({"data": d2}, {"split_utc": split}, "oos")
    assert len(b) == 35 and b.ts[0] == split - 30 * 86400 and b.first_oos_index == 30 and b.ts[30] == split
    assert k.load_bars({"data": d2}, None, "all").first_oos_index == 40
    assert k.load_bars({"data": d2}, {"split_utc": split}, "all").first_oos_index == 35
    # every checkdata FAIL class the loader can see stops it with exit 3
    head, good = "open_time,open,high,low,close,volume\n", "{},100,101,99,100,1\n"
    for name, body in (("zero data rows", ""), ("not ascending", good.format(120) + good.format(60)),
                       ("different prices", good.format(60) + "60,100,101,99,100.5,1\n"), ("bar rules", "60,100,100.5,99,101,1\n"),
                       ("bar rules", "60,100,101,0,100,1\n"), ("cannot be read", "60,100,abc,99,100,1\n"), ("timestamp", "soon,1,1,1,1,1\n")):
        write(path, head + body)
        assert name in exits(3, k.load_bars, {"data": dict(data, ts_unit="s")}, {"split_utc": 10 ** 6}, "dev"), name
    # the synthetic generator is seeded, loads cleanly, and carries the planted effect in its window
    a, c = os.path.join(tmp, "a.csv"), os.path.join(tmp, "c.csv")
    assert synth.generate(a, days=30, bar_seconds=3600, seed=3, effect_bp=40) == 720
    synth.generate(c, days=30, bar_seconds=3600, seed=3, effect_bp=40)
    assert open(a).read() == open(c).read() and open(a).readline().strip() == "open_time,open,high,low,close,volume"
    synth.generate(c, days=30, bar_seconds=3600, seed=3, effect_bp=0)
    planted, plain = (k.load_bars({"data": dict(data, path=p, bar_seconds=3600)}, None, "all") for p in (a, c))
    assert len(planted) == 720 and planted.ts[0] == 1609718400 and planted.ts[1] - planted.ts[0] == 3600
    hour = lambda bars, i: math.log(bars.close[i] / bars.open[i]) * 1e4
    diffs = [hour(planted, i) - hour(plain, i) for i in range(720)]
    assert all(near(d, 40.0 if i % 24 == 14 else 0.0, 0.01) for i, d in enumerate(diffs))
    assert all(planted.open[i + 1] == planted.close[i] for i in range(719))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_hash_and_declarations(tmp)
    test_time()
    test_statistics()
    with tempfile.TemporaryDirectory() as tmp:
        test_bars(tmp)


if __name__ == "__main__":
    main()
    print("test_kit: all assertions passed")
