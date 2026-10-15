#!/usr/bin/env python3
"""Numerical tests of deflate.py: hand-worked values, the published examples, the CLI and its guards."""
from __future__ import annotations

import contextlib, csv, io, json, math, os, random, subprocess, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import _kit as k
import deflate as d

SCRIPT = os.path.join(os.path.dirname(HERE), "deflate.py")
SUMMARY = "--sr 0.12 --n 400 --skew -0.3 --kurt 4.5".split()


def close(a, b, tol):
    return abs(a - b) <= tol


def run(*argv):
    """deflate.main in this process: (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            d.main([str(a) for a in argv])
    except SystemExit as e:
        return e.code, out.getvalue(), err.getvalue()
    raise AssertionError("deflate.main returned without exiting")


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def test_functions():
    # The 15 assertions of the earlier helper, unchanged. Case A: SR 0.1, 101 normal observations.
    assert close(d.psr(0.1, 101), 0.840741, 1e-6)  # 1 / sqrt(1.005) = 0.997509
    r = [0.01, -0.02, 0.03, 0.00, 0.02, -0.01, 0.04, -0.03, 0.02, 0.01]  # Case B: ten returns with round moments
    sr = d.sharpe(r)
    skew, kurt = d.skew_kurt(r)
    assert close(sr, 1 / math.sqrt(10), 1e-12)
    assert close(skew, -0.248785, 1e-6)
    assert close(kurt, 2.064248, 1e-6)
    assert close(d.psr(sr, len(r), skew, kurt), 0.816570, 1e-6)
    assert close(d.sr0_best_of_n(100, 0.1), 0.253060, 1e-6)  # scaling regression: not 2.5306
    assert close(d.sr0_best_of_n(600, 0.05), 0.155346, 1e-6)
    assert d.sr0_best_of_n(1, 0.05) == 0.0
    p0, dd = d.psr(0.12, 400, -0.3, 4.5), d.dsr(0.12, 400, -0.3, 4.5, 0.05, 600)
    assert close(p0, 0.990379, 1e-6)
    assert close(dd, 0.245260, 1e-6)
    assert dd < p0
    assert d.dsr(0.12, 400, -0.3, 4.5, 0.05, 6000) < dd < d.dsr(0.12, 400, -0.3, 4.5, 0.05, 60)
    assert close(d.min_track_record(0.1), 272.907, 1e-3)
    assert d.min_track_record(0.05, benchmark=0.05) == math.inf
    assert close(d.psr(0.2, 50, benchmark=0.2), 0.5, 1e-12)
    # Published DSR example: annualised 2.5 on 250 periods, n 1250, skew -3, kurt 10, V = 1/500.
    sr, sd = 2.5 / math.sqrt(250), math.sqrt(1 / 500)
    assert close(sr, 0.158114, 1e-6)
    assert close(d.sr0_best_of_n(100, sd), 0.113172, 1e-5) and close(d.dsr(sr, 1250, -3, 10, sd, 100), 0.900397, 1e-5)
    assert close(d.sr0_best_of_n(46, sd), 0.100362, 1e-5) and close(d.dsr(sr, 1250, -3, 10, sd, 46), 0.950502, 1e-5)
    assert close(d.dsr(sr, 1250, 0, 3, sd, 88), 0.950491, 1e-5)
    # Published PSR example: mean 0.036, sd 0.079, skew -2.448, kurt 10.164.
    assert close(d.psr(0.036 / 0.079, 24, -2.448, 10.164), 0.9127, 5e-4)
    assert close(d.psr(0.036 / 0.079, 36, -2.448, 10.164), 0.9530, 5e-4)
    assert all(close(d.psr(*a), k.psr(*a), 1e-12) for a in ((0.1, 101), (0.12, 400, -0.3, 4.5, 0.05)))  # agrees with _kit
    # Days needed (1 + ((z*sqrt(R) + Emax) / SR)^2): 272.907, 490.80, 1005.72.
    assert [d.days_needed(0.1, n_trials=n)[0] for n in (1, 2, 9)] == [273, 491, 1006]
    assert d.days_needed(0.13) == (163, False)
    assert d.days_needed(-0.1) == (None, True) and d.days_needed(0.1, n_trials=9, std_measured=0.2) == (None, True)
    # the figure under the floor spread alone stays finite when the measured spread of the cells makes the other one infinite
    assert [d.days_needed_floor(0.1, n_trials=n) for n in (1, 2, 9)] == [273, 491, 1006] and d.days_needed_floor(-0.1) is None
    wide = d.evaluate(0.1494, 266, 0.0, 3.0, 12, std_measured=0.0977)
    assert wide["no_days_enough"] and wide["days_needed"] is None and wide["days_needed_floor"] == d.days_needed_floor(0.1494, n_trials=12) > 266
    e = d.evaluate(0.1, 300, 0.0, 3.0, 2, None)  # N = 2 uses the exact expected maximum, not the closed form
    assert close(e["emax_used"], 0.564190, 1e-5) and close(e["emax_closed"], 0.519755, 1e-5)
    assert not hasattr(d, "expected_max_sharpe")


def test_calibration():
    """300 seeded runs of 9 unskilled cells of 300 observations: the best cell passes DSR 0.95 in at most 5%."""
    rng, passed = random.Random(20261006), 0
    for _ in range(300):
        cells = [[rng.gauss(0, 1) for _ in range(300)] for _ in range(9)]
        sharpes = [d.sharpe(c) for c in cells]
        best = cells[sharpes.index(max(sharpes))]
        passed += d.evaluate(max(sharpes), 300, *d.skew_kurt(best), 9, d.sample_std(sharpes))["pass"]
    assert passed <= 15, f"{passed} of 300 unskilled grids passed"
    return passed


def test_cli(tmp):
    code, out, _ = run(*SUMMARY, "--trials", 600, "--trials-sr-std", 0.05)  # the floor 1/sqrt(399) replaces 0.05
    assert code == 1 and out.startswith(d.HAND_NOTE) and "used 0.050063" in out and "+0.155541" in out
    assert "Deflated Sharpe Ratio  0.2441  (not a pass at 0.95)" in out
    assert out.splitlines()[-2].startswith("RESULT: ") and out.splitlines()[-1].startswith("NEXT: ") and len(out.splitlines()) <= 45
    code, js, _ = run(*SUMMARY, "--trials", 600, "--trials-sr-std", 0.05, "--json")
    j = json.loads(js)
    assert code == 1 and close(j["sr0"], 0.155541, 1e-6) and close(j["dsr"], 0.2441, 5e-5) and f"{j['dsr']:.4f}" in out
    assert close(j["std_trials_floor"], 0.050063, 1e-6) and j["std_trials_measured"] == 0.05 and j["N"] == 600 and j["pass"] is False
    same = write(os.path.join(tmp, "same.csv"), "sharpe\n0.1\n0.1\n0.1\n")  # the cheat that used to zero the deflation
    code, _, err = run(*SUMMARY, "--trials", 600, "--grid-sharpes", same, "--grid-column", "sharpe")
    assert code == 2 and "3 Sharpe values read but --trials is 600" in err
    code, js, _ = run(*SUMMARY, "--trials", 3, "--grid-sharpes", same, "--grid-column", "sharpe", "--json")
    j = json.loads(js)
    assert j["std_trials_measured"] < 1e-12 and close(j["std_trials_used"], 0.050063, 1e-6) and j["sr0"] > 0.04
    code, out, _ = run("--sr", 0.08225, "--n", 400, "--trials", 1)  # t = 1.645 exactly misses 0.95
    assert code == 1 and d.ONE_TRIAL in out and "PSR against zero                  0.9495" in out and "Ratio  0.9495" in out
    assert run("--sr", 0.2, "--n", 400, "--trials", 1)[0] == 0
    rng = random.Random(3)
    rets = write(os.path.join(tmp, "r.csv"), "ret\n" + "".join(f"{rng.gauss(0.3, 1):.6f}\n" for _ in range(200)))
    code, js, _ = run("--returns", rets, "--column", "ret", "--trials", 4, "--json")
    j = json.loads(js)
    vals = [float(x) for x in open(rets).read().split()[1:]]
    assert close(j["sharpe"], k.sharpe(vals), 1e-12) and j["n"] == 200 and close(j["lag1_autocorr"], k.lag1_autocorr(vals), 1e-12)
    assert run("--returns", rets, "--trials", 4, "--json")[1] == js  # headerless reading skips the header line
    big = write(os.path.join(tmp, "big.csv"), "".join(f"{1 + 0.1 * (i % 3)}\n" for i in range(30)))
    code, out, _ = run("--returns", big, "--trials", 1)
    assert code == 0 and "SUSPICIOUS:" in out and out.index("SUSPICIOUS:") < out.index("Deflated Sharpe Ratio")
    trend = write(os.path.join(tmp, "trend.csv"), "".join(f"{i * 0.01 + rng.gauss(0, 0.1):.5f}\n" for i in range(100)))
    out = run("--returns", trend, "--trials", 1)[1]
    assert "WARNING: lag-1 autocorrelation" in out and "first-order adjustment" in out
    # Guards, through the real command line: exit 2, three stderr lines, no traceback.
    nan = write(os.path.join(tmp, "nan.csv"), "ret\n0.1\nnan\n0.2\n")
    text = write(os.path.join(tmp, "text.csv"), "0.1\n0.2\noops\n0.3\n")
    empty, one = write(os.path.join(tmp, "empty.csv"), ""), write(os.path.join(tmp, "one.csv"), "ret\n0.1\n")
    flat = write(os.path.join(tmp, "flat.csv"), "1\n1\n1\n1\n")
    for argv, word in ((["--sr", "0.1", "--n", "400", "--trials", "0"], "--trials"), (["--sr", "0.1", "--n", "400", "--trials", "-5"], "--trials"),
                       ([*SUMMARY[:4], "--kurt", "0", "--trials", "5"], "add 3"), (["--returns", nan, "--column", "ret", "--trials", "2"], "finite"),
                       (["--returns", empty, "--trials", "2"], "holds 0 numbers"), (["--returns", one, "--column", "ret", "--trials", "2"], "holds 1"),
                       (["--returns", text, "--trials", "2"], "line 3"), (["--returns", flat, "--trials", "2"], "zero variance"),
                       (["--sr", "nan", "--n", "400", "--trials", "2"], "finite"), (["--sr", "0.1", "--n", "2", "--trials", "2"], "at least 3"),
                       (["--sr", "0.1", "--n", "400"], "arguments"), (["--returns", rets, "--column", "nope", "--trials", "2"], "no column"),
                       (["--sr", "2.0", "--n", "400", "--trials", "2"], "annualised")):
        p = subprocess.run([sys.executable, "-B", SCRIPT, *argv], capture_output=True, text=True)
        assert p.returncode == 2 and word in p.stderr and "Traceback" not in p.stderr, (argv, p.returncode, p.stderr)
        assert [ln.split(":")[0] for ln in p.stderr.splitlines()] == ["ERROR", "EXPECTED", "TRY"], p.stderr
    assert run("--sr", 2.0, "--n", 400, "--trials", 2, "--sr-is-per-observation")[0] == 0


def test_exp(tmp):
    """--exp: N comes from the lock (3 cells + 4 earlier variants = 7), whatever grid.csv looks like."""
    exp, rng = os.path.join(tmp, "exp"), random.Random(11)
    os.makedirs(os.path.join(exp, "results"))
    decl = {"schema": 1, "kind": "clock", "method": {"gates": {"dsr_min": 0.95}, "null": {"alpha": 0.05}}}
    lock = {"schema": 1, "decl_sha256": k.canonical_sha256(decl), "cells_declared": 3, "variants_seen": 4, "amend_penalty": 0, "N": 7}
    write(os.path.join(exp, "declarations.json"), json.dumps(decl))
    write(os.path.join(exp, "declarations.lock"), json.dumps(lock))
    assert run("--exp", exp)[0] == 3  # no sweep.json yet: a step out of order
    k.write_result(exp, "sweep.json", {"cells_declared": 3, "chosen_cell": 1, "grid_null": {"p": 0.01}}, 0, script="sweep")
    days = [[rng.gauss(m, 10) for _ in range(250)] for m in (-1.0, 2.5, -0.5)]
    grid = "cell,sharpe\n" + "".join(f"{i},{k.sharpe(c):.6f}\n" for i, c in enumerate(days))
    write(os.path.join(exp, "results", "grid.csv"), grid)
    with open(os.path.join(exp, "results", "grid_daily.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["day", "c0", "c1", "c2"])
        w.writerows([f"d{i}", f"{days[0][i]:.6f}", "" if i % 50 == 0 else f"{days[1][i]:.6f}", f"{days[2][i]:.6f}"] for i in range(250))
    code, out, _ = run("--exp", exp)
    j = json.load(open(os.path.join(exp, "results", "deflate.json")))
    kept = [round(v, 6) for i, v in enumerate(days[1]) if i % 50]
    assert d.HAND_NOTE not in out and j["N"] == 7 and j["cells_declared"] == 3 and j["cell"] == 1 and j["n"] == 245  # blank cells skipped
    assert close(j["sharpe"], k.sharpe(kept), 1e-9) and close(j["std_trials_measured"], k.sd([round(k.sharpe(c), 6) for c in days]), 1e-9)
    assert close(j["sr0"], j["std_trials_used"] * k.emax(7).used, 1e-12) and close(j["dsr"], d.psr(j["sharpe"], 245, j["skew"], j["kurt"], j["sr0"]), 1e-12)
    assert j["script"] == "deflate" and j["decl_sha256"] == lock["decl_sha256"] and j["exit_code"] == code == (0 if j["pass"] else 1)
    last = out.splitlines()[-1]
    assert last.startswith("NEXT: python3 ") and os.path.abspath(exp) in last and last.endswith(" --oos") == j["pass"] and ("sweep.py" in last) == j["pass"]
    code, _, err = run("--exp", exp, "--trials", 1)  # N cannot be typed in beside a frozen declaration
    assert code == 3 and "frozen declarations" in err
    write(os.path.join(exp, "results", "grid.csv"), grid.rsplit("\n", 2)[0] + "\n")  # one row deleted
    code, _, err = run("--exp", exp)
    assert code == 3 and "2 rows but 3 cells were declared" in err
    write(os.path.join(exp, "results", "grid.csv"), grid)
    write(os.path.join(exp, "declarations.json"), json.dumps(dict(decl, kind="rule")))  # edited after the freeze
    assert run("--exp", exp)[0] == 3


def main():
    test_functions()
    with tempfile.TemporaryDirectory() as tmp:
        test_cli(tmp)
        test_exp(tmp)
    return test_calibration()


if __name__ == "__main__":
    print(f"test_deflate: all assertions passed ({main()} of 300 unskilled grids reached DSR 0.95)")
