#!/usr/bin/env python3
"""Tests of declare.py: its functions directly and every subcommand through the command line."""
from __future__ import annotations

import contextlib, io, json, os, shlex, subprocess, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path[:0] = [HERE, SCRIPTS]
import _kit, declare, synth


def run(script, *args):
    """Run a skill command; returns (exit code, stdout + stderr)."""
    p = subprocess.run([sys.executable, "-B", os.path.join(SCRIPTS, script + ".py"), *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def edit(exp, **changes):
    """Set dotted keys (with __ for the dots) in EXP/declarations.json and return the declarations."""
    path = os.path.join(exp, "declarations.json")
    with open(path, encoding="utf-8") as f:
        decl = json.load(f)
    for key, value in changes.items():
        node, parts = decl, key.split("__")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = value
    with open(path, "w", encoding="utf-8") as f:
        json.dump(decl, f)
    return decl


FILLED = dict(idea__hypothesis="Synthetic bars rise after the declared clock time", idea__instrument="SYNTH",
              idea__venue="none (synthetic)", idea__side="long", idea__event__local_time="09:30",
              idea__event__zone="America/New_York", idea__event__days="weekdays", idea__trade__hold_minutes=60,
              idea__prior_looks__text="never looked at", idea__prior_looks__variants_seen=0,
              costs__fee_bp_per_fill=5, costs__half_spread_bp_per_fill=1, costs__source="assumed for the test")


def test_init(tmp):
    rows = "".join(f"{1700000000000 + 60000 * k},100,101,99,100.5,3\n" for k in range(10))
    with open(os.path.join(tmp, "typed.csv"), "w", encoding="utf-8") as f:
        f.write("open_time,open,high,low,close,volume\n" + rows)
    exp = os.path.join(tmp, "typed")
    code, out = run("declare", "init", "--exp", exp, "--kind", "rule", "--data", os.path.join(tmp, "typed.csv"))
    assert code == 0 and out.rstrip().splitlines()[-2].startswith("RESULT:") and "NEXT:" in out.splitlines()[-1], out
    decl = _kit.read_json(os.path.join(exp, "declarations.json"))
    assert decl["data"]["ts_unit"] == "ms" and decl["data"]["bar_seconds"] == 60 and decl["data"]["columns"]["ts"] == "open_time"
    assert decl["method"] == declare.method_defaults("rule") and decl["method"]["null"]["pool"] == "same-year-any-time"
    assert decl["idea"]["side"] is None and decl["costs"] == {"fee_bp_per_fill": None, "half_spread_bp_per_fill": None, "source": None}
    assert decl["idea"]["event"] == {"rule_file": "rule.py"} and "LOOKBACK = None" in open(os.path.join(exp, "rule.py")).read()
    assert "ask the user" in out and "idea.side" in out and "optional" in out
    assert run("declare", "init", "--exp", exp, "--kind", "rule", "--data", os.path.join(tmp, "typed.csv"))[0] == 3
    assert run("declare", "check", "--exp", exp)[0] == 2            # nulls, and the rule is still the empty template
    assert run("declare", "init", "--exp", exp + "2", "--kind", "clock", "--data", os.path.join(tmp, "nowhere.csv"))[0] == 2
    assert run("declare", "status", "--exp", os.path.join(tmp, "empty"))[0] == 0
    # a file that is not price bars is refused at init, with nothing written and no Python None in the text
    for name, text, word in (("empty.csv", "", "no data rows"), ("header.csv", "open_time,open,high,low,close\n", "no data rows"),
                             ("semi.csv", "time;open;high;low;close\n1700000000;1;2;1;2\n", "not comma-separated")):
        with open(os.path.join(tmp, name), "w", encoding="utf-8") as f:
            f.write(text)
        code, out = run("declare", "init", "--exp", os.path.join(tmp, "bad_" + name), "--kind", "clock", "--data", os.path.join(tmp, name))
        assert code == 2 and word in out and "None" not in out and "Traceback" not in out and not os.path.exists(os.path.join(tmp, "bad_" + name)), out
    with open(os.path.join(tmp, "odd.csv"), "w", encoding="utf-8") as f:   # columns init cannot name: said so, with the header to read them from
        f.write("when,o,h,l,c\n" + "".join(f"{1700000000 + 60 * k},1,2,1,2\n" for k in range(5)))
    code, out = run("declare", "init", "--exp", os.path.join(tmp, "odd"), "--kind", "clock", "--data", os.path.join(tmp, "odd.csv"))
    assert code == 0 and "not detected" in out and "columns not detected: ts, open, high, low, close" in out and "when, o, h, l, c" in out and "None" not in out, out
    # set: keys are filled without a helper script; text with an apostrophe arrives whole; unknown keys are refused
    odd = os.path.join(tmp, "odd")
    code, out = run("declare", "set", "--exp", odd, "data.columns.ts=when", "data.columns.open=o", "data.columns.high=h", "data.columns.low=l",
                    "data.columns.close=c", "idea.venue=my exchange (the user's own words)", "idea.trade.hold_minutes=60", "idea.side=long",
                    "idea.grid.trade.hold_minutes=[30, 60]", "idea.params.lookback=20", "costs.source=assumed: user's own assumption",
                    "idea.event.local_time=09:30", "idea.prior_looks.variants_seen=0", "idea.reason=null")
    d = _kit.read_json(os.path.join(odd, "declarations.json"))
    assert code == 0 and "14 key(s) written" in out and next_is(out, "declare.py", "check"), out
    assert d["data"]["columns"]["ts"] == "when" and d["idea"]["venue"] == "my exchange (the user's own words)" and d["idea"]["trade"]["hold_minutes"] == 60
    assert d["idea"]["grid"] == {"trade.hold_minutes": [30, 60]} and d["idea"]["params"] == {"lookback": 20} and d["idea"]["reason"] is None
    assert d["costs"]["source"] == "assumed: user's own assumption" and d["idea"]["event"]["local_time"] == "09:30" and d["idea"]["prior_looks"]["variants_seen"] == 0
    assert run("declare", "set", "--exp", odd, "idea.grid.trade.hold_minutes=null", "idea.params.lookback=null")[0] == 0
    d2 = _kit.read_json(os.path.join(odd, "declarations.json"))
    assert d2["idea"]["grid"] == {} and d2["idea"]["params"] == {}
    for pair in ("idea.sidee=long", "kind=rule", "nothing", "idea.trade=5", "idea.event.nope=1", "=x"):
        code, out = run("declare", "set", "--exp", odd, pair)
        assert code == 2 and "nothing was written" in out and "Traceback" not in out and _kit.read_json(os.path.join(odd, "declarations.json")) == d2, (pair, out)


def next_is(out, script, *words):
    """True when the last line is a NEXT: python3 command for `script` carrying --exp and every word of `words`."""
    line = out.rstrip().splitlines()[-1]
    argv = shlex.split(line[6:]) if line.startswith("NEXT: python3 ") else []
    return len(argv) > 3 and os.path.basename(argv[1]) == script and "--exp" in argv and all(w in argv for w in words)


def test_check_and_show(tmp, data):
    exp = os.path.join(tmp, "exp")
    assert run("declare", "init", "--exp", exp, "--kind", "clock", "--data", data)[0] == 0
    assert run("checkdata", "--exp", exp)[0] == 3 and run("events", "--exp", exp)[0] == 3      # nothing runs before the freeze
    code, out = run("declare", "check", "--exp", exp)
    assert code == 2 and "direction" in out and "costs.fee_bp_per_fill is null" in out, out
    assert run("declare", "show", "--exp", exp)[0] == 2 and run("declare", "freeze", "--exp", exp)[0] == 2
    good = edit(exp, **FILLED)
    assert declare.problems(good, exp) == [] and run("declare", "check", "--exp", exp)[0] == 0

    def bad(text, **changes):
        decl = json.loads(json.dumps(good))
        for key, value in changes.items():
            node, parts = decl, key.split("__")
            for part in parts[:-1]:
                node = node[part]
            node[parts[-1]] = value
        found = declare.problems(decl, exp)
        assert any(text in p for p in found), (text, found)

    bad("direction", idea__side=None)
    bad("one of long, short", idea__side="both")
    bad("costs.fee_bp_per_fill is null", costs__fee_bp_per_fill=None)
    bad("zero or above", costs__half_spread_bp_per_fill=-1)
    bad("method.gates.dsr_min is 'looks good'", method__gates__dsr_min="looks good")
    bad("199 or more", method__null__draws=50)
    bad("hold of 45 minutes is not a positive multiple of the 1800 s bars", idea__trade__hold_minutes=45)
    bad("09:45 cannot be entered on bars of 1800 s", idea__event__local_time="09:45")
    bad("same-day-other-times", method__null__pool="same-year-any-time")
    bad("base value 60 of trade.hold_minutes is not in its own grid list [30, 120]", idea__grid={"trade.hold_minutes": [30, 120]})
    bad("duplicate", idea__grid={"trade.hold_minutes": [60, 60]})
    bad("not allowed", idea__grid={"trade.side": ["long"]})
    bad("variants_seen is -1", idea__prior_looks__variants_seen=-1)
    bad("at most 1000000", idea__prior_looks__variants_seen=10 ** 30)
    bad("is not a file", idea__event__skip_dates_file="holidays.txt")
    bad("cannot be resolved", idea__event__zone="Mars/Olympus")
    bad("each segment needs at least", method__gates__min_event_days=200)
    bad("is missing", data__path=os.path.join(tmp, "gone.csv"))
    bad("is not a column", data__columns__close="last")
    # the gates cannot be declared weak enough to pass noise: alpha at most 0.10, both confidence gates at least 0.90
    bad("method.null.alpha is 0.99: it must be above 0 and at most 0.10", method__null__alpha=0.99)
    bad("method.null.alpha is 0.11", method__null__alpha=0.11)
    bad("method.gates.dsr_min is 0.5: it must be from 0.90 to below 1", method__gates__dsr_min=0.5)
    bad("method.gates.oos_psr_min is 0.89", method__gates__oos_psr_min=0.89)
    assert declare.problems(json.loads(json.dumps(good).replace('"alpha": 0.05', '"alpha": 0.1').replace('"dsr_min": 0.95', '"dsr_min": 0.9')), exp) == []
    # costs.source says in its first word whether the figures were measured or assumed; a figure of the model's own has no word
    for word in ("the tester's figures", "unconfirmed: the venue's published taker fee", "user own assumption", 7):
        bad("begin" if isinstance(word, str) else "must be text", costs__source=word)
    for word in ("measured: fee from my statement, spread from my quotes", "Assumed, no quote data", "assumed"):
        assert declare.problems({**good, "costs": {**good["costs"], "source": word}}, exp) == [], word
    # wrong shapes are problems that check lists, never tracebacks in show or freeze
    bad("idea.params is ['lookback', 20]", idea__params=["lookback", 20])
    bad("idea.params is 'lookback'", idea__params="lookback")
    bad("idea.params is {'lookback': 'twenty'}", idea__params={"lookback": "twenty"})
    bad("idea.grid is [30, 60]", idea__grid=[30, 60])
    bad("data.first_utc is 1e+308", data__first_utc=1e308)
    bad("data.last_utc is 1700000000000", data__last_utc=1700000000000)
    bad("data.first_utc is 'yesterday'", data__first_utc="yesterday")
    bad("idea.hypothesis is 5", idea__hypothesis=5)
    for key, value in (("idea__params", ["lookback", 20]), ("idea__params", True), ("data__first_utc", 1e308), ("idea__grid", "x"), ("idea__trade", 5),
                       ("idea__event", []), ("data__columns", 3), ("method__gates", "strict"), ("costs", None), ("idea", None)):
        saved = open(os.path.join(exp, "declarations.json"), encoding="utf-8").read()
        edit(exp, **{key: value})
        for sub in ("check", "show", "freeze"):
            code, out = run("declare", sub, "--exp", exp)
            assert code == 2 and "Traceback" not in out and "ERROR:" in out, (key, value, sub, out[-400:])
        with open(os.path.join(exp, "declarations.json"), "w", encoding="utf-8") as f:
            f.write(saved)
    assert not os.path.exists(os.path.join(exp, "declarations.lock"))
    with open(data, encoding="utf-8") as f:
        lines = f.read().splitlines()
    with open(os.path.join(tmp, "reversed.csv"), "w", encoding="utf-8") as f:
        f.write("\n".join([lines[0]] + lines[:0:-1]) + "\n")
    bad("rows are newest-first: sort ascending by time first", data__path=os.path.join(tmp, "reversed.csv"))
    # show: every method line is tagged, no idea or cost line is; one changed value gives one changed tag
    code, out = run("declare", "show", "--exp", exp)
    text = open(os.path.join(exp, "STEP0_DECLARATIONS.md"), encoding="utf-8").read()
    assert code == 0 and text.rstrip() in out and out.rstrip().endswith("NEXT: show this whole file to the user; freeze only after they answer it")
    assert text.startswith("# STEP 0 DECLARATIONS: SYNTH, Synthetic bars rise") and "Draft, not frozen" in text
    method = text.split("## Method")[1].split("## Fixed rules")[0]
    tagged = [l for l in method.splitlines() if l.startswith("- ")]
    assert len(tagged) == 12 == len([l for l in method.splitlines() if l.strip()]) and all(" [default]" in l for l in tagged), tagged
    assert sum(l.endswith(")") for l in tagged) == 11 and "- null.alpha: 0.05 [default] (One-sided, in the declared direction)" in tagged
    assert len(text.splitlines()) <= 85, len(text.splitlines())       # one screen or so: it is pasted whole to the user
    assert "worked out from split.dev_fraction 0.6667" in text and "no gate can be loosened" in text
    assert "the grid is run only if the base trade passes the characterisation gate" in text
    # the title: the instrument is not said twice, and a long hypothesis is cut at a word
    assert _kit.title("BTCUSDT perpetual", "BTCUSDT perpetual rises over the 60 minutes after the US stock market cash open") == \
        "BTCUSDT perpetual rises over the 60 minutes after the US ..."
    assert _kit.title("SYNTH", "Synthetic bars rise.") == "SYNTH, Synthetic bars rise" and _kit.title("ES", "es falls, then rises") == "es falls, then rises"
    assert text.count("[default]") == 14 and "[changed" not in text
    assert "[" not in text.split("## The idea (yours)")[1].split("## Data")[0]
    assert "round trip (two fills): 12 bp" in text and "calendar event days: development" in text
    edit(exp, method__null__draws=500)
    run("declare", "show", "--exp", exp)
    text = open(os.path.join(exp, "STEP0_DECLARATIONS.md"), encoding="utf-8").read()
    assert text.count("[changed from default: 1000]") == 1 and text.count("[changed") == 1 and "1/501" in text
    edit(exp, method__null__draws=1000)
    for n, t in ((1, "1.645"), (2, "2.209"), (6, "2.945"), (9, "3.166")):       # sizing lines at N = 1, 2, 6, 9
        sized = declare.render(edit(exp, idea__prior_looks__variants_seen=n - 1), exp)
        assert f"at this N: about {t}" in sized and f"= {n}\n" in sized, (n, sized[-900:])
    return exp


def test_cells_and_split():
    decl = {"idea": {"trade": {"hold_minutes": 60, "stop_bp": 20, "target_bp": None}, "params": {},
                     "grid": {"trade.stop_bp": [20, 40], "trade.hold_minutes": [30, 60, 120]}},
            "method": {"split": {"dev_fraction": 0.6667, "date_utc": None}}}
    cells, primary = declare.cells_of(decl)
    assert [(c["hold_minutes"], c["stop_bp"]) for c in cells] == [(30, 20), (30, 40), (60, 20), (60, 40), (120, 20), (120, 40)]
    assert primary == 2 and [c["index"] for c in cells] == list(range(6)) and {c["pset"] for c in cells} == {0}
    assert list(cells[0]) == ["index", "pset", "hold_minutes", "stop_bp", "target_bp", "params"]
    decl["idea"].update(params={"k": 1}, grid={"params.k": [1, 2], "trade.hold_minutes": [60, 30]})
    cells, primary = declare.cells_of(decl)
    assert [(c["params"]["k"], c["hold_minutes"], c["pset"]) for c in cells] == [(1, 60, 0), (1, 30, 0), (2, 60, 1), (2, 30, 1)]
    assert primary == 0 and len(declare.cells_of({"idea": {"trade": {"hold_minutes": 5}}})[0]) == 1
    day = 86400
    assert declare.split_utc(decl, 0, 300 * day) == 200 * day            # 300 days at 0.6667: 00:00 UTC of day 200
    assert declare.split_utc(decl, 1000 * day + 3600, 1300 * day + 3600) == 1200 * day
    decl["method"]["split"]["date_utc"] = "2023-03-18"
    assert declare.split_utc(decl, 0, 300 * day) == 1679097600


def test_freeze_and_amend(tmp, exp):
    lockfile = os.path.join(exp, "declarations.lock")
    grid = {"trade.hold_minutes": [30, 60, 120], "trade.stop_bp": [20, 40]}
    edit(exp, idea__grid=grid, idea__trade__stop_bp=20, idea__prior_looks__variants_seen=4)
    os.makedirs(os.path.join(exp, "results"))
    open(os.path.join(exp, "results", "early.json"), "w").close()
    assert run("declare", "freeze", "--exp", exp)[0] == 3 and not os.path.exists(lockfile)   # a result older than the freeze
    assert run("declare", "amend", "--exp", exp, "--reason", "x")[0] == 3                 # nothing frozen to amend
    os.remove(os.path.join(exp, "results", "early.json"))
    os.rmdir(os.path.join(exp, "results"))
    code, out = run("declare", "freeze", "--exp", exp)
    decl, lock = _kit.load_decl(exp)
    assert code == 0 and "N = 10" in out and out.rstrip().splitlines()[-1].startswith("NEXT: python3 ") and "checkdata.py" in out
    assert lock["decl_sha256"] == _kit.canonical_sha256(decl) and len(lock["decl_sha256"]) == 64 and lock["history"] == []
    assert (lock["cells_declared"], lock["variants_seen"], lock["amend_penalty"], lock["N"], lock["primary_cell"]) == (6, 4, 0, 10, 2)
    size = os.path.getsize(decl["data"]["path"])
    assert lock["data"]["bytes"] == size and lock["data"]["first_utc"] == 1609718400 and lock["split_utc"] % 86400 == 0
    assert lock["data"]["sha256"] == declare.file_sha256(decl["data"]["path"])
    text = open(os.path.join(exp, "STEP0_DECLARATIONS.md"), encoding="utf-8").read()
    assert f"Frozen {lock['frozen_utc']}, sha256 {lock['decl_sha256'][:12]}" in text and "cell 5: hold 120 min, stop 40" in text
    # a grid is told before the freeze what it costs: the t printed is a minimum, and one cell would need 1.645
    assert "development t needed for DSR 0.95 at this N: about" in text and "that is the least it can be" in text
    assert "one cell alone needs about 1.645" in text and "that is the least it can be" not in declare.render(edit(exp, idea__grid={}), exp)
    edit(exp, idea__grid=grid)
    assert run("declare", "freeze", "--exp", exp)[0] == 3                                   # freeze twice
    code, out = run("declare", "status", "--exp", exp)
    assert code == 0 and "1 declare: done" in out and "2 checkdata: not done" in out and next_is(out, "checkdata.py")
    assert lock["oos_opened_utc"] is None and lock["frozen_declarations"] == decl
    # one changed value after the freeze: every later step refuses, status says amend
    edit(exp, idea__trade__hold_minutes=120)
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            _kit.load_decl(exp)
        raise AssertionError("load_decl accepted edited declarations")
    except SystemExit as e:
        assert e.code == 3 and "changed since the freeze" in err.getvalue()
    assert run("checkdata", "--exp", exp)[0] == 3 and "amend" in run("declare", "status", "--exp", exp)[1].splitlines()[-1]
    edit(exp, idea__trade__hold_minutes=60)
    assert run("checkdata", "--exp", exp)[0] == 0
    # amend: a new grid value adds cells and no penalty; results are moved, not deleted
    edit(exp, idea__grid={**grid, "trade.hold_minutes": [30, 60, 120, 90]})
    code, out = run("declare", "amend", "--exp", exp, "--reason", "user asked for a 90 minute hold")
    lock2 = _kit.load_decl(exp)[1]
    assert code == 0 and "N was 10, is now 12" in out, out
    assert (lock2["cells_declared"], lock2["amend_penalty"], lock2["N"], lock2["frozen_utc"]) == (8, 0, 12, lock["frozen_utc"])
    assert lock2["history"][0]["reason"] == "user asked for a 90 minute hold" and lock2["history"][0]["N"] == 12
    assert lock2["history"][0]["decl_sha256"] == lock2["decl_sha256"] != lock["decl_sha256"]
    assert os.path.isfile(os.path.join(exp, "results_superseded_1", "data_check.json")) and not os.path.exists(os.path.join(exp, "results"))
    assert lock2["history"][0]["trial_definition_changed"] is False and lock2["history"][0]["penalty_added"] == 0
    # a change that adds no cell costs one trial
    edit(exp, data__first_utc="2021-01-05")
    assert run("declare", "amend", "--exp", exp, "--reason", "first day dropped")[0] == 0
    lock3 = _kit.load_decl(exp)[1]
    assert (lock3["cells_declared"], lock3["amend_penalty"], lock3["N"], len(lock3["history"])) == (8, 1, 13, 2)
    assert lock3["data"]["first_utc"] == 1609804800
    assert lock3["history"][-1]["data_changed"] is True and lock3["history"][-1]["cells_run_before"] == 0   # no cell had been run
    # a gate cannot be loosened after the freeze; tightening one is an ordinary amend
    for key, value in (("method__null__alpha", 0.1), ("method__gates__dsr_min", 0.9), ("method__gates__oos_psr_min", 0.9),
                       ("method__gates__min_event_days", 50), ("method__gates__max_dropped_event_share", 0.5)):
        saved = open(os.path.join(exp, "declarations.json"), encoding="utf-8").read()
        edit(exp, **{key: value})
        code, out = run("declare", "amend", "--exp", exp, "--reason", "make it easier")
        assert code == 3 and "a gate cannot be loosened after the freeze" in out and _kit.read_json(lockfile) == lock3, (key, out)
        with open(os.path.join(exp, "declarations.json"), "w", encoding="utf-8") as f:
            f.write(saved)
    # the event time, the side or a cost moved after the freeze: the 8 cells frozen before were other trials, already
    # looked at, so they stay in N beside the cells as they are now (adding a grid value in the same amend does not hide them)
    edit(exp, idea__event__local_time="10:00", idea__grid={**grid, "trade.hold_minutes": [30, 60, 120, 90, 150]})
    code, out = run("declare", "amend", "--exp", exp, "--reason", "tidy")
    lock4 = _kit.load_decl(exp)[1]
    assert code == 0 and "N was 13, is now 23" in out and "count as trials already made" in out, out
    assert (lock4["cells_declared"], lock4["amend_penalty"], lock4["N"]) == (10, 9, 23) and lock4["history"][-1]["trial_definition_changed"] is True
    assert lock4["history"][-1]["penalty_added"] == 8 and lock4["history"][-1]["cells_added"] == 2
    for change in (dict(idea__side="short"), dict(costs__fee_bp_per_fill=0.01), dict(costs__half_spread_bp_per_fill=0.01)):
        before = _kit.load_decl(exp)[1]
        edit(exp, **change)
        assert run("declare", "amend", "--exp", exp, "--reason", "tidy")[0] == 0
        after = _kit.load_decl(exp)[1]
        assert after["N"] == before["N"] + 10 and after["amend_penalty"] == before["amend_penalty"] + 10, (change, before["N"], after["N"])
    edit(exp, idea__hypothesis="Synthetic bars rise after the declared clock time (typo fixed)")   # words only: one trial, as before
    assert run("declare", "amend", "--exp", exp, "--reason", "typo")[0] == 0
    assert _kit.load_decl(exp)[1]["N"] == 23 + 30 + 1
    grid = {**grid, "trade.hold_minutes": [30, 60, 120, 90, 150]}
    lock3 = _kit.load_decl(exp)[1]
    # N can only grow: removing a value or lowering variants_seen is refused, and so is anything after out-of-sample
    edit(exp, idea__grid={**grid, "trade.hold_minutes": [30, 60, 90]})
    code, out = run("declare", "amend", "--exp", exp, "--reason", "drop the ugly cell")
    assert code == 3 and "N can only grow" in out and _kit.read_json(lockfile) == lock3
    edit(exp, idea__grid={**grid, "trade.hold_minutes": [30, 60, 120, 90]}, idea__prior_looks__variants_seen=1)
    assert run("declare", "amend", "--exp", exp, "--reason", "fewer")[0] == 3
    edit(exp, idea__prior_looks__variants_seen=4, idea__grid={**grid, "trade.hold_minutes": [30, 60, 120, 90, 150, 180]})
    _kit.write_result(exp, "oos.json", {"cell": 0}, 0, script="sweep")
    code, out = run("declare", "amend", "--exp", exp, "--reason", "try another hold on the newer data")
    assert code == 3 and "out-of-sample was opened" in out and _kit.read_json(lockfile) == lock3
    assert os.path.isfile(os.path.join(exp, "results", "oos.json"))
    # the look is recorded in the lock as well: with the result file moved away the amend is still refused, and every
    # script that finds the declarations changed says to restore them, not to amend
    os.remove(os.path.join(exp, "results", "oos.json"))
    with open(lockfile, "w", encoding="utf-8") as f:
        json.dump({**lock3, "oos_opened_utc": "2026-10-06T00:00:00Z"}, f)
    code, out = run("declare", "amend", "--exp", exp, "--reason", "the result file is gone")
    assert code == 3 and "out-of-sample was opened" in out
    code, out = run("checkdata", "--exp", exp)
    assert code == 3 and "amend is refused" in out and "frozen_declarations" in out
    assert "amend is refused" in run("declare", "status", "--exp", exp)[1].splitlines()[-1]


def test_amend_counts_cells_run_on_other_data(tmp, data):
    """Cells already run and then run again on another sample (another file, range, split or way of reading the
    file) are trials already made: all of them go into N, not one. Found in review: 12 cells swept, the data file
    swapped for another market, N rose by 1."""
    other, copy = os.path.join(tmp, "other.csv"), os.path.join(tmp, "copy.csv")
    synth.generate(other, days=320, bar_seconds=1800, seed=4)
    with open(data, "rb") as f, open(copy, "wb") as g:
        g.write(f.read())

    def fresh(name, *results):
        exp = os.path.join(tmp, name)
        assert run("declare", "init", "--exp", exp, "--kind", "clock", "--data", data)[0] == 0
        edit(exp, **FILLED, idea__grid={"trade.hold_minutes": [30, 60], "trade.stop_bp": [20, 40]}, idea__trade__stop_bp=20)
        code, out = run("declare", "freeze", "--exp", exp)
        assert code == 0 and "N = 4" in out, out
        ran(exp, *results)
        return exp

    def ran(exp, *results):
        for name in results:
            _kit.write_result(exp, name, {}, 0, script="test")

    def amend(exp, **changes):
        edit(exp, **changes)
        code, out = run("declare", "amend", "--exp", exp, "--reason", "test")
        assert code == 0, out
        lock = _kit.load_decl(exp)[1]
        return lock, lock["history"][-1], out

    for change in (dict(data__path=other), dict(data__first_utc="2021-01-06"), dict(method__split__dev_fraction=0.6),
                   dict(method__split__date_utc="2021-08-01"), dict(data__stamp="close")):
        lock, h, out = amend(fresh("swept_" + next(iter(change)), "effect_dev.json", "sweep.json"), **change)
        assert (lock["N"], lock["amend_penalty"], h["penalty_added"], h["data_changed"], h["cells_run_before"]) == (8, 4, 4, True, 4), (change, out)
        assert "N was 4, is now 8" in out and "4 cell(s) already run" in out and lock["cells_run_on_this_data"] == 0, out
    # before any cell was run the same change is one trial (a file repaired after a failed data check), and so is
    # a change after effect.py alone, which ran the base cell only
    for results in ((), ("data_check.json", "events.json"), ("data_check.json", "effect_dev.json")):
        lock, h, out = amend(fresh("early_" + "_".join(r[:3] for r in results), *results), data__path=other)
        assert (lock["N"], h["penalty_added"], h["data_changed"]) == (5, 1, True) and "N was 4, is now 5" in out, (results, out)
    # the same bytes at another path are the same sample; a label is not the sample either
    lock, h, out = amend(fresh("moved", "sweep.json"), data__path=copy, idea__instrument="SYNTH2")
    assert (lock["N"], h["data_changed"], h["trial_definition_changed"], lock["cells_run_on_this_data"]) == (5, False, False, 4), out
    # an amend of something else in between does not hide the cells: its results are moved away, the count stays in
    # the lock, and the data change that follows still adds all four
    exp = fresh("two_steps", "sweep.json")
    lock, h, out = amend(exp, idea__reason="a reason added afterwards")
    assert (lock["N"], lock["cells_run_on_this_data"]) == (5, 4) and not os.path.exists(os.path.join(exp, "results"))
    lock, h, out = amend(exp, data__path=other)
    assert (lock["N"], h["penalty_added"], h["cells_run_before"], lock["cells_run_on_this_data"]) == (9, 4, 4, 0), out
    lock, h, out = amend(exp, data__first_utc="2021-01-06")          # counted once: nothing has been run on the new file
    assert (lock["N"], h["penalty_added"]) == (10, 1), out
    # cells added in the same amend count as cells, beside the four already run
    lock, h, out = amend(fresh("added", "sweep.json"), data__path=other,
                         idea__grid={"trade.hold_minutes": [30, 60, 90], "trade.stop_bp": [20, 40]})
    assert (lock["cells_declared"], lock["amend_penalty"], lock["N"]) == (6, 4, 10), out
    # the event moved and the data changed in one amend: the frozen cells are counted once, not twice
    lock, h, out = amend(fresh("both", "sweep.json"), data__path=other, idea__event__local_time="10:00")
    assert (lock["N"], h["penalty_added"], h["trial_definition_changed"], h["data_changed"]) == (8, 4, True, True), out


def main():
    before = sorted(os.listdir(SCRIPTS))
    with tempfile.TemporaryDirectory() as tmp:
        data = os.path.join(tmp, "bars.csv")
        synth.generate(data, days=320, bar_seconds=1800, seed=3)
        test_cells_and_split()
        test_init(tmp)
        exp = test_check_and_show(tmp, data)
        test_freeze_and_amend(tmp, exp)
        test_amend_counts_cells_run_on_other_data(tmp, data)
    assert sorted(os.listdir(SCRIPTS)) == before, "a file was left in the skill folder"


if __name__ == "__main__":
    main()
    print("test_declare.py: all passed")
