#!/usr/bin/env python3
"""Tests of events.py: clock, rule and file events through build_events and through the command line."""
from __future__ import annotations

import ast, csv, json, os, shlex, subprocess, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path[:0] = [HERE, SCRIPTS]
import _kit, declare, events, synth

HEADER = "open_time,open,high,low,close,volume"
T0 = 1672617600  # 2023-01-02T00:00:00Z
TOY = '''LOOKBACK = 2
def signal(window, params):
    assert len(window.close) == len(window.ts) == len(window.volume) == LOOKBACK
    try:
        window.close[LOOKBACK]
    except IndexError:
        return 1 if int(window.close[-1]) % params.get("mod", 7) == 0 else 0
    raise AssertionError("indexing past the end of the window did not raise")
'''
COUNTER = "LOOKBACK = 2\ncalls = 0\ndef signal(window, params):\n    global calls\n    calls += 1\n    return 1 if calls % 3 == 0 else 0\n"


def run(script, exp, *args):
    p = subprocess.run([sys.executable, "-B", os.path.join(SCRIPTS, script + ".py"), "--exp", exp, *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def setup(tmp, name, data, kind, event, bar_seconds, split, hold=60, side="long", files=None, grid=None, params=None, check=True):
    """A frozen experiment on `data` (lock built without declare.py check: the fixtures are short), data check run."""
    exp = os.path.join(tmp, name)
    os.makedirs(exp)
    for fname, text in (files or {}).items():
        with open(os.path.join(exp, fname), "w", encoding="utf-8") as f:
            f.write(text)
    decl = {"schema": 1, "kind": kind,
            "idea": {"side": side, "event": event, "trade": {"hold_minutes": hold, "stop_bp": None, "target_bp": None},
                     "params": params or {}, "grid": grid or {}, "prior_looks": {"text": "none", "variants_seen": 0}},
            "costs": {"fee_bp_per_fill": 5, "half_spread_bp_per_fill": 1, "source": "test"},
            "data": {"path": data, "columns": dict(zip(("ts", "open", "high", "low", "close", "volume"), HEADER.split(","))),
                     "ts_unit": "ms", "ts_zone": "UTC", "stamp": "open", "bar_seconds": bar_seconds, "first_utc": None, "last_utc": None},
            "method": declare.method_defaults(kind)}
    decl["method"]["split"]["date_utc"] = split
    with open(os.path.join(exp, "declarations.json"), "w", encoding="utf-8") as f:
        json.dump(decl, f)
    lock = declare.make_lock(exp, decl)
    if check:
        assert run("checkdata", exp)[0] == 0
    return exp, decl, lock


def typed(path, closes, drop=()):
    """One-minute bars with the given closes (bar k opens at T0 + 60 k); indices in `drop` are left out."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(HEADER + "\n" + "".join(f"{(T0 + 60 * k) * 1000},{c},{c + 1},{c - 1},{c},1\n" for k, c in enumerate(closes) if k not in drop))
    return path


def without(src, dst, stamp):
    with open(src, encoding="utf-8") as f, open(dst, "w", encoding="utf-8") as g:
        g.writelines(line for line in f if not line.startswith(f"{stamp * 1000},"))
    return dst


def test_clock(tmp):
    data = os.path.join(tmp, "march.csv")
    synth.generate(data, days=12, bar_seconds=1800, start="2023-03-06")           # 2023-03-06 .. 2023-03-17
    ny = {"local_time": "09:30", "zone": "America/New_York", "days": "weekdays", "skip_dates_file": None}
    exp, decl, lock = setup(tmp, "ny", data, "clock", ny, 1800, "2023-03-18")
    assert run("events", exp, "--json")[0] == 0
    code, out = run("events", exp)
    doc = _kit.read_json(os.path.join(exp, "results", "events.json"))
    assert code == 0 and "event in UTC:" in out and "causality: by construction" in out and os.path.basename(shlex.split(out.splitlines()[-1][6:])[1]) == "effect.py" and "--exp" in shlex.split(out.splitlines()[-1][6:])
    assert out.rstrip().splitlines()[-2].startswith("RESULT: 10 development events")
    assert doc["events"] == {"0": 10} and doc["days_by_utc_time"] == {"14:30": 5, "13:30": 5} and doc["causality"] == "by construction"
    assert doc["dropped_missing_entry"] == [] and doc["dropped_share"] == 0 and doc["replay"] is None and doc["kind"] == "clock"
    assert doc["utc_time_summer"] is None and doc["events_by_year"] == {"2023": 10} and doc["exit_code"] == 0
    with open(os.path.join(exp, "results", "events_dev.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == events.COLUMNS and [r["day"] for r in rows] == [f"2023-03-{d:02d}" for d in (6, 7, 8, 9, 10, 13, 14, 15, 16, 17)]
    assert all(r["decision_ts"] == r["entry_ts"] and r["side"] == "1" and r["segment"] == "dev" for r in rows)
    assert [_kit.utc_iso(int(r["decision_ts"]))[11:16] for r in rows] == ["14:30"] * 5 + ["13:30"] * 5       # the US clock change
    # the 13:30 bar of one day removed: exactly that event is dropped and listed with its date; 1 in 10 is over the limit
    gone = _kit.local_to_utc("2023-03-15", "09:30", "America/New_York")
    exp, decl, lock = setup(tmp, "nybar", without(data, os.path.join(tmp, "nobar.csv"), gone), "clock", ny, 1800, "2023-03-18")
    code, out = run("events", exp)
    doc = _kit.read_json(os.path.join(exp, "results", "events.json"))
    assert code == 1 and doc["dropped_missing_entry"] == [{"date": "2023-03-15", "decision_ts": gone}] and doc["events"] == {"0": 9}
    assert doc["dropped_share"] == 0.1 and "2023-03-15" in out and "dropped" in out.rstrip().splitlines()[-2]
    # every day, with and without a skip file; short side; a list of weekday numbers
    utc = {"local_time": "14:00", "zone": "UTC", "days": "all", "skip_dates_file": None}
    data = os.path.join(tmp, "two_weeks.csv")
    synth.generate(data, days=14, bar_seconds=1800, start="2023-03-06")
    exp, decl, lock = setup(tmp, "all", data, "clock", utc, 1800, "2023-03-20", side="short", check=False)
    bars = _kit.load_bars(decl, lock, "dev")
    ev, counts = events.build_events(decl, lock, bars, "dev", 0, exp=exp)
    assert len(ev) == 14 and {e["side"] for e in ev} == {-1} and counts["dropped_straddles_split"] == 0
    skip = {**utc, "skip_dates_file": "skip.txt"}
    exp, decl, lock = setup(tmp, "skip", data, "clock", skip, 1800, "2023-03-20", files={"skip.txt": "2023-03-08\n"}, check=False)
    ev, _ = events.build_events(decl, lock, bars, "dev", 0)                     # no exp: the lock's stored path is used
    assert len(ev) == 13 and "2023-03-08" not in [e["day"] for e in ev]
    exp, decl, lock = setup(tmp, "tue", data, "clock", {**utc, "days": [1, 6]}, 1800, "2023-03-20", check=False)
    assert [e["day"][8:] for e in events.build_events(decl, lock, bars, "dev", 0)[0]] == ["07", "12", "14", "19"]
    # split: an event one bar before the split with a two-bar hold would exit after it, so it is dropped and counted
    late = {**utc, "local_time": "23:30"}
    exp, decl, lock = setup(tmp, "split", data, "clock", late, 1800, "2023-03-13", check=False)
    bars = _kit.load_bars(decl, lock, "dev")
    ev, counts = events.build_events(decl, lock, bars, "dev", 0)
    assert counts["dropped_straddles_split"] == 1 and len(ev) == 6 and ev[-1]["day"] == "2023-03-11"
    oos = _kit.load_bars(decl, lock, "oos")
    ev, counts = events.build_events(decl, lock, oos, "oos", 0)
    assert len(ev) == 7 and ev[0]["day"] == "2023-03-13" and all(e["decision_ts"] >= lock["split_utc"] for e in ev)


def test_rule(tmp):
    closes = [100 + k for k in range(30)]                                          # 105, 112, 119, 126 are multiples of 7
    rule = {"rule_file": "rule.py"}
    exp, decl, lock = setup(tmp, "toy", typed(os.path.join(tmp, "toy.csv"), closes), "rule", rule, 60, "2023-01-03", hold=1,
                            files={"rule.py": TOY})
    bars = _kit.load_bars(decl, lock, "dev")
    ev, counts = events.build_events(decl, lock, bars, "dev", 0, exp=exp)
    assert [bars.index_at(e["entry_ts"]) for e in ev] == [6, 13, 20, 27] and counts["skipped_gap_in_lookback"] == 0
    assert all(e["decision_ts"] == e["entry_ts"] and e["side"] == 1 for e in ev)
    code, out = run("events", exp)
    doc = _kit.read_json(os.path.join(exp, "results", "events.json"))
    assert code == 0 and doc["causality"] == "checked: 0 differences in 28 probes" and "causality: checked" in out, out
    assert doc["replay"] == {"probes": 28, "differences": 0, "first_mismatches": []} and doc["events"] == {"0": 4}
    # every bar from index 15 on overwritten: decisions before it do not move (the rule never sees the bar it enters on)
    later = closes[:15] + [7 * c for c in closes[15:]]
    exp2, decl2, lock2 = setup(tmp, "toy2", typed(os.path.join(tmp, "toy2.csv"), later), "rule", rule, 60, "2023-01-03", hold=1,
                               files={"rule.py": TOY}, check=False)
    ev2, _ = events.build_events(decl2, lock2, _kit.load_bars(decl2, lock2, "dev"), "dev", 0, exp=exp2)
    cut = T0 + 15 * 60
    assert [e for e in ev2 if e["entry_ts"] <= cut] == [e for e in ev if e["entry_ts"] <= cut] and len(ev2) == 2 + 14
    # a short-only idea takes none of the +1 returns; a gridded parameter gives one event list per parameter set
    exp3, decl3, lock3 = setup(tmp, "short", decl["data"]["path"], "rule", rule, 60, "2023-01-03", hold=1, side="short",
                               files={"rule.py": TOY}, check=False)
    assert events.build_events(decl3, lock3, bars, "dev", 0, exp=exp3)[0] == []
    exp4, decl4, lock4 = setup(tmp, "psets", decl["data"]["path"], "rule", rule, 60, "2023-01-03", hold=1, files={"rule.py": TOY},
                               params={"mod": 7}, grid={"params.mod": [7, 10]})
    assert run("events", exp4)[0] == 0
    doc = _kit.read_json(os.path.join(exp4, "results", "events.json"))
    assert doc["psets"] == [0, 1] and doc["events"] == {"0": 4, "1": 2} and doc["replay"]["probes"] == 56
    # a gap inside the lookback: the two decisions whose window spans the missing bar are skipped and counted
    exp5, decl5, lock5 = setup(tmp, "gap", typed(os.path.join(tmp, "gap.csv"), closes, drop=(10,)), "rule", rule, 60, "2023-01-03",
                               hold=1, files={"rule.py": TOY}, check=False)
    gapped = _kit.load_bars(decl5, lock5, "dev")
    ev5, counts5 = events.build_events(decl5, lock5, gapped, "dev", 0, exp=exp5)
    assert counts5["skipped_gap_in_lookback"] == 2 and [e["entry_ts"] for e in ev5] == [e["entry_ts"] for e in ev]
    # hidden state: a rule that counts its own calls decides differently when it sees one bar alone
    exp6, _, _ = setup(tmp, "state", decl["data"]["path"], "rule", rule, 60, "2023-01-03", hold=1, files={"rule.py": COUNTER})
    code, out = run("events", exp6)
    doc = _kit.read_json(os.path.join(exp6, "results", "events.json"))
    assert code == 1 and "causality: FAIL" in out and doc["replay"]["differences"] == 9 and len(doc["replay"]["first_mismatches"]) == 3
    assert doc["causality"].startswith("FAIL") and doc["exit_code"] == 1 and "effect.py" not in out.splitlines()[-1]
    # a rule file with no LOOKBACK, one that raises, and one edited after the freeze
    exp7, _, _ = setup(tmp, "nolb", decl["data"]["path"], "rule", rule, 60, "2023-01-03", hold=1,
                       files={"rule.py": "def signal(window, params):\n    return 0\n"})
    code, out = run("events", exp7)
    assert code == 2 and "LOOKBACK" in out and not os.path.exists(os.path.join(exp7, "results", "events.json"))
    with open(os.path.join(exp7, "rule.py"), "w", encoding="utf-8") as f:
        f.write(TOY)
    code, out = run("events", exp7)
    assert code == 3 and "rule.py changed since the freeze" in out
    exp8, _, _ = setup(tmp, "raises", decl["data"]["path"], "rule", rule, 60, "2023-01-03", hold=1,
                       files={"rule.py": "LOOKBACK = 1\ndef signal(window, params):\n    return window.nothing\n"})
    assert run("events", exp8)[0] == 2
    # the rule file is ordinary Python run on the user's machine: its text is checked before any of it runs, so that
    # loading it (declare.py check does, before the user has accepted the draft) cannot do anything
    mark = os.path.join(tmp, "SIDE_EFFECT.txt")
    body = "LOOKBACK = 2\ndef signal(window, params):\n    return 0\n"
    for n, (text, word) in enumerate([
            (f"import os\nopen({mark!r}, 'a').write('ran')\n" + body, "does something when the file is loaded"),
            (f"open({mark!r}, 'a').write('ran')\n" + body, "does something when the file is loaded"),
            ("import os\n" + body, "imports os"),
            ("from subprocess import run\n" + body, "imports subprocess"),
            (f"LOOKBACK = 2\ndef signal(window, params):\n    open({mark!r}, 'a').write('ran')\n    return 0\n", "uses open"),
            ("LOOKBACK = 2\ndef signal(window, params):\n    import socket\n    return 0\n", "imports socket"),
            ("LOOKBACK = 2\ndef signal(window, params):\n    return ().__class__.__name__ and 0\n", "uses __"),
            ("LOOKBACK = len('ab')\ndef signal(window, params):\n    return 0\n", "does something when the file is loaded")]):
        assert word in events.rule_text_problem(ast.parse(text)), (n, events.rule_text_problem(ast.parse(text)))
        with open(os.path.join(tmp, "bad_rule.py"), "w", encoding="utf-8") as f:
            f.write(text)
        p = subprocess.run([sys.executable, "-B", "-c", "import sys; sys.path.insert(0, sys.argv[1]); import events; events.load_rule(sys.argv[2])",
                            SCRIPTS, os.path.join(tmp, "bad_rule.py")], capture_output=True, text=True)
        assert p.returncode == 2 and "rule file was not run" in p.stderr and word in p.stderr and "Traceback" not in p.stderr, (n, p.stderr)
    assert not os.path.exists(mark), "a refused rule file was run"
    for text in (TOY, COUNTER, "import math, statistics\nfrom math import sqrt\nLOOKBACK = 3\nK: float = 2.5\nLEVELS = (1, 2)\n"
                 "def helper(x):\n    return sqrt(x)\ndef signal(window, params):\n    return 1 if helper(window.close[-1]) > K else 0\n"):
        assert events.rule_text_problem(ast.parse(text)) is None, text
    exp9, _, _ = setup(tmp, "sideeffect", decl["data"]["path"], "rule", rule, 60, "2023-01-03", hold=1,
                       files={"rule.py": f"import os\nopen({mark!r}, 'a').write('ran')\n" + body})
    code, out = run("events", exp9)
    assert code == 2 and "rule file was not run" in out and not os.path.exists(mark)


def test_file_and_order(tmp):
    data = typed(os.path.join(tmp, "file.csv"), [100 + k for k in range(30)], drop=(12, 13))
    listed = "decision_ts,side\n" + "".join(f"{t * 1000},{s}\n" for t, s in (
        (T0 + 5 * 60 + 20, "long"), (T0 + 8 * 60, "1"), (T0 + 11 * 60 + 30, "long"), (T0 + 20 * 60 + 59, "-1"), (T0 + 86400 * 3, "long")))
    fe = {"events_file": "events.csv"}
    exp, decl, lock = setup(tmp, "file", data, "file", fe, 60, "2023-01-03", hold=1, files={"events.csv": listed})
    code, out = run("events", exp)
    doc = _kit.read_json(os.path.join(exp, "results", "events.json"))
    with open(os.path.join(exp, "results", "events_dev.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert code == 1 and "not verified" in doc["causality"] and "causality: not verified" in out          # 1 of 3 dropped
    assert [(int(r["decision_ts"]) - T0, int(r["entry_ts"]) - T0) for r in rows] == [(320, 360), (480, 480)]  # 20 s into bar 5 -> bar 6
    assert doc["dropped_missing_entry"] == [{"date": "2023-01-02", "decision_ts": T0 + 690}]             # fell in the gap
    assert doc["skipped_other_side"] == 1 and doc["outside_data_range"] == 0 and doc["replay"] is None
    exp, decl, lock = setup(tmp, "both", data, "file", fe, 60, "2023-01-03", hold=1, side="both", files={"events.csv": listed}, check=False)
    ev, counts = events.build_events(decl, lock, _kit.load_bars(decl, lock, "dev"), "dev", 0, exp=exp)
    assert [e["side"] for e in ev] == [1, 1, -1] and ev[-1]["entry_ts"] == T0 + 21 * 60
    # zero events is a result (exit 1), an unreadable events line is bad input (exit 2)
    exp, _, _ = setup(tmp, "none", data, "file", fe, 60, "2023-01-03", hold=1, files={"events.csv": "decision_ts,side\n"})
    code, out = run("events", exp)
    assert code == 1 and "no event" in out and _kit.read_json(os.path.join(exp, "results", "events.json"))["events"] == {"0": 0}
    exp, _, _ = setup(tmp, "badline", data, "file", fe, 60, "2023-01-03", hold=1, files={"events.csv": "decision_ts,side\nsoon,long\n"})
    assert run("events", exp)[0] == 2
    # order and tamper: no data check yet, a failed data check, declarations edited after the freeze, no lock
    exp, decl, lock = setup(tmp, "order", data, "file", fe, 60, "2023-01-03", hold=1, files={"events.csv": listed}, check=False)
    code, out = run("events", exp)
    assert code == 3 and "data_check.json is missing" in out and out.splitlines()[-1].startswith("TRY:")
    _kit.write_result(exp, "data_check.json", {"result": "FAIL"}, 1, script="checkdata")
    assert run("events", exp)[0] == 3
    _kit.write_result(exp, "data_check.json", {"result": "PASS"}, 0, script="checkdata")
    decl["idea"]["trade"]["hold_minutes"] = 2
    with open(os.path.join(exp, "declarations.json"), "w", encoding="utf-8") as f:
        json.dump(decl, f)
    code, out = run("events", exp)
    assert code == 3 and "changed since the freeze" in out
    os.remove(os.path.join(exp, "declarations.lock"))
    code, out = run("events", exp)
    assert code == 3 and "not frozen" in out and not os.path.exists(os.path.join(exp, "results", "events.json"))


def main():
    before = sorted(os.listdir(SCRIPTS))
    with tempfile.TemporaryDirectory() as tmp:
        test_clock(tmp)
        test_rule(tmp)
        test_file_and_order(tmp)
    assert sorted(os.listdir(SCRIPTS)) == before, "a file was left in the skill folder"


if __name__ == "__main__":
    main()
    print("test_events.py: all passed")
