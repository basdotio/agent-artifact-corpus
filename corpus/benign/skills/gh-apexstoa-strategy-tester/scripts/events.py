#!/usr/bin/env python3
"""Build the development events of a frozen experiment and test that they use nothing from the future.

  python3 events.py --exp EXP [--json]

clock: one event per declared date, the local clock time converted to UTC for that date (daylight saving
       resolved per date); the entry bar is the bar opening exactly then, a missing bar drops the event.
rule:  EXP/rule.py is called once per bar with a window of the LOOKBACK closed bars before it and nothing
       later; a replay on fresh imports of the rule then looks for hidden state. The rule file is ordinary
       Python run on this machine with the user's rights. It is not sandboxed: before it is run its text is
       checked (top level holds only a docstring, constants and functions; no import but math and statistics;
       no open, exec, eval, compile, input or __import__), which stops accidents, not a determined author.
file:  EXP/<events_file> (decision_ts[,side]); each event enters at the first bar opening at or after it.
Writes results/events_dev.csv and results/events.json. Times are UTC epoch seconds. Exits: 0 done; 1 replay
failed, no events, or too many dropped; 2 a rule or events file that cannot be used; 3 refused.
"""
from __future__ import annotations

import argparse, ast, bisect, csv, hashlib, os, random, shlex, sys, types
from datetime import date, timedelta

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _kit

COLUMNS = ["pset", "segment", "day", "decision_ts", "entry_ts", "side"]
SIDES = {"long": 1, "short": -1, "1": 1, "+1": 1, "-1": -1}
WANT = {"long": (1,), "short": (-1,), "both": (1, -1)}
NOT_CALLED = 255  # marker in the per-bar record of what the rule returned


def _input(decl, lock, key, exp):
    """Path of a declared input file (rule_file, events_file, skip_dates_file), or None when not declared. Exit 3 if
    its bytes differ from the freeze. The lock's stored path is used when no experiment folder is given."""
    name = (decl["idea"].get("event") or {}).get(key)
    if name is None:
        return None
    rec = ((lock or {}).get("inputs") or {}).get(key) or {}
    path = rec.get("path") if exp is None else name if os.path.isabs(name) else os.path.join(exp, name)
    if not path or not os.path.isfile(path):
        _kit.die(2, f"{key} {name!r} cannot be found", "the file named in declarations.json, in the experiment folder",
                 "put the file back (callers of build_events: pass exp=EXP when the lock holds no path for it)")
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    if rec.get("sha256") and sha != rec["sha256"]:
        _kit.die(3, f"{name} changed since the freeze", "the file exactly as frozen",
                 "restore it, or run declare.py amend --reason \"...\" so the change is recorded")
    return path


def clock_schedule(decl, lo, hi, skip_path=None):
    """Yield (local date 'YYYY-MM-DD', decision_ts) for every declared event date whose decision time lies in
    lo .. hi (epoch seconds, inclusive). Dates listed in the skip file are left out."""
    ev, skip = decl["idea"]["event"], set()
    want = set(range(5)) if ev["days"] == "weekdays" else set(range(7)) if ev["days"] == "all" else set(ev["days"])
    if skip_path:
        with open(skip_path, encoding="utf-8-sig") as f:
            skip = {line.strip() for line in f if line.strip()}
    d, end = (date.fromisoformat(_kit.utc_day(t)) + timedelta(days=k) for t, k in ((lo, -1), (hi, 1)))
    while d <= end:
        if d.weekday() in want and d.isoformat() not in skip:
            ts = _kit.local_to_utc(d, ev["local_time"], ev["zone"])
            if lo <= ts <= hi:
                yield d.isoformat(), ts
        d += timedelta(days=1)


RULE_IMPORTS = ("math", "statistics")
RULE_BANNED = ("open", "exec", "eval", "compile", "input", "__import__", "globals", "breakpoint")


def rule_text_problem(tree):
    """Why the parsed rule file may not be run, or None. The top level may hold a docstring, names set to plain
    constants, functions and `import math` / `import statistics`; nothing anywhere may import another module or
    name open, exec, eval, compile, input, __import__, globals or breakpoint. This keeps a rule from doing
    anything when it is loaded (declare.py check loads it before the user has accepted the draft). It is a
    check of the text, not a sandbox."""
    def literal(node):
        try:
            ast.literal_eval(node)
            return True
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            return False
    for node in tree.body:
        ok = (isinstance(node, (ast.FunctionDef, ast.Import, ast.ImportFrom))
              or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
              or (isinstance(node, ast.Assign) and literal(node.value))
              or (isinstance(node, ast.AnnAssign) and node.value is not None and literal(node.value)))
        if not ok:
            return f"line {node.lineno} does something when the file is loaded: the top level may only set constants and define functions"
    for node in ast.walk(tree):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or "."] if isinstance(node, ast.ImportFrom) else []
        if any(n.split(".")[0] not in RULE_IMPORTS for n in names) or (isinstance(node, ast.ImportFrom) and node.level):
            return f"line {node.lineno} imports {', '.join(names)}: a rule may import only math and statistics"
        if (isinstance(node, ast.Name) and node.id in RULE_BANNED) or (isinstance(node, ast.Attribute) and node.attr.startswith("__")):
            return f"line {node.lineno} uses {getattr(node, 'id', None) or getattr(node, 'attr', '')}: a rule reads nothing but its two arguments"
    return None


def compile_rule(path):
    """Compiled source of the rule file; exit 2 when it cannot be read or parsed, or when its text fails
    rule_text_problem (nothing of it has been run at that point)."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        tree = ast.parse(text, path)
        code = compile(text, path, "exec", dont_inherit=True)
    except (OSError, SyntaxError, ValueError, RecursionError, MemoryError) as e:
        _kit.die(2, f"rule file does not import ({type(e).__name__}: {e})", "a Python file following assets/rule.template.py",
                 "fix the file; it needs LOOKBACK and signal(window, params)")
    bad = rule_text_problem(tree)
    if bad:
        _kit.die(2, f"rule file was not run: {bad}", "a file that only sets LOOKBACK (and plain constants) and defines signal(window, params) "
                 "and helper functions, importing nothing but math and statistics",
                 "rewrite the rule to use only window and params; show the user the file before running declare.py check again")
    return code


def fresh_rule(code, tag="pass"):
    """A new module object holding the rule, so nothing a previous import kept in memory survives. Exit 2 when it
    fails to run or lacks a whole-number LOOKBACK >= 1 or a callable signal."""
    mod = types.ModuleType("user_rule_" + tag)
    try:
        exec(code, mod.__dict__)
    except (Exception, SystemExit) as e:
        _kit.die(2, f"rule file does not import ({type(e).__name__}: {e})", "a file that only defines LOOKBACK and signal",
                 "remove whatever it does at import time")
    lb = getattr(mod, "LOOKBACK", None)
    if not callable(getattr(mod, "signal", None)) or not isinstance(lb, int) or isinstance(lb, bool) or lb < 1:
        _kit.die(2, "rule file lacks a whole-number LOOKBACK of 1 or more, or a signal(window, params) function",
                 "LOOKBACK = <bars the rule needs> and def signal(window, params)", "fill both in from the user's rule")
    return mod


def load_rule(path):
    """Import the rule file at `path` under a fresh module; exit 2 if it does not import or lacks LOOKBACK or signal."""
    return fresh_rule(compile_rule(path))


def _build(decl, lock, bars, segment, pset, exp=None):
    kind, split, bs, ts = decl["kind"], lock.get("split_utc"), bars.bar_seconds, bars.ts
    counts = {"dropped_missing_entry": [], "dropped_straddles_split": 0, "skipped_gap_in_lookback": 0,
              "outside_data_range": 0, "skipped_other_side": 0}
    events, record = [], None
    if segment not in ("dev", "oos", "all"):
        _kit.die(2, f"unknown segment {segment!r}", "dev, oos or all", "pass one of the three")
    if not len(bars):
        return events, counts, record
    max_hold = max(c["hold_minutes"] for c in lock["cells"]) * 60
    lo, hi = (max(split, ts[0]) if segment == "oos" else ts[0]), (split - 1 if segment == "dev" else ts[-1])
    want = WANT[decl["idea"]["side"]]

    def take(decision, entry, side):
        if segment == "dev" and entry + max_hold >= split:
            counts["dropped_straddles_split"] += 1
        else:
            events.append({"pset": pset, "segment": segment, "day": _kit.utc_day(entry), "decision_ts": decision,
                           "entry_ts": entry, "side": side})

    if kind == "clock":
        for day, t in clock_schedule(decl, lo, hi, _input(decl, lock, "skip_dates_file", exp)):
            if bars.index_at(t) is None:
                counts["dropped_missing_entry"].append({"date": day, "decision_ts": t})
            else:
                take(t, t, want[0])
    elif kind == "rule":
        mod = fresh_rule(compile_rule(_input(decl, lock, "rule_file", exp)))
        lb, signal = mod.LOOKBACK, mod.signal
        params = next((c["params"] for c in lock["cells"] if c["pset"] == pset), {})
        record, span = bytearray([NOT_CALLED]) * len(bars), lb * bs
        for i in range(max(lb, bars.first_oos_index if segment == "oos" else 0), len(bars)):
            if ts[i] - ts[i - lb] != span:
                counts["skipped_gap_in_lookback"] += 1
                continue
            try:
                r = signal(bars.window(i, lb), dict(params))
            except Exception as e:
                _kit.die(2, f"rule file raised {type(e).__name__}: {e} (deciding the bar at {_kit.utc_iso(ts[i])})",
                         "signal(window, params) returning +1, -1 or 0", "fix the rule; it may use only its two arguments")
            if r not in (1, 0, -1):
                _kit.die(2, f"signal returned {r!r} (deciding the bar at {_kit.utc_iso(ts[i])})", "+1, -1 or 0",
                         "return +1 to enter long, -1 to enter short, 0 to do nothing")
            record[i] = int(r) + 1
            if r in want:
                take(ts[i], ts[i], int(r))
    else:
        d, rows = decl["data"], []
        with open(_input(decl, lock, "events_file", exp), newline="", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            head = [h.strip().lower() for h in next(rd, [])]
            it, iside = (head.index(k) if k in head else -1 for k in ("decision_ts", "side"))
            for n, row in enumerate(rd, 2):
                if not "".join(row).strip():
                    continue
                try:
                    text = row[iside].strip().lower() if iside >= 0 and iside < len(row) else ""
                    side = SIDES[text] if text else want[0] if len(want) == 1 else None
                    if it < 0 or side is None:
                        raise ValueError
                    rows.append((_kit.parse_ts(row[it], d.get("ts_unit"), d.get("ts_zone")), side))
                except (ValueError, IndexError, KeyError, OverflowError):
                    _kit.die(2, f"events file line {n} cannot be read", "header decision_ts[,side]; decision_ts in the unit of "
                             "the data; side long|short|1|-1 (required when idea.side is both)", "fix that line")
        for t, side in sorted(rows):
            if (segment == "dev" and t >= split) or (segment == "oos" and t < split):
                continue
            if t <= ts[0] - bs or t > ts[-1]:
                counts["outside_data_range"] += 1
                continue
            j = bisect.bisect_left(ts, t)
            if ts[j] >= t + bs or (segment == "oos" and ts[j] < split):
                counts["dropped_missing_entry"].append({"date": _kit.utc_day(t), "decision_ts": t})
            elif side not in want:
                counts["skipped_other_side"] += 1
            else:
                take(t, ts[j], side)
    return events, counts, record


def build_events(decl, lock, bars, segment, pset, exp=None):
    """Events of one parameter set on `bars` (a _kit.Bars loaded for the same segment: 'dev', 'oos' or 'all').
    Returns (events, counts). events: dicts with pset, segment, day, decision_ts, entry_ts, side (+1 / -1), in
    time order. counts: dropped_missing_entry (list of {date, decision_ts}), dropped_straddles_split,
    skipped_gap_in_lookback, outside_data_range, skipped_other_side. Development events whose longest declared
    hold would reach the split are dropped; out-of-sample events start at the split. `exp` is the experiment
    folder; without it the rule, events and skip files are taken from the paths stored in the lock."""
    events, counts, _ = _build(decl, lock, bars, segment, pset, exp)
    return events, counts


def replay(code, bars, params, record, probes, seed):
    """Re-decide `probes` randomly chosen bars, each on a fresh import of the rule seeing that bar's window alone,
    and compare with what the sequential pass returned. Returns {probes, differences, first_mismatches}."""
    called = [i for i, r in enumerate(record) if r != NOT_CALLED]
    picks = sorted(random.Random(seed).sample(called, min(int(probes), len(called))))
    bad = []
    for k, i in enumerate(picks):
        try:
            mod = fresh_rule(code, f"probe{k}")
            r = mod.signal(bars.window(i, mod.LOOKBACK), dict(params))
        except (Exception, SystemExit):
            r = None
        if r is None or r != record[i] - 1:
            bad.append(bars.ts[i])
    return {"probes": len(picks), "differences": len(bad), "first_mismatches": bad[:3]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the development events of a frozen experiment and replay-test a rule.")
    ap.add_argument("--exp", required=True, help="the experiment folder")
    ap.add_argument("--json", action="store_true", help="print the result JSON instead of text")
    a = ap.parse_args(argv)
    decl, lock = _kit.load_decl(a.exp)
    check = _kit.require(a.exp, "data_check.json", "result", "PASS")
    if check.get("decl_sha256") != lock["decl_sha256"]:
        _kit.die(3, "the data check on file is not for these declarations", "results/data_check.json written after the freeze or the last amend",
                 "run checkdata.py --exp EXP again")
    _kit.check_data(decl, lock)
    bars = _kit.load_bars(decl, lock, "dev")
    kind, cells, method = decl["kind"], lock["cells"], decl["method"]
    psets, primary = sorted({c["pset"] for c in cells}), cells[lock["primary_cell"]]["pset"]
    all_events, per, rep, share = [], {}, None, 0.0
    for p in psets:
        events, counts, record = _build(decl, lock, bars, "dev", p, a.exp)
        missing = len(counts["dropped_missing_entry"])
        share = max(share, missing / (len(events) + missing) if events or missing else 0.0)
        per[p], all_events = (events, counts), all_events + events
        if kind == "rule":
            params = next(c["params"] for c in cells if c["pset"] == p)
            r = replay(compile_rule(_input(decl, lock, "rule_file", a.exp)), bars, params, record,
                       method["replay_probes"], method["null"]["seed"])
            rep = r if rep is None else {"probes": rep["probes"] + r["probes"], "differences": rep["differences"] + r["differences"],
                                         "first_mismatches": (rep["first_mismatches"] + r["first_mismatches"])[:3]}
    os.makedirs(os.path.join(a.exp, "results"), exist_ok=True)
    with open(os.path.join(a.exp, "results", "events_dev.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(COLUMNS)
        w.writerows([e[c] for c in COLUMNS] for e in all_events)
    events, counts = per[primary]
    causality = {"clock": "by construction", "file": "not verified (events were supplied as a file)"}.get(kind) or (
        f"checked: 0 differences in {rep['probes']} probes" if not rep["differences"] else
        f"FAIL: {rep['differences']} differences in {rep['probes']} probes, first at "
        + ", ".join(_kit.utc_iso(t) for t in rep["first_mismatches"]))
    by_year, by_time, season = {}, {}, {"07": None, "01": None}
    for e in events:
        by_year[e["day"][:4]] = by_year.get(e["day"][:4], 0) + 1
        hhmm = _kit.utc_iso(e["decision_ts"])[11:16]
        by_time[hhmm] = by_time.get(hhmm, 0) + 1
        if e["day"][5:7] in season and season[e["day"][5:7]] is None:
            season[e["day"][5:7]] = hhmm
    limit, missing = method["gates"]["max_dropped_event_share"], counts["dropped_missing_entry"]
    why = ("the replay found the rule deciding differently when it sees one bar alone" if causality.startswith("FAIL") else
           "no event was found in the development data" if not events else
           f"{share:.1%} of events were dropped for a missing entry bar, above the declared {limit:.1%}" if share > limit else None)
    code = 1 if why else 0
    payload = {"kind": kind, "psets": psets, "events": {str(p): len(per[p][0]) for p in psets}, "events_by_year": by_year,
               "dropped_missing_entry": missing, "dropped_straddles_split": counts["dropped_straddles_split"],
               "skipped_gap_in_lookback": counts["skipped_gap_in_lookback"], "dropped_share": share,
               "causality": causality, "replay": rep, "primary_pset": primary,
               "outside_data_range": counts["outside_data_range"], "skipped_other_side": counts["skipped_other_side"],
               "by_pset": {str(p): {k: (len(v) if isinstance(v, list) else v) for k, v in per[p][1].items()} for p in psets}}
    lines = [f"development events ({kind}): {len(events)} kept, {len(missing)} dropped for a missing entry bar, "
             f"{counts['dropped_straddles_split']} dropped for reaching the split" +
             (f", {counts['skipped_gap_in_lookback']} decisions skipped for a gap in the lookback" if kind == "rule" else "") +
             (f"; {len(psets)} parameter sets: " + ", ".join(f"{p}: {len(per[p][0])}" for p in psets) if len(psets) > 1 else "")]
    if kind == "clock":
        zone = decl["idea"]["event"]["zone"]
        payload.update(utc_time_summer=season["07"], utc_time_winter=season["01"], days_by_utc_time=by_time,
                       zone_rule=_kit.zone_rule(zone))
        lines.append(f"event in UTC: {season['07'] or 'no July date in the data'} in summer (July), "
                     f"{season['01'] or 'no January date in the data'} in winter (January); days by UTC time: "
                     + ", ".join(f"{k} on {v}" for k, v in by_time.items()))
        lines += ["zone rule: built-in US fallback"] if payload["zone_rule"] == "built-in US fallback" else []
    if missing:
        lines.append("dropped, no bar at the event time: " + ", ".join(m["date"] for m in missing[:12])
                     + (f" and {len(missing) - 12} more in results/events.json" if len(missing) > 12 else ""))
    lines.append(f"causality: {causality}")
    out = _kit.write_result(a.exp, "events.json", payload, code, script="events")
    q = shlex.quote
    nxt = f"python3 {q(os.path.join(HERE, 'effect.py'))} --exp {q(os.path.abspath(a.exp))}" if not code else (
        "fix the rule so that it uses only its two arguments (declare.py amend records the change), then run events.py again"
        if causality.startswith("FAIL") else
        "show the user the lines above and stop; a change to the event or the data goes through declare.py amend")
    _kit.finish(out, why or f"{len(events)} development events built; causality {causality.split(':')[0]}", nxt, code, a.json, lines)


if __name__ == "__main__":
    _kit.guard(main)
