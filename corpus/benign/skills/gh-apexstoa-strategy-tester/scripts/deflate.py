#!/usr/bin/env python3
"""Probabilistic and Deflated Sharpe Ratio for the chosen cell of a declared grid, and days needed.

Written from the published formulas (Bailey and Lopez de Prado):
  "The Sharpe Ratio Efficient Frontier"  https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf   PSR, MinTRL
  "The Deflated Sharpe Ratio"            https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf   SR0, DSR

Every Sharpe here is PER OBSERVATION (per event day): mean / sd of the series, never annualised.
  SR      = mean / sd (ddof 1)
  PSR(b)  = Phi( (SR - b) * sqrt(n - 1) / sqrt(1 - skew*SR + (kurt - 1)/4 * SR^2) )    kurt is raw: a normal has 3
  SR0     = std_trials * Emax(N)      Emax = expected maximum of N standard normals, max(closed form, exact integral)
  DSR     = PSR(SR0)                  std_trials = max(sd of the declared cells' Sharpes, 1/sqrt(n - 1))
  MinTRL  = 1 + (1 - skew*SR + (kurt - 1)/4 * SR^2) * (z / (SR - b))^2

  python3 deflate.py --exp EXP [--json]            N and the cells come from the frozen declarations
  python3 deflate.py --returns r.csv --column ret --trials N [--grid-sharpes g.csv --grid-column sharpe | --trials-sr-std S]
  python3 deflate.py --sr 0.12 --n 400 --skew -0.3 --kurt 4.5 --trials 600 --trials-sr-std 0.05 [--sr-is-per-observation]
Exit 0: DSR at or above the level; 1: below it (a result); 2: bad input; 3: refused.
"""
from __future__ import annotations

import argparse, csv, math, os, shlex, sys
from statistics import NormalDist

sys.dont_write_bytecode = True  # nothing is ever written into the skill folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _kit

EULER_GAMMA = 0.5772156649015329
_N = NormalDist()
HAND_NOTE = "N was typed by hand and is not bound to a frozen declaration"
ONE_TRIAL = "one trial: nothing to deflate, DSR equals PSR(0)"
NO_DAYS = "no number of days is enough at this Sharpe"


def sharpe(returns: list[float]) -> float:
    """Per-observation Sharpe: mean over sample standard deviation (ddof=1)."""
    n = len(returns)
    if n < 2:
        raise ValueError("need at least 2 returns")
    m = sum(returns) / n
    var = sum((x - m) ** 2 for x in returns) / (n - 1)
    if var <= 0:
        raise ValueError("returns have zero variance: check the input, this is not a real series")
    return m / math.sqrt(var)


def skew_kurt(returns: list[float]) -> tuple[float, float]:
    """(skewness, kurtosis) as standardised population moments. Kurtosis is not excess."""
    n = len(returns)
    m = sum(returns) / n
    m2 = sum((x - m) ** 2 for x in returns) / n
    if m2 <= 0:
        raise ValueError("returns have zero variance")
    m3 = sum((x - m) ** 3 for x in returns) / n
    m4 = sum((x - m) ** 4 for x in returns) / n
    return m3 / m2 ** 1.5, m4 / m2 ** 2


def psr(sr: float, n: int, skew: float = 0.0, kurt: float = 3.0, benchmark: float = 0.0) -> float:
    """Probability that the true per-observation Sharpe exceeds `benchmark`."""
    if n < 3:
        raise ValueError("need at least 3 observations")
    radicand = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if radicand <= 0:
        raise ValueError("variance term is not positive: moments and Sharpe are inconsistent")
    return _N.cdf((sr - benchmark) * math.sqrt(n - 1) / math.sqrt(radicand))


def sr0_best_of_n(n_trials: int, std_trials: float) -> float:
    """SR0 by the published closed form: the Sharpe the best of n_trials unskilled cells is expected to show.
    A single cell, or cells with no spread, leave nothing to deflate against: 0.0."""
    if n_trials <= 1:
        return 0.0
    quantiles = (_N.inv_cdf(1.0 - 1.0 / n_trials), _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e)))
    return max(std_trials, 0.0) * sum(w * q for w, q in zip((1.0 - EULER_GAMMA, EULER_GAMMA), quantiles))


def dsr(sr: float, n: int, skew: float, kurt: float, std_trials: float, n_trials: int) -> float:
    """Deflated Sharpe Ratio: PSR measured against the expected best-of-N Sharpe (closed form, spread as given)."""
    return psr(sr, n, skew, kurt, benchmark=sr0_best_of_n(n_trials, std_trials))


def min_track_record(sr: float, skew: float = 0.0, kurt: float = 3.0,
                     benchmark: float = 0.0, confidence: float = 0.95) -> float:
    """Observations needed before PSR(benchmark) reaches `confidence`. Infinite if sr <= benchmark."""
    if sr <= benchmark:
        return math.inf
    z = _N.inv_cdf(confidence)
    return 1.0 + (1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr) * (z / (sr - benchmark)) ** 2


def sample_std(values: list[float]) -> float:
    """Sample standard deviation (ddof=1)."""
    n = len(values)
    if n < 2:
        raise ValueError("need at least 2 values")
    m = sum(values) / n
    return math.sqrt(sum((x - m) ** 2 for x in values) / (n - 1))


def days_needed(sr, skew=0.0, kurt=3.0, n_trials=1, std_measured=None, dsr_min=0.95):
    """(days, no_days_enough): observations for DSR >= dsr_min at this Sharpe. The larger of the figure under the
    floor spread 1/sqrt(n-1) and the MinTRL against std_measured * Emax. (None, True) when no number is enough."""
    if sr <= 0:
        return None, True
    z, e = _N.inv_cdf(dsr_min), _kit.emax(n_trials).used
    radicand = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    need = max(1.0 + ((z * math.sqrt(radicand) + e) / sr) ** 2,
               min_track_record(sr, skew, kurt, (std_measured or 0.0) * e, dsr_min))
    return (math.ceil(need), False) if math.isfinite(need) else (None, True)


def days_needed_floor(sr, skew=0.0, kurt=3.0, n_trials=1, dsr_min=0.95):
    """Observations for DSR >= dsr_min when the trial spread is the floor 1/sqrt(n-1) alone; None when sr <= 0."""
    if sr <= 0:
        return None
    need = 1.0 + ((_N.inv_cdf(dsr_min) * math.sqrt(1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr) + _kit.emax(n_trials).used) / sr) ** 2
    return math.ceil(need) if math.isfinite(need) else None


def evaluate(sr, n, skew, kurt, n_trials, std_measured=None, dsr_min=0.95, series=None) -> dict:
    """Every figure of the deflation as a dict (the deflate.json keys except cell and cells_declared).
    std_measured: sd of the declared cells' Sharpes, or None; the spread used is never below 1/sqrt(n-1).
    series: the return list, for the lag-1 autocorrelation sensitivity line (None when only summary numbers exist)."""
    e, floor = _kit.emax(n_trials), 1.0 / math.sqrt(n - 1)
    used = max(std_measured or 0.0, floor)
    sr0 = used * e.used if n_trials > 1 else 0.0
    d = psr(sr, n, skew, kurt, sr0)
    days, never = days_needed(sr, skew, kurt, n_trials, std_measured, dsr_min)
    rho = _kit.lag1_autocorr(series) if series else None
    adj = _N.cdf(sr * math.sqrt(n * (1 - rho) / (1 + rho))) if rho is not None and 0 < rho < 1 else None
    return {"n": n, "sharpe": sr, "t": sr * math.sqrt(n), "skew": skew, "kurt": kurt, "psr0": psr(sr, n, skew, kurt, 0.0),
            "N": n_trials, "std_trials_measured": std_measured, "std_trials_floor": floor, "std_trials_used": used,
            "emax_closed": e.closed, "emax_exact": e.exact, "emax_used": e.used, "sr0": sr0, "dsr": d, "dsr_min": dsr_min,
            "pass": d >= dsr_min, "days_needed": days, "no_days_enough": never,
            "days_needed_floor": days_needed_floor(sr, skew, kurt, n_trials, dsr_min), "lag1_autocorr": rho,
            "psr0_autocorr_adjusted": adj}


def bad(what, expected, try_):
    """Exit 2 with the three stderr lines."""
    _kit.die(2, what, expected, try_)


def read_column(path, column=None, least=2) -> list[float]:
    """Numbers from one CSV column (by header name; blank cells skipped), or from a one-number-per-line file whose
    first line may be a header. Exit 2 on a missing file or column, a non-numeric or non-finite value, or fewer
    than `least` numbers."""
    out, fix = [], "give a file of plain numbers, one per row"
    try:
        fh = open(path, newline="", encoding="utf-8-sig")
    except OSError as e:
        bad(f"{path} cannot be opened ({e})", "a readable CSV or one-number-per-line file", "correct the path")
    with fh:
        if column is None:
            rows = ((i, line.split(",")[0].strip()) for i, line in enumerate(fh, 1))
        else:
            rd = csv.DictReader(fh)
            if column not in (rd.fieldnames or []):
                bad(f"{path} has no column named {column!r}", f"one of {rd.fieldnames or []}", "correct the column name")
            rows = ((i, (row.get(column) or "").strip()) for i, row in enumerate(rd, 2))
        for i, cell in rows:
            if not cell:
                continue
            try:
                v = float(cell)
            except ValueError:
                if column is None and i == 1:
                    continue  # a header line
                bad(f"{path} line {i}: {cell!r} is not a number", "numbers only after the first line", fix)
            if not math.isfinite(v):
                bad(f"{path} line {i}: {cell!r} is not a finite number", "finite numbers only", "remove or repair that row; do not fill it")
            out.append(v)
    if len(out) < least:
        bad(f"{path} holds {len(out)} numbers", f"at least {least}", fix)
    return out


def text_block(r, cells_declared=None) -> list[str]:
    """The aligned text summary; WARNING: and SUSPICIOUS: lines come before the result line, which is last."""
    f = lambda v, spec="{:.6f}": "none" if v is None else spec.format(v)
    lines = [f"observations (n)                  {r['n']}",
             f"Sharpe per observation            {r['sharpe']:+.6f}",
             f"t-statistic (SR * sqrt(n))        {r['t']:+.3f}",
             f"skewness / kurtosis (raw)         {r['skew']:+.4f} / {r['kurt']:.4f}",
             f"PSR against zero                  {r['psr0']:.4f}",
             f"trials (N)                        {r['N']}" + ("" if cells_declared is None else f"  ({cells_declared} cells declared)"),
             f"sd of Sharpe across cells         measured {f(r['std_trials_measured'])}, floor 1/sqrt(n-1) {r['std_trials_floor']:.6f}, used {r['std_trials_used']:.6f}",
             f"expected maximum of N normals     closed form {r['emax_closed']:.6f}, exact {r['emax_exact']:.6f}, used {r['emax_used']:.6f}",
             f"expected best-of-N Sharpe (SR0)   {r['sr0']:+.6f}"]
    if r["N"] == 1:
        lines.append(ONE_TRIAL)
    if r["lag1_autocorr"] is not None:
        lines.append(f"lag-1 autocorrelation             {r['lag1_autocorr']:+.4f}  (sensitivity only, not used in any gate)")
    if r["psr0_autocorr_adjusted"] is not None:
        lines.append(f"PSR(0), first-order adjustment    {r['psr0_autocorr_adjusted']:.4f}  (Phi(SR*sqrt(n(1-rho)/(1+rho))), as in the 2025 authors' code)")
    lines.append(f"days needed for DSR {r['dsr_min']:<13} " + (NO_DAYS if r["no_days_enough"] else str(r["days_needed"])))
    lines += r["warnings"] + r["flags"]
    lines.append(f"Deflated Sharpe Ratio  {r['dsr']:.4f}  ({'PASS' if r['pass'] else 'not a pass'} at {r['dsr_min']})")
    return lines


def run(sr, n, skew, kurt, n_trials, std_measured, dsr_min, series, from_file):
    """Guards (exit 2) then evaluate(); adds the 'warnings' and 'flags' lists."""
    vals = [sr, skew, kurt, dsr_min] + ([] if std_measured is None else [std_measured])
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vals):
        bad("a value is not a finite number (nan or inf)", "finite numbers everywhere", "check the inputs; a nan usually means an empty or broken series")
    if n_trials < 1:
        bad(f"--trials is {n_trials}", "the number of cells declared, at least 1", "count every variant tried, including abandoned ones")
    if kurt < 1 + skew * skew:
        bad(f"kurtosis {kurt} is below 1 + skew^2 = {1 + skew * skew:.4f}, which no series can have",
            "raw kurtosis (a normal has 3)", "this looks like excess kurtosis: add 3")
    if std_measured is not None and std_measured < 0:
        bad(f"--trials-sr-std is {std_measured}", "a standard deviation, zero or above", "give the sd of the cells' per-observation Sharpes")
    try:
        r = evaluate(sr, n, skew, kurt, n_trials, std_measured, dsr_min, series)
    except (ValueError, ZeroDivisionError) as e:
        bad(f"cannot compute: {e}", "n of at least 3 and moments consistent with the Sharpe", "check --n, --skew and --kurt")
    r["warnings"], r["flags"] = [], []
    rho = r["lag1_autocorr"]
    if rho is not None and abs(rho) > 2 / math.sqrt(n):
        r["warnings"].append(f"WARNING: lag-1 autocorrelation {rho:+.3f} is beyond 2/sqrt(n) = {2 / math.sqrt(n):.3f}: the observations are not independent and every figure here is optimistic")
    if from_file and abs(sr) > 1:
        r["flags"].append(f"SUSPICIOUS: a per-observation Sharpe of {sr:+.3f} means t = {r['t']:+.1f}; reproduce three trades by hand before believing it")
    return r


def from_exp(exp):
    """--exp mode inputs: (sr, n, skew, kurt, N, std_measured, dsr_min, series, extra keys, sweep.json)."""
    decl, lock = _kit.load_decl(exp)
    sweep = _kit.require(exp, "sweep.json")
    fix = "run sweep.py --exp EXP again; do not edit files in results/"
    if sweep.get("decl_sha256") != lock["decl_sha256"]:
        _kit.die(3, "results/sweep.json was made under other declarations", "a sweep run after the last freeze or amend", fix)
    cell, declared = sweep.get("chosen_cell"), int(lock["cells_declared"])
    if cell is None:
        _kit.die(3, "the sweep chose no cell (none reached the minimum event days)", "a chosen cell", "run verdict.py --exp EXP")
    with open(_kit.require(exp, "grid.csv"), newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != declared:
        _kit.die(3, f"results/grid.csv holds {len(rows)} rows but {declared} cells were declared", "one row per declared cell", fix)
    try:
        sharpes = [float(r["sharpe"]) for r in rows if (r.get("sharpe") or "").strip()]
    except ValueError:
        _kit.die(3, "results/grid.csv has a sharpe value that is not a number", "the file as sweep.py wrote it", fix)
    series = read_column(_kit.require(exp, "grid_daily.csv"), f"c{cell}", least=3)
    try:
        sr, (skew, kurt) = sharpe(series), skew_kurt(series)
    except ValueError as e:
        bad(f"chosen cell c{cell}: {e}", "a return series with some spread", fix)
    measured = sample_std(sharpes) if declared > 1 and len(sharpes) > 1 else None
    return (sr, len(series), skew, kurt, int(lock["N"]), measured, float(decl["method"]["gates"]["dsr_min"]), series,
            {"cell": cell, "cells_declared": declared}, sweep, float(decl["method"]["null"]["alpha"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description="PSR, SR0, DSR and days needed. Sharpe is per observation, never annualised.")
    ap.add_argument("--exp", help="experiment folder: N and the cells are read from the frozen declarations")
    ap.add_argument("--returns", help="stand-alone: CSV of per-observation returns of the chosen cell")
    ap.add_argument("--column", help="column name in --returns (omit for one number per line)")
    ap.add_argument("--sr", type=float, help="stand-alone: per-observation Sharpe (not annualised)")
    ap.add_argument("--n", type=int, help="number of observations, with --sr")
    ap.add_argument("--skew", type=float, default=0.0)
    ap.add_argument("--kurt", type=float, default=3.0, help="raw kurtosis, NOT excess (a normal has 3)")
    ap.add_argument("--trials", type=int, help="stand-alone: every cell and variant tried, all of them")
    ap.add_argument("--trials-sr-std", type=float, help="sd of the per-observation Sharpe across the cells")
    ap.add_argument("--grid-sharpes", help="CSV holding every cell's per-observation Sharpe")
    ap.add_argument("--grid-column", help="column name in --grid-sharpes")
    ap.add_argument("--sr-is-per-observation", action="store_true", help="confirm a typed --sr above 1 is not annualised")
    ap.add_argument("--json", action="store_true", help="print the result as JSON instead of text")
    a = ap.parse_args(argv)
    typed = [k for k in ("returns", "sr", "n", "trials", "trials_sr_std", "grid_sharpes") if getattr(a, k) is not None]
    if a.exp:
        if typed:
            _kit.die(3, "--exp takes no --" + typed[0].replace("_", "-") + ": the trial count and the series come from the frozen declarations",
                     "deflate.py --exp EXP alone", "run it without the extra arguments; N cannot be typed in")
        sr, n, skew, kurt, trials, measured, level, series, extra, sweep, alpha = from_exp(a.exp)
        r = {**extra, **run(sr, n, skew, kurt, trials, measured, level, series, True)}
        gn = sweep.get("grid_null") or {}
        ahead = r["pass"] and not (sweep.get("grid_null") and (gn.get("p") is None or gn["p"] > alpha))
        out = _kit.write_result(a.exp, "deflate.json", r, 0 if r["pass"] else 1, script="deflate")
        here, where = os.path.dirname(os.path.abspath(__file__)), shlex.quote(os.path.abspath(a.exp))
        nxt = f"python3 {shlex.quote(os.path.join(here, 'sweep.py' if ahead else 'verdict.py'))} --exp {where}{' --oos' if ahead else ''}"
        lines = text_block(r, extra["cells_declared"])
    else:
        if a.trials is None or (a.returns is None and (a.sr is None or a.n is None)):
            bad("not enough arguments", "--exp EXP, or --trials N with --returns FILE, or --trials N with --sr and --n", "see deflate.py --help")
        if a.returns:
            series = read_column(a.returns, a.column)
            try:
                sr, n, (skew, kurt) = sharpe(series), len(series), skew_kurt(series)
            except ValueError as e:
                bad(f"{a.returns}: {e}", "a return series with some spread", "check the column")
        else:
            sr, n, skew, kurt, series = a.sr, a.n, a.skew, a.kurt, None
            if math.isfinite(sr) and abs(sr) > 1 and not a.sr_is_per_observation:
                bad(f"--sr {sr} is above 1. A per-observation Sharpe above 1 means t = sqrt(n): an annualised Sharpe must be divided by sqrt(periods per year)",
                    "mean / sd of one observation's return", "divide by sqrt(periods per year), or add --sr-is-per-observation if it really is per observation")
        measured = a.trials_sr_std
        if a.grid_sharpes:
            cells = read_column(a.grid_sharpes, a.grid_column, least=1)
            if len(cells) != a.trials:
                bad(f"{len(cells)} Sharpe values read but --trials is {a.trials}", "one Sharpe for every declared cell",
                    "count every cell, including abandoned ones, and give them all")
            measured = sample_std(cells) if len(cells) > 1 else None
        r = run(sr, n, skew, kurt, a.trials if a.trials is not None else 0, measured, 0.95, series, bool(a.returns))
        out, lines = {"script": "deflate", "note": HAND_NOTE, **r}, [HAND_NOTE] + text_block(r)
        nxt = "a stand-alone figure; to bind N to a declaration start with declare.py init"
    word = "PASS" if r["pass"] else "not a pass"
    _kit.finish(out, f"DSR {r['dsr']:.4f} at N = {r['N']}: {word} at {r['dsr_min']}", nxt, 0 if r["pass"] else 1, as_json=a.json, lines=lines)


if __name__ == "__main__":
    _kit.guard(main)
