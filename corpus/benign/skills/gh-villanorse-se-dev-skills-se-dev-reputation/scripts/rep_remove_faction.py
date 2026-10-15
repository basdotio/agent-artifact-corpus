"""Remove NPC factions (by tag) from a world's Sandbox.sbc.

python rep_remove_faction.py <world folder> --tags SPRT[,FCTM,...] [--apply]

Dry run by default. With --apply, a timestamped backup of Sandbox.sbc is written first.
The game must be CLOSED (it rewrites Sandbox.sbc on save/exit).

Removes, per faction: the <MyObjectBuilder_Faction> block, identity->faction map items that point
at it, faction<->faction relations, player reputation entries, faction requests, and the faction's
own bank account. Identities are kept (harmless; PirateAntennas references the pirate identity).
The result is re-parsed as XML before writing.
"""
import argparse
import datetime
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET


def remove(s, element, pred):
    pat = re.compile(r"[ \t]*<" + element + r"(?:\s[^>]*)?>.*?</" + element + r">[ \t]*\r?\n", re.S)
    out, pos, n = [], 0, 0
    for m in pat.finditer(s):
        if pred(m.group(0)):
            out.append(s[pos:m.start()]); pos = m.end(); n += 1
    out.append(s[pos:])
    return "".join(out), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("world")
    ap.add_argument("--tags", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    path = os.path.join(a.world, "Sandbox.sbc")
    raw = open(path, "rb").read()
    s = raw.decode("utf-8")
    total = 0
    for t in a.tags.split(","):
        m = re.search(r"<MyObjectBuilder_Faction>\s*<FactionId>(\d+)</FactionId>\s*<Tag>" + re.escape(t) + r"</Tag>", s)
        if not m:
            print("%s: not in save" % t)
            continue
        fid = m.group(1)
        ref = re.compile(r">" + fid + r"<")
        steps = [
            ("faction block", "MyObjectBuilder_Faction", lambda b: re.search(r"<FactionId>" + fid + r"</FactionId>\s*<Tag>", b)),
            ("identity->faction map items", "item", lambda b: re.fullmatch(r"\s*<item>\s*<Key>\d+</Key>\s*<Value>" + fid + r"</Value>\s*</item>\s*", b)),
            ("faction relations", "MyObjectBuilder_FactionRelation", ref.search),
            ("player reputation entries", "MyObjectBuilder_PlayerFactionRelation", ref.search),
            ("faction requests", "MyObjectBuilder_FactionRequests", ref.search),
            ("bank account", "MyObjectBuilder_AccountEntry", lambda b: re.search(r"<OwnerIdentifier>" + fid + r"</OwnerIdentifier>", b)),
        ]
        print("%s: faction id %s" % (t, fid))
        for label, el, pred in steps:
            s, n = remove(s, el, lambda b, p=pred: p(b) is not None)
            total += n
            print("  %-28s %d" % (label, n))
        left = len(ref.findall(s))
        print("  remaining references         %d%s" % (left, "  <- inspect manually" if left else ""))
    if not total:
        return
    try:
        ET.fromstring(s.encode("utf-8"))
    except ET.ParseError as e:
        sys.exit("result is not valid XML (%s); nothing written" % e)
    if not a.apply:
        print("dry run: %d elements would be removed; rerun with --apply" % total)
        return
    bak = path + ".bak-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(path, bak)
    with open(path, "wb") as f:
        f.write(s.encode("utf-8"))
    print("wrote %s (backup %s)" % (path, bak))


if __name__ == "__main__":
    main()
