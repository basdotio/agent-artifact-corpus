#!/usr/bin/env python3
"""Tests of checkdata.py through its command line, on one-minute files typed here (20 rows unless said)."""
from __future__ import annotations

import json, os, random, shlex, subprocess, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path[:0] = [HERE, SCRIPTS]
import _kit, declare

T0 = 1672617600  # 2023-01-02T00:00:00Z, a Monday
HEADER = "open_time,open,high,low,close,volume"


def typed(n=20, closes=None):
    """n one-minute rows [ms stamp, open, high, low, close, volume]; each open is the previous close."""
    rng = random.Random(5)
    closes = closes or [round(100 + rng.uniform(-0.3, 0.3), 2) for _ in range(n)]
    rows, prev = [], closes[0]
    for k, c in enumerate(closes):
        rows.append([(T0 + 60 * k) * 1000, prev, max(prev, c) + 0.5, min(prev, c) - 0.5, c, 10 + k])
        prev = c
    return rows


def case(tmp, name, rows, kind="file", bar_seconds=60, event=None):
    """Write the rows and a frozen experiment around them (the lock is built without declare.py check: these files
    are far too short to pass it). Returns (experiment folder, data path)."""
    exp, data = os.path.join(tmp, name), os.path.join(tmp, name + ".csv")
    os.makedirs(exp)
    with open(data, "w", encoding="utf-8") as f:
        f.write("\n".join([HEADER] + [",".join(str(x) for x in r) for r in rows]) + "\n")
    with open(os.path.join(exp, "events.csv"), "w", encoding="utf-8") as f:
        f.write("decision_ts,side\n")
    decl = {"schema": 1, "kind": kind,
            "idea": {"side": "long", "event": event or {"events_file": "events.csv"},
                     "trade": {"hold_minutes": 1, "stop_bp": None, "target_bp": None}, "params": {}, "grid": {},
                     "prior_looks": {"text": "none", "variants_seen": 0}},
            "costs": {"fee_bp_per_fill": 5, "half_spread_bp_per_fill": 1, "source": "test"},
            "data": {"path": data, "columns": dict(zip(("ts", "open", "high", "low", "close", "volume"), HEADER.split(","))),
                     "ts_unit": "ms", "ts_zone": "UTC", "stamp": "open", "bar_seconds": bar_seconds, "first_utc": None, "last_utc": None},
            "method": declare.method_defaults(kind)}
    decl["method"]["split"]["date_utc"] = "2023-01-03"
    with open(os.path.join(exp, "declarations.json"), "w", encoding="utf-8") as f:
        json.dump(decl, f)
    declare.make_lock(exp, decl)
    return exp, data


def check(exp, as_json=True):
    """Run checkdata.py; returns (exit code, parsed JSON or the text, stderr)."""
    p = subprocess.run([sys.executable, "-B", os.path.join(SCRIPTS, "checkdata.py"), "--exp", exp] + (["--json"] if as_json else []),
                       capture_output=True, text=True)
    return p.returncode, (json.loads(p.stdout) if as_json and p.stdout.strip() else p.stdout), p.stderr


def main():
    before = sorted(os.listdir(SCRIPTS))
    with tempfile.TemporaryDirectory() as tmp:
        # clean file: PASS, and the script changes nothing in the data
        exp, data = case(tmp, "clean", typed())
        sha = declare.file_sha256(data)
        code, text, _ = check(exp, as_json=False)
        tail = text.rstrip().splitlines()[-3:]
        assert code == 0 and tail[0] == "DATA CHECK: PASS" and tail[1].startswith("RESULT: ") and tail[2].startswith("NEXT: python3 ") and os.path.basename(shlex.split(tail[2][6:])[1]) == "events.py" and "--exp" in shlex.split(tail[2][6:]), text
        assert len(text.splitlines()) <= 45 and declare.file_sha256(data) == sha
        doc = _kit.read_json(os.path.join(exp, "results", "data_check.json"))
        assert list(doc)[:4] == ["script", "decl_sha256", "created_utc", "exit_code"] and doc["script"] == "checkdata"
        assert doc["decl_sha256"] == _kit.read_json(os.path.join(exp, "declarations.lock"))["decl_sha256"]
        assert (doc["result"], doc["rows"], doc["missing_bars"], doc["bar_seconds"], doc["ts_unit"]) == ("PASS", 20, 0, 60, "ms")
        assert (doc["first_utc"], doc["last_utc"], doc["rows_by_year"]) == (T0, T0 + 19 * 60, {"2023": 20})
        assert doc["fails"] == [] and doc["flat_share"] == 0 and doc["zero_volume_share"] == 0 and doc["outliers"] == []
        assert not os.path.exists(os.path.join(exp, "results", "missing_bars.csv"))
        # the file is edited after the freeze: refused, whatever the edit
        with open(data, "a", encoding="utf-8") as f:
            f.write(f"{(T0 + 1200) * 1000},100,101,99,100,1\n")
        code, _, err = check(exp)
        assert code == 3 and "sha256 differs" in err and "before out-of-sample is opened" in err and err.splitlines()[1].startswith("EXPECTED:") and err.splitlines()[2].startswith("TRY:")
        # rows 7 and 8 removed: listed as one gap of two bars, PASS with a warning
        rows = typed()
        exp, _ = case(tmp, "gap", rows[:6] + rows[8:])
        code, doc, _ = check(exp)
        assert code == 0 and (doc["missing_bars"], doc["largest_gap_bars"], doc["rows"], doc["result"]) == (2, 2, 18, "PASS")
        assert len(doc["warns"]) == 1 and "2 bars are missing" in doc["warns"][0]
        gaps = open(os.path.join(exp, "results", "missing_bars.csv")).read().splitlines()
        assert gaps == ["gap_start_utc,gap_end_utc,bars_missing", f"{T0 + 360},{T0 + 420},2"]
        assert "WARNING: 2 bars are missing" in check(exp, as_json=False)[1]
        # row 5 repeated identically: a warning; repeated with another close: a FAIL
        exp, _ = case(tmp, "same", rows[:5] + [rows[4]] + rows[5:])
        code, doc, _ = check(exp)
        assert code == 0 and doc["duplicates_identical"] == 1 and doc["rows"] == 20 and doc["result"] == "PASS"
        exp, _ = case(tmp, "conflict", rows[:5] + [rows[4][:4] + [rows[4][4] + 0.1, 1]] + rows[5:])
        code, doc, _ = check(exp)
        assert code == 1 and doc["duplicates_conflicting"] == 1 and doc["result"] == "FAIL" and doc["exit_code"] == 1
        # one row with its high below its close: counted and named by line number (row 12 is file line 13)
        broken = [list(r) for r in rows]
        broken[11][2] = broken[11][4] - 0.2
        exp, _ = case(tmp, "ohlc", broken)
        code, doc, _ = check(exp)
        assert code == 1 and doc["ohlc_violations"] == 1 and "line 13" in doc["fails"][0], doc["fails"]
        code, text, _ = check(exp, as_json=False)
        assert code == 1 and "DATA CHECK: FAIL (1 problems)" in text and "FAIL: 1 rows break the bar rules" in text
        assert "events.py" not in text.splitlines()[-1] and text.splitlines()[-1].startswith("NEXT: show the user")
        # a zero price, two rows swapped, an unreadable price, a header with no rows
        zero = [list(r) for r in rows]
        zero[3][3] = 0
        code, doc, _ = check(case(tmp, "zero", zero)[0])
        assert code == 1 and doc["nonpositive_prices"] == 1
        code, doc, _ = check(case(tmp, "swapped", rows[:9] + [rows[10], rows[9]] + rows[11:])[0])
        assert code == 1 and doc["out_of_order"] == 1 and "out of time order" in doc["fails"][0]
        text_row = [list(r) for r in rows]
        text_row[6][4] = "NaN"
        code, doc, _ = check(case(tmp, "nan", text_row)[0])
        assert code == 1 and doc["unreadable_rows"] == 1 and "line 8" in doc["fails"][0]
        code, doc, _ = check(case(tmp, "empty", [])[0])
        assert code == 1 and doc["rows"] == 0 and "zero rows" in doc["fails"][0]
        # ten bars closing 1,1,2,2,3,4,5,6,7,8: two of the nine close-to-close returns are exactly zero
        code, doc, _ = check(case(tmp, "ties", typed(closes=[1, 1, 2, 2, 3, 4, 5, 6, 7, 8]))[0])
        assert code == 0 and abs(doc["tie_rate"] - 2 / 9) < 1e-12
        # the declared bar size is wrong
        code, doc, _ = check(case(tmp, "bar300", rows, bar_seconds=300)[0])
        assert code == 1 and "300" in doc["fails"][0] and doc["bar_seconds"] == 60 and doc["bar_seconds_declared"] == 300
        # one bar 400 times the size of its neighbours is listed as an outlier and left in place
        wild = typed(60)
        wild[30][4], wild[31][1] = wild[30][4] * 1.5, wild[30][4] * 1.5
        wild[30][2], wild[31][2] = wild[30][4] + 1, wild[31][1] + 1
        code, doc, _ = check(case(tmp, "wild", wild)[0])
        assert code == 0 and doc["rows"] == 60 and doc["outliers"][0]["ts"] == T0 + 30 * 60 and doc["outliers"][0]["sigmas"] > 20
        # a clock idea: the event time whose bar is missing is listed with its date
        event = {"local_time": "00:05", "zone": "UTC", "days": "all", "skip_dates_file": None}
        code, doc, _ = check(case(tmp, "clock", rows, kind="clock", event=event)[0])
        assert code == 0 and doc["missing_event_bars"] == []
        code, doc, _ = check(case(tmp, "clockgap", rows[:5] + rows[6:], kind="clock", event=event)[0])
        assert code == 0 and doc["missing_event_bars"] == [{"date": "2023-01-02", "decision_ts": T0 + 300}] and doc["missing_bars"] == 1
        # not frozen, and a mapped column that is not in the file
        exp, _ = case(tmp, "nolock", rows)
        os.remove(os.path.join(exp, "declarations.lock"))
        assert check(exp)[0] == 3 and not os.path.exists(os.path.join(exp, "results"))
        exp, data = case(tmp, "nocol", rows)
        text = open(data, encoding="utf-8").read().replace("close", "last")
        with open(data, "w", encoding="utf-8") as f:
            f.write(text)
        decl = _kit.read_json(os.path.join(exp, "declarations.json"))
        declare.make_lock(exp, decl)
        assert check(exp)[0] == 2
    assert sorted(os.listdir(SCRIPTS)) == before, "a file was left in the skill folder"


if __name__ == "__main__":
    main()
    print("test_checkdata.py: all passed")
