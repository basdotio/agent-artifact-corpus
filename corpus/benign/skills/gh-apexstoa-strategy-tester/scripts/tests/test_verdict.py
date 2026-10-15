#!/usr/bin/env python3
"""verdict.py: every row of the decision table, the integrity and step-order refusals, FINDINGS.md and --check.
Fixtures are hand-written result files (spec section 5) in a temp folder; no market data is involved."""
from __future__ import annotations

import contextlib, copy, hashlib, io, json, os, re, subprocess, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import _kit as k
import verdict as v

DROP = object()
NULL = {"pool": "same-day-other-times", "draws": 1000, "seed": 1, "statistic_bp": 9.0, "null_mean_bp": 1.0, "null_sd_bp": 2.0,
        "null_p95_bp": 4.3, "excess_bp": 8.0, "z": 4.0, "b": 0, "m": 1000, "p": 0.000999, "days_excluded": 0}
BASE = {  # a consistent set that reaches GO; each test overrides the fields it names
    "data_check": {"rows": 86400, "first_utc": 1609718400, "last_utc": 1635638100, "bar_seconds": 300, "missing_bars": 0, "largest_gap_bars": 0,
                   "duplicates_identical": 0, "flat_share": 0.0, "zero_volume_share": 0.0, "tie_rate": 0.01, "outliers": [], "fails": [],
                   "warns": [], "result": "PASS"},
    "events": {"kind": "clock", "psets": 1, "events": {"0": 300}, "dropped_missing_entry": [], "dropped_straddles_split": 0,
               "skipped_gap_in_lookback": 0, "dropped_share": 0.0, "causality": "by construction", "replay": None,
               "utc_time_summer": "14:00", "utc_time_winter": "14:00", "days_by_utc_time": {"14:00": 300}},
    "effect_dev": {"cell": 0, "events": 300, "trades": 300, "skipped_overlap": 0, "dropped_missing_exit": 0, "event_days": 300, "enough_days": True,
                   "gross": {"mean_bp": 21.0, "median_bp": 20.0, "sd_bp": 30.0, "t": 12.1, "upper95_bp": 23.8}, "hit_rate": 0.7, "tie_rate": 0.0,
                   "cost_round_trip_bp": 12.0, "break_even_cost_bp": 21.0,
                   "net_by_tier": [{"tier": 0.5, "cost_bp": 6.0, "mean_bp": 15.0, "t": 8.7}, {"tier": 1.0, "cost_bp": 12.0, "mean_bp": 9.0, "t": 5.2},
                                   {"tier": 2.0, "cost_bp": 24.0, "mean_bp": -3.0, "t": -1.7}],
                   "by_year": [{"year": 2021, "days": 300, "gross_mean_bp": 21.0, "net_mean_bp": 9.0}], "lag1_autocorr": 0.02, "null": NULL,
                   "placebo": None, "flags": [], "gate": {"net_mean_positive": True, "null_p_ok": True, "pass": True, "reason": ""}},
    "sweep": {"cells_declared": 1, "cells_run": 1, "net_positive_cells": 1, "chosen_cell": 0, "selection_rule": "highest net per-day Sharpe",
              "grid_null": None},
    "deflate": {"cell": 0, "n": 300, "sharpe": 0.3, "t": 5.2, "skew": 0.1, "kurt": 3.2, "psr0": 0.9999, "N": 1, "cells_declared": 1,
                "std_trials_measured": None, "std_trials_floor": 0.0578, "std_trials_used": 0.0578, "emax_closed": 0.0, "emax_exact": 0.0,
                "emax_used": 0.0, "sr0": 0.0, "dsr": 0.9999, "dsr_min": 0.95, "pass": True, "days_needed": 32, "no_days_enough": False,
                "lag1_autocorr": 0.02, "psr0_autocorr_adjusted": 0.9999, "warnings": [], "flags": []},
    "oos": {"cell": 0, "opened_utc": "2026-10-06T04:00:00Z", "events": 150, "trades": 150, "event_days": 150, "enough_days": True,
            "net_mean_bp": 8.0, "net_sd_bp": 30.0, "sharpe": 0.2667, "t": 3.27, "skew": 0.0, "kurt": 3.0, "psr0": 0.9994,
            "null": dict(NULL, excess_bp=7.0, z=3.0, p=0.002), "by_year": [{"year": 2021, "days": 150, "net_mean_bp": 8.0}],
            "gate": {"net_mean_positive": True, "psr_ok": True, "null_p_ok": True, "pass": True}},
}
COLS = "cell,pset,hold_minutes,stop_bp,target_bp,params,trades,event_days,gross_mean_bp,net_mean_bp,net_sd_bp,sharpe,t,ties,primary,chosen,flag"
EARLY = {s: DROP for s in ("sweep", "deflate", "oos")}  # rows 1 to 4: nothing after the characterisation step exists


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def make(tmp, name, over=None, cells=1, kind="clock", variants=0, history=(), source="measured: exchange fee page, my own quotes", chosen_net=9.0,
         alpha=0.05, dsr_min=0.95, mark=None):
    """An experiment folder with a consistent lock and result set. over: {"step.key.sub": value, "step": DROP}."""
    exp = os.path.join(tmp, name)
    os.makedirs(os.path.join(exp, "results"))
    write(os.path.join(exp, "bars.csv"), "open_time,open,high,low,close,volume\n1609718400000,100,101,99,100,1\n")
    raw = open(os.path.join(exp, "bars.csv"), "rb").read()
    decl = {"schema": 1, "kind": kind,
            "idea": {"hypothesis": "A made-up instrument drifts up in the hour after 14:00 UTC, for no reason at all", "instrument": "SYNTH", "side": "long",
                     "prior_looks": {"text": "none; this is the first version", "variants_seen": variants}},
            "costs": {"fee_bp_per_fill": 5, "half_spread_bp_per_fill": 1, "source": source}, "data": {"path": os.path.join(exp, "bars.csv")},
            "method": {"null": {"alpha": alpha}, "gates": {"dsr_min": dsr_min, "oos_psr_min": 0.95, "min_event_days": 100, "max_dropped_event_share": 0.02},
                       "next_if_go": "Four weeks of paper trading on the declared venue before any capital.",
                       "next_if_no_go": "Write the findings and close the experiment. Any variant is a new declaration."}}
    lock = {"schema": 1, "decl_sha256": k.canonical_sha256(decl), "frozen_utc": "2026-01-01T00:00:00Z",
            "data": {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}, "cells_declared": cells, "variants_seen": variants,
            "amend_penalty": 0, "N": cells + variants, "history": list(history), "oos_opened_utc": mark}
    write(os.path.join(exp, "declarations.json"), json.dumps(decl))
    write(os.path.join(exp, "declarations.lock"), json.dumps(lock))
    docs = copy.deepcopy(BASE)
    docs["sweep"].update(cells_declared=cells, cells_run=cells, net_positive_cells=cells)
    docs["deflate"].update(N=cells + variants, cells_declared=cells)
    if cells > 1:
        docs["sweep"]["grid_null"] = {"draws_declared": 1000, "draws_used": 1000, "real_best_sharpe": 0.3, "null_mean": 0.05, "null_sd": 0.05,
                                      "null_p95": 0.13, "z": 5.0, "b": 0, "m": 1000, "p": 0.000999}
    for key, value in (over or {}).items():
        step, *path = key.split(".")
        if value is DROP:
            docs.pop(step)
            continue
        node = docs[step]
        for part in path[:-1]:
            node = node[int(part)] if isinstance(node, list) else node[part]
        node[int(path[-1]) if isinstance(node, list) else path[-1]] = value
    for step, doc in docs.items():
        k.write_result(exp, step + ".json", doc, 0, script=step)
    if "sweep" in docs:
        rows = [f"{i},0,{60 + i},,,{{}},300,300,21.0,{chosen_net if i == 0 else 1.0},30.0,{0.3 if i == 0 else 0.03},5.2,0,{int(i == 0)},{int(i == 0)},"
                for i in range(cells)]
        write(os.path.join(exp, "results", "grid.csv"), "\n".join([COLS] + rows) + "\n")
    return exp


def run(exp, *flags):
    """verdict.main in this process: (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            v.main(["--exp", exp, *flags])
    except SystemExit as e:
        return e.code, out.getvalue(), err.getvalue()
    raise AssertionError("verdict.main returned without exiting")


def findings(exp):
    text = open(os.path.join(exp, "FINDINGS.md"), encoding="utf-8").read()
    return text, text[text.index(v.START):text.index(v.END)]


def section(block, title):
    return block.split(f"## {title}\n", 1)[1].split("\n## ", 1)[0]


def patch(exp, step, **fields):
    path = os.path.join(exp, "results", step + ".json")
    write(path, json.dumps({**json.load(open(path)), **fields}))


def test_rows(tmp):
    """Rows 1 to 14: (overrides, fixture options, verdict, days needed or None)."""
    cases = {
        1: ({"effect_dev.event_days": 50, **EARLY}, {}, v.INC, 100),
        2: ({"effect_dev.net_by_tier.1.mean_bp": -4.5, "effect_dev.break_even_cost_bp": 7.5, **EARLY}, {}, v.NOGO, None),
        3: ({"effect_dev.null.excess_bp": -1.0, "effect_dev.null.z": -0.5, **EARLY}, {}, v.NOGO, None),
        4: ({"effect_dev.event_days": 200, "effect_dev.null.p": 0.16, "effect_dev.null.z": 1.0, **EARLY}, {}, v.INC, 542),
        5: ({"oos": DROP}, {"chosen_net": -2.0}, v.NOGO, None),
        6: ({"deflate.no_days_enough": True, "deflate.days_needed": None, "deflate.dsr": 0.31, "deflate.pass": False, "sweep.grid_null.p": 0.2,
             "sweep.grid_null.z": 0.9, "oos": DROP}, {"cells": 3}, v.NOGO, None),
        7: ({"deflate.dsr": 0.80, "deflate.pass": False, "deflate.days_needed": 777, "oos": DROP}, {"cells": 3}, v.INC, 777),
        8: ({"sweep.grid_null.z": -0.4, "sweep.grid_null.p": 0.66, "oos": DROP}, {"cells": 3}, v.NOGO, None),
        9: ({"sweep.grid_null.z": 1.0, "sweep.grid_null.p": 0.16, "oos": DROP}, {"cells": 3}, v.INC, 812),  # ceil(300 * 1.644854^2)
        10: ({"oos.event_days": 40}, {}, v.INC, 100),
        11: ({"oos.net_mean_bp": -1.0}, {}, v.NOGO, None),
        12: ({"oos.sharpe": 0.1, "oos.psr0": 0.89, "oos.null.z": 1.9}, {}, v.INC, 273),  # MinTRL 272.907 > ceil(150 * (1.644854/1.9)^2) = 113
        13: ({"effect_dev.flags": ["SUSPICIOUS: hit rate 0.95 on 300 trades"]}, {}, v.INC, None),
        14: ({}, {}, v.GO, None),
    }
    odd = {"oos.null.excess_bp": None, "oos.null.z": None, "oos.null.p": None, "oos.psr0": None, "oos.sharpe": None}  # a null that could not be formed
    exp = make(tmp, "oddnull", {**odd, "sweep.grid_null.z": None}, cells=3)
    assert run(exp)[0] == 0 and json.load(open(os.path.join(exp, "results", "verdict.json")))["row"] == 12
    exp = make(tmp, "nocell", {"sweep.chosen_cell": None, "deflate": DROP, "oos": DROP})  # the sweep chose nothing: row 1 on the cells
    j = (run(exp)[0], json.load(open(os.path.join(exp, "results", "verdict.json"))))[1]
    assert (j["verdict"], j["row"]) == (v.INC, 1)
    for row, (over, opts, verdict, days) in cases.items():
        exp = make(tmp, f"row{row}", over, **opts)
        code, out, err = run(exp)
        assert code == 0, (row, code, err)
        j = json.load(open(os.path.join(exp, "results", "verdict.json")))
        text, block = findings(exp)
        assert (j["verdict"], j["row"], j["days_needed"]) == (verdict, row, days), (row, j["verdict"], j["row"], j["days_needed"])
        assert f"VERDICT: {verdict}\n" in out and out.splitlines()[-1] == "NEXT: " + v.NEXT and len(out.splitlines()) <= 45
        line = next(ln for ln in text.splitlines() if ln.startswith("**Verdict:** "))       # what the model sees is what the file says
        assert out.splitlines()[-2] == f"RESULT: {line[13:]} [row {row}]", (out.splitlines()[-2], line)
        assert ("No row failed: GO." in block) == (row == 14) and (f"The first failing row decides: row {row}." in block) == (row != 14)
        assert "Row 14" not in block and '{"' not in block and "null: null" not in block and "warnings" not in block, row
        assert text.splitlines()[0].endswith(": " + verdict) and text.splitlines()[0].startswith("# SYNTH, A made-up instrument")
        assert not re.search(r"\{\{|<[A-Za-z][A-Za-z _-]*>", block), row  # no placeholder left in the generated block
        assert text.count(v.TODO) == 3 and all(f"## {h}\n" in text.split(v.END)[1] for h in v.PROSE)
        assert [g["row"] for g in j["gates"]] == list(range(1, 14)) and set(j["gates"][0]) == {"row", "name", "required", "observed", "pass"}
        assert (verdict == v.INC) == ("history in this file:" in j["deciding"]) and j["script"] == "verdict" and j["exit_code"] == 0
        early = row <= 4
        for title in ("The declared grid", "Deflation", "Out-of-sample, one look"):
            assert (section(block, title).strip().splitlines()[0] == "not run") == (early or (title.startswith("Out") and row <= 9)), (row, title)
        assert all(f"Source: results/{f}" in block for f in ("data_check.json", "events.json", "effect_dev.json", "deflate.json", "oos.json"))
        if not early:
            cells = opts.get("cells", 1)
            assert len(re.findall(r"^\| \d+ \| 0 \|", section(block, "The declared grid"), re.M)) == cells and f"of {cells}." in block
        assert run(exp, "--check")[0] == 0, row
    j = json.load(open(os.path.join(tmp, "row12", "results", "verdict.json")))
    assert j["history_event_days"] == 450 and "days needed: 273; history in this file: 450 event days" in j["deciding"]
    block = findings(os.path.join(tmp, "row2"))[1]
    # the deciding sentence leads with the number of the row that decided, then says the same thing per trade
    assert "development net mean -4.50 bp per event day: the raw effect +7.50 bp per trade does not cover the round-trip cost 12 bp" in block
    assert "| development net mean at the declared cost | > 0 bp | -4.50 bp | FAIL (decides) |" in block and "NOT RUN" in block
    assert "## Deviations\n\nnone\n" in block and "Prior looks: none; this is the first version." in block
    assert "weekend placebo (reported, not gated): NOT RUN" in block and "- events by parameter set: 0 = 300" in block and "- days by utc time: 14:00 = 300" in block
    assert "- null pool: same-day-other-times" in block and "- null mean (bp): 1" in block and "- null p: 0.0010" in block
    go = findings(os.path.join(tmp, "row14"))[1]
    assert "| Deflated Sharpe Ratio | >= 0.95 | 0.9999 |" in go and "- gate: net_mean_positive = yes, psr_ok = yes, null_p_ok = yes, pass = yes" in go
    assert "- PSR against zero: 0.9994" in go and "PASS, 0 warning(s), 0 missing bar(s)" in go
    # row 6 is a wrong-side row. The same deflation figures with a grid null that puts the best cell above random entries
    # are not a NO-GO: every estimate is on the right side, DSR is short, and that is INCONCLUSIVE at row 7
    six = json.load(open(os.path.join(tmp, "row6", "results", "verdict.json")))
    assert "at or below 0" in six["deciding"] and "the grid null does not put it above random entries (p 0.2000)" in six["deciding"]
    wide = {"deflate.no_days_enough": True, "deflate.days_needed": None, "deflate.days_needed_floor": 1234, "deflate.dsr": 0.31, "deflate.pass": False,
            "deflate.std_trials_measured": 0.0977, "deflate.std_trials_floor": 0.0614, "deflate.sharpe": 0.1494, "deflate.sr0": 0.1627, "oos": DROP}
    exp = make(tmp, "row6_structure", wide, cells=3)
    assert run(exp)[0] == 0
    j = json.load(open(os.path.join(exp, "results", "verdict.json")))
    assert (j["verdict"], j["row"], j["days_needed"]) == (v.INC, 7, 1234) and j["gates"][5]["pass"] is True, j
    assert "luckiest" not in j["deciding"] and "spread 0.0977 wide against a floor of 0.0614" in j["deciding"] and "days needed: 1234" in j["deciding"]
    assert "Sharpe 0.1494, SR0 0.1627, grid p 0.0010" in j["gates"][5]["observed"] and run(exp, "--check")[0] == 0
    exp = make(tmp, "row6_gridshort", {**wide, "sweep.grid_null.p": 0.0501}, cells=3)     # just above alpha: the NO-GO stands
    assert run(exp)[0] == 0 and json.load(open(os.path.join(exp, "results", "verdict.json")))["row"] == 6
    exp = make(tmp, "negative_break_even", {"effect_dev.net_by_tier.1.mean_bp": -15.4, "effect_dev.break_even_cost_bp": -4.4, **EARLY})
    assert run(exp)[0] == 0 and "the break-even cost is below zero: the trade lost on average before any cost was charged" in findings(exp)[1]
    assert "| 2 | 24 | -3 | -1.7 |" in section(block, "Costs: three tiers and break-even")
    assert section(findings(os.path.join(tmp, "row14"))[1], "Gates").count("| pass |") == 11  # rows 8 and 9 are not run on one cell


def test_qualifiers(tmp):
    exp = make(tmp, "file", {"events.kind": "file", "events.causality": "not verified (events were supplied as a file)"}, kind="file",
               source="Assumed 1 bp", history=[{"decl_sha256": "ab", "utc": "2025-12-01T00:00:00Z", "reason": "typo in the venue", "N": 1}])
    assert run(exp)[0] == 0
    j, (text, block) = json.load(open(os.path.join(exp, "results", "verdict.json"))), findings(exp)
    line = next(ln for ln in text.splitlines() if ln.startswith("**Verdict:**"))
    assert j["verdict"] == v.GO and "not verified" in line and "Four weeks of paper trading" in line
    assert "1 deviations after the freeze" in line and "half-spread assumed, not measured" in line and "typo in the venue" in section(block, "Deviations")
    head = next(l for l in text.splitlines() if l.startswith("Declarations sha256"))
    assert "amended 1 time(s), last 2025-12-01T00:00:00Z" in head and text.splitlines()[4] == "## In plain words", head
    exp = make(tmp, "measured")
    assert run(exp)[0] == 0 and findings(exp)[0].splitlines()[2].endswith("before any capital.")   # nothing to qualify
    exp = make(tmp, "noword", source="user own assumption")      # a source that does not say it was measured is not taken as measured
    code, out, _ = run(exp)
    assert code == 0 and "half-spread assumed, not measured" in findings(exp)[0].splitlines()[2] and "half-spread assumed, not measured" in out.splitlines()[-2]
    # gates declared weaker than the defaults are said on the verdict line, in the file and on RESULT:
    exp = make(tmp, "weak", alpha=0.1, dsr_min=0.9)
    code, out, _ = run(exp)
    line = findings(exp)[0].splitlines()[2]
    assert code == 0 and line.endswith("(gates weaker than the defaults: alpha 0.1 against 0.05, dsr_min 0.9 against 0.95)"), line
    assert out.splitlines()[-2] == "RESULT: " + line[13:] + " [row 14]"
    exp = make(tmp, "strict", alpha=0.01, dsr_min=0.99, over={"deflate.dsr": 0.995})
    assert run(exp)[0] == 0 and "weaker" not in findings(exp)[0]
    exp = make(tmp, "variants", variants=5)
    assert run(exp)[0] == 0
    text = findings(exp)[0]
    assert "N = 6 (1 cells + 5 earlier variants + 0 amend penalty)" in text and "N includes 5 earlier variants" in text
    exp = make(tmp, "sixty", {"oos": DROP, "deflate.dsr": 0.5, "deflate.pass": False}, cells=60)
    assert run(exp)[0] == 0
    grid = section(findings(exp)[1], "The declared grid")
    assert len(re.findall(r"^\| \d+ \| 0 \|", grid, re.M)) == 40 and "results/grid.csv" in grid and "first 40 of 60" in grid


def test_refusals(tmp):
    def refused(name, code, word, over=None, after=None, **opts):
        exp = make(tmp, name, over, **opts)
        if after:
            after(exp)
        got, out, err = run(exp)
        assert got == code and word in err and "Traceback" not in err, (name, got, err)
        assert not os.path.exists(os.path.join(exp, "FINDINGS.md")) and not os.path.exists(os.path.join(exp, "results", "verdict.json")), name
    grid = lambda exp: os.path.join(exp, "results", "grid.csv")
    refused("sha", 3, "other declarations", after=lambda e: patch(e, "effect_dev", decl_sha256="0" * 64))
    refused("dated", 3, "before the freeze", after=lambda e: patch(e, "events", created_utc="2025-12-31T23:59:59Z"))
    refused("gridrow", 3, "2 rows but 3 cells", cells=3, after=lambda e: write(grid(e), open(grid(e)).read().rsplit("\n", 2)[0] + "\n"))
    refused("ooscell", 3, "not the cell the sweep chose", {"oos.cell": 2}, cells=3)
    refused("data", 3, "data file changed", after=lambda e: write(os.path.join(e, "bars.csv"), "open_time,open\n1,2\n"))
    refused("shape", 3, "not a result the scripts wrote", after=lambda e: write(os.path.join(e, "results", "data_check.json"), "[]"))
    refused("shape2", 3, "not a result the scripts wrote", after=lambda e: write(os.path.join(e, "results", "oos.json"), '"x"'))
    # the out-of-sample look is recorded in the lock: a verdict is refused when its result file is gone or is from another look
    refused("oosgone", 3, "results/oos.json is missing", {"oos": DROP}, mark="2026-10-06T04:00:00Z")
    refused("oosagain", 3, "from another look", {"oos.opened_utc": "2026-10-06T05:00:00Z"}, mark="2026-10-06T04:00:00Z")
    assert run(make(tmp, "oosmark", mark="2026-10-06T04:00:00Z"))[0] == 0
    refused("edited", 3, "changed since the freeze", after=lambda e: write(os.path.join(e, "declarations.json"), "{}"))
    refused("nolock", 3, "not frozen", after=lambda e: os.remove(os.path.join(e, "declarations.lock")))
    refused("nosweep", 2, "sweep.py", {"sweep": DROP, "deflate": DROP, "oos": DROP})
    refused("nodeflate", 2, "deflate.py", {"deflate": DROP, "oos": DROP})
    refused("nooos", 2, " --oos, then", {"oos": DROP})
    refused("nodata", 2, "checkdata.py", {"data_check": DROP})
    refused("datafail", 2, "data check failed", {"data_check.result": "FAIL"})
    refused("noevents", 2, "events.py", {"events": DROP})
    refused("replay", 2, "replay test failed", {"events.causality": "FAIL: 3 differences in 200 probes"})
    refused("noeffect", 2, "effect.py", {"effect_dev": DROP, **EARLY})
    refused("zeroevents", 2, "no event was found", {"effect_dev": DROP, **EARLY}, after=lambda e: patch(e, "events", exit_code=1))


def test_check(tmp):
    exp = make(tmp, "check")
    path = os.path.join(exp, "FINDINGS.md")
    assert run(exp, "--check")[0] == 2  # nothing written yet
    assert run(exp)[0] == 0
    code, out, _ = run(exp, "--check")
    assert code == 0 and "RESULT: the generated block matches" in out and v.TODO in out.splitlines()[-1]
    text = open(path, encoding="utf-8").read()
    assert "- net mean (bp): 8" in text
    write(path, text.replace("- net mean (bp): 8", "- net mean (bp): 9"))  # one digit inside the block
    code, out, _ = run(exp, "--check")
    assert code == 1 and "FINDINGS.md was edited inside the generated block" in out
    write(path, text.replace(": GO\n", ": NO-GO\n", 1))  # the title line is covered too
    assert run(exp, "--check")[0] == 1
    write(path, text.replace(v.TODO, "Because the fixture says so."))  # prose filled in: still a pass, and kept on a re-run
    code, out, _ = run(exp, "--check")
    assert code == 0 and v.TODO not in out
    assert run(exp)[0] == 0
    assert open(path, encoding="utf-8").read().count("Because the fixture says so.") == 3 and run(exp, "--check")[0] == 0
    p = subprocess.run([sys.executable, "-B", os.path.join(os.path.dirname(HERE), "verdict.py"), "--exp", exp, "--json"], capture_output=True, text=True)
    j = json.loads(p.stdout)
    assert p.returncode == 0 and j["verdict"] == v.GO and j["row"] == 14 and j["NEXT"] == v.NEXT and j["decl_sha256"]


def test_plain_words():
    """A NO-GO at row 2 is one of three findings; each is named, and every verdict gets three plain lines."""
    def eff(mean, t, up, cost=12.0):
        return {"gross": {"mean_bp": mean, "t": t, "upper95_bp": up}, "cost_round_trip_bp": cost, "event_days": 500, "break_even_cost_bp": mean}
    m, hit = {"next_if_go": "paper trade"}, {"sentence": "DSR 0.80 is below 0.95"}
    d, lines = v.plain_words("NO-GO", 2, hit, eff(-4.4, -1.9, -0.6), None, m, None, 500)
    assert d == "wrong_way" and len(lines) == 3 and "points the wrong way" in lines[0] and "no level of cost makes it pay" in lines[1], lines
    d, lines = v.plain_words("NO-GO", 2, hit, eff(0.39, 0.21, 3.48), None, m, None, 500)
    assert d == "no_effect" and "cannot be told apart from zero" in lines[0] and "below the 12 bp it costs" in lines[0] and "less than 0.39 bp" in lines[1], lines
    d, lines = v.plain_words("NO-GO", 2, hit, eff(6.0, 0.9, 17.0), None, m, None, 500)
    assert d == "no_effect" and "cannot rule a tradable effect out" in lines[0], lines
    d, lines = v.plain_words("NO-GO", 2, hit, eff(7.5, 4.0, 10.6), None, m, None, 500)
    assert d == "below_cost" and "smaller than the 12 bp" in lines[0] and "variants already seen" in lines[2], lines
    assert v.plain_words("NO-GO", 3, hit, eff(20, 5, 26), None, m, None, 500)[0] == "no_better_than_random"
    assert v.plain_words("NO-GO", 11, hit, eff(20, 5, 26), None, m, None, 500)[0] == "failed_later_test"
    d, lines = v.plain_words("INCONCLUSIVE", 7, hit, eff(20, 5, 26), None, m, 640, 500)
    assert d == "short_sample" and "About 640 event days" in lines[1] and "Do not trade it" in lines[2], lines
    d, lines = v.plain_words("INCONCLUSIVE", 13, hit, eff(30, 21, 33), None, m, None, 700)
    assert d == "too_clean" and "not reported as GO" in lines[0] and "by hand" in lines[1], lines
    d, lines = v.plain_words("GO", 14, None, eff(20, 5, 26), {"net_mean_bp": 9.126, "event_days": 130}, m, None, 630)
    assert d == "passed" and "+9.13 bp per event day over 130 days" in lines[0] and lines[2].endswith("paper trade"), lines


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_rows(tmp)
        test_qualifiers(tmp)
        test_refusals(tmp)
        test_check(tmp)
    test_plain_words()


if __name__ == "__main__":
    main()
    print("test_verdict: all assertions passed")
