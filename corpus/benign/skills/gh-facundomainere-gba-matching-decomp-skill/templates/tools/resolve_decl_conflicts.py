#!/usr/bin/env python3
"""Resolve diff3-style merge conflicts between header-unification branches
(git -c merge.conflictStyle=diff3 merge ...). Per hunk: start from the base lines, drop every
base line that either side deleted, then add each side's new lines (HEAD's #includes go after
theirs' includes, other additions keep their side's order). Hunks where BOTH sides changed the
same non-declaration line are left as conflicts. Prints the files left unresolved.
  tools/resolve_decl_conflicts.py FILE...
"""
import difflib, re, sys

DECL = re.compile(r"^\s*(#include|extern\b|struct\b|union\b|typedef\b|\}\s*(\w+\s*)?;?\s*$|$|(volatile\s+)?(u8|s8|u16|s16|u32|s32|vu16|vu32|int|void|const)\b)")


def resolve(ours, base, theirs):
    """Line-position 3-way merge: a base line survives only if both sides kept it; each side's
    insertions are placed before the base line they precede (HEAD's first)."""
    def side(x):
        kept, ins = set(), {}
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base, x, autojunk=False).get_opcodes():
            if op == "equal":
                kept.update(range(i1, i2))
            if op in ("insert", "replace"):
                ins.setdefault(i1, []).extend(x[j1:j2])
        return kept, ins
    ko, io = side(ours); kt, it = side(theirs)
    code_o = [l for v in io.values() for l in v if not DECL.match(l)]
    code_t = [l for v in it.values() for l in v if not DECL.match(l)]
    gone = [base[i] for i in range(len(base)) if (i not in ko) and (i not in kt) and not DECL.match(base[i])]
    if code_o and code_t and gone:
        return None  # both sides rewrote the same code
    out = []
    for i in range(len(base) + 1):
        out += io.get(i, []) + [l for l in it.get(i, []) if l not in io.get(i, [])]
        if i < len(base) and i in ko and i in kt:
            out.append(base[i])
    return out


for path in sys.argv[1:]:
    lines, out, ok, i = open(path).read().split("\n"), [], True, 0
    while i < len(lines):
        if not lines[i].startswith("<<<<<<< "):
            out.append(lines[i]); i += 1; continue
        b = next(n for n in range(i, len(lines)) if lines[n].startswith("||||||| "))
        m = lines.index("=======", b)
        e = next(n for n in range(m, len(lines)) if lines[n].startswith(">>>>>>> "))
        r = resolve(lines[i + 1:b], lines[b + 1:m], lines[m + 1:e])
        if r is None:
            ok = False; out += lines[i:e + 1]
        else:
            out += r
        i = e + 1
    open(path, "w").write("\n".join(out))
    if not ok:
        print("UNRESOLVED", path)
