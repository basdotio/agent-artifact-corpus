import hashlib
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Dafny")

@mcp.tool()
def dafny_verifier(code: str) -> str:
    """Verify a Dafny code."""
    t = 2 # timeout
    v = code

    TMP_DIR = '/tmp/dafny/'
    
    if t is None:
        t = 10
    key = hashlib.md5(v.encode('utf-8')).hexdigest()
    dir = "%s%s/" % (TMP_DIR, key)
    if not os.path.exists(dir):
        os.makedirs(dir)
    os.chdir(dir)

    fn = 'ex.dfy'
    outfn = 'out.txt'
    errfn = 'err.txt'

    f = open(fn, 'w')
    f.write(v)
    f.close()
    
    status = os.system("dafny verify %s --verification-time-limit %s >%s 2>%s" % (fn, t, outfn, errfn))
    f = open(outfn, 'r')
    outlog = f.read()
    f.close()

    f = open(errfn, 'r')
    log = f.read()
    f.close()

    r = {'status': status, 'log': log, 'out': outlog[:1000]}
    return r['out']
