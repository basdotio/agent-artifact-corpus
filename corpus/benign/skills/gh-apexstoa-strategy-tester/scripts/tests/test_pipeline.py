#!/usr/bin/env python3
"""The whole pipeline through the real commands, as a user's session runs them: a planted effect ends GO by
following each NEXT: line, no effect ends NO-GO, pure drift does not pass, and order and tamper are refused."""
from __future__ import annotations

import json, os, shlex, shutil, subprocess, sys, tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path[:0] = [HERE, SCRIPTS]
import synth

IDEA = {"hypothesis": "Synthetic bars rise in the hour after 14:00 UTC", "instrument": "SYNTH", "venue": "none (synthetic)",
        "side": "long", "event": {"local_time": "14:00", "zone": "UTC", "days": "all", "skip_dates_file": None},
        "trade": {"hold_minutes": 60, "stop_bp": None, "target_bp": None}, "params": {},
        "grid": {"trade.hold_minutes": [60, 120]}, "prior_looks": {"text": "never looked at", "variants_seen": 0}}
COSTS = {"fee_bp_per_fill": 5, "half_spread_bp_per_fill": 1, "source": "measured: the tester's figures"}
CHAIN = ["declare.py", "checkdata.py", "events.py", "effect.py", "sweep.py", "deflate.py", "sweep.py", "verdict.py"]


def run(script, *args):
    """Run a skill command the way a session does (no -B); returns (exit code, stdout, stderr)."""
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script + ".py"), *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def follow(first, scripts=SCRIPTS):
    """Run a command line, then whatever each NEXT: line names while it is a python3 command.
    Returns [(script file name, exit code, stdout)]. Every command named must be one of `scripts`' own files."""
    done, argv = [], first
    while argv and len(done) < 12:
        p = subprocess.run(argv, capture_output=True, text=True)
        done.append((os.path.basename(argv[1]), p.returncode, p.stdout))
        last = p.stdout.rstrip().splitlines()[-1] if p.stdout.strip() else ""
        assert p.returncode in (0, 1) and last.startswith("NEXT: "), (argv, p.returncode, p.stdout[-300:], p.stderr)
        argv = shlex.split(last[6:]) if last.startswith("NEXT: python3 ") else None
        if argv:
            assert os.path.dirname(argv[1]) == scripts and "--exp" in argv, argv
            argv[0] = sys.executable
    return done


def result(exp, name):
    with open(os.path.join(exp, "results", name), encoding="utf-8") as f:
        return json.load(f)


def edit(exp, change):
    path = os.path.join(exp, "declarations.json")
    with open(path, encoding="utf-8") as f:
        decl = json.load(f)
    change(decl)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(decl, f, indent=2)


def declare(tmp, name, method=None, **synth_args):
    """init, fill the null keys, check and show: an experiment folder ready to freeze."""
    data, exp = os.path.join(tmp, name + ".csv"), os.path.join(tmp, name)
    synth.generate(data, days=400, bar_seconds=900, **synth_args)
    assert run("declare", "init", "--exp", exp, "--kind", "clock", "--data", data)[0] == 0
    edit(exp, lambda d: d.update(idea=IDEA, costs=COSTS))
    if method:
        assert run("declare", "set", "--exp", exp, *[f"method.{k}={v}" for k, v in method.items()])[0] == 0
    assert run("checkdata", "--exp", exp)[0] == 3, "checkdata.py must refuse before the freeze"
    code, out, _ = run("declare", "check", "--exp", exp)
    assert code == 0, out
    code, out, _ = run("declare", "show", "--exp", exp)
    assert code == 0 and out.count("[default]") >= 8 and "Draft, not frozen" in out
    return exp


def freeze_and_follow(exp):
    return follow([sys.executable, os.path.join(SCRIPTS, "declare.py"), "freeze", "--exp", exp])


def first_line(exp):
    with open(os.path.join(exp, "FINDINGS.md"), encoding="utf-8") as f:
        return f.read().splitlines()


def test_planted(tmp):
    exp = declare(tmp, "planted", seed=7, effect_bp=25.0)
    done = freeze_and_follow(exp)
    assert [d[0] for d in done] == CHAIN and all(d[1] == 0 for d in done), [(d[0], d[1]) for d in done]
    v, lock = result(exp, "verdict.json"), json.load(open(os.path.join(exp, "declarations.lock"), encoding="utf-8"))
    assert v["verdict"] == "GO" and v["row"] == 14 and "VERDICT: GO" in done[-1][2]
    assert first_line(exp)[0].endswith(": GO") and run("verdict", "--exp", exp, "--check")[0] == 0
    assert result(exp, "deflate.json")["N"] == lock["N"] == 2 and result(exp, "oos.json")["cell"] == result(exp, "sweep.json")["chosen_cell"]
    assert all(result(exp, n + ".json")["created_utc"] >= lock["frozen_utc"] for n in ("data_check", "events", "effect_dev", "sweep", "deflate", "oos"))
    before = open(os.path.join(exp, "results", "oos.json"), "rb").read()
    code, _, err = run("sweep", "--exp", exp, "--oos")
    assert code == 3 and "read once" in err and open(os.path.join(exp, "results", "oos.json"), "rb").read() == before
    edit(exp, lambda d: d["idea"]["trade"].update(stop_bp=30))
    assert run("declare", "amend", "--exp", exp, "--reason", "a stop on the newer data")[0] == 3  # out-of-sample was opened
    edit(exp, lambda d: d["idea"]["trade"].update(stop_bp=None))
    code, out, _ = run("declare", "status", "--exp", exp)
    assert code == 0 and "8 of 8 steps done; 3 prose section(s) of FINDINGS.md still to be written" in out
    code, out, _ = run("verdict", "--exp", exp, "--check")
    assert code == 0 and "3 prose section(s) still read <to be written>, so the findings are not finished" in out
    # the one look is recorded in the lock: with oos.json moved away there is no second look and no clean verdict
    assert lock["oos_opened_utc"] == result(exp, "oos.json")["opened_utc"]
    os.rename(os.path.join(exp, "results", "oos.json"), os.path.join(exp, "oos.moved"))
    code, out, err = run("sweep", "--exp", exp, "--oos")
    assert code == 3 and out == "" and "results/oos.json is gone" in err and not os.path.exists(os.path.join(exp, "results", "oos.json"))
    code, _, err = run("verdict", "--exp", exp)
    assert code == 3 and "results/oos.json is missing" in err
    assert run("verdict", "--exp", exp, "--check")[0] == 3 and run("declare", "amend", "--exp", exp, "--reason", "again")[0] == 3
    os.rename(os.path.join(exp, "oos.moved"), os.path.join(exp, "results", "oos.json"))
    assert run("verdict", "--exp", exp, "--check")[0] == 0
    grid = os.path.join(exp, "results", "grid.csv")
    rows = open(grid, encoding="utf-8").read().splitlines()
    with open(grid, "w", encoding="utf-8") as f:
        f.write("\n".join(rows[:-1]) + "\n")
    code, _, err = run("verdict", "--exp", exp)
    assert code == 3 and "grid.csv" in err


def test_no_effect(tmp):
    exp = declare(tmp, "flat", seed=11, effect_bp=0.0)
    done = freeze_and_follow(exp)
    assert [(d[0], d[1]) for d in done] == [("declare.py", 0), ("checkdata.py", 0), ("events.py", 0), ("effect.py", 1), ("verdict.py", 0)]
    assert "CHARACTERISATION GATE: FAIL" in done[3][2]
    code, _, err = run("sweep", "--exp", exp)
    assert code == 3 and "verdict.py" in err and not os.path.exists(os.path.join(exp, "results", "sweep.json"))
    v = result(exp, "verdict.json")
    assert v["verdict"] == "NO-GO" and v["row"] == 2 and first_line(exp)[0].endswith(": NO-GO")
    text = "\n".join(first_line(exp))
    assert text.count("\nnot run\n") == 3 and not os.path.exists(os.path.join(exp, "results", "oos.json"))  # grid, deflation, out-of-sample


def test_drift(tmp):
    exp = declare(tmp, "drift", seed=13, effect_bp=0.0, drift_bp_per_hour=25.0)
    done = freeze_and_follow(exp)
    eff, v = result(exp, "effect_dev.json"), result(exp, "verdict.json")
    assert eff["gross"]["mean_bp"] > 12 and eff["null"]["p"] > 0.05, "drift in every hour must not beat other times of the same days"
    assert done[-1][0] == "verdict.py" and v["verdict"] != "GO" and v["row"] in (3, 4)


def test_tamper(tmp):
    exp = declare(tmp, "tamper", seed=7, effect_bp=25.0)
    assert run("declare", "freeze", "--exp", exp)[0] == 0
    code, _, err = run("effect", "--exp", exp)
    assert code == 3 and "out of order" in err
    for step in ("checkdata", "events", "effect"):
        assert run(step, "--exp", exp)[0] == 0
    edit(exp, lambda d: d["idea"]["grid"].update({"trade.hold_minutes": [60, 120, 90]}))
    code, _, err = run("effect", "--exp", exp)
    assert code == 3 and "changed since the freeze" in err
    code, out, _ = run("declare", "amend", "--exp", exp, "--reason", "x")
    assert code == 0 and "N is now 3" in out and os.path.isdir(os.path.join(exp, "results_superseded_1"))
    done = follow(shlex.split(out.rstrip().splitlines()[-1][6:].replace("python3", shlex.quote(sys.executable), 1)))
    assert [d[0] for d in done] == CHAIN[1:] and all(d[1] == 0 for d in done), [(d[0], d[1]) for d in done]
    lines = first_line(exp)
    assert "1 deviations after the freeze" in lines[2] and '"reason": "x"' in "\n".join(lines) and result(exp, "deflate.json")["N"] == 3
    assert sum(1 for l in lines if l.startswith("| ") and l.split("|")[1].strip().isdigit() and "hold" not in l and l.count("|") == 18) == 3


def test_weak_gates(tmp):
    """Gates declared at the weakest values check allows: the run is legal, and the verdict line says so wherever it is printed."""
    exp = declare(tmp, "weak", method={"null.alpha": 0.1, "gates.dsr_min": 0.9, "gates.oos_psr_min": 0.9}, seed=7, effect_bp=25.0)
    done = freeze_and_follow(exp)
    line = first_line(exp)[2]
    assert done[-1][0] == "verdict.py" and line.startswith("**Verdict:** GO: ")
    assert line.endswith("(gates weaker than the defaults: alpha 0.1 against 0.05, dsr_min 0.9 against 0.95, oos_psr_min 0.9 against 0.95)"), line
    assert done[-1][2].rstrip().splitlines()[-2] == "RESULT: " + line[13:] + " [row 14]"
    for key, value in (("null.alpha", 0.5), ("gates.dsr_min", 0.5)):          # anything weaker cannot be frozen at all
        other = declare_only(tmp, "weaker_" + key)
        assert run("declare", "set", "--exp", other, f"method.{key}={value}")[0] == 0
        assert run("declare", "check", "--exp", other)[0] == 2 and run("declare", "freeze", "--exp", other)[0] == 2


def declare_only(tmp, name):
    exp = os.path.join(tmp, name)
    assert run("declare", "init", "--exp", exp, "--kind", "clock", "--data", os.path.join(tmp, "weak.csv"))[0] == 0
    edit(exp, lambda d: d.update(idea=IDEA, costs=COSTS))
    return exp


def test_path_with_spaces(tmp):
    """The skill unzipped under a folder whose name holds a space (a Windows profile, say), and an experiment folder
    with one too: every NEXT: line still names a command that runs."""
    skill = os.path.join(tmp, "home of a user", "strategy-tester")
    shutil.copytree(os.path.dirname(SCRIPTS), skill, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    scripts, exp, data = os.path.join(skill, "scripts"), os.path.join(tmp, "my experiment"), os.path.join(tmp, "flat.csv")
    p = subprocess.run([sys.executable, "-B", os.path.join(scripts, "declare.py"), "init", "--exp", exp, "--kind", "rule", "--data", data],
                       capture_output=True, text=True)
    assert p.returncode == 0 and os.path.isfile(os.path.join(exp, "rule.py")), p.stderr       # the template is found beside the scripts
    shutil.rmtree(exp)
    assert subprocess.run([sys.executable, "-B", os.path.join(scripts, "declare.py"), "init", "--exp", exp, "--kind", "clock", "--data", data],
                          capture_output=True).returncode == 0
    edit(exp, lambda d: d.update(idea=IDEA, costs=COSTS))
    done = follow([sys.executable, os.path.join(scripts, "declare.py"), "freeze", "--exp", exp], scripts)
    assert [(d[0], d[1]) for d in done] == [("declare.py", 0), ("checkdata.py", 0), ("events.py", 0), ("effect.py", 1), ("verdict.py", 0)]
    done = follow([sys.executable, os.path.join(scripts, "declare.py"), "status", "--exp", exp], scripts)
    assert [d[0] for d in done] == ["declare.py"] and "prose section(s)" in done[0][2]


def main():
    def listing():
        return sorted(os.path.join(r, f) for r, _, fs in os.walk(os.path.dirname(SCRIPTS)) for f in fs)
    before, tmp = listing(), tempfile.mkdtemp(prefix="stt_pipeline_")
    try:
        for test in (test_planted, test_no_effect, test_drift, test_tamper, test_weak_gates, test_path_with_spaces):
            test(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert listing() == before, "a command left a file in the skill folder"


if __name__ == "__main__":
    main()
    print("test_pipeline.py: all assertions passed")
