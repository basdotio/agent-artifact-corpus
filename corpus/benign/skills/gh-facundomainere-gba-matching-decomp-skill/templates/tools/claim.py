#!/usr/bin/env python3
"""Claim the next function to decompile (address order). Prints "ADDR END SIZE" or nothing.
Must run under the repo lock: flock .decomp.lock tools/claim.py
Skips functions already in src/ or splits.txt asm ranges, ARM / non-4-aligned ones, and
anything in claims.txt (claimed or given up)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from split import load_funcs, load_splits

CLAIMS = "claims.txt"
taken = set()
if os.path.exists(CLAIMS):
    taken = {l.split()[0] for l in open(CLAIMS) if l.strip()}
covered = [(s, e) for s, e, _, _ in load_splits()]
for s, e, t, _ in load_funcs():
    if t != 1 or s % 4 or "%08X" % s in taken or any(a <= s < b for a, b in covered):
        continue
    open(CLAIMS, "a").write("%08X claimed\n" % s)
    print("%08X %08X %d" % (s, e, e - s))
    break
