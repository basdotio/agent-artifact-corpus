#!/usr/bin/env python3
"""Align the functions of the base ROM (build/medabots_ax.elf) with another version's ROM.
  tools/version_align.py OTHER.gba [out.json]
For each function (in address order) finds its address in OTHER by trying small shifts, comparing
bytes with bl immediates and literal-pool pointers (words 0x02/03/08/09xxxxxx) masked. Prints a
summary and writes [{name, base, other, size_base, size_other, same}] (same = normalized bytes equal).
"""
import json, struct, subprocess, sys

BASE = 0x08000000
a = open("baserom.gba", "rb").read()
b = open(sys.argv[1], "rb").read()
syms = []
for l in subprocess.run(["arm-none-eabi-nm", "-n", "build/medabots_ax.elf"], capture_output=True, text=True).stdout.splitlines():
    q = l.split()
    if len(q) == 3 and q[1] in "Tt" and 0x08000000 <= int(q[0], 16) < 0x08056538:
        if not syms or syms[-1][1] != int(q[0], 16):
            syms.append((q[2], int(q[0], 16)))
syms.append(("_end", 0x08056538))


def norm(rom, off, n):
    out = bytearray(rom[off:off + n])
    i = 0
    while i + 4 <= n:
        h1, h2 = struct.unpack_from("<HH", out, i)
        if (h1 & 0xF800) == 0xF000 and (h2 & 0xF800) == 0xF800:  # bl pair
            out[i:i + 4] = b"\xff\xf0\xff\xf8"; i += 4; continue
        i += 2
    for j in range((4 - off % 4) % 4, n - 3, 4):  # aligned words
        w = struct.unpack_from("<I", out, j)[0]
        if (w >> 24) in (2, 3, 8, 9):
            out[j:j + 4] = b"\0\0\0\x80"
    return bytes(out)


res, delta = [], 0
for k in range(len(syms) - 1):
    name, s = syms[k]
    n = syms[k + 1][1] - s
    off = s - BASE
    best = None
    for d in sorted(range(-0x800, 0x2000, 2), key=lambda d: abs(d - delta)):
        o = off + d
        if o < 0 or o + n > len(b):
            continue
        if norm(a, off, n) == norm(b, o, n):
            best = d; break
    if best is None:
        res.append({"name": name, "base": s, "other": None, "size": n, "same": False})
        continue
    delta = best
    res.append({"name": name, "base": s, "other": s + best, "size": n, "same": True})
# fill other-addresses of changed functions between matched neighbours
for i, r in enumerate(res):
    if r["other"] is None:
        prev = next((x for x in reversed(res[:i]) if x["other"] is not None), None)
        r["other_guess"] = prev and prev["other"] + prev["size"] + sum(x["size"] for x in res[res.index(prev) + 1:i])
same = sum(r["same"] for r in res)
print("functions %d, identical (normalized) %d, changed %d (%d bytes)" % (len(res), same, len(res) - same,
      sum(r["size"] for r in res if not r["same"])))
for r in res:
    if not r["same"]:
        print("  %-40s %08X size %d" % (r["name"], r["base"], r["size"]))
if len(sys.argv) > 2:
    json.dump(res, open(sys.argv[2], "w"), indent=0)
