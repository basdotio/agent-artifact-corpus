#!/usr/bin/env python3
"""Split naming work by owner, for workflows/name-symbols.js:
  tools/ownership.py CHUNKS.json OUT.json
CHUNKS.json: [["08000258","08009604"], ["08009604","08015A70"], ...] (the same address chunks as
the workflow's `chunks` arg). Writes {"0": {"functions": [...], "globals": [...]}, "1": ...}:
each still-unnamed function (sub_XXXXXXXX defined in src/) belongs to the chunk holding its file;
each unnamed global (gUnk_XXXXXXXX) belongs to the chunk whose files use it most.
"""
import collections, glob, json, re, sys
sys.path.insert(0, "tools")
from split import load_splits

chunks = [(int(s, 16), int(e, 16)) for s, e in json.load(open(sys.argv[1]))]
chunk_of = lambda a: next(i for i, (s, e) in enumerate(chunks) if s <= a < e)
file_chunk = {n: chunk_of(s) for s, e, k, n in load_splits() if k == "c"}
funcs, uses = collections.defaultdict(set), collections.defaultdict(collections.Counter)
for f in glob.glob("src/*.c"):
    c, t = file_chunk[f[4:-2]], open(f).read()
    for m in re.finditer(r"^[\w\s\*]+?\b(sub_[0-9A-F]{8})\s*\([^;{]*\)\s*\n\{", t, re.M):
        funcs[c].add(m.group(1))
    for g in re.findall(r"\bgUnk_[0-9A-Fa-f]{8}\b", t):
        uses[g][c] += 1
own = collections.defaultdict(set)
for g, c in uses.items():
    own[max(c, key=c.get)].add(g)
out = {str(i): {"functions": sorted(funcs[i]), "globals": sorted(own[i])} for i in range(len(chunks))}
json.dump(out, open(sys.argv[2], "w"), indent=1)
for i in range(len(chunks)):
    print("chunk %d: %d functions, %d globals" % (i, len(funcs[i]), len(own[i])))
