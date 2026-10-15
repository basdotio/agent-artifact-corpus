#!/usr/bin/env python3
"""Claim a near-miss to retry (largest first). Run under the lock: flock .decomp.lock tools/retry_claim.py
Near-miss = claimed in claims.txt but not in src/. Each retry is recorded in claims.txt as
"ADDR retry<N>"; a function is retried at most MAX times. Prints "ADDR END SIZE" or nothing."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from split import load_funcs, load_splits

MAX = 25  # raised step by step for the last near-misses
lines = open("claims.txt").read().splitlines()
# only claims that existed when the retry run started (.retry_cutoff = line count then), so a
# function a fresh agent claimed during the same run is never taken over
cutoff = int(open(".retry_cutoff").read()) if os.path.exists(".retry_cutoff") else len(lines)
state, idx = {}, {}
for i, l in enumerate(lines):
    p = l.split()
    if len(p) >= 2 and i < cutoff:
        state[p[0]] = p[1]; idx[p[0]] = i
covered = [(s, e) for s, e, _, _ in load_splits()]
taken = set(open(".retry_taken").read().split()) if os.path.exists(".retry_taken") else set()
cands = []
for s, e, t, _ in load_funcs():
    a = "%08X" % s
    st = state.get(a, "")
    if t != 1 or s % 4 or any(x <= s < y for x, y in covered):
        continue
    m = re.match(r"retry(\d+)$", st)
    n = int(m.group(1)) if m else (0 if st == "claimed" else None)
    if n is None or n >= MAX or a in taken:
        continue
    cands.append((-(e - s), s, e, n))
if cands:
    _, s, e, n = sorted(cands)[0]
    a = "%08X" % s
    lines[idx[a]] = "%s retry%d" % (a, n + 1)  # in place, keeps line indices (cutoff) valid
    open("claims.txt", "w").write("\n".join(lines) + "\n")
    open(".retry_taken", "a").write(a + "\n")
    print("%s %08X %d" % (a, e, e - s))
