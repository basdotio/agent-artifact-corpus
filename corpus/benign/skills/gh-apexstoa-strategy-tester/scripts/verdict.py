#!/usr/bin/env python3
"""Apply the fixed verdict rule to the result files of one experiment and write FINDINGS.md.

No new statistics are computed here. The rule is a table read top to bottom; the first row whose condition
holds decides: GO, NO-GO (an estimate is on the wrong side) or INCONCLUSIVE (every estimate is on the right
side and only a significance gate is short; the days needed are printed).

  python3 verdict.py --exp EXP [--json]     writes EXP/results/verdict.json and EXP/FINDINGS.md
  python3 verdict.py --exp EXP --check      exit 1 if FINDINGS.md was edited inside the generated block
Exit 0 whenever a verdict is written (whichever verdict); 2 a step is missing; 3 refused (integrity).
The RESULT: line is the verdict line of FINDINGS.md word for word, qualifiers included.
"""
from __future__ import annotations

import argparse, csv, hashlib, json, math, os, shlex, sys

sys.dont_write_bytecode = True  # nothing is ever written into the skill folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _kit, declare

START, END = "<!-- generated:start -->", "<!-- generated:end -->"
TODO = "<to be written>"
PROSE = ("Why", "Artifact checks done by hand", "What this does not show")
STEPS = ("data_check", "events", "effect_dev", "sweep", "deflate", "oos")
GO, NOGO, INC = "GO", "NO-GO", "INCONCLUSIVE"
NEXT = "write the three prose sections of FINDINGS.md, then run verdict.py --check"
PASTE = "paste the In plain words lines, the **Verdict:** line and the Gates table of FINDINGS.md to the user word for word, plain words first"
KEEP = "do not edit files in results/: run the step again"


PROBABILITIES = ("p", "psr0", "dsr", "dsr_min", "psr0_autocorr_adjusted", "hit_rate", "tie_rate", "flat_share",
                 "zero_volume_share", "dropped_share")  # always printed to 4 decimals, so 1 reads 1.0000
LABELS = {"break_even_cost_bp": "break-even round-trip cost (bp), the gross mean per trade",
          "cost_round_trip_bp": "round-trip cost charged (bp)", "psr0": "PSR against zero", "dsr": "Deflated Sharpe Ratio",
          "N": "N (trials)", "n": "n (event days)", "sr0": "SR0 (expected best-of-N Sharpe)"}


def num(v) -> str:
    """Plain text for a JSON value: n/a for null, yes/no, floats to 4 decimals without trailing zeros, an object
    as 'key = value' pairs, a list as its values."""
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    if isinstance(v, dict):
        return ", ".join(f"{k} = {num(x)}" for k, x in v.items()) or "none"
    if isinstance(v, list):
        return ", ".join(num(x) for x in v) or "none"
    return str(v)


def prob(v) -> str:
    """A probability or a share to 4 decimals; n/a for null."""
    return "n/a" if v is None else f"{v:.4f}"


def bullets(doc, keys, prefix="") -> list[str]:
    """One '- label: value' line per key present in doc; *_utc integers are shown as UTC text, probabilities
    to 4 decimals. With a prefix such as 'null ' a key that repeats it ('null_mean_bp') is not said twice."""
    out, cut = [], prefix.strip().split(" ")[-1] + "_"
    for k in keys:
        if k in (doc or {}):
            v = doc[k]
            v = _kit.utc_iso(v) if k.endswith("_utc") and isinstance(v, int) else prob(v) if k in PROBABILITIES and not isinstance(v, bool) else num(v)
            name = k[len(cut):] if prefix and k.startswith(cut) else k
            out.append(f"- {prefix}{LABELS.get(k) or name.replace('_bp', ' (bp)').replace('_', ' ')}: {v}")
    return out


def shown(column, text) -> str:
    """A grid.csv cell for the findings table: the measured columns to 4 decimals, the rest as written."""
    try:
        return num(float(text)) if column in ("gross_mean_bp", "net_mean_bp", "net_sd_bp", "sharpe", "t") and text.strip() else text
    except ValueError:
        return text


def table(head, rows) -> list[str]:
    """A Markdown table."""
    line = lambda cells: "| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |"
    return [line(head), line(["---"] * len(head))] + [line(r) for r in rows]


def null_days(days, z):
    """Event days for a random-entry null to reach one-sided 95% at the observed effect: ceil(D * (z95 / z)^2)."""
    return math.ceil(days * (_kit.Z95 / z) ** 2) if z is not None and z > 0 else None


def load(exp):
    """(decl, lock, results by step name, grid rows or None) after the integrity checks; exit 3 on any of them."""
    decl, lock = _kit.load_decl(exp)
    res = {s: _kit.read_json(os.path.join(exp, "results", s + ".json")) for s in STEPS}
    last = max([lock.get("frozen_utc") or ""] + [h.get("utc") or "" for h in lock.get("history") or []])
    for s, doc in res.items():
        if doc is not None and not isinstance(doc, dict):
            _kit.die(3, f"results/{s}.json is not a result the scripts wrote (it holds {type(doc).__name__}, not an object)", "the file as its script wrote it", KEEP)
        if doc is not None and doc.get("decl_sha256") != lock["decl_sha256"]:
            _kit.die(3, f"results/{s}.json was made under other declarations", "every result made after the last freeze or amend", KEEP)
        if doc is not None and (doc.get("created_utc") or "") < last:
            _kit.die(3, f"results/{s}.json is dated {doc.get('created_utc')}, before the freeze or amend at {last}", "results made after the declarations were frozen", KEEP)
    _kit.check_data(decl, lock)
    mark = lock.get("oos_opened_utc")
    if mark and (res["oos"] is None or res["oos"].get("opened_utc") != mark):
        _kit.die(3, f"out-of-sample was opened on {mark} (recorded in declarations.lock) but results/oos.json is "
                 + ("missing" if res["oos"] is None else f"from another look ({res['oos'].get('opened_utc')})"),
                 "the results/oos.json written by that one look", "put that file back; out-of-sample is read once and a second look is not a result")
    grid, path = None, os.path.join(exp, "results", "grid.csv")
    if os.path.exists(path) or res["sweep"] is not None:
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                grid = list(csv.DictReader(fh))
        except OSError:
            grid = []
        if len(grid) != lock["cells_declared"]:
            _kit.die(3, f"results/grid.csv holds {len(grid)} rows but {lock['cells_declared']} cells were declared", "one row per declared cell", KEEP)
    if res["oos"] is not None and (res["sweep"] is None or res["oos"].get("cell") != res["sweep"].get("chosen_cell")):
        _kit.die(3, f"oos.json is for cell {res['oos'].get('cell')}, not the cell the sweep chose", "the out-of-sample look on the chosen cell", KEEP)
    return decl, lock, res, grid


def missing(exp, what, script, extra=""):
    """Exit 2 naming the step to run."""
    here = os.path.dirname(os.path.abspath(__file__))
    _kit.die(2, what, "every step up to this point done in order",
             f"run python3 {shlex.quote(os.path.join(here, script))} --exp {shlex.quote(os.path.abspath(exp))}{extra}, then verdict.py again")


def decide(exp, decl, lock, res, grid) -> dict:
    """The verdict.json payload: every gate that can be evaluated, and the first failing row as the verdict."""
    m, kind = decl["method"], decl.get("kind")
    alpha, mind, gates = m["null"]["alpha"], m["gates"]["min_event_days"], []
    dc, ev, eff, sw, de, oos = (res[s] for s in STEPS)
    if dc is None:
        missing(exp, "no results/data_check.json", "checkdata.py")
    if dc.get("result") != "PASS":
        _kit.die(2, "the data check failed: no verdict is given on data that fails it", "DATA CHECK: PASS",
                 "repair the file as checkdata.py lists, then start a new experiment folder on the repaired file")
    if ev is None:
        missing(exp, "no results/events.json", "events.py")
    if "FAIL" in str(ev.get("causality")) or (ev.get("replay") or {}).get("differences"):
        _kit.die(2, "the replay test failed: the rule gives different answers when replayed", "causality checked with 0 differences",
                 "fix the rule so it uses only its two arguments, amend, and run events.py again")
    if (ev.get("dropped_share") or 0) > m["gates"]["max_dropped_event_share"]:
        _kit.die(2, f"{num(ev['dropped_share'])} of the events were dropped, above the declared {m['gates']['max_dropped_event_share']}",
                 "a sample that is the declared one", "see the dropped list in events.json; repair the data gaps and start again")
    if ev.get("exit_code") not in (0, None):
        _kit.die(2, "events.py did not pass (no event was found in the development data): there is nothing to give a verdict on",
                 "results/events.json with exit_code 0", "show the user the events.py output; a change to the event or the data goes through declare.py amend")
    if eff is None:
        missing(exp, "no results/effect_dev.json", "effect.py")

    def gate(row, name, required, observed, ok=None, verdict=None, sentence=None, days=None):
        gates.append({"row": row, "name": name, "required": required, "observed": observed, "pass": ok,
                      "verdict": verdict, "sentence": sentence, "days": days})

    days, nul = eff["event_days"], eff["null"]
    net = next(t["mean_bp"] for t in eff["net_by_tier"] if abs(t["tier"] - 1) < 1e-9)
    gate(1, "development event days", f">= {mind}", str(days), days >= mind, INC, f"{days} event days, {mind} declared as the minimum", mind)
    gate(2, "development net mean at the declared cost", "> 0 bp", f"{net:+.2f} bp", net > 0, NOGO,
         f"development net mean {net:+.2f} bp per event day: the raw effect {eff['break_even_cost_bp']:+.2f} bp per trade "
         f"does not cover the round-trip cost {eff['cost_round_trip_bp']:g} bp")
    gate(3, "development excess over random entries", "> 0 bp", f"{nul['excess_bp']:+.2f} bp", nul["excess_bp"] > 0, NOGO,
         f"the event did no better than random entries ({nul['pool']})")
    gate(4, "development random-entry null p", f"<= {alpha}", prob(nul["p"]), nul["p"] <= alpha, INC,
         f"development null p {prob(nul['p'])} is above {alpha}", null_days(days, nul.get("z")))
    ahead = all(g["pass"] for g in gates)
    if ahead and sw is None:
        missing(exp, "the characterisation gate passed but there is no results/sweep.json", "sweep.py")
    chosen = sw.get("chosen_cell") if ahead else None
    if ahead and chosen is None:  # the sweep found no cell with the minimum event days: row 1 on the cells
        best = max([int(r["event_days"]) for r in grid if (r.get("event_days") or "").strip()] or [0])
        gates[0].update({"observed": f"{best} in the best cell", "pass": False, "sentence": f"{best} event days, {mind} declared as the minimum"})
        ahead = False
    if ahead and de is None:
        missing(exp, "the characterisation gate passed but there is no results/deflate.json", "deflate.py")
    names = {5: "chosen cell net mean", 6: "Sharpe above SR0 (luckiest of N), or grid null met", 7: "Deflated Sharpe Ratio",
             8: "grid null z", 9: "grid null p", 10: "out-of-sample event days", 11: "out-of-sample net mean and excess",
             12: "out-of-sample PSR(0) and null p"}
    req = {5: "> 0 bp", 6: f"> SR0, or grid p <= {alpha}", 7: f">= {m['gates']['dsr_min']}", 8: "> 0", 9: f"<= {alpha}",
           10: f">= {mind}", 11: "both > 0 bp", 12: f">= {m['gates']['oos_psr_min']} and <= {alpha}"}
    if ahead:
        row = next((r for r in grid if r.get("cell") == str(chosen)), grid[int(chosen)])
        gate(5, names[5], req[5], f"{float(row['net_mean_bp']):+.2f} bp (cell {chosen})", float(row["net_mean_bp"]) > 0, NOGO, "no declared cell is net positive")
        gn = sw.get("grid_null")
        # Row 6 is a wrong-side row (NO-GO), so it may fire only when no estimate contradicts it. The spread of the
        # cells' Sharpes that sets SR0 also holds the structure of the grid (a short hold pays the whole cost for part
        # of the effect), so "Sharpe at or below SR0" alone does not show luck. When the grid null puts the best cell
        # above the best cell on random entries (p <= alpha), the row passes and the short DSR is row 7: INCONCLUSIVE.
        beaten = bool(gn) and gn.get("p") is not None and gn["p"] <= alpha
        gate(6, names[6], req[6], f"Sharpe {num(de['sharpe'])}, SR0 {num(de['sr0'])}" + (f", grid p {prob(gn.get('p'))}" if gn else ""),
             not de["no_days_enough"] or beaten, NOGO,
             f"the best cell's Sharpe {num(de['sharpe'])} is at or below {num(de['sr0'])}, what the luckiest of {de['N']} unskilled cells is "
             "expected to show" + (f", and the grid null does not put it above random entries (p {prob(gn.get('p'))})" if gn else ""))
        wide = de["no_days_enough"] and beaten
        gate(7, names[7], req[7], prob(de["dsr"]), de["dsr"] >= m["gates"]["dsr_min"], INC,
             f"DSR {prob(de['dsr'])} is below {m['gates']['dsr_min']} at N = {de['N']}" + (
                 f" (the cells' Sharpes are spread {num(de.get('std_trials_measured'))} wide against a floor of {num(de.get('std_trials_floor'))}, "
                 "so no number of days reaches the gate with this grid; the figure given is for the floor spread alone)" if wide else ""),
             de.get("days_needed_floor") if wide else de.get("days_needed"))
        if gn:
            gate(8, names[8], req[8], num(gn.get("z")), gn.get("z") is None or gn["z"] > 0, NOGO, "the best cell is no better than the best cell on random entries")
            gate(9, names[9], req[9], prob(gn.get("p")), gn.get("p") is not None and gn["p"] <= alpha, INC,
                 f"grid null p {prob(gn.get('p'))} is not at or below {alpha}", null_days(de["n"], gn.get("z")))
        ahead = all(g["pass"] for g in gates)
        if ahead and oos is None:
            missing(exp, "development passed but there is no results/oos.json", "sweep.py", " --oos")
    if oos is not None and ahead:
        on, od, pmin = oos["null"], oos["event_days"], m["gates"]["oos_psr_min"]
        gate(10, names[10], req[10], str(od), od >= mind, INC, f"{od} out-of-sample event days, {mind} declared as the minimum", mind)
        exc, p, p0 = on.get("excess_bp"), on.get("p"), oos.get("psr0")  # a null that could not be formed is short, not wrong-sided
        gate(11, names[11], req[11], f"{(oos.get('net_mean_bp') or 0):+.2f} bp, " + ("n/a" if exc is None else f"{exc:+.2f} bp"), (oos.get("net_mean_bp") or 0) > 0 and (exc is None or exc > 0),
             NOGO, "it did not hold on the unseen segment")
        trl = _kit.min_trl(oos.get("sharpe") or 0.0, oos.get("skew") or 0.0, oos.get("kurt") or 3.0, 0.0, _kit.PhiInv(pmin))
        need = max(trl, null_days(od, on.get("z")) or 0)
        gate(12, names[12], req[12], f"{prob(p0)}, {prob(p)}", p0 is not None and p0 >= pmin and p is not None and p <= alpha, INC,
             f"out-of-sample PSR(0) {prob(p0)} against {pmin}, null p {prob(p)} against {alpha}", math.ceil(need) if math.isfinite(need) else None)
    done = {g["row"] for g in gates}
    for r in range(5, 13):
        if r not in done:
            gate(r, names[r], req[r], "not run")
    flags = list(eff.get("flags") or []) + list((de or {}).get("flags") or [])
    gate(13, "no suspiciously clean result", "0 flags", f"{len(flags)} flags", not flags, INC,
         "result is suspiciously clean: reproduce three trades by hand, then declare again")
    gates.sort(key=lambda g: g["row"])
    hit = next((g for g in gates if g["pass"] is False), None)
    history = days + (oos["event_days"] if oos else 0)
    verdict, row, days_needed = (hit["verdict"], hit["row"], hit["days"]) if hit else (GO, 14, None)
    if hit is None:
        deciding = f"survived every declared test; next: {m.get('next_if_go')}"
    elif verdict == INC:
        deciding = f"{hit['sentence']}; days needed: {'not computable' if days_needed is None else days_needed}; history in this file: {history} event days"
    else:
        deciding, days_needed = f"{hit['sentence']}; next: {m.get('next_if_no_go')}", None
    q = ["causality of supplied events not verified"] if kind == "file" else []
    if lock.get("variants_seen"):
        q.append(f"N includes {lock['variants_seen']} earlier variants")
    if lock.get("history"):
        q.append(f"{len(lock['history'])} deviations after the freeze")
    source = str(decl["costs"].get("source") or "").strip().lower()
    if not source.startswith("measured"):  # declare.py check allows only measured or assumed as the first word
        q.append("half-spread assumed, not measured")
    weak = []
    for key, sign in declare.LOOSER:
        now, std = declare.get(m, key), declare.get(declare.method_defaults(kind), key)
        if declare.num(now) and (now - std) * sign > 0:
            weak.append(f"{key.split('.')[-1]} {now:g} against {std:g}")
    if weak:
        q.append("gates weaker than the defaults: " + ", ".join(weak))
    diagnosis, plain = plain_words(verdict, row, hit, eff, oos, m, days_needed, history)
    return {"verdict": verdict, "row": row, "deciding": deciding, "qualifiers": q, "days_needed": days_needed, "history_event_days": history,
            "diagnosis": diagnosis, "plain": plain,
            "gates": [{k: g[k] for k in ("row", "name", "required", "observed", "pass")} for g in gates]}


def plain_words(verdict, row, hit, eff, oos, m, days_needed, history):
    """(diagnosis, lines): the verdict in sentences a newcomer can act on. Built only from result figures.
    A NO-GO at row 2 is one of three different findings, and the user needs to know which:
    wrong_way (lost before costs), no_effect (nothing distinguishable from zero), below_cost (real but too small)."""
    g, cost, D = eff["gross"], eff["cost_round_trip_bp"], eff["event_days"]
    mean, t, up, be = g["mean_bp"], g["t"], g["upper95_bp"], eff["break_even_cost_bp"]
    again = ("This experiment is closed. To test a different version, start a new experiment folder and count this one "
             "under 'variants already seen', so the next result is held to a higher bar.")
    if verdict == GO:
        tail = "" if not oos else f" On the unseen segment the net mean was {oos.get('net_mean_bp') or 0:+.2f} bp per event day over {oos.get('event_days')} days."
        return "passed", ["It passed every test that was declared before the data was read." + tail,
                          "This is evidence about the past at the declared costs. It is not a promise about the future.",
                          f"Next, as declared: {m.get('next_if_go')}"]
    if verdict == INC and row == 13:
        return "too_clean", ["Every declared test passed, but the result is stronger than real markets normally give. That more often "
                             "means a fault in the data or the rule than a real edge, so it is not reported as GO.",
                             "Reproduce three trades by hand from the raw price rows, and confirm where the price file came from.",
                             "If both hold up, declare the idea again and test it on data this experiment has not used."]
    if verdict == INC:
        need = "No number of extra days is computable from this result." if days_needed is None else \
               f"About {days_needed} event days would be needed; this file has {history}."
        return "short_sample", [f"Every estimate points the right way, but the evidence is not strong enough yet: {hit['sentence']}.",
                                need, "Do not trade it on this result. More data settles it; a changed rule does not."]
    if row == 2:
        pays = (f"It would pay only if a round trip cost less than {be:.2f} bp; the declared cost is {cost:g} bp."
                if be > 0 else "The average was at or below zero before any cost, so no level of cost makes it pay on this sample.")
        if up <= 0:
            return "wrong_way", [f"Before any cost the trade lost on average ({mean:+.2f} bp per event day over {D} days), and even the "
                                 f"optimistic end of the estimate ({up:+.2f} bp) is below zero: on this data the idea points the wrong way.",
                                 pays, again]
        if t < _kit.Z95:
            reach = (f"Even the optimistic end of the estimate ({up:+.2f} bp) is below the {cost:g} bp it costs to trade."
                     if up < cost else
                     f"The optimistic end of the estimate ({up:+.2f} bp) is above the {cost:g} bp cost, so this sample cannot rule a tradable effect out.")
            return "no_effect", [f"No effect shows up before costs: the average was {mean:+.2f} bp per event day over {D} days, "
                                 f"which cannot be told apart from zero (t {t:+.2f}). {reach}", pays, again]
        return "below_cost", [f"There is an effect before costs ({mean:+.2f} bp per event day over {D} days, t {t:+.2f}), "
                              f"but it is smaller than the {cost:g} bp it costs to trade.", pays, again]
    if row == 3:
        return "no_better_than_random", ["The trade was net positive only because prices moved that way in general: the same trade at random "
                                         "times did as well or better.", "Nothing is special about the declared moment on this data.", again]
    return "failed_later_test", [f"It passed the first checks and then failed a later one: {hit['sentence']}.",
                                 "A result that does not survive its own declared tests is not an edge.", again]


def verdict_line(out) -> str:
    """The verdict with its deciding sentence and every qualifier: the text of the **Verdict:** line and of RESULT:."""
    return f"{out['verdict']}: {out['deciding']}" + (f" ({'; '.join(out['qualifiers'])})" if out["qualifiers"] else "")


def result_word(g, out) -> str:
    return "not run" if g["pass"] is None else "pass" if g["pass"] else "FAIL (decides)" if g["row"] == out["row"] else "FAIL"


def render(exp, decl, lock, res, grid, out) -> str:
    """Title line plus the generated block of FINDINGS.md, built only from the lock and results/."""
    dc, ev, eff, sw, de, oos = (res[s] for s in STEPS)
    idea, sec, net = decl["idea"], [], eff.get("net")

    def section(title, lines, source):
        sec.extend(["", f"## {title}", ""] + (lines if lines else ["not run"]) + ["", f"Source: {source}"])

    hist = lock.get("history") or []
    head = [f"# {_kit.title(idea.get('instrument'), idea.get('hypothesis'))}: {out['verdict']}", START,
            f"**Verdict:** {verdict_line(out)}", "", "## In plain words", ""] + [f"- {s}" for s in out["plain"]] + ["",
            f"Declarations sha256 {lock['decl_sha256'][:12]}, frozen {lock.get('frozen_utc')}"
            + (f", amended {len(hist)} time(s), last {hist[-1].get('utc')}" if hist else "") + f". N = {lock['N']} ({lock['cells_declared']} cells + "
            f"{lock.get('variants_seen', 0)} earlier variants + {lock.get('amend_penalty', 0)} amend penalty). "
            f"Prior looks: {' '.join(str((idea.get('prior_looks') or {}).get('text')).split()).rstrip('.')}."]
    section("Gates", table(["#", "Gate", "Required", "Observed", "Result"],
                           [[g["row"], g["name"], g["required"], g["observed"], result_word(g, out)] for g in out["gates"]])
            + ["", "No row failed: GO." if out["row"] == 14 else f"The first failing row decides: row {out['row']}."], "results/verdict.json")
    section("Data check", bullets(dc, ("result", "rows", "first_utc", "last_utc", "bar_seconds", "missing_bars", "largest_gap_bars",
                                       "duplicates_identical", "flat_share", "zero_volume_share", "tie_rate"))
            + [f"- warning: {w}" for w in dc.get("warns") or []]
            + [f"- {n}" for n in dc.get("notes") or []], "results/data_check.json")
    drop = ev.get("dropped_missing_entry") or []
    section("Events and causality", bullets(ev, ("kind",)) + [f"- events by parameter set: {num(ev.get('events'))}"]
            + bullets(ev, ("events_by_year", "dropped_straddles_split", "skipped_gap_in_lookback",
                                                  "dropped_share", "causality", "replay", "utc_time_summer", "utc_time_winter", "days_by_utc_time"))
            + [f"- dropped for a missing entry bar: {len(drop)}" + (": " + ", ".join(str(d.get("date")) for d in drop[:10]) if drop else "")]
            + (["- no holiday calendar is applied: closed-market weekdays count as events unless a skip_dates_file was declared"]
               if decl.get("kind") == "clock" else []), "results/events.json")
    section("Raw effect and random-entry null",
            bullets(eff, ("cell", "events", "trades", "skipped_overlap", "dropped_missing_exit", "event_days", "hit_rate", "tie_rate", "lag1_autocorr"))
            + bullets(eff.get("gross"), ("mean_bp", "median_bp", "sd_bp", "t", "upper95_bp"), "gross ")
            + ([f"- net per event day at the declared cost: mean {num(net['mean_bp'])} bp, sd {num(net['sd_bp'])} bp, Sharpe {num(net['sharpe'])} "
                f"(per day, not annualised), t {num(net['t'])}, PSR against zero {prob(net['psr0'])} (this cell alone: no trial count in it)"]
               if net else [])
            + bullets(eff["null"], ("pool", "draws", "seed", "statistic_bp", "null_mean_bp", "null_sd_bp", "null_p95_bp", "excess_bp", "z", "b", "m", "p_draws", "event_se_bp", "p_adjusted", "p",
                                    "days_excluded"), "null ")
            + ["- weekend placebo (reported, not gated): " + (num(eff["placebo"]) if eff.get("placebo") else "NOT RUN")]
            + [f"- flag: {f}" for f in eff.get("flags") or []], "results/effect_dev.json")
    section("Costs: three tiers and break-even",
            bullets(decl["costs"], ("fee_bp_per_fill", "half_spread_bp_per_fill", "source")) + bullets(eff, ("cost_round_trip_bp", "break_even_cost_bp"))
            + (["- the break-even cost is below zero: the trade lost on average before any cost was charged"] if eff["break_even_cost_bp"] < 0 else [])
            + [""] + table(["Tier", "Round-trip cost (bp)", "Net mean (bp)", "t"],
                           [[num(t["tier"]), num(t["cost_bp"]), num(t["mean_bp"]), num(t["t"])] for t in eff["net_by_tier"]]), "results/effect_dev.json")
    lines = []
    if sw is not None:
        cols = list(grid[0].keys()) if grid else []
        lines = [f"{lock['cells_declared']} cells declared, {sw.get('cells_run')} run, net-positive {sw.get('net_positive_cells')} of {lock['cells_declared']}. "
                 f"Chosen cell: {num(sw.get('chosen_cell'))} ({sw.get('selection_rule')}).", ""] + table(cols, [[shown(c, r[c]) for c in cols] for r in grid[:40]])
        if len(grid) > 40:
            lines += ["", f"The first 40 of {len(grid)} cells are shown; every cell is in results/grid.csv."]
        lines += [""] + (bullets(sw["grid_null"], ("draws_declared", "draws_used", "real_best_sharpe", "null_mean", "null_sd", "null_p95", "z", "b", "m", "p"),
                                 "grid null ") if sw.get("grid_null") else ["grid null: not run"])
    section("The declared grid", lines, "results/grid.csv, results/sweep.json")
    section("Deflation", de and bullets(de, ("cell", "n", "sharpe", "t", "skew", "kurt", "psr0", "N", "cells_declared", "std_trials_measured",
                                             "std_trials_floor", "std_trials_used", "emax_closed", "emax_exact", "emax_used", "sr0", "dsr", "dsr_min",
                                             "pass", "days_needed", "no_days_enough", "days_needed_floor", "lag1_autocorr", "psr0_autocorr_adjusted"))
            + list(de.get("warnings") or []) + list(de.get("flags") or []), "results/deflate.json")
    section("Out-of-sample, one look", oos and bullets(oos, ("cell", "opened_utc", "events", "trades", "event_days", "gross_mean_bp", "cost_round_trip_bp",
                                                             "break_even_cost_bp", "net_mean_bp", "net_sd_bp", "sharpe", "t", "skew", "kurt", "psr0", "gate"))
            + bullets(oos.get("null"), ("pool", "statistic_bp", "null_mean_bp", "null_sd_bp", "excess_bp", "z", "b", "m", "p"), "null "), "results/oos.json")
    years = [("development", y) for y in eff.get("by_year") or []] + [("out-of-sample", y) for y in (oos or {}).get("by_year") or []]
    keys = sorted({k for _, y in years for k in y}, key=lambda k: (k != "year", k != "days", k))
    section("By year", table(["segment"] + keys, [[seg] + [num(y.get(k)) for k in keys] for seg, y in years]) if years else ["no rows"],
            "results/effect_dev.json" + (", results/oos.json" if oos else ""))
    section("Deviations", [json.dumps(h, sort_keys=True) for h in lock.get("history") or []] or ["none"], "declarations.lock")
    state = lambda doc, text: "NOT RUN" if doc is None else text
    section("Artifact checks done by the scripts", table(["Artifact", "Checked by", "State"], [
        ["declarations or data changed after the freeze", "declarations.lock sha256", "checked: unchanged"],
        ["broken or missing bars", "data_check.json result", f"{dc['result']}, {len(dc.get('warns') or [])} warning(s), {num(dc.get('missing_bars'))} missing bar(s)"],
        ["look-ahead in the event timing", "events.json causality", str(ev.get("causality"))],
        ["events lost to gaps", "events.json dropped_share", f"{prob(ev.get('dropped_share'))} against {decl['method']['gates']['max_dropped_event_share']} allowed"],
        ["costs left out", "effect_dev.json break_even_cost_bp", f"break-even {num(eff['break_even_cost_bp'])} bp against {num(eff['cost_round_trip_bp'])} bp charged"],
        ["drift mistaken for an effect", "effect_dev.json null.p", f"p {prob(eff['null']['p'])} (the larger of the draw count and the p adjusted for the event window's own spread)"],
        ["calendar artifact (weekend placebo)", "effect_dev.json placebo", "checked: see the raw effect section" if eff.get("placebo") else "NOT RUN"],
        ["serial dependence between event days", "effect_dev.json lag1_autocorr", num(eff.get("lag1_autocorr"))],
        ["best cell picked from many", "deflate.json dsr at N", state(de, f"DSR {prob((de or {}).get('dsr'))} at N = {lock['N']}")],
        ["cells that are copies of each other", "sweep.json grid_null", state((sw or {}).get("grid_null"), f"p {prob(((sw or {}).get('grid_null') or {}).get('p'))}")],
        ["fitted to the development segment", "oos.json gate", state(oos, f"opened once, gate pass: {num(((oos or {}).get('gate') or {}).get('pass'))}")],
        ["too clean to be true", "flags in effect_dev.json and deflate.json", out["gates"][-1]["observed"]]]), "results/verdict.json")
    return "\n".join(head + sec + ["", END])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Apply the verdict rule and write FINDINGS.md; --check detects edits to the generated block.")
    ap.add_argument("--exp", required=True, help="experiment folder")
    ap.add_argument("--check", action="store_true", help="compare FINDINGS.md with the result files; write nothing")
    ap.add_argument("--json", action="store_true", help="print verdict.json instead of text")
    a = ap.parse_args(argv)
    decl, lock, res, grid = load(a.exp)
    out = decide(a.exp, decl, lock, res, grid)
    block, path = render(a.exp, decl, lock, res, grid, out), os.path.join(a.exp, "FINDINGS.md")
    try:
        with open(path, encoding="utf-8") as fh:
            old = fh.read().replace("\r\n", "\n")
    except OSError:
        old = None
    if a.check:
        if old is None:
            _kit.die(2, "there is no FINDINGS.md to check", "a file written by verdict.py", "run python3 verdict.py --exp EXP first")
        same, left = old.split(END)[0] + END == block and old.count(END) == 1, old.count(TODO)
        _kit.finish({"check": same, "prose_sections_unwritten": left},
                    ("the generated block matches the result files" + (f"; {left} prose section(s) still read {TODO}, so the findings are not finished" if left else ""))
                    if same else "FINDINGS.md was edited inside the generated block",
                    ("write the prose sections still reading " + TODO + ", then run this check again" if left else
                     PASTE) if same
                    else "run python3 verdict.py --exp EXP to restore the block (the prose is kept); change a result only by declare.py amend",
                    0 if same else 1, as_json=a.json)
    tail = old.split(END, 1)[1] if old and END in old else "\n" + "".join(f"\n## {h}\n\n{TODO}\n" for h in PROSE)
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(block + tail)
    os.replace(path + ".tmp", path)
    full = _kit.write_result(a.exp, "verdict.json", out, 0, script="verdict")
    lines = [f"{g['row']:>2}  {g['name']:<50} {g['required']:<30} {g['observed']:<30} {result_word(g, out)}" for g in out["gates"]]
    _kit.finish(full, verdict_line(out) + f" [row {out['row']}]", NEXT, 0, as_json=a.json,
                lines=lines + ["IN PLAIN WORDS:"] + [f"  {s}" for s in out["plain"]] + [f"VERDICT: {out['verdict']}"])


if __name__ == "__main__":
    _kit.guard(main)
