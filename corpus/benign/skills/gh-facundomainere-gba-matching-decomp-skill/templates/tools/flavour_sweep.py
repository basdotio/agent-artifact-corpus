#!/usr/bin/env python3
"""tools/flavour_sweep.py SCRATCH: re-check every saved near-miss (SCRATCH/ADDR.c) with each
compiler flavour (default, bugfix, -O1, noiw, old, old -O1) and print the ones that MATCH."""
import os, subprocess, sys
sys.path.insert(0, "tools")
from split import load_funcs, load_splits
S = sys.argv[1]
sp = [(s, e) for s, e, k, _ in load_splits() if k in ("c", "asm")]
left = [a for a, b, *_ in load_funcs() if not any(s <= a < e for s, e in sp)]
FL = [("", ""), ("", "-fprologue-bugfix"), ("", "-O1"), ("", "-mno-thumb-interwork"), ("old", ""), ("old", "-O1")]
for a in left:
    f = os.path.join(S, "%08X.c" % a)
    if not os.path.exists(f):
        continue
    for cc, opt in FL:
        env = dict(os.environ, OPT=opt)
        if cc:
            env["CC1"] = "tools/agbcc/bin/old_agbcc"
        r = subprocess.run(["python3", "tools/check_func.py", f, "%08X" % a], env=env, capture_output=True, text=True, timeout=60)
        if r.stdout.startswith("MATCH"):
            print("%08X %s %s" % (a, cc or "-", opt or "-"), flush=True)
            break
