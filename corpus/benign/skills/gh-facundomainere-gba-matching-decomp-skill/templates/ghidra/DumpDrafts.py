# Post-script: decompile the functions listed (one hex address per line) into <outdir>/<ADDR>.c
# Usage: -postScript DumpDrafts.py <addrfile> <outdir>
# @category GBA
from ghidra.app.decompiler import DecompInterface
import os
args = getScriptArgs()
addrs = [l.strip() for l in open(args[0]) if l.strip()]
out = args[1]
d = DecompInterface(); d.openProgram(currentProgram)
fm = currentProgram.getFunctionManager()
ok = 0
for a in addrs:
    fn = fm.getFunctionAt(toAddr(int(a, 16)))
    if fn is None:
        fn = fm.getFunctionContaining(toAddr(int(a, 16)))
    if fn is None:
        continue
    r = d.decompileFunction(fn, 30, monitor)
    if r.decompileCompleted():
        f = open(os.path.join(out, a + ".c"), "w")
        f.write("// Ghidra draft for sub_%s (rough: types, structs and boundaries are unreliable)\n" % a)
        f.write(r.getDecompiledFunction().getC())
        f.close(); ok += 1
print("drafts written: %d of %d" % (ok, len(addrs)))
