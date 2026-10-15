#!/usr/bin/env python3
"""Replace local prototypes of functions defined in other subsystems with #include "<subsys>.h",
when the local declaration has the same types as the header's prototype. Each changed file must
still compile; otherwise it is restored. Run make compare afterwards.
  tools/use_headers.py [src/file.c ...]
"""
import glob, os, re, subprocess, sys

KW = {"u8", "u16", "u32", "s8", "s16", "s32", "int", "void", "char", "short", "long", "unsigned", "signed",
      "const", "volatile", "struct", "union", "vu16", "vu32", "bool8", "*"}
PROTO = re.compile(r"^(?:extern\s+)?((?:const\s+)?[\w\s\*]+?)\b(\w+)\s*\(([^;{}]*)\)\s*;\s*$")


def sig(ret, args):
    def norm(p):
        t = re.findall(r"\w+|\*", p)
        if len(t) > 1 and t[-1] not in KW and not (len(t) >= 2 and t[-2] in ("struct", "union")):
            t = t[:-1]  # drop the parameter name
        return " ".join(t)
    a = re.sub(r"\s+", " ", args).strip()
    return (" ".join(re.findall(r"\w+|\*", ret)), ("void",) if a in ("", "void") else tuple(norm(p) for p in a.split(",")))


def header_protos():
    hp = {}
    for h in glob.glob("include/*.h"):
        for line in open(h):
            m = PROTO.match(line.strip())
            if m and not line.lstrip().startswith(("typedef", "#", "return")):
                hp.setdefault(m.group(2), (os.path.basename(h), sig(m.group(1), m.group(3))))
    return hp


def compiles(path):
    pp = subprocess.run(["arm-none-eabi-cpp", "-nostdinc", "-I", "include", "-I", "tools/agbcc/include", path],
                        capture_output=True, text=True)
    cc = subprocess.run(["tools/agbcc/bin/agbcc", "-mthumb-interwork", "-O2", "-fhex-asm", "-fprologue-bugfix",
                         "-o", "/dev/null"], input=pp.stdout, capture_output=True, text=True)
    return pp.returncode == 0 and cc.returncode == 0 and "error" not in cc.stderr


def main(files):
    hp = header_protos()
    removed = kept = 0
    for f in files:
        own = os.path.basename(f)[:-2].removesuffix("_2") + ".h"
        text = open(f).read()
        lines, out, need = text.split("\n"), [], set()
        for line in lines:
            m = PROTO.match(line.strip()) if not line.startswith((" ", "\t")) else None
            if m and m.group(2) in hp and hp[m.group(2)][0] != own and sig(m.group(1), m.group(3)) == hp[m.group(2)][1]:
                need.add(hp[m.group(2)][0]); removed += 1
                continue
            out.append(line)
        if not need:
            continue
        inc = ['#include "%s"' % h for h in sorted(need) if '#include "%s"' % h not in text]
        pos = max(i for i, l in enumerate(out) if l.startswith("#include")) + 1
        new = "\n".join(out[:pos] + inc + out[pos:])
        open(f, "w").write(new)
        if not compiles(f):
            open(f, "w").write(text); kept += len(need)
            print("restored", f)
    print("removed %d local prototypes" % removed)


if __name__ == "__main__":
    main(sys.argv[1:] or sorted(glob.glob("src/*.c")))
