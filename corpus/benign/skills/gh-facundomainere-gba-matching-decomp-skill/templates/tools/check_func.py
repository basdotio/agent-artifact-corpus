#!/usr/bin/env python3
"""Check one decompiled function against the ROM without a full build.

Usage: tools/check_func.py <file.c> <XXXXXXXX>     (function start address, hex)

Compiles <file.c> with agbcc (same flags as the Makefile), links it at the function's
address, resolves any undefined symbol whose name ends in _XXXXXXXX (sub_, gUnk_, ...) to
that address, and compares with baserom.gba over the function's range (code + literal
pool). The .c file must contain only that one function (plus declarations).
Prints MATCH, or the original and compiled disassembly side by side.
"""
import json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from split import BASE, load_funcs, rom
VERSION = os.environ.get("VERSION", "")  # e.g. rokusho: check against baserom_rokusho.gba
if VERSION and VERSION != "metabee":
    rom = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "baserom_%s.gba" % VERSION), "rb").read()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CC1 = os.environ.get("CC1") or os.path.join(ROOT, "tools/agbcc/bin/agbcc")
ALIASES = {"memcpy": 0x08056440, "__divsi3": 0x080561A0, "__modsi3": 0x08056238,
           "__udivsi3": 0x08056308, "__umodsi3": 0x08056380,
           **{"_call_via_" + n: 0x08056164 + 4 * i for i, n in enumerate(
               ["r%d" % k for k in range(8)] + ["r8", "r9", "sl", "fp", "ip", "lr"])}}
if VERSION and VERSION != "metabee":
    for _l in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib", "aliases_%s.s" % VERSION)):
        _m = re.match(r"\s*\.thumb_set (\w+), (0x[0-9A-Fa-f]+)", _l)
        if _m:
            ALIASES[_m.group(1)] = int(_m.group(2), 16)  # library code moved with the version

CFLAGS = ["-mthumb-interwork", "-Wimplicit", "-Wparentheses", "-O2", "-fhex-asm", "-fprologue-bugfix"]


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("FAILED: %s\n%s%s" % (" ".join(cmd[:2]), r.stdout, r.stderr))
    return r.stdout


def disasm(path, start):
    out = run(["arm-none-eabi-objdump", "-D", "-b", "binary", "-marmv4t", "-M", "force-thumb",
               "--adjust-vma=%#x" % start, path])
    return [l.split(":", 1)[1].strip() for l in out.splitlines() if re.match(r"\s+[0-9a-f]+:", l)]


def known_symbols():
    """name -> (addr, is_func) for renamed symbols: symbols.txt (data) and the last built ELF."""
    syms = {}
    st = os.path.join(ROOT, "symbols.txt")
    if os.path.exists(st):
        for l in open(st):
            q = l.split("#")[0].split()
            if len(q) >= 2:
                syms[q[0]] = (int(q[1], 16), False)
    if VERSION and VERSION != "metabee":
        # data symbols: symbols_<v>.ld; functions: base address -> other via build/align_<v>.json
        for l in open(os.path.join(ROOT, "symbols_%s.ld" % VERSION)):
            m = re.match(r"(\w+) = (0x[0-9A-Fa-f]+);", l)
            if m:
                syms[m.group(1)] = (int(m.group(2), 16), False)
        for f in json.load(open(os.path.join(ROOT, "build", "align_%s.json" % VERSION))):
            if f.get("other"):
                syms.setdefault(f["name"], (f["other"], True))
        return syms
    elf = os.path.join(ROOT, "build", "medabots_ax.elf")
    if os.path.exists(elf):
        for l in subprocess.run(["arm-none-eabi-nm", elf], capture_output=True, text=True).stdout.splitlines():
            q = l.split()
            if len(q) == 3 and q[1] in "Tt":
                syms.setdefault(q[2], (int(q[0], 16) & ~1, True))
    return syms


def main(cfile, addr):
    start = int(addr, 16)
    f = next((f for f in load_funcs() if f[0] == start), None)
    if not f:
        sys.exit("no function starts at %08X (see sub_ labels in asm/)" % start)
    end = int(os.environ["END"], 16) if os.environ.get("END") else f[1]  # END: span several functions
    if VERSION and VERSION != "metabee":  # same function in the other version's ROM
        al = json.load(open(os.path.join(ROOT, "build", "align_%s.json" % VERSION)))
        i = next(k for k, x in enumerate(al) if x["base"] == start)
        ostart = al[i]["other"] or al[i].get("other_guess")
        nxt = next((x for x in al[i + 1:] if x["other"]), None)
        oend = nxt["other"] if nxt and not os.environ.get("END") else ostart + (end - start)
        start, end = ostart, oend
    want = rom[start - BASE:end - BASE]
    with tempfile.TemporaryDirectory() as d:
        vdef = ["-DVERSION_%s" % (VERSION or "metabee").upper()]
        pp = run(["arm-none-eabi-cpp"] + vdef + ["-nostdinc", "-I", os.path.join(ROOT, "include"),
                  "-I", os.path.join(ROOT, "tools/agbcc/include"), cfile])
        s, o, elf, b = (os.path.join(d, x) for x in ("f.s", "f.o", "f.elf", "f.bin"))
        run([CC1] + CFLAGS + os.environ.get("OPT", "").split() + ["-o", s], input=pp)
        open(s, "a").write("\t.align 2, 0\n")  # same as the Makefile
        run(["arm-none-eabi-as", "-mcpu=arm7tdmi", "-o", o, s])
        # Externals resolve to the address in their name. Functions need .thumb_set so ld
        # emits a direct bl instead of an ARM interworking veneer.
        stub = ["\t.syntax unified"]
        for line in run(["arm-none-eabi-nm", "-u", o]).splitlines():
            name = line.split()[-1]
            m = re.search(r"_([0-9A-Fa-f]{8})$", name)
            if name in ALIASES:  # library names agbcc emits itself (see lib/aliases.s)
                stub += ["\t.global %s" % name, "\t.thumb_set %s, %#x" % (name, ALIASES[name])]
                continue
            if VERSION and VERSION != "metabee":
                known = known_symbols()
                if name in known:
                    v, fn = known[name]
                elif m and name.startswith("sub_"):  # unrenamed function: map its base address
                    al = {x["base"]: x["other"] for x in json.load(open(os.path.join(ROOT, "build", "align_%s.json" % VERSION)))}
                    v, fn = al.get(int(m.group(1), 16)) or int(m.group(1), 16), True
                else:
                    sys.exit("undefined symbol %s (no %s address known)" % (name, VERSION))
                stub += ["\t.global %s" % name, "\t.%s %s, %#x" % ("thumb_set" if fn else "set", name, v)]
                continue
            if not m:
                known = known_symbols()
                if name not in known:
                    sys.exit("undefined symbol %s: name externals like sub_XXXXXXXX / gUnk_XXXXXXXX" % name)
                v, fn = known[name]
                stub += ["\t.global %s" % name, "\t.%s %s, %#x" % ("thumb_set" if fn else "set", name, v)]
                continue
            v = int(m.group(1), 16)
            fn = name.startswith("sub_")
            stub += ["\t.global %s" % name, "\t.%s %s, %#x" % ("thumb_set" if fn else "set", name, v)]
        so = os.path.join(d, "syms.o")
        open(so + ".s", "w").write("\n".join(stub) + "\n")
        run(["arm-none-eabi-as", "-mcpu=arm7tdmi", "-o", so, so + ".s"])
        run(["arm-none-eabi-ld", "-Ttext=%#x" % start, "-e", "%#x" % start, "-o", elf, o, so])
        run(["arm-none-eabi-objcopy", "-O", "binary", "-j", ".text", elf, b])
        got = open(b, "rb").read()
        if got == want:
            print("MATCH %08X (%d bytes)" % (start, len(want)))
            return 0
        w = os.path.join(d, "want.bin"); open(w, "wb").write(want)
        A, B = disasm(w, start), disasm(b, start)
        print("MISMATCH %08X: want %d bytes, got %d" % (start, len(want), len(got)))
        for i in range(max(len(A), len(B))):
            a = A[i] if i < len(A) else ""
            c = B[i] if i < len(B) else ""
            print("%s %-44s | %s" % (" " if a == c else "*", a[:44], c[:44]))
        return 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
