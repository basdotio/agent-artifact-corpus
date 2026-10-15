#!/usr/bin/env python3
"""Step 0 of strategy-tester: the declarations. Nothing else runs until they are frozen.

  python3 declare.py init   --exp EXP --kind clock|rule|file --data PATH
  python3 declare.py set    --exp EXP KEY=VALUE [KEY=VALUE ...]     # e.g. idea.side=long 'idea.grid.trade.hold_minutes=[30,60]'
  python3 declare.py check  --exp EXP [--json]
  python3 declare.py show   --exp EXP            # prints and writes EXP/STEP0_DECLARATIONS.md
  python3 declare.py freeze --exp EXP
  python3 declare.py amend  --exp EXP --reason "TEXT"
  python3 declare.py status --exp EXP

init writes EXP/declarations.json with every method key at its default and every idea and cost key null
(fill only the nulls, from the user's words, with set or a file edit). freeze writes
EXP/declarations.lock (sha256 and a copy of the declarations, data fingerprint, split, cells, trial count
N). After the freeze the only way to change anything is amend, which raises N: by the cells already
frozen when the event, the side, the costs or an input file changed, by the cells already run when the
data file, its range, the way it is read or the split changed, else by 1 when no cell was added.
amend refuses a loosened gate, a removed cell and anything after out-of-sample was opened. A rule file
is ordinary Python: check, events.py and sweep.py run it on this machine. Times are UTC epoch seconds,
costs are bp. Exits: 0 done, 2 bad input (check lists every problem), 3 refused.
"""
from __future__ import annotations

import argparse, contextlib, csv, hashlib, io, itertools, json, os, re, shlex, shutil, sys
from collections import Counter
from datetime import datetime

sys.dont_write_bytecode = True  # nothing is ever written into the skill folder
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _kit, fills

FIELDS = ("ts", "open", "high", "low", "close", "volume")
TS_NAMES = ("open_time", "timestamp", "time", "datetime", "date", "ts")
EVENT = {"clock": {"local_time": None, "zone": None, "days": None, "skip_dates_file": None},
         "rule": {"rule_file": "rule.py"}, "file": {"events_file": None}}
POOLS = ("same-day-other-times", "same-year-any-time")
GO = "Four weeks of paper trading on the declared venue before any capital."
NO_GO = "Write the findings and close the experiment. Any variant is a new declaration."
Q = {"a": "ask again what the event or signal is, exactly, with its clock time and time zone if it has one",
     "b": "ask again which instrument, on which venue they would really trade it, and where the price file is",
     "c": "ask again for the trade in their own words: direction, when in, when out",
     "d": "ask again whether they have already looked at this on this data, and roughly how many other versions "
          "(variants_seen is 0 when this exact idea is the only version looked at)",
     "cost": "these are the user's figures, never yours: ask for the fee and the half-spread in bp per fill and where each comes from"}
SOURCES = ("measured", "assumed")  # the first word of costs.source; verdict.py prints a qualifier for "assumed"
LOOSER = [("null.alpha", 1), ("gates.dsr_min", -1), ("gates.oos_psr_min", -1), ("gates.min_event_days", -1),
          ("gates.max_dropped_event_share", 1)]  # (method key, direction in which the gate gets weaker)
YEAR_2100 = 4102444800
REQUIRED = [("idea.hypothesis", "a"), ("idea.instrument", "b"), ("idea.venue", "b"), ("idea.side", "c"),
            ("idea.trade.hold_minutes", "c"), ("idea.prior_looks.text", "d"), ("idea.prior_looks.variants_seen", "d"),
            ("costs.fee_bp_per_fill", "cost"), ("costs.half_spread_bp_per_fill", "cost"), ("costs.source", "cost")]
OPTIONAL = ["idea.reason", "idea.trade.stop_bp", "idea.trade.target_bp", "idea.event.skip_dates_file",
            "data.first_utc", "data.last_utc", "method.split.date_utc", "data.columns.volume"]
whole = lambda v: isinstance(v, int) and not isinstance(v, bool)
RANGES = [("split.dev_fraction", lambda v: 0 < v < 1, "above 0 and below 1"),
          ("null.draws", lambda v: whole(v) and v >= 199, "a whole number, 199 or more"),
          ("null.seed", whole, "a whole number"), ("null.alpha", lambda v: 0 < v <= 0.10, "above 0 and at most 0.10"),
          ("gates.dsr_min", lambda v: 0.90 <= v < 1, "from 0.90 to below 1"),
          ("gates.oos_psr_min", lambda v: 0.90 <= v < 1, "from 0.90 to below 1"),
          ("gates.min_event_days", lambda v: whole(v) and v >= 30, "a whole number, 30 or more"),
          ("gates.max_dropped_event_share", lambda v: 0 <= v < 1, "from 0 to below 1"),
          ("replay_probes", lambda v: whole(v) and v >= 1, "a whole number, 1 or more")]
REASONS = [(("split.dev_fraction",), "Out-of-sample must be later than every choice (the split is chronological)"),
           (("split.date_utc",), "An explicit YYYY-MM-DD here replaces the fraction"),
           (("null.pool",), "The null must keep everything except the thing the idea claims matters"),
           (("null.draws", "null.seed"), "Smallest reachable p is 1/{p}; a fixed seed makes the run repeatable"),
           (("null.alpha",), "One-sided, in the declared direction"),
           (("gates.dsr_min",), "The published DSR convention; same level as the null"),
           (("gates.oos_psr_min",), "One pre-specified confirmatory test at the same level"),
           (("gates.min_event_days",), "A convention, not a derived number: below it only very large effects are detectable"),
           (("gates.max_dropped_event_share",), "Dropped events are not random; beyond a few percent the sample is not the declared one"),
           (("cost_tiers",), "Shows whether the verdict depends on the cost assumed"),
           (("replay_probes",), "Finds a fault present on {f:.1%} of bars with 95% probability")]
FIXED = ["Entry is the open of the entry bar; the time exit is the open of the bar stamped entry + hold, found by timestamp.",
         "A missing bar drops the event or the trade and is listed; nothing is filled, clipped or carried forward.",
         "A stop never fills better than its level; a gap through it fills at the open; a target needs a trade-through; "
         "stop and target inside one bar count as the stop.",
         "One position at a time; fee plus half-spread is charged on both fills of every trade, whatever the outcome.",
         "The unit of evidence is the event-day; Sharpe is per day and never annualised; p from draws is (b + 1) / (m + 1).",
         "The raw effect is measured on development only, on the base trade with its time exit (stop and target ignored).",
         "Characterisation gate: development net mean above zero at the declared cost and random-entry null p at or below "
         "alpha. If it fails there is no sweep and out-of-sample stays unopened.",
         "Every declared cell is run and reported; the chosen cell is the highest development net Sharpe with enough event days.",
         "Out-of-sample is read once, for the chosen cell only, and only after development passed.",
         "Verdict: NO-GO when a point estimate is on the wrong side with the minimum sample met; INCONCLUSIVE when every "
         "estimate is on the right side and a significance gate is short; GO only when every declared test is passed.",
         "After the freeze any change goes through declare.py amend: it is recorded, the trial count N can only grow, "
         "and no gate can be loosened."]


def method_defaults(kind):
    """The built-in method block for an idea of `kind` (the single place the defaults live)."""
    return {"split": {"dev_fraction": 0.6667, "date_utc": None},
            "null": {"pool": POOLS[0 if kind == "clock" else 1], "draws": 1000, "seed": 1, "alpha": 0.05},
            "gates": {"dsr_min": 0.95, "oos_psr_min": 0.95, "min_event_days": 100, "max_dropped_event_share": 0.02},
            "cost_tiers": [0.5, 1.0, 2.0], "replay_probes": 200, "next_if_go": GO, "next_if_no_go": NO_GO}


def get(d, dotted):
    """Value at a dotted key ('idea.trade.hold_minutes'), None when any part is absent."""
    for k in dotted.split("."):
        d = d.get(k) if isinstance(d, dict) else None
    return d


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf")


def cmd(script, exp, extra=""):
    """The exact next command for a NEXT: line, e.g. cmd("declare check", exp) or cmd("sweep --oos", exp)."""
    name, _, rest = script.partition(" ")
    return f"python3 {shlex.quote(os.path.join(HERE, name + '.py'))}{' ' + rest if rest else ''} {extra}--exp {shlex.quote(os.path.abspath(exp))}"


def resolve(exp, name):
    return name if os.path.isabs(str(name)) else os.path.join(exp, str(name))


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def captured(fn, *args):
    """Run a _kit-style function that may die(); return its ERROR text instead of exiting, None when it passes."""
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            fn(*args)
    except SystemExit:
        return (err.getvalue().splitlines() or ["refused"])[0].replace("ERROR: ", "")
    return None


def peek(path, n=200):
    """(header, first n data rows, last data row) of a CSV without reading the whole file."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.reader(f)
        header = [h.strip() for h in next(rd, [])]
        rows = [r for r in itertools.islice(rd, n) if r]
    with open(path, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 65536))
        tail = [l for l in f.read().decode("utf-8", "replace").splitlines() if l.strip()]
    return header, rows, (next(csv.reader([tail[-1]])) if rows and tail else None)


def data_facts(decl):
    """(problems, first, last): the data block checked against the file's header, first row and last row; first and
    last are open times in epoch seconds inside data.first_utc .. data.last_utc (None when they cannot be read)."""
    d, P = decl.get("data") or {}, []
    path, cols, unit, zone, bs = d.get("path"), d.get("columns") or {}, d.get("ts_unit"), d.get("ts_zone"), d.get("bar_seconds")
    if not isinstance(path, str) or not os.path.isfile(path):
        return [f"data file {path} is missing: correct data.path"], None, None
    if not isinstance(cols, dict):
        return ["data.columns must map ts, open, high, low, close (and volume) to header names of the data file"], None, None
    for k in ("first_utc", "last_utc"):
        v = d.get(k)
        if v is not None and not (isinstance(v, str) and re.fullmatch(r"\d{4}-\d\d-\d\d([T ].*)?", v)) and not (whole(v) and 0 <= v <= YEAR_2100):
            return [f"data.{k} is {v!r}: it must be null, a date written YYYY-MM-DD, or whole epoch seconds (not milliseconds)"], None, None
    if unit not in (*_kit.UNIT_DIV, "iso"):
        P.append(f"data.ts_unit is {unit!r}: it must be s, ms, us, ns or iso")
    if d.get("stamp") not in ("open", "close"):
        P.append("data.stamp must be open or close (whether a bar's timestamp is its open or its close time)")
    if not whole(bs) or bs <= 0:
        P.append(f"data.bar_seconds is {bs!r}: it must be the bar length in whole seconds")
    if zone is not None and captured(_kit.zone_rule, zone):
        P.append(f"data.ts_zone {zone!r} cannot be resolved here: use an IANA name such as UTC or America/New_York")
    try:
        header, rows, last_row = peek(path)
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        return P + [f"data file cannot be read as CSV text ({e})"], None, None
    low = [h.lower() for h in header]
    for k in FIELDS:
        if not (cols.get(k) is None and k == "volume") and str(cols.get(k)).lower() not in low:
            P.append(f"data.columns.{k} = {cols.get(k)!r} is not a column of the data file (header: {', '.join(header)})")
    if len(header) == 1 and any(c in header[0] for c in ";\t"):
        P.append("the data file is not comma-separated (its header holds ';' or a tab): ask the user for a comma-separated export")
    if P or not rows:
        return P + ([] if rows else ["the data file has no data rows"]), None, None
    i, shift = low.index(str(cols["ts"]).lower()), (bs if d.get("stamp") == "close" else 0)
    try:
        if unit == "iso" and zone is None and datetime.fromisoformat(rows[0][i].strip().replace("Z", "+00:00")).tzinfo is None:
            return ["ISO timestamps without an offset while data.ts_zone is null: ask the user which time zone the "
                    "file's clock is in and put its IANA name in data.ts_zone"], None, None
        first, last = (_kit.parse_ts(r[i], unit, zone) - shift for r in (rows[0], last_row))
        lo, hi = _kit.to_epoch(d.get("first_utc")), _kit.to_epoch(d.get("last_utc"))
    except (ValueError, IndexError, OverflowError) as e:
        return [f"a timestamp cannot be read with data.ts_unit {unit} ({e}); data.first_utc and data.last_utc take "
                "epoch seconds or YYYY-MM-DD"], None, None
    if first > last:
        return ["rows are newest-first: sort ascending by time first"], None, None
    return [], (first if lo is None else max(first, lo)), (last if hi is None else min(last, hi))


def split_utc(decl, first, last):
    """00:00 UTC of the day containing first + dev_fraction * (last - first), or the explicit split.date_utc."""
    s = decl["method"]["split"]
    if s.get("date_utc"):
        return _kit.to_epoch(s["date_utc"])
    return None if first is None or last is None else int((first + s["dev_fraction"] * (last - first)) // 86400) * 86400


def cells_of(decl):
    """(cells, primary_cell): the Cartesian product of the grid, keys sorted, values in declared order; ungridded
    keys take the base value; pset numbers the distinct params in order of first appearance."""
    idea = decl["idea"]
    grid, trade = idea.get("grid") or {}, idea.get("trade") or {}
    base = {"hold_minutes": trade.get("hold_minutes"), "stop_bp": trade.get("stop_bp"),
            "target_bp": trade.get("target_bp"), "params": dict(idea.get("params") or {}) if isinstance(idea.get("params"), dict) else {}}
    keys, out, psets = sorted(grid), [], []
    for combo in itertools.product(*(grid[k] for k in keys)):
        c = {**base, "params": dict(base["params"])}
        for k, v in zip(keys, combo):
            (c["params"] if k.startswith("params.") else c)[k.split(".", 1)[1]] = v
        pkey = json.dumps(c["params"], sort_keys=True)
        psets += [] if pkey in psets else [pkey]
        out.append({"index": len(out), "pset": psets.index(pkey), **c})
    return out, next((c["index"] for c in out if all(c[k] == base[k] for k in base)), 0)


def cell_key(c):
    return json.dumps([c["hold_minutes"], c["stop_bp"], c["target_bp"], c["params"]], sort_keys=True)


def problems(decl, exp):
    """Every reason the declarations cannot be frozen, one line each (empty list = ready to show)."""
    try:
        return _problems(decl, exp)
    except (KeyError, TypeError, AttributeError, ValueError, IndexError) as e:
        return [f"declarations.json has an unexpected shape ({type(e).__name__}: {e}): compare it with what declare.py init writes"]


def _problems(decl, exp):
    P, g, kind = [], (lambda k: get(decl, k)), decl.get("kind")
    if decl.get("schema") != 1 or kind not in EVENT:
        return ["schema must be 1 and kind one of clock, rule, file: start again with declare.py init in a new folder"]
    for key, q in REQUIRED + [("idea.event." + k, "a") for k in EVENT[kind] if k != "skip_dates_file"]:
        if g(key) is None or (isinstance(g(key), str) and not g(key).strip()):
            P.append(f"{key} is null: {Q[q]}")
    sides = ("long", "short") if kind == "clock" else ("long", "short", "both")
    if g("idea.side") is not None and g("idea.side") not in sides:
        P.append(f"idea.side is {g('idea.side')!r}: the direction must be one of {', '.join(sides)}")
    for key in ("costs.fee_bp_per_fill", "costs.half_spread_bp_per_fill"):
        if g(key) is not None and (not num(g(key)) or g(key) < 0):
            P.append(f"{key} is {g(key)!r}: it must be a number of bp per fill, zero or above")
    src = g("costs.source")
    if isinstance(src, str) and src.strip() and src.split()[0].strip(":,.;").lower() not in SOURCES:
        P.append(f"costs.source is {src!r}: begin it with the word measured (the figures come from the user's own quotes, "
                 "statements or fee schedule) or assumed (the user's figure with nothing measured behind it), then say where "
                 "each figure comes from. Fee and half-spread are the user's: if they gave none, ask; do not supply one")
    elif src is not None and not isinstance(src, str):
        P.append(f"costs.source is {src!r}: it must be text beginning with measured or assumed")
    par = g("idea.params")
    if par is not None and not (isinstance(par, dict) and all(isinstance(k, str) and num(v) for k, v in par.items())):
        P.append(f"idea.params is {par!r}: it must be an object of name: number pairs, or empty")
    if g("idea.grid") is not None and not isinstance(g("idea.grid"), dict):
        P.append(f"idea.grid is {g('idea.grid')!r}: it must be an object of grid key: list of values, or empty")
        return P
    for key in ("idea.hypothesis", "idea.instrument", "idea.venue", "idea.prior_looks.text"):
        if g(key) is not None and not isinstance(g(key), str):
            P.append(f"{key} is {g(key)!r}: it must be text in the user's words")
    for key, ok, text in RANGES:
        if not num(g("method." + key)) or not ok(g("method." + key)):
            P.append(f"method.{key} is {g('method.' + key)!r}: it must be {text}")
    tiers = g("method.cost_tiers")
    if not isinstance(tiers, list) or 1 not in tiers or not all(num(t) and t > 0 for t in tiers):
        P.append("method.cost_tiers must be a list of positive multipliers that includes 1 (the declared cost)")
    if g("method.null.pool") not in POOLS or (kind == "clock" and g("method.null.pool") != POOLS[0]):
        P.append(f"method.null.pool is {g('method.null.pool')!r}: a clock idea needs same-day-other-times (another pool "
                 "reproduces the clock effect inside its own null); rule and file ideas take either pool name")
    for key in ("method.next_if_go", "method.next_if_no_go"):
        if not isinstance(g(key), str) or not g(key).strip():
            P.append(f"{key} must say in words what happens after that verdict")
    v = g("idea.prior_looks.variants_seen")
    if v is not None and (not whole(v) or not 0 <= v <= 10 ** 6):
        P.append(f"idea.prior_looks.variants_seen is {v!r}: it must be a whole number, zero or above (and at most 1000000)")
    grid, params, bs = g("idea.grid") or {}, (par if isinstance(par, dict) else {}), g("data.bar_seconds")
    for k, vals in grid.items():
        if k not in ("trade.hold_minutes", "trade.stop_bp", "trade.target_bp") and not (k.startswith("params.") and k[7:]):
            P.append(f"grid key {k} is not allowed: use trade.hold_minutes, trade.stop_bp, trade.target_bp or params.<name>")
        elif not isinstance(vals, list) or not vals:
            P.append(f"grid {k} must be a non-empty list of values")
        else:
            base = params.get(k[7:]) if k.startswith("params.") else g("idea." + k)
            if any(a == b for j, a in enumerate(vals) for b in vals[:j]):
                P.append(f"grid {k} has duplicate values")
            if base not in vals:
                P.append(f"base value {base!r} of {k} is not in its own grid list {vals}: the declared trade must be one of the cells")
    listed = lambda k: grid[k] if isinstance(grid.get(k), list) else [g("idea." + k)]
    for h in listed("trade.hold_minutes"):
        if h is not None and (not num(h) or h <= 0 or not num(bs) or bs <= 0 or (h * 60) % bs):
            P.append(f"hold of {h} minutes is not a positive multiple of the {bs} s bars")
    for k in ("trade.stop_bp", "trade.target_bp"):
        if any(x is not None and (not num(x) or x <= 0) for x in listed(k)):
            P.append(f"idea.{k} must be a distance in bp above zero, or null for none")
    if kind == "clock":
        lt, days = g("idea.event.local_time"), g("idea.event.days")
        m = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", str(lt))
        if lt is not None and not m:
            P.append(f"idea.event.local_time is {lt!r}: write it as HH:MM on the 24-hour clock")
        elif m and num(bs) and bs > 0 and (int(m[1]) * 3600 + int(m[2]) * 60) % bs:
            P.append(f"{lt} cannot be entered on bars of {bs} s: the event time must be the open of a bar")
        if g("idea.event.zone") is not None and captured(_kit.zone_rule, g("idea.event.zone")):
            P.append(f"idea.event.zone {g('idea.event.zone')!r} cannot be resolved on this machine: use an IANA name; "
                     "without a zone database only America/New_York and UTC work")
        if days is not None and days not in ("weekdays", "all") and not (
                isinstance(days, list) and days and len(set(days)) == len(days) and all(whole(x) and 0 <= x <= 6 for x in days)):
            P.append("idea.event.days must be \"weekdays\", \"all\" or a list of weekday numbers (Monday = 0 .. Sunday = 6)")
    for k in ("rule_file", "events_file", "skip_dates_file"):
        name = g("idea.event." + k)
        if name is not None and not os.path.isfile(resolve(exp, name)):
            P.append(f"idea.event.{k} names {name!r}, which is not a file in {exp}")
        elif name is not None and k == "rule_file":
            import events
            bad = captured(events.load_rule, resolve(exp, name))
            P += [f"{name}: {bad}: write the user's rule into it before the freeze"] if bad else []
    dp, first, last = data_facts(decl)
    P += dp
    date_utc, need = g("method.split.date_utc"), g("method.gates.min_event_days")
    if date_utc is not None and not re.fullmatch(r"\d{4}-\d\d-\d\d", str(date_utc)):
        P.append(f"method.split.date_utc is {date_utc!r}: write it as YYYY-MM-DD, or null to use dev_fraction")
    elif first is not None and num(need) and (date_utc or num(g("method.split.dev_fraction"))):
        sp = split_utc(decl, first, last)
        dev, oos = (sp - first) / 86400, (last + (bs if num(bs) else 0) - sp) / 86400
        if dev < need or oos < need:
            P.append(f"the split at {_kit.utc_day(sp)} leaves {max(dev, 0):.0f} development and {max(oos, 0):.0f} out-of-sample "
                     f"calendar days; each segment needs at least min_event_days = {need}")
    return P


def scan_data(decl):
    """One read of the data file: (bytes, sha256, first, last) with first/last the open times inside the declared range."""
    d = decl["data"]
    path, unit, zone = d["path"], d.get("ts_unit"), d.get("ts_zone")
    shift, first, last = (d["bar_seconds"] if d.get("stamp") == "close" else 0), None, None
    lo, hi = _kit.to_epoch(d.get("first_utc")), _kit.to_epoch(d.get("last_utc"))
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.reader(f)
        names = [h.strip().lower() for h in next(rd, [])]
        i = names.index(str(d["columns"]["ts"]).lower()) if str(d["columns"]["ts"]).lower() in names else 0
        for row in rd:
            try:
                t = _kit.parse_ts(row[i], unit, zone) - shift
            except (ValueError, IndexError, OverflowError):
                continue  # checkdata.py reports unreadable rows; the freeze only needs the range
            if (lo is None or t >= lo) and (hi is None or t <= hi):
                first, last = (t if first is None else min(first, t)), (t if last is None else max(last, t))
    return os.path.getsize(path), file_sha256(path), first, last


def trial_definition(decl, inputs):
    """What makes a cell the trial it is, apart from the grid: the event, the side, the two cost figures and the
    bytes of the rule, events and skip-dates files. If an amend changes any of these, every cell frozen before it
    was a different trial that has already been looked at."""
    return {"event": get(decl, "idea.event"), "side": get(decl, "idea.side"), "fee": get(decl, "costs.fee_bp_per_fill"),
            "half_spread": get(decl, "costs.half_spread_bp_per_fill"), "inputs": {k: v.get("sha256") for k, v in (inputs or {}).items()}}


def data_definition(decl, data, split):
    """The sample a cell is run on: the bytes of the price file, the range in force, the split, and how the file is
    read (columns, units, bar size, stamp). The path is left out: the same bytes somewhere else are the same sample.
    `data` and `split` are the lock's, so a range typed differently that selects the same bars is no change."""
    reading = {k: v for k, v in ((decl or {}).get("data") or {}).items() if k not in ("path", "first_utc", "last_utc")}
    return {"sha256": (data or {}).get("sha256"), "first": (data or {}).get("first_utc"), "last": (data or {}).get("last_utc"),
            "split": split, "reading": reading}


def cells_with_results(exp, lock):
    """How many of the frozen cells have development results in EXP/results/: all of them once sweep.py has written its
    grid, the base cell once effect.py has run, none before that."""
    have = set(results_files(exp))
    return int(lock.get("cells_declared", 1)) if have & {"grid.csv", "grid_daily.csv", "sweep.json", "deflate.json"} else \
        1 if have & {"effect_dev.json", "trades_raw_dev.csv"} else 0


def loosened(decl, frozen):
    """Text for every gate that `decl` sets weaker than the frozen declarations did (empty list when none)."""
    out = []
    for key, sign in LOOSER:
        new, old = get(decl, "method." + key), get(frozen or {}, "method." + key)
        if num(new) and num(old) and (new - old) * sign > 0:
            out.append(f"{key} {old:g} -> {new:g}")
    return out


def make_lock(exp, decl, prev=None, reason=None, ran=0):
    """Build and write EXP/declarations.lock from the declarations as they are (no check is run here). With `prev`
    (the lock being amended) the freeze time, history and penalty carry over and one history entry is added. The
    amend penalty grows by the largest of: the cells frozen before, when the trial definition changed (they were
    other trials); the cells already run, when the data changed (they are run again on another sample); 1, when
    the amend added no cell. `ran` is the number of frozen cells with results on file when the amend was asked
    for; the lock carries the count (`cells_run_on_this_data`) across amends that leave the data alone, so that an
    amend of something else in between does not hide them."""
    size, sha, first, last = scan_data(decl)
    cells, primary = cells_of(decl)
    now, old = _kit.utc_iso(), prev or {}
    added = len(cells) - len(old.get("cells", cells))
    seen = get(decl, "idea.prior_looks.variants_seen") or 0
    inputs = {}
    for k in ("rule_file", "events_file", "skip_dates_file"):
        name = get(decl, "idea.event." + k)
        if name is not None and os.path.isfile(resolve(exp, name)):
            inputs[k] = {"path": os.path.abspath(resolve(exp, name)), "sha256": file_sha256(resolve(exp, name))}
    was = old.get("frozen_declarations")  # absent only in a lock written before this key existed: counted as changed
    redefined = bool(prev) and (was is None or trial_definition(decl, inputs) != trial_definition(was, old.get("inputs")))
    split = split_utc(decl, first, last)
    data = {"bytes": size, "sha256": sha, "first_utc": first, "last_utc": last}
    resampled = bool(prev) and (was is None or data_definition(decl, data, split) != data_definition(was, old.get("data"), old.get("split_utc")))
    run_before = max(int(old.get("cells_run_on_this_data", 0)), int(ran)) if prev else 0
    step = max(int(old.get("cells_declared", 1)) if redefined else 0, run_before if resampled else 0, 1 if added == 0 else 0) if prev else 0
    penalty = old.get("amend_penalty", 0) + step
    lock = {"schema": 1, "decl_sha256": _kit.canonical_sha256(decl), "frozen_utc": old.get("frozen_utc", now),
            "data": data, "split_utc": split, "cells": cells, "primary_cell": primary,
            "cells_declared": len(cells), "variants_seen": seen, "amend_penalty": penalty,
            "N": len(cells) + seen + penalty, "history": list(old.get("history", [])), "inputs": inputs,
            "oos_opened_utc": None, "cells_run_on_this_data": 0 if redefined or resampled else run_before,
            "frozen_declarations": decl}
    if prev:
        lock["history"].append({"decl_sha256": lock["decl_sha256"], "utc": now, "reason": reason, "N": lock["N"],
                                "previous_sha256": prev.get("decl_sha256"), "previous_N": prev.get("N"), "cells_added": added,
                                "trial_definition_changed": redefined, "data_changed": resampled,
                                "cells_run_before": run_before, "penalty_added": step})
    with open(os.path.join(exp, "declarations.lock"), "w", encoding="utf-8") as f:
        f.write(json.dumps(lock, indent=1) + "\n")
    return lock


def show_value(v):
    return "none" if v is None or v == {} or v == [] else ", ".join(show_value(x) for x in v) if isinstance(v, list) else \
        json.dumps(v, sort_keys=True) if isinstance(v, dict) else str(v)


def render(decl, exp, lock=None):
    """The text of STEP0_DECLARATIONS.md. Idea and cost lines never carry a tag; method lines always do."""
    g, kind = (lambda k: get(decl, k)), decl["kind"]
    frozen = bool(lock) and lock.get("decl_sha256") == _kit.canonical_sha256(decl)
    if frozen:
        first, last, split = lock["data"]["first_utc"], lock["data"]["last_utc"], lock["split_utc"]
    else:
        _, first, last = data_facts(decl)
        split = split_utc(decl, first, last)
    iso = lambda t: "unknown" if t is None else _kit.utc_iso(t)
    cells, primary = cells_of(decl)
    seen, penalty = g("idea.prior_looks.variants_seen") or 0, (lock or {}).get("amend_penalty", 0)
    N, fee, half, stop = len(cells) + seen + penalty, g("costs.fee_bp_per_fill"), g("costs.half_spread_bp_per_fill"), g("idea.trade.stop_bp")
    rt = fills.round_trip_cost_bp(fee, half)
    state = f"Frozen {lock['frozen_utc']}, sha256 {lock['decl_sha256'][:12]}" if frozen else "Draft, not frozen" + (
        f" (differs from the freeze of {lock['frozen_utc']}: not in force until declare.py amend)" if lock else "")
    if frozen and lock["history"]:
        state += f"; amended {len(lock['history'])} time(s), last {lock['history'][-1]['utc']}"
    L = [f"# STEP 0 DECLARATIONS: {_kit.title(g('idea.instrument'), g('idea.hypothesis'))}", "", state, "",
         "## The idea (yours)", ""]
    L += [f"- {label}: {show_value(g('idea.' + key))}" for label, key in
          [("hypothesis", "hypothesis"), ("reason", "reason"), ("instrument", "instrument"), ("venue", "venue"), ("side", "side")]
          + [("event " + k.replace("_", " "), "event." + k) for k in EVENT[kind]]
          + [("trade: hold minutes", "trade.hold_minutes"), ("trade: stop (bp from entry)", "trade.stop_bp"),
             ("trade: target (bp from entry)", "trade.target_bp"), ("rule parameters", "params")]]
    L += [f"- grid {k}: {show_value(v)}" for k, v in sorted((g("idea.grid") or {}).items())] or ["- grid: none (one cell)"]
    L += [f"- prior looks: {g('idea.prior_looks.text')}", f"- variants already seen: {seen}", "", "## Costs (your figures)", "",
          f"- fee per fill: {fee} bp", f"- half-spread per fill: {half} bp", f"- round trip (two fills): {rt:g} bp"]
    L += [f"- cost in R (round trip / stop): {rt / stop:.2f}"] if num(stop) and stop > 0 else []
    L += [f"- source: {g('costs.source')}", "", "## Data", "", f"- path: {g('data.path')}",
          f"- bar size: {g('data.bar_seconds')} s", f"- bars are stamped with their {g('data.stamp')} time ({g('data.ts_unit')}"
          + (f", zone {g('data.ts_zone')})" if g("data.ts_unit") == "iso" else ")"),
          f"- first bar: {iso(first)}", f"- last bar: {iso(last)}",
          f"- split date: {'unknown' if split is None else _kit.utc_day(split)} (00:00 UTC; "
          + ("declared as split.date_utc)" if g("method.split.date_utc") else f"worked out from split.dev_fraction {g('method.split.dev_fraction')})"),
          f"- development: {iso(first)} up to, not including, {iso(split)}",
          f"- out-of-sample: {iso(split)} to {iso(last)}, read once", "", "## Method", ""]
    default = method_defaults(kind)
    tag = lambda k: "[default]" if g("method." + k) == get(default, k) else f"[changed from default: {show_value(get(default, k))}]"
    for keys, reason in REASONS:  # the reason sits on the line of the last key it covers, so the file stays short to paste
        L += [f"- {k}: {show_value(g('method.' + k))} {tag(k)}" for k in keys]
        L[-1] += " (" + reason.format(p=g("method.null.draws") + 1, f=1 - 0.05 ** (1 / g("method.replay_probes"))) + ")"
    L += ["", "## Fixed rules", ""] + ["- " + r for r in FIXED] + ["", "## Trial count", ""]
    L += [f"- cell {c['index']}: hold {c['hold_minutes']} min, stop {show_value(c['stop_bp'])}, target {show_value(c['target_bp'])}, "
          f"params {show_value(c['params'])}" + (" (the base trade)" if c["index"] == primary else "") for c in cells[:30]]
    L += [f"- ... and {len(cells) - 30} more cells, all in declarations.lock after the freeze"] if len(cells) > 30 else []
    em, z = _kit.emax(N).used, _kit.PhiInv(g("method.gates.dsr_min"))
    L += [f"- cells declared: {len(cells)}", f"- variants already seen: {seen}",
          f"- N = cells + variants (+ amend penalty) = {len(cells)} + {seen} + {penalty} = {N}",
          "- the grid is run only if the base trade passes the characterisation gate; every cell counts in N either way",
          f"- luckiest of N unskilled cells: expected t about {em:.3f}",
          f"- development t needed for DSR {g('method.gates.dsr_min')} at this N: about {em + z:.3f}"]
    if len(cells) > 1:  # the figure above assumes the cells' Sharpes are no wider apart than chance makes them
        L.append(f"- that is the least it can be: the bar is the luckiest-of-N figure times the spread of the cells' Sharpes, so cells "
                 f"that differ in kind raise it further and every grid value added raises N; one cell alone needs about {z:.3f}")
    if kind == "clock" and None not in (first, last, split):
        import events
        skip = g("idea.event.skip_dates_file")
        days = [ts for _, ts in events.clock_schedule(decl, first, last, resolve(exp, skip) if skip else None)]
        L.append(f"- calendar event days: development {sum(t < split for t in days)}, out-of-sample {sum(t >= split for t in days)}")
    L += ["", "## What happens next", "", f"- next_if_go: {g('method.next_if_go')} {tag('next_if_go')}",
          f"- next_if_no_go: {g('method.next_if_no_go')} {tag('next_if_no_go')}"]
    return "\n".join(L) + "\n"


def write_show(exp, decl, lock):
    text = render(decl, exp, lock)
    with open(os.path.join(exp, "STEP0_DECLARATIONS.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return text


def checked(a):
    """Declarations and lock for show/freeze/amend; exit 2 with every problem listed when the check fails."""
    decl, lock = _kit.load_decl(a.exp, need_lock=False)
    P = problems(decl, a.exp)
    if P:
        sys.stderr.write(f"ERROR: {len(P)} problem(s) in declarations.json\nEXPECTED: every required key filled and valid\n"
                         "TRY: fix each line listed (ask the user; do not guess), then run declare.py check again\n")
        _kit.finish({"problems": P}, f"{len(P)} problem(s) in declarations.json; nothing was written",
                    cmd("declare check", a.exp) + " after fixing each line above", 2, a.json, ["- " + p for p in P])
    return decl, lock


def do_init(a):
    path = os.path.join(a.exp, "declarations.json")
    if os.path.exists(path):
        _kit.die(3, f"{path} already exists", "a new experiment folder for a new idea",
                 "edit the existing file (before the freeze) or choose another --exp folder")
    try:
        header, rows, _ = peek(a.data)
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        _kit.die(2, f"data file cannot be read ({e})", "a CSV of price bars with a header row", "correct --data")
    low = [h.lower() for h in header]
    if not rows or (len(header) == 1 and any(c in header[0] for c in ";\t")):
        _kit.die(2, f"{a.data} holds no price bars that can be read" + (" (its header is not comma-separated)" if rows else " (no data rows)"),
                 "a comma-separated file with a header row and one row per bar, oldest first",
                 "ask the user for a comma-separated export of the bars; nothing was written")
    cols = {k: next((header[low.index(n)] for n in names if n in low), None)
            for k, names in [("ts", TS_NAMES)] + [(k, (k,)) for k in FIELDS[1:]]}
    unit = zone = bar = None
    if cols["ts"] and rows:
        i = low.index(cols["ts"].lower())
        unit, zone = _kit.detect_ts_unit(rows[0][i]), "UTC"
        try:
            if unit == "iso" and datetime.fromisoformat(rows[0][i].strip().replace("Z", "+00:00")).tzinfo is None:
                zone = None
            ts = [_kit.parse_ts(r[i], unit, zone or "UTC") for r in rows]
            diffs = Counter(abs(b - x) for x, b in zip(ts, ts[1:]) if b != x)
            bar = diffs.most_common(1)[0][0] if diffs else None
        except (ValueError, IndexError, OverflowError):
            unit = zone = None
    decl = {"schema": 1, "kind": a.kind,
            "idea": {"hypothesis": None, "reason": None, "instrument": None, "venue": None, "side": None,
                     "event": dict(EVENT[a.kind]), "trade": {"hold_minutes": None, "stop_bp": None, "target_bp": None},
                     "params": {}, "grid": {}, "prior_looks": {"text": None, "variants_seen": None}},
            "costs": {"fee_bp_per_fill": None, "half_spread_bp_per_fill": None, "source": None},
            "data": {"path": os.path.abspath(a.data), "columns": cols, "ts_unit": unit, "ts_zone": zone, "stamp": "open",
                     "bar_seconds": bar, "first_utc": None, "last_utc": None},
            "method": method_defaults(a.kind)}
    os.makedirs(a.exp, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(decl, indent=2) + "\n")
    seen_ = lambda v, unit_="": "not detected" if v is None else f"{v}{unit_}"
    lines = [f"wrote {path}: method keys hold their defaults, idea and cost keys are null",
             f"data: {len(header)} columns, timestamps in {seen_(unit)}, bars of {seen_(bar, ' s')} (read from the first {len(rows)} rows)"]
    lost = [k for k in FIELDS[:5] if cols[k] is None]
    if lost:
        lines.append(f"columns not detected: {', '.join(lost)}. The file's header is: {', '.join(header)}. Set data.columns.<name> to the "
                     "header name that holds each (read them off this header; ask the user only if it is unclear)")
    if a.kind == "rule" and not os.path.exists(os.path.join(a.exp, "rule.py")):
        shutil.copyfile(os.path.join(os.path.dirname(HERE), "assets", "rule.template.py"), os.path.join(a.exp, "rule.py"))
        lines.append(f"wrote {os.path.join(a.exp, 'rule.py')}: an empty rule to fill with the user's rule (LOOKBACK and signal)")
    ask = [k for k, _ in REQUIRED + [("idea.event." + k, "a") for k in EVENT[a.kind]] if get(decl, k) is None and k not in OPTIONAL]
    ask += [k for k in ("data.columns.ts", "data.columns.open", "data.columns.high", "data.columns.low", "data.columns.close",
                        "data.ts_unit", "data.ts_zone", "data.bar_seconds") if get(decl, k) is None]
    opt = [k for k in OPTIONAL if get(decl, k) is None and (a.kind == "clock" or "event" not in k)] + ["idea.params", "idea.grid"]
    lines += ["ask the user (still null): " + ", ".join(ask), "optional (may stay null or empty): " + ", ".join(opt)]
    if a.kind == "rule":
        lines.append("rule.py is ordinary Python that declare.py check, events.py and sweep.py run on this machine: show it to the user before the first check")
    _kit.finish({"declarations": path, "ask_the_user": ask, "optional": opt, "data": decl["data"]},
                f"declarations drafted with {len(ask)} keys for the user to supply",
                "fill only the null keys from the user's words (" + cmd("declare set", a.exp) + " KEY=VALUE ..., or a file edit), then "
                + cmd("declare check", a.exp), 0, a.json, lines)


def do_set(a):
    """Set dotted keys of declarations.json from KEY=VALUE pairs. VALUE is read as JSON when it parses (60, null,
    [30, 60], "text") and as plain text otherwise. Only keys that declare.py init wrote can be set, plus
    idea.params.<name>, idea.grid.<grid key> and data.columns.<name>; null removes a params or grid entry."""
    decl, lock = _kit.load_decl(a.exp, need_lock=False)
    done = []
    for pair in a.pairs:
        key, sep, raw = pair.partition("=")
        key = key.strip()
        try:
            value = json.loads(raw)
        except ValueError:
            value = raw.strip()
        if not sep or not key:
            _kit.die(2, f"{pair!r} is not KEY=VALUE", "for example idea.side=long or 'idea.grid.trade.hold_minutes=[30, 60]'",
                     "quote each pair for the shell; nothing was written")
        free = next((p for p in ("idea.grid.", "idea.params.", "data.columns.") if key.startswith(p) and key[len(p):]), None)
        parts = free.rstrip(".").split(".") + [key[len(free):]] if free else key.split(".")
        node = decl
        for part in parts[:-1]:
            node = node.get(part) if isinstance(node, dict) else None
        if not isinstance(node, dict) or (not free and parts[-1] not in node) or parts[0] in ("schema", "kind"):
            _kit.die(2, f"{key} is not a key of declarations.json", "a dotted key as declare.py init wrote it, such as idea.event.local_time, "
                     "costs.fee_bp_per_fill, idea.params.<name> or idea.grid.trade.hold_minutes", "check the spelling; nothing was written")
        if not free and isinstance(node[parts[-1]], dict) != isinstance(value, dict):
            _kit.die(2, f"{key} holds {'an object' if isinstance(node[parts[-1]], dict) else 'a single value'}, not {value!r}",
                     "one of the keys inside it, or a whole JSON object for it", "set the inner key; nothing was written")
        done.append(f"{key}: {show_value(node.get(parts[-1]))} -> {show_value(value)}")
        if free and value is None and free != "data.columns.":
            node.pop(parts[-1], None)
        else:
            node[parts[-1]] = value
    with open(os.path.join(a.exp, "declarations.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(decl, indent=2, ensure_ascii=False) + "\n")
    after = "; this folder is frozen, so the edit is not in force until " + cmd("declare amend", a.exp, '--reason "..." ') if lock else ""
    _kit.finish({"set": done}, f"{len(done)} key(s) written to declarations.json" + after, cmd("declare check", a.exp), 0, a.json, done)


def do_check(a):
    checked(a)
    _kit.finish({"problems": []}, "the declarations are complete and valid", cmd("declare show", a.exp), 0, a.json,
                ["no problem found in declarations.json"])


def do_show(a):
    decl, lock = checked(a)
    text = write_show(a.exp, decl, lock)
    _kit.finish({"file": os.path.join(a.exp, "STEP0_DECLARATIONS.md"), "text": text},
                "declarations rendered to STEP0_DECLARATIONS.md" + ("" if lock else "; not frozen yet"),
                "show this whole file to the user; freeze only after they answer it", 0, a.json, [text.rstrip("\n")])


def summary(lock):
    return [f"sha256 {lock['decl_sha256'][:12]}, frozen {lock['frozen_utc']}",
            f"data fingerprint: {lock['data']['bytes']} bytes, sha256 {lock['data']['sha256'][:12]}",
            f"split at {_kit.utc_day(lock['split_utc'])} 00:00 UTC: out-of-sample starts there and is read once",
            f"N = {lock['N']} ({lock['cells_declared']} cells + {lock['variants_seen']} earlier variants + "
            f"{lock['amend_penalty']} amend penalty)"]


def results_files(exp):
    d = os.path.join(exp, "results")
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def oos_opened(exp, lock):
    """True when the out-of-sample segment was read: the lock carries the mark sweep.py --oos wrote, or the result exists."""
    return bool((lock or {}).get("oos_opened_utc")) or "oos.json" in results_files(exp)


def do_freeze(a):
    if os.path.exists(os.path.join(a.exp, "declarations.lock")):
        _kit.die(3, "already frozen: use amend", "one freeze per experiment",
                 "to change anything edit declarations.json, then run declare.py amend --reason \"...\"")
    if results_files(a.exp):
        _kit.die(3, "results/ already holds files: results cannot be older than the freeze",
                 "an experiment folder with no results", "start a new experiment folder with declare.py init")
    decl, _ = checked(a)
    render(decl, a.exp)  # a declaration that cannot be rendered is not frozen: nothing is written if this fails
    lock = make_lock(a.exp, decl)
    write_show(a.exp, decl, lock)
    _kit.finish(lock, f"declarations frozen with N = {lock['N']}", cmd("checkdata", a.exp), 0, a.json, summary(lock))


def do_amend(a):
    decl, lock = checked(a)
    if lock is None:
        _kit.die(3, "declarations are not frozen: there is nothing to amend", "a declarations.lock",
                 "before the freeze just edit declarations.json; then declare.py show and declare.py freeze")
    if oos_opened(a.exp, lock):
        _kit.die(3, "out-of-sample was opened: this is a new experiment on new data", "an experiment whose out-of-sample segment is unread",
                 "restore declarations.json as frozen and finish with verdict.py; a new idea needs new data")
    weaker = loosened(decl, lock.get("frozen_declarations"))
    if weaker:
        _kit.die(3, "a gate cannot be loosened after the freeze (" + "; ".join(weaker) + ")", "gates as strict as the frozen ones, or stricter",
                 "put the gate back; a test with weaker gates is a new experiment, declared before its data is seen")
    cells, _ = cells_of(decl)
    if {cell_key(c) for c in lock["cells"]} - {cell_key(c) for c in cells}:
        _kit.die(3, "N can only grow: keep the old cells and add the new ones", "every frozen cell still in the grid",
                 "put the old values back in idea.grid beside the new ones, then run amend again")
    if (get(decl, "idea.prior_looks.variants_seen") or 0) < lock.get("variants_seen", 0):
        _kit.die(3, "variants_seen went down: N can only grow", f"variants_seen of {lock.get('variants_seen')} or more",
                 "restore idea.prior_looks.variants_seen")
    moved, ran = None, cells_with_results(a.exp, lock)
    if results_files(a.exp):
        k = next(i for i in itertools.count(1) if not os.path.exists(os.path.join(a.exp, f"results_superseded_{i}")))
        moved = f"results_superseded_{k}"
        os.rename(os.path.join(a.exp, "results"), os.path.join(a.exp, moved))
    new = make_lock(a.exp, decl, prev=lock, reason=a.reason, ran=ran)
    write_show(a.exp, decl, new)
    h = new["history"][-1]
    sample = "the data file, its range, the way it is read or the split changed"
    why = (f"the event, side, costs or an input file changed, so the {lock.get('cells_declared')} cell(s) frozen before count as trials already made"
           if h["trial_definition_changed"] else
           f"{sample}, so the {h['cells_run_before']} cell(s) already run on the data as it was count as trials already made"
           if h["data_changed"] and h["cells_run_before"] and h["penalty_added"] == h["cells_run_before"] else
           "no cell was added, so the amend itself counts as one trial" + (f"; {sample} before any cell was run" if h["data_changed"] else "")
           if h["penalty_added"] else "the added cells count")
    lines = summary(new) + [f"amend recorded: {a.reason}; cells added {h['cells_added']}; N was {lock['N']}, is now {new['N']} ({why})",
                            f"earlier results moved to {moved}" if moved else "no earlier results to move"]
    _kit.finish(new, f"amended: N is now {new['N']} and every step is run again", cmd("checkdata", a.exp), 0, a.json, lines)


STEPS = [("checkdata", "data_check.json", lambda r: r.get("result") == "PASS"),
         ("events", "events.json", lambda r: r.get("exit_code") == 0),
         ("effect", "effect_dev.json", lambda r: bool(get(r, "gate.pass")) and r.get("exit_code") == 0),
         ("sweep", "sweep.json", lambda r: r.get("exit_code") == 0),
         ("deflate", "deflate.json", lambda r: bool(r.get("pass"))),
         ("sweep --oos", "oos.json", lambda r: bool(get(r, "gate.pass"))),
         ("verdict", "verdict.json", lambda r: True)]


def do_status(a):
    lock, ready, nxt, failed, sweep_chose = None, False, None, None, False
    if not os.path.exists(os.path.join(a.exp, "declarations.json")):
        steps, nxt = [("declare", "not done")], "python3 " + shlex.quote(os.path.join(HERE, "declare.py")) + \
            f" init --exp {shlex.quote(os.path.abspath(a.exp))} --kind clock|rule|file --data PATH"
    else:
        decl, lock = _kit.load_decl(a.exp, need_lock=False)
        P = problems(decl, a.exp)
        if lock is None:
            steps = [("declare", f"not done (draft, {len(P)} problem(s) left, not frozen)")]
            nxt = cmd("declare check", a.exp) if P else cmd("declare show", a.exp) + ", show it to the user, then freeze"
        elif lock.get("decl_sha256") != _kit.canonical_sha256(decl):
            steps = [("declare", "failed (declarations changed since the freeze)")]
            nxt = "restore declarations.json as frozen: out-of-sample was opened, so amend is refused" if oos_opened(a.exp, lock) \
                else cmd("declare amend", a.exp, '--reason "..." ') + ", or restore declarations.json"
        else:
            steps, ready = [("declare", f"done (frozen {lock['frozen_utc']}, N = {lock['N']})")], True
    for name, fname, ok in STEPS:
        r = _kit.read_json(os.path.join(a.exp, "results", fname)) if ready else None
        if r is None:
            state = "not done"
        elif r.get("decl_sha256") != lock["decl_sha256"]:
            state = "not done (the result on file belongs to other declarations)"
        else:
            state = ("done" if ok(r) else "failed") + (f" ({r.get('verdict')})" if name == "verdict" else "")
        sweep_chose = (r or {}).get("chosen_cell") is not None if name == "sweep" else sweep_chose
        steps.append((name, state))
        failed = name if state == "failed" and failed is None else failed
        if nxt is None and not state.startswith("done"):
            if failed in ("checkdata", "events"):
                nxt = f"read results/{fname}, show the user what it lists and stop; a repair goes through declare.py amend"
            elif failed is None or name == "verdict" or (failed == "sweep" and name == "deflate" and sweep_chose):
                nxt = cmd(name, a.exp)  # a sweep whose grid null fell short still needs deflate.py before the verdict
    nxt = nxt or "write the three prose sections of FINDINGS.md, then run verdict.py --check"
    done, left = sum(s.startswith("done") for _, s in steps), 0
    if steps[-1][1].startswith("done"):
        try:
            with open(os.path.join(a.exp, "FINDINGS.md"), encoding="utf-8") as f:
                left = f.read().count("<to be written>")
        except OSError:
            left = 3
        nxt = nxt if left else "nothing: the experiment is finished; report the verdict line and the gates table from FINDINGS.md as written"
    _kit.finish({"steps": [{"step": n, "state": s} for n, s in steps], "prose_sections_unwritten": left},
                f"{done} of {len(steps)} steps done" + (f"; {failed} failed" if failed else "")
                + (f"; {left} prose section(s) of FINDINGS.md still to be written" if left else ""), nxt, 0, a.json,
                [f"{i} {name}: {state}" for i, (name, state) in enumerate(steps, 1)])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write, check, show, freeze, amend and report the declarations of one experiment.")
    sub = ap.add_subparsers(dest="command", required=True)
    for name, fn, text in [("init", do_init, "write declarations.json with method defaults and null idea keys"),
                           ("set", do_set, "set keys of declarations.json from KEY=VALUE pairs (no helper script needed)"),
                           ("check", do_check, "list every problem; exit 2 if any"),
                           ("show", do_show, "print and write STEP0_DECLARATIONS.md"),
                           ("freeze", do_freeze, "write declarations.lock; nothing may change after it"),
                           ("amend", do_amend, "re-freeze after an edit: recorded, and N grows"),
                           ("status", do_status, "one line per step and the next command")]:
        p = sub.add_parser(name, help=text, description=text)
        p.add_argument("--exp", required=True, help="the experiment folder (the user's, outside the skill)")
        p.add_argument("--json", action="store_true", help="print JSON instead of text")
        p.set_defaults(fn=fn)
        if name == "init":
            p.add_argument("--kind", required=True, choices=sorted(EVENT), help="clock time, rule on past bars, or events file")
            p.add_argument("--data", required=True, help="CSV of price bars with a header row")
        if name == "set":
            p.add_argument("pairs", nargs="+", metavar="KEY=VALUE", help="dotted key and its value; the value is JSON, or plain text")
        if name == "amend":
            p.add_argument("--reason", required=True, help="why the declarations changed, in words")
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    _kit.guard(main)
