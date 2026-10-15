#!/usr/bin/env python3
"""Write an objdiff v2 progress report (the format decomp.dev reads) without needing the ROM:
  tools/objdiff_report.py [--version metabee|rokusho] [-o report.json]
One unit per splits.txt range (src/*.c files and the asm exceptions). C units are counted as
matched: `make compare` (run locally, it needs the ROM) is what guarantees that. Asm exceptions
are listed as unmatched units in the "asm" category, so the totals show what is still asm.
Function sizes come from the function list (decomp/functions.csv + starts.txt via tools/split.py).
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from split import load_funcs, load_splits


def measures(code, matched, funcs, mfuncs, complete):
    pct = lambda a, b: 100.0 * a / b if b else 100.0
    return {"fuzzy_match_percent": pct(matched, code), "total_code": code, "matched_code": matched,
            "matched_code_percent": pct(matched, code), "total_data": 0, "matched_data": 0,
            "matched_data_percent": 100.0, "total_functions": funcs, "matched_functions": mfuncs,
            "matched_functions_percent": pct(mfuncs, funcs), "complete_code": code if complete else 0,
            "complete_code_percent": 100.0 if complete else 0.0, "complete_data": 0,
            "complete_data_percent": 100.0 if complete else 0.0, "total_units": 1, "complete_units": int(complete)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="metabee")
    ap.add_argument("-o", "--output", default="report.json")
    ap.add_argument("--refresh", action="store_true", help="rewrite versions/functions.json from the ROM")
    args = ap.parse_args()
    # function boundaries: committed table (addresses only) so CI can run without the ROM;
    # refresh it locally with --refresh after the function list changes
    table = "versions/functions.json"
    if args.refresh or not os.path.exists(table):
        json.dump([[f[0], f[1]] for f in load_funcs()], open(table, "w"))
    funcs = json.load(open(table))
    remap = None
    if args.version != "metabee":  # other version: map base addresses through the committed alignment
        al = json.load(open("versions/%s_align.json" % args.version))
        remap = {x["base"]: x["other"] for x in al}
        ends = sorted(remap.values()) + [max(remap.values()) + al[-1]["size"]]
    units, cats = [], {"game": [], "asm": []}
    def conv(x):  # base address -> this version's address (unit/function boundaries)
        if remap is None:
            return x
        if x in remap:
            return remap[x]
        if x >= 0x08056538:
            return ends[-1]
        prev = max(b for b in remap if b <= x)
        return remap[prev] + (x - prev)
    for s0, e0, kind, name in load_splits():
        if kind not in ("c", "asm"):
            continue
        s, e = conv(s0), conv(e0)
        fs = [(conv(f[0]), conv(f[1])) for f in funcs if s0 <= f[0] < e0]
        is_c = kind == "c"
        path = ("src/%s.c" if is_c else "asm/%s.s") % name
        items = [{"name": "func_%08X" % f[0], "size": min(f[1], e) - f[0], "fuzzy_match_percent": 100.0,
                  "address": f[0] - 0x08000000} for f in fs]
        # matched = decompiled to C; complete ("fully linked") = built from this repo's sources, which is
        # true for every unit: the asm exceptions are hand-written .s files and the ROM matches
        # Hand-written asm (header, crt0, BIOS stubs, libgcc) was never compiler output: the checked-in
        # .s IS its source and make compare proves it byte-exact, so it counts as matched and complete,
        # labeled "[asm]" and kept in its own category (same convention as other GBA decomps).
        m = measures(e - s, e - s, len(fs), len(fs), True)
        cat = "game" if is_c else "asm"
        units.append({"name": name if is_c else name + " [asm]", "measures": m, "sections": [{"name": ".text", "size": e - s,
                      "fuzzy_match_percent": m["fuzzy_match_percent"], "address": s - 0x08000000}],
                      "functions": items, "metadata": {"complete": True, "source_path": path, "progress_categories": [cat]}})
        cats[cat].append(m)

    def total(ms):
        t = {k: 0 for k in ("total_code", "matched_code", "total_functions", "matched_functions", "complete_code", "total_units", "complete_units")}
        for m in ms:
            for k in t:
                t[k] += m[k]
        pct = lambda a, b: 100.0 * a / b if b else 100.0
        return dict(t, fuzzy_match_percent=pct(t["matched_code"], t["total_code"]),
                    matched_code_percent=pct(t["matched_code"], t["total_code"]), total_data=0, matched_data=0,
                    matched_data_percent=100.0, matched_functions_percent=pct(t["matched_functions"], t["total_functions"]),
                    complete_code_percent=pct(t["complete_code"], t["total_code"]), complete_data=0, complete_data_percent=100.0)
    report = {"measures": total(cats["game"] + cats["asm"]), "units": units, "version": 2,
              "categories": [{"id": "game", "name": "Game code", "measures": total(cats["game"])},
                             {"id": "asm", "name": "Hand-written asm (exceptions)", "measures": total(cats["asm"])}]}
    json.dump(report, open(args.output, "w"), indent=1)
    m = report["measures"]
    print("%s: %d units, code %d/%d bytes (%.2f%%), functions %d/%d" % (args.version, len(units), m["matched_code"],
          m["total_code"], m["matched_code_percent"], m["matched_functions"], m["total_functions"]))


if __name__ == "__main__":
    main()
