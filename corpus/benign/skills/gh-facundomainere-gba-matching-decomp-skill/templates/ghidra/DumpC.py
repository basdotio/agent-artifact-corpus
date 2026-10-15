# Post-script: decompile every function into one .c file.
# @category GBA
from ghidra.app.decompiler import DecompInterface
import os
out = getScriptArgs()[0]
d = DecompInterface(); d.openProgram(currentProgram)
fm = currentProgram.getFunctionManager()
ok = bad = 0
with open(out, "w") as f:
    for fn in fm.getFunctions(True):
        r = d.decompileFunction(fn, 60, monitor)
        if r.decompileCompleted():
            f.write("// %s\n%s\n" % (fn.getEntryPoint(), r.getDecompiledFunction().getC())); ok += 1
        else:
            f.write("// %s FAILED: %s\n\n" % (fn.getEntryPoint(), r.getErrorMessage())); bad += 1
print("decompiled %d, failed %d -> %s" % (ok, bad, out))
