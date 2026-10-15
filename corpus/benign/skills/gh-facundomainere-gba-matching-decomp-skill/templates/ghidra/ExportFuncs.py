# Post-script: write function list (start,end,thumb,name) as CSV for the splitter.
# @category GBA
out = getScriptArgs()[0]
tmode = currentProgram.getRegister("TMode")
ctx = currentProgram.getProgramContext()
n = 0
with open(out, "w") as f:
    f.write("start,end,thumb,name\n")
    for fn in currentProgram.getFunctionManager().getFunctions(True):
        b = fn.getBody()
        v = ctx.getValue(tmode, fn.getEntryPoint(), False)
        f.write("%s,%s,%d,%s\n" % (b.getMinAddress(), b.getMaxAddress(), 1 if v is not None and int(v) == 1 else 0, fn.getName())); n += 1
print("exported %d functions -> %s" % (n, out))
