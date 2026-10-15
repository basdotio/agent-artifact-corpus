#!/usr/bin/env python3
"""Token-level 3-way merge of diff3 conflict hunks left by tools/resolve_decl_conflicts.py:
  tools/tokmerge.py FILE...  (each line is split into identifier/punctuation tokens, so edits
  to different globals on one line merge cleanly). Prints files it could not resolve."""
# Token-level 3-way merge of remaining diff3 conflict hunks via git merge-file.
import ast, re, sys, subprocess, tempfile, os
TOK = re.compile(r"[A-Za-z_]\w*|0[xX][0-9a-fA-F]+|\d+|\s+|.", re.S)
def tok(lines):
    return [repr(t) for t in TOK.findall("\n".join(lines))]
def merge(o, b, t):
    d = tempfile.mkdtemp(); ps = []
    for n, x in (("o", o), ("b", b), ("t", t)):
        p = os.path.join(d, n); open(p, "w").write("\n".join(tok(x)) + "\n"); ps.append(p)
    r = subprocess.run(["git", "merge-file", "-p", *ps], capture_output=True, text=True)
    if r.returncode != 0: return None
    return "".join(ast.literal_eval(l) for l in r.stdout.splitlines()).split("\n")
for path in sys.argv[1:]:
    lines, out, ok, i = open(path).read().split("\n"), [], True, 0
    while i < len(lines):
        if not lines[i].startswith("<<<<<<< "):
            out.append(lines[i]); i += 1; continue
        b = next(n for n in range(i, len(lines)) if lines[n].startswith("||||||| "))
        m = lines.index("=======", b)
        e = next(n for n in range(m, len(lines)) if lines[n].startswith(">>>>>>> "))
        r = merge(lines[i+1:b], lines[b+1:m], lines[m+1:e])
        if r is None: ok = False; out += lines[i:e+1]
        else: out += r
        i = e + 1
    open(path, "w").write("\n".join(out))
    print(("OK " if ok else "STILL ") + path)
