#!/usr/bin/env python3
"""Write a linker script defining every undefined data symbol named *_XXXXXXXX at that address.
Usage: tools/syms.py out.ld obj.o...   (functions are defined in asm/ or src/, so sub_ is skipped)"""
import os, re, subprocess, sys

out, objs = sys.argv[1], sys.argv[2:]
names = set()
for o in objs:
    for line in subprocess.run(["arm-none-eabi-nm", "-u", o], capture_output=True, text=True, check=True).stdout.splitlines():
        n = line.split()[-1]
        if re.search(r"_[0-9A-Fa-f]{8}$", n) and not n.startswith("sub_"):
            names.add(n)
# renamed data symbols: symbols.txt lines "name 0xADDR"
named = {}
if os.path.exists("symbols.txt"):
    for l in open("symbols.txt"):
        q = l.split("#")[0].split()
        if len(q) >= 2:
            named[q[0]] = q[1]
open(out, "w").write("".join("%s = 0x%s;\n" % (n, n[-8:]) for n in sorted(names))
                     + "".join("%s = %s;\n" % (n, a) for n, a in sorted(named.items())))
