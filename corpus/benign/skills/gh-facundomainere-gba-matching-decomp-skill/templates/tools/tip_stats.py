#!/usr/bin/env python3
"""Usefulness of docs/matching_tips.md entries.

  tools/tip_stats.py              # report; flags purge candidates
  tools/tip_stats.py tally F.json # (used by post_run.py) add one run's function results

Per tip: exposure = functions attempted while the tip was in the file, tried = reported as
applied at some point, helped = present in final code that MATCHED (committed).
Purge candidate: exposure >= 400 and helped == 0, or tried >= 10 and helped/tried < 10%.
"""
import json, os, re, sys

STATS = os.path.join(os.path.dirname(__file__), "tip_stats.json")
TIPS = "docs/matching_tips.md"


def tip_ids():
    """Active tip IDs (anything under "## Retired" is excluded)."""
    if not os.path.exists(TIPS):
        return []
    return re.findall(r"^- \[(T\d+)\]", open(TIPS).read().split("## Retired")[0], re.M)


def load():
    return json.load(open(STATS)) if os.path.exists(STATS) else {}


def tally(fns):
    if not any("tips_tried" in f for f in fns):
        return  # run predates tip reporting: don't count exposure without usage data
    st, ids = load(), tip_ids()
    for t in ids:
        st.setdefault(t, {"exposure": 0, "tried": 0, "helped": 0})["exposure"] += len(fns)
    for f in fns:
        for t in set(f.get("tips_tried") or []) & set(ids):
            st[t]["tried"] += 1
        if f.get("committed"):
            for t in set(f.get("tips_helped") or []) & set(ids):
                st[t]["helped"] += 1
    json.dump(st, open(STATS, "w"), indent=1, sort_keys=True)


def kept():
    """Tips reviewed and deliberately kept: their line contains "(keep: reason)"."""
    return set(re.findall(r"^- \[(T\d+)\].*\(keep:", open(TIPS).read(), re.M)) if os.path.exists(TIPS) else set()


def purge_candidates(st):
    k, active = kept(), set(tip_ids())
    return [t for t, c in st.items() if t in active and t not in k and ((c["exposure"] >= 400 and c["helped"] == 0)
            or (c["tried"] >= 10 and c["helped"] / c["tried"] < 0.10))]


def report():
    st, ids = load(), tip_ids()
    print("%-5s %8s %6s %7s" % ("tip", "exposure", "tried", "helped"))
    for t in ids:
        c = st.get(t, {"exposure": 0, "tried": 0, "helped": 0})
        print("%-5s %8d %6d %7d" % (t, c["exposure"], c["tried"], c["helped"]))
    print("purge candidates:", [t for t in purge_candidates(st) if t in ids] or "none")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "tally":
        tally(json.load(open(sys.argv[2])))
    else:
        report()
