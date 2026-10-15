#!/usr/bin/env python3
"""Integrate decompiled functions: tools/add_funcs.py results.json

results.json: [{"addr": "XXXXXXXX", "matched": true, "c_code": "...", "name": "..."}, ...]
Each claimed match is re-checked with tools/check_func.py (inline asm is rejected). Runs of
consecutive matched functions go into one src/code_<first addr>.c, appended to an existing
file when it ends right where the run starts. Then the split is regenerated and `make compare`
must pass; on any failure every touched file is restored.
"""
import json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from split import load_funcs, load_splits

TRACKED = ["splits.txt", "ld_script.ld", "objects.mk"]


def check(code, addr, end=None):
    if re.search(r"\basm\b|__asm|naked", code):
        return False
    with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False) as f:
        f.write(code)
    try:
        env = dict(os.environ, END=end) if end else None
        r = subprocess.run(["python3", "tools/check_func.py", f.name, addr], capture_output=True, text=True, env=env)
        return r.stdout.startswith("MATCH")
    finally:
        os.unlink(f.name)


def compiles(code):
    pp = subprocess.run(["arm-none-eabi-cpp", "-nostdinc", "-I", "include", "-I", "tools/agbcc/include", "-"],
                        input=code, capture_output=True, text=True)
    cc = subprocess.run(["tools/agbcc/bin/agbcc", "-mthumb-interwork", "-O2", "-fhex-asm", "-fprologue-bugfix", "-o", "/dev/null"],
                        input=pp.stdout, capture_output=True, text=True)
    return pp.returncode == 0 and cc.returncode == 0 and "error" not in cc.stderr


def merge(codes):
    """Concatenate function files, dropping repeated include/extern/typedef lines."""
    seen, out = set(), []
    for c in codes:
        for line in c.strip().splitlines() + [""]:
            key = line.strip()
            if key and line == line.lstrip() and (key.startswith("#include") or key.startswith("extern") or re.match(r"^[\w\s\*]+\([^)]*\);$", key)):
                if key in seen:
                    continue
                seen.add(key)
            out.append(line)
    return "\n".join(out).rstrip() + "\n"


def main(path):
    funcs = {f[0]: f for f in load_funcs()}
    res = [r for r in json.load(open(path)) if r.get("matched")]
    good = sorted((int(r["addr"], 16), r) for r in res if check(r["c_code"], r["addr"], r.get("end")))
    print("verified %d/%d claimed matches" % (len(good), len(res)))
    if not good:
        return 1
    splits = load_splits()
    ends = {e: (s, n) for s, e, k, n in splits if k == "c"}
    runs = []  # [start, end, [codes]]
    for a, r in good:
        f = funcs[a]
        fe = int(r["end"], 16) if r.get("end") else f[1]  # "end": one C file spanning several functions
        if runs and runs[-1][1] == a and not r.get("end"):
            runs[-1][1] = fe; runs[-1][2].append(r["c_code"])
        else:
            runs.append([a, fe, [r["c_code"]]])
    # ponytail: functions whose guessed declarations conflict go in separate files; a
    # header-consolidation pass (include/*.h) merges them into subsystem files later.
    split_runs = []
    for s, e, codes in runs:
        prev = ends.get(s)
        alone_ok = len(codes) == 1 or compiles(merge(codes))
        if alone_ok and not (prev and not compiles(merge([open("src/%s.c" % prev[1]).read()] + codes))):
            split_runs.append([s, e, codes, False])
            continue
        for a, r in good:
            if s <= a < e:
                split_runs.append([a, int(r["end"], 16) if r.get("end") else funcs[a][1], [r["c_code"]], True])
    runs = split_runs
    backup = tempfile.mkdtemp()
    touched = list(TRACKED)
    for t in TRACKED:
        if os.path.exists(t):
            shutil.copy(t, backup)
    srcs, srcs_names = {}, []
    # compiler flavour of this integration (old_agbcc / -O1 / default); never extend a file built differently
    opt = os.environ.get("OPT", "")
    # -fprologue-bugfix is global and old_agbcc output equals it, so only -O1 / no-interwork remain
    flav = "o1" if "-O1" in opt else ("noiw" if "-mno-thumb-interwork" in opt else "")
    file_flav = {}
    if os.path.exists("splits.txt"):
        for l in open("splits.txt"):
            q = l.split()
            if len(q) >= 4 and q[2] == "c":
                file_flav[q[3]] = q[4] if len(q) >= 5 else ""
    for s, e, codes, standalone in runs:
        prev = None if standalone else ends.get(s)
        if prev and file_flav.get(prev[1], "") != flav:
            prev = None
        if prev:  # extend the file that ends where this run starts
            ps, name = prev
            splits = [x for x in splits if x[0] != ps]
            s, old = ps, open("src/%s.c" % name).read()
            codes = [old] + codes
        else:
            name = "code_%08X" % s
        srcs["src/%s.c" % name] = merge(codes)
        srcs_names.append(name)
        splits.append((s, e, "c", name))
        ends[e] = (s, name)
    for p in srcs:
        if os.path.exists(p):
            shutil.copy(p, os.path.join(backup, os.path.basename(p)))
        touched.append(p)
        open(p, "w").write(srcs[p])
    for n in srcs_names:
        file_flav[n] = flav
    tag = lambda n: " " + file_flav[n] if file_flav.get(n) else ""
    open("splits.txt", "w").write("".join("%08X %08X %s %s%s\n" % (x + (tag(x[3]),)) for x in sorted(splits)))
    ok = subprocess.run(["python3", "tools/split.py"]).returncode == 0 and \
        subprocess.run(["make", "-s", "-j%d" % os.cpu_count(), "compare"]).returncode == 0
    if not ok and not os.environ.get("KEEP"):
        print("make compare FAILED: restoring")
        for p in touched:
            b = os.path.join(backup, os.path.basename(p))
            if os.path.exists(b):
                shutil.copy(b, p)
            elif os.path.exists(p):
                os.remove(p)
        subprocess.run(["python3", "tools/split.py"])
        return 1
    print("added %d functions in %d files; make compare OK" % (len(good), len(srcs)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
