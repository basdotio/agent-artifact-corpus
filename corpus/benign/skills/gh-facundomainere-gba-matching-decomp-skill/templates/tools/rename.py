#!/usr/bin/env python3
"""Apply a name map: tools/rename.py map.json
map.json: [{"old": "sub_08012FA0", "new": "Ai_ChooseMoveDirection", "comment": "one line, optional"}, ...]
- Functions (old = sub_XXXXXXXX) and data symbols (old = gUnk_XXXXXXXX) are renamed with word
  boundaries in src/ include/ asm/ lib/. Data renames are recorded in symbols.txt (name address),
  which tools/syms.py and tools/check_func.py read, since the address is no longer in the name.
- A function's comment is inserted above its definition (if none is there yet).
- Refuses new names that are not C identifiers, are duplicated in the map, or already exist.
Run make compare afterwards (names never change code).
"""
import glob, json, re, sys

FILES = sorted(glob.glob("src/*.c") + glob.glob("include/*.h") + glob.glob("asm/*.s") + glob.glob("lib/*.s"))


def main(path):
    renames = json.load(open(path))
    text = {f: open(f).read() for f in FILES}
    corpus = "\n".join(text.values())
    seen, ok = set(), []
    for r in renames:
        old, new = r["old"], r["new"]
        if old == new:
            continue
        if not re.fullmatch(r"[A-Za-z_]\w*", new) or new in seen or re.search(r"\b%s\b" % re.escape(new), corpus):
            print("skip %s -> %s (invalid or name taken)" % (old, new))
            continue
        if not re.search(r"\b%s\b" % re.escape(old), corpus):
            print("skip %s (not found)" % old)
            continue
        seen.add(new)
        ok.append(r)
    if not ok:
        return
    table = {r["old"]: r["new"] for r in ok}
    pat = re.compile(r"\b(%s)\b" % "|".join(map(re.escape, table)))
    for f, t in text.items():
        n = pat.sub(lambda m: table[m.group(1)], t)
        for r in ok:
            c = (r.get("comment") or "").strip()
            if c and r["old"].startswith("sub_") and f.startswith("src/"):
                # definition: name( ... )\n{  at line start; add the comment if the line above isn't one
                m = re.search(r"^([\w \*]+\b%s\s*\([^;{}\n]*\)\s*\n\{)" % re.escape(r["new"]), n, re.M)
                if m:
                    before = n[:m.start()].rstrip("\n").split("\n")[-1].strip()
                    if not (before.endswith("*/") or before.startswith("//")):
                        n = n[:m.start()] + "/* %s */\n" % c.replace("*/", "* /") + n[m.start():]
        if n != t:
            open(f, "w").write(n)
    with open("symbols.txt", "a") as st:
        for r in ok:
            if r["old"].startswith("gUnk_"):
                st.write("%s 0x%s\n" % (r["new"], r["old"][-8:]))
    print("renamed %d symbols" % len(ok))


if __name__ == "__main__":
    main(sys.argv[1])
