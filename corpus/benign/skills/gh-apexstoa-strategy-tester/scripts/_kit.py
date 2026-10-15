"""Shared library of strategy-tester (no command line; standard library only).
Units: timestamps are integer UTC epoch seconds, days are 'YYYY-MM-DD' (UTC), returns are basis
points (bp), Sharpe is per observation, never annualised. Exits: 0 done, 1 gate failed, 2 bad input, 3 refused."""
from __future__ import annotations

import bisect, csv, hashlib, json, math, os, statistics, sys, time, traceback
from array import array
from collections import namedtuple
from datetime import date as _date, datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:  # Python built without the module
    ZoneInfo = None

FORCE_TZ_FALLBACK = False  # tests set True to behave like a machine without zone data
EULER_GAMMA, Z95 = 0.5772156649015329, 1.644854
UNIT_DIV = {"s": 1, "ms": 10 ** 3, "us": 10 ** 6, "ns": 10 ** 9}
_N = statistics.NormalDist()
Phi, PhiInv = _N.cdf, _N.inv_cdf  # standard normal CDF and its inverse
Emax = namedtuple("Emax", "closed exact used")
_FIELDS = ("ts", "open", "high", "low", "close", "volume")

def die(code, what, expected, try_):
    """Print the three stderr lines ERROR: / EXPECTED: / TRY: and exit with `code` (2 or 3)."""
    sys.stderr.write(f"ERROR: {what}\nEXPECTED: {expected}\nTRY: {try_}\n")
    sys.exit(code)
def guard(main):
    """Run a script's main(). An exception nobody expected becomes the three stderr lines and exit 2: no traceback
    reaches the user, and exit 1 keeps its one meaning (a declared gate failed)."""
    try:
        main()
    except Exception as e:
        at = traceback.extract_tb(e.__traceback__)[-1]
        die(2, f"{type(e).__name__}: {e} (at {os.path.basename(at.filename)} line {at.lineno})",
            "declarations laid out as declare.py init writes them, and result files as the scripts wrote them",
            "run declare.py check --exp EXP and fix what it lists; if a file under results/ was edited, run that step again")
def canonical_sha256(obj) -> str:
    """Hex sha256 of obj's canonical JSON (sorted keys, no spaces, ASCII)."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()

def read_json(path):
    """Parsed JSON file; None when the file does not exist; exit 2 when it is not valid JSON."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (ValueError, OSError) as e:
        die(2, f"{path} cannot be read as JSON ({e})", "valid JSON", "fix the syntax or restore the file")

def load_decl(exp, need_lock=True):
    """(decl, lock) from EXP/declarations.json and EXP/declarations.lock. need_lock=True: exit 3 if the lock is
    missing or the declarations hash differs from it. need_lock=False: lock may be None, no hash comparison."""
    decl, lock = (read_json(os.path.join(exp, "declarations." + e)) for e in ("json", "lock"))
    if decl is None:
        die(3, f"no declarations.json in {exp}", "a folder made by declare.py init", "run declare.py init --exp EXP --kind clock|rule|file --data PATH")
    if need_lock and lock is None:
        die(3, "declarations are not frozen", "a declarations.lock written by declare.py freeze", "run declare.py show, get the user's answer, then declare.py freeze")
    if need_lock and canonical_sha256(decl) != lock.get("decl_sha256"):
        die(3, "declarations changed since the freeze", "declarations.json exactly as frozen (a copy is kept under "
            "frozen_declarations in declarations.lock)", "restore the file: out-of-sample was opened, so declare.py amend is refused"
            if lock.get("oos_opened_utc") else "run declare.py amend --reason ..., or restore the file")
    return decl, lock

DATA_FIX = ("put the file back exactly as it was frozen; a corrected or longer file is frozen again with declare.py amend "
            "--reason \"...\" before out-of-sample is opened, and is a new experiment after")
def check_data(decl, lock) -> str:
    """Exit 3 unless the data file's size and sha256 equal the lock's (one rule and one message for every step);
    exit 2 when the file cannot be opened. Returns the sha256."""
    h, size, want = hashlib.sha256(), 0, lock.get("data") or {}
    try:
        with open(decl["data"]["path"], "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
                size += len(chunk)
    except (OSError, TypeError, KeyError) as e:
        die(2, f"data file cannot be opened ({e})", "the CSV named in data.path, where it was frozen", DATA_FIX)
    if size != want.get("bytes") or h.hexdigest() != want.get("sha256"):
        die(3, "the data file changed since the freeze (its size or sha256 differs from the lock)", "the file exactly as frozen", DATA_FIX)
    return h.hexdigest()

def title(instrument, hypothesis, width=60) -> str:
    """'<instrument>, <hypothesis>' for a heading: the hypothesis cut at a word within `width` characters, and the
    instrument left out when the hypothesis already begins with it."""
    ins, hyp = (" ".join(str(v or "").split()) for v in (instrument, hypothesis))
    hyp = hyp.rstrip(" ,.;:")
    if len(hyp) > width:
        hyp = hyp[:width + 1].rsplit(" ", 1)[0].rstrip(" ,.;:") + " ..."
    return hyp if ins and (hyp.lower() + " ").startswith(ins.lower() + " ") else f"{ins}, {hyp}"

def require(exp, filename, key=None, equals=None):
    """Step-order guard on EXP/results/<filename>: exit 3 if it is missing, or if dotted `key` ('gate.pass') is
    absent/null or (with `equals`) differs. Returns the parsed JSON for .json files, else the path."""
    path, fix = os.path.join(exp, "results", filename), "run declare.py status --exp EXP and follow its NEXT: line"
    if not os.path.exists(path):
        die(3, f"results/{filename} is missing: a step was run out of order", "the earlier steps done first", fix)
    if not filename.endswith(".json"):
        return path
    doc = val = read_json(path)
    for part in (key.split(".") if key else ()):
        val = val.get(part) if isinstance(val, dict) else None
    if key and (val is None or (equals is not None and val != equals)):
        die(3, f"results/{filename} has {key} = {json.dumps(val)}", f"{key} {'present' if equals is None else json.dumps(equals)} before this step", fix)
    return doc

def _us_eastern_hours(dt):
    # post-2007 US rule on a naive New York wall time: -4 from the 2nd Sunday of March 02:00 to the 1st Sunday of November 02:00
    def sunday(month, nth):
        first = datetime(dt.year, month, 1)
        return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (nth - 1), hours=2)
    return -4 if sunday(3, 2) <= dt < sunday(11, 1) else -5
def _tz(zone):
    try:
        return None if FORCE_TZ_FALLBACK or ZoneInfo is None else ZoneInfo(zone)
    except Exception:
        return None

def zone_rule(zone) -> str:
    """How `zone` is resolved on this machine: 'UTC', 'zoneinfo' or 'built-in US fallback'; any other case exits 2."""
    if zone in ("UTC", "Etc/UTC"):
        return "UTC"
    if isinstance(zone, str) and _tz(zone) is not None:
        return "zoneinfo"
    if zone == "America/New_York":
        return "built-in US fallback"
    die(2, f"no time-zone database on this machine for {zone}", "a zone Python can resolve",
        "give the event in America/New_York or UTC, or run where Python has zone data")

def _naive_to_utc(dt, zone) -> int:
    epoch, rule = math.floor((dt - datetime(1970, 1, 1)).total_seconds()), zone_rule(zone)
    if rule == "zoneinfo":
        return epoch - int(dt.replace(tzinfo=_tz(zone)).utcoffset().total_seconds())
    return epoch if rule == "UTC" else epoch - _us_eastern_hours(dt) * 3600

def detect_ts_unit(text) -> str:
    """'s', 'ms', 'us' or 'ns' by magnitude (below 1e11, 1e14, 1e17, else); 'iso' when text is not a number."""
    try:
        v = abs(float(text))
    except (TypeError, ValueError):
        return "iso"
    return "s" if v < 1e11 else "ms" if v < 1e14 else "us" if v < 1e17 else "ns"

def parse_ts(text, unit=None, zone="UTC") -> int:
    """Timestamp text -> UTC epoch seconds. unit 's'|'ms'|'us'|'ns'|'iso' (None = detect by magnitude). ISO text
    with an offset or Z is honoured; without one it is wall time in `zone`. Raises ValueError if unreadable."""
    s = str(text).strip()
    unit = unit or detect_ts_unit(s)
    if unit in UNIT_DIV:
        try:
            return int(s) // UNIT_DIV[unit]
        except ValueError:
            return int(float(s) // UNIT_DIV[unit])  # "nan" and "inf" raise ValueError here
    if unit != "iso":
        raise ValueError(f"unknown timestamp unit {unit!r}")
    dt = datetime.fromisoformat(s[:-1] + "+00:00" if s[-1:] in ("Z", "z") else s)
    if dt.tzinfo is None and zone is None:
        raise ValueError("ISO timestamp without an offset while data.ts_zone is null")
    return math.floor(dt.timestamp()) if dt.tzinfo is not None else _naive_to_utc(dt, zone)

def local_to_utc(date, hhmm, zone) -> int:
    """UTC epoch seconds of wall clock 'HH:MM' in IANA `zone` on `date` (datetime.date or 'YYYY-MM-DD'); daylight
    saving is resolved for that date. A zone that cannot be resolved exits 2; UTC is never assumed."""
    d = _date.fromisoformat(date) if isinstance(date, str) else date
    hh, mm = (int(p) for p in str(hhmm).split(":")[:2])
    return _naive_to_utc(datetime(d.year, d.month, d.day, hh, mm), zone)

def utc_day(ts) -> str:
    """'YYYY-MM-DD' of the UTC date containing epoch second ts."""
    return time.strftime("%Y-%m-%d", time.gmtime(ts))
def utc_iso(ts=None) -> str:
    """'YYYY-MM-DDTHH:MM:SSZ' for epoch second ts (now when None)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
def to_epoch(value):
    """None -> None; a number -> int epoch seconds; text ('YYYY-MM-DD' or ISO, read as UTC) -> epoch seconds."""
    return None if value is None else int(value) if isinstance(value, (int, float)) else parse_ts(value, None, "UTC")

class Bars:
    """ts: array('q') of bar OPEN times (epoch s, ascending, unique); open, high, low, close, volume: array('d');
    bar_seconds; first_oos_index = first index with ts >= split_utc (len(bars) when there is none)."""
    __slots__ = _FIELDS + ("bar_seconds", "first_oos_index")
    def __init__(self, bar_seconds):
        self.ts, self.bar_seconds, self.first_oos_index = array("q"), int(bar_seconds), 0
        self.open, self.high, self.low, self.close, self.volume = (array("d") for _ in range(5))
    def __len__(self):
        return len(self.ts)
    def index_at(self, ts):
        """Index of the bar whose open time is exactly ts (by bisect), or None when that bar does not exist."""
        i = bisect.bisect_left(self.ts, ts)
        return i if i < len(self.ts) and self.ts[i] == ts else None
    def window(self, i, lookback):
        """Window over the `lookback` closed bars i-lookback .. i-1; bar i itself is not in it."""
        return Window(self, i - lookback, i)

class Window:
    """Read-only view given to a rule: .ts .open .high .low .close .volume are tuples of bars lo .. hi-1, oldest
    first, built on access. ValueError if the range is outside the loaded bars."""
    __slots__ = ("_b", "_lo", "_hi")
    def __init__(self, bars, lo, hi):
        if lo < 0 or hi > len(bars) or lo > hi:
            raise ValueError("window outside the loaded bars")
        for name, v in zip(self.__slots__, (bars, lo, hi)):
            object.__setattr__(self, name, v)
    def __getattr__(self, name):
        if name not in _FIELDS:
            raise AttributeError(name)
        return tuple(getattr(self._b, name)[self._lo:self._hi])
    def __setattr__(self, name, value):
        raise AttributeError("the window is read-only")

def load_bars(decl, lock, segment) -> Bars:
    """Stream decl['data']['path'] once into Bars. 'dev': open time < lock['split_utc'], reading stops there (later
    rows are never parsed); 'oos': rows from split_utc - 30 days on (the 30 days are lookback only, see
    first_oos_index); 'all': every row (lock may be None). data.first_utc/last_utc bound the rows when set;
    identical duplicate rows are skipped. Exit 2: file or mapped column missing. Exit 3: a checkdata.py FAIL."""
    d = decl["data"]
    bs, unit, zone, cols = int(d["bar_seconds"]), d.get("ts_unit") or "s", d.get("ts_zone"), d.get("columns") or {}
    split = lock.get("split_utc") if lock else None
    if segment not in ("dev", "oos", "all") or (split is None and segment != "all"):
        die(2, f"cannot load segment {segment!r}", "'dev', 'oos' or 'all', and a lock for dev and oos", "freeze first")
    shift, div = (bs if d.get("stamp") == "close" else 0), UNIT_DIV.get(unit)
    lo, hi = to_epoch(d.get("first_utc")), to_epoch(d.get("last_utc"))
    if segment == "oos":
        lo = max(split - 30 * 86400, split - 30 * 86400 if lo is None else lo)
    def bad(n, why):
        die(3, f"data line {n}: {why}", "a file that passes checkdata.py", "run checkdata.py --exp EXP and fix what it lists")
    try:
        f = open(d["path"], newline="", encoding="utf-8-sig")
    except (OSError, TypeError) as e:
        die(2, f"data file cannot be opened ({e})", "the CSV named in data.path", "correct data.path")
    bars, last, prev, n = Bars(bs), None, None, 1
    with f:
        rd = csv.reader(f)
        names = [h.strip().lower() for h in next(rd, [])]
        def col(key):
            want = cols.get(key)
            if want is None and key == "volume":
                return -1
            if str(want).lower() not in names:
                die(2, f"column {want!r} ({key}) is not in the data header", f"one of {names}", "correct data.columns")
            return names.index(str(want).lower())
        it, io, ih, il, ic, iv = (col(k) for k in _FIELDS)
        for row in rd:
            n += 1
            if not row:
                continue
            try:
                t = (int(row[it]) // div if div else parse_ts(row[it], unit, zone)) - shift
            except (ValueError, IndexError):
                try:
                    t = parse_ts(row[it], unit, zone) - shift
                except (ValueError, IndexError, OverflowError):
                    bad(n, "the timestamp cannot be read")
            if (segment == "dev" and t >= split) or (hi is not None and t > hi):
                break
            if prev is not None and t < prev:
                bad(n, "open times are not ascending")
            same, prev = t == prev, t
            if lo is not None and t < lo:
                continue
            try:
                o, h, l, c = float(row[io]), float(row[ih]), float(row[il]), float(row[ic])
                v = float(row[iv]) if iv >= 0 and row[iv].strip() else 0.0
            except (ValueError, IndexError):
                bad(n, "a price cannot be read")
            if same and last == (o, h, l, c):
                continue
            if same and last is not None:
                bad(n, "duplicate open time with different prices")
            if not (0 < l <= min(o, c) and max(o, c) <= h < math.inf):
                bad(n, "prices break the bar rules (0 < low <= open, close <= high)")
            last = (o, h, l, c)
            bars.ts.append(t); bars.open.append(o); bars.high.append(h)
            bars.low.append(l); bars.close.append(c); bars.volume.append(v)
    if n == 1:
        bad(1, "zero data rows")
    bars.first_oos_index = len(bars) if split is None else bisect.bisect_left(bars.ts, split)
    return bars

def cells(lock) -> list:
    """The frozen cell list: dicts {index, pset, hold_minutes, stop_bp, target_bp, params}, in lock order."""
    return list(lock["cells"])

def mean(x) -> float:
    """Arithmetic mean (0.0 for an empty sequence)."""
    return math.fsum(x) / len(x) if len(x) else 0.0
def sd(x) -> float:
    """Sample standard deviation, ddof = 1 (0.0 for fewer than 2 values)."""
    m = mean(x)
    return math.sqrt(math.fsum((v - m) ** 2 for v in x) / (len(x) - 1)) if len(x) > 1 else 0.0
def sharpe(x) -> float:
    """Per-observation Sharpe = mean / sd; 0.0 when sd is 0 (callers treat zero variance as bad input)."""
    s = sd(x)
    return mean(x) / s if s > 0 else 0.0
def tstat(x) -> float:
    """t = mean / (sd / sqrt(n)); 0.0 when sd is 0."""
    return sharpe(x) * math.sqrt(len(x))
def median(x) -> float:
    """Median (0.0 for an empty sequence)."""
    return float(statistics.median(x)) if len(x) else 0.0

def skew_kurt(x):
    """(skew, kurt): population standardised 3rd and 4th moments; kurt is RAW (a normal has 3). (0.0, 3.0) at zero variance."""
    m, n = mean(x), len(x)
    m2 = math.fsum((v - m) ** 2 for v in x) / n if n else 0.0
    if m2 <= 0:
        return 0.0, 3.0
    return math.fsum((v - m) ** 3 for v in x) / n / m2 ** 1.5, math.fsum((v - m) ** 4 for v in x) / n / m2 ** 2

def lag1_autocorr(x) -> float:
    """Lag-1 autocorrelation sum((x_t - m)(x_t+1 - m)) / sum((x_t - m)^2); 0.0 when the denominator is 0."""
    m = mean(x)
    den = math.fsum((v - m) ** 2 for v in x)
    return math.fsum((a - m) * (b - m) for a, b in zip(x, x[1:])) / den if den > 0 else 0.0

def day_sums(trades, key="net_bp"):
    """(days, values): per UTC entry day the sum of trade[key] in bp; trades are dicts holding 'day' or 'entry_ts'.
    Days ascending; values[i] is the event-day x_d, len(values) is D."""
    acc = {}
    for t in trades:
        day = t.get("day") or utc_day(t["entry_ts"])
        acc[day] = acc.get(day, 0.0) + t[key]
    return sorted(acc), [acc[d] for d in sorted(acc)]

def emax(N) -> Emax:
    """Expected maximum of N standard normals as Emax(closed, exact, used): published closed form, Simpson's rule on
    [-10, 10] with 4,000 steps, and the larger of the two. All three are 0.0 for N <= 1."""
    if N <= 1:
        return Emax(0.0, 0.0, 0.0)
    closed = (1 - EULER_GAMMA) * PhiInv(1 - 1 / N) + EULER_GAMMA * PhiInv(1 - 1 / (N * math.e))
    f = lambda x: x * N * _N.pdf(x) * _N.cdf(x) ** (N - 1)
    exact = (f(-10) + f(10) + sum((4 if i % 2 else 2) * f(-10 + i * 0.005) for i in range(1, 4000))) * 0.005 / 3
    return Emax(closed, exact, max(closed, exact))

def psr(sr, n, skew=0.0, kurt=3.0, benchmark=0.0) -> float:
    """Probabilistic Sharpe Ratio P(true per-observation Sharpe > benchmark) from n observations, raw kurtosis.
    DSR is psr(..., benchmark=std_trials * emax(N).used)."""
    return Phi((sr - benchmark) * math.sqrt(n - 1) / math.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr * sr))
def min_trl(sr, skew=0.0, kurt=3.0, benchmark=0.0, z=Z95) -> float:
    """Minimum track record length in observations for PSR(benchmark) to reach Phi(z); inf when sr <= benchmark."""
    return math.inf if sr <= benchmark else 1 + (1 - skew * sr + (kurt - 1) / 4 * sr * sr) * (z / (sr - benchmark)) ** 2

def _clean(v):
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return None if isinstance(v, float) and not math.isfinite(v) else v

def write_result(exp, filename, payload, exit_code, script=None, decl_sha256=None):
    """Write EXP/results/<filename> (indent 1) as {script, decl_sha256, created_utc, exit_code, ...payload} and
    return that dict. script defaults to the running file's stem, decl_sha256 to the lock's; non-finite floats -> null."""
    if decl_sha256 is None:
        decl_sha256 = (read_json(os.path.join(exp, "declarations.lock")) or {}).get("decl_sha256")
    head = {"script": script or os.path.splitext(os.path.basename(sys.argv[0]))[0], "decl_sha256": decl_sha256,
            "created_utc": utc_iso(), "exit_code": int(exit_code)}
    out = _clean({**head, **{k: v for k, v in payload.items() if k not in head}})
    os.makedirs(os.path.join(exp, "results"), exist_ok=True)
    path = os.path.join(exp, "results", filename)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(json.dumps(out, indent=1) + "\n")
    os.replace(path + ".tmp", path)
    return out

def finish(payload, result, next_, exit_code, as_json=False, lines=()):
    """End a script: print `lines`, then 'RESULT: <result>' and 'NEXT: <next_>' as the last two stdout lines (with
    as_json: only the payload as JSON, carrying RESULT and NEXT keys), then exit with exit_code."""
    if as_json:
        print(json.dumps(_clean({**payload, "RESULT": result, "NEXT": next_}), indent=1))
    else:
        print("\n".join([*lines, f"RESULT: {result}", f"NEXT: {next_}"]))
    sys.exit(exit_code)
