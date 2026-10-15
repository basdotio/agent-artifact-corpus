#!/usr/bin/env python3
"""Run decomp-permuter on a near-miss: tools/permute.py ADDR file.c [seconds] [--old]

Builds permuter/ADDR/ (base.c, target.o from ROM bytes with symbolic bl/pool words, compile.sh), runs the
permuter for the given time (default 600s), and prints the best score. Score 0 = match;
the winning source is saved in permuter/ADDR/output-*/source.c.
"""
import os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from split import load_funcs, BASE

addr, cfile = sys.argv[1].upper(), sys.argv[2]
secs = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 600
old = "--old" in sys.argv
d = os.path.join("permuter", addr)
shutil.rmtree(d, ignore_errors=True); os.makedirs(d)

# target.s from ROM bytes: .inst.n per halfword, symbolic bl, and pool words as symbol
# references wherever the compiled base has an ABS32 reloc whose name matches the ROM value
f = next((f for f in load_funcs() if f[0] == int(addr, 16)), None)
if not f:
    sys.exit("no function starts at %s" % addr)
s0, e0 = f[0], f[1]
cc = os.path.abspath("tools/agbcc/bin/" + ("old_agbcc" if old else "agbcc"))
bo = os.path.join(d, "base_probe.o")
subprocess.run(["sh", "-c", 'CC1=%s tools/permuter_compile.sh "$0" -o "$1"' % cc, cfile, bo], check=True)
relocs = {}
for line in subprocess.run(["arm-none-eabi-objdump", "-r", bo], capture_output=True, text=True).stdout.splitlines():
    m = re.match(r"([0-9a-f]{8}) R_ARM_ABS32\s+(\S+)", line)
    if m:
        relocs[int(m.group(1), 16)] = m.group(2)
from split import rom
w = lambda o: int.from_bytes(rom[s0 - BASE + o:s0 - BASE + o + 2], "little")
lines = ["\t.syntax unified", "\t.text", "\t.thumb", "\t.global sub_%s" % addr, "\t.thumb_func", "sub_%s:" % addr]
o = 0
while s0 + o < e0:
    v32 = int.from_bytes(rom[s0 - BASE + o:s0 - BASE + o + 4], "little")
    name = relocs.get(o)
    if name and re.search(r"_([0-9A-Fa-f]{8})$", name) and int(name[-8:], 16) | (1 if name.startswith("sub_") else 0) == v32:
        lines.append("\t.4byte %s" % name); o += 4; continue
    h1, h2 = w(o), w(o + 2) if s0 + o + 2 < e0 else 0
    if h1 & 0xF800 == 0xF000 and h2 & 0xF800 == 0xF800:
        off = ((h1 & 0x7FF) << 12) | ((h2 & 0x7FF) << 1)
        if off & 0x400000:
            off -= 0x800000
        lines.append("\tbl sub_%08X" % (s0 + o + 4 + off)); o += 4; continue
    lines.append("\t.inst.n 0x%04x" % h1); o += 2
open(os.path.join(d, "target.s"), "w").write("\n".join(lines) + "\n")
subprocess.run(["arm-none-eabi-as", "-mcpu=arm7tdmi", "-o", os.path.join(d, "target.o"),
                os.path.join(d, "target.s")], check=True)
# the permuter runs a bare cpp, so hand it base.c with our headers already expanded
open(os.path.join(d, "base.c"), "w").write(subprocess.run(
    ["arm-none-eabi-cpp", "-P", "-nostdinc", "-I", "include", "-I", "tools/agbcc/include", cfile],
    capture_output=True, text=True, check=True).stdout)
open(os.path.join(d, "compile.sh"), "w").write(
    "#!/bin/sh\nCC1=%s exec %s \"$@\"\n" % (cc, os.path.abspath("tools/permuter_compile.sh")))
os.chmod(os.path.join(d, "compile.sh"), 0o755)
open(os.path.join(d, "settings.toml"), "w").write('func_name = "sub_%s"\ncompiler_type = "gcc"\n' % addr)
py = os.path.abspath("tools/permuter-venv/bin/python")
# own process group: on timeout kill the permuter and all its worker processes
proc = subprocess.Popen([py, os.path.abspath("tools/decomp-permuter/permuter.py"), d, "-j%d" % max(1, os.cpu_count() // 2),
                         "--stop-on-zero", "--best-only"], start_new_session=True)
try:
    proc.wait(timeout=secs)
except subprocess.TimeoutExpired:
    import signal
    os.killpg(proc.pid, signal.SIGTERM)
    proc.wait()
outs = sorted(x for x in os.listdir(d) if x.startswith("output-"))
print("best outputs:", outs[:3])
