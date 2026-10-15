#!/usr/bin/env python3
"""After a decomp-stream workflow run: tools/post_run.py <workflow transcript dir>

- adds every "missed start at XXXXXXXX" reported in agent notes to starts.txt and
  releases the claim of the function whose range it splits (so it gets redone),
- releases claims an agent reported as not attempted / skipped,
- records the run in the bandit stats.
Run split.py + make compare afterwards (the caller commits).
"""
import json, os, re, subprocess, sys

d = sys.argv[1]
fns = []
for line in open(os.path.join(d, "journal.jsonl")):
    e = json.loads(line)
    if e.get("type") == "result" and isinstance(e.get("result"), dict):
        fns += e["result"].get("functions", [])

starts = set()
if os.path.exists("starts.txt"):
    starts = {l.split()[0].upper() for l in open("starts.txt") if l.split()}
new, release = [], set()
for f in fns:
    notes = f.get("notes", "")
    m = re.search(r"(?:missed starts?|unlabeled (?:function )?starts?) at ((?:[0-9A-Fa-f]{8}(?:,\s*|\s+and\s+|\s*)?)+)", notes, re.I)
    if m:
        for a in re.findall(r"[0-9A-Fa-f]{8}", m.group(1)):
            if a.upper() not in starts:
                new.append((a.upper(), f["addr"]))
                starts.add(a.upper())
        if not f.get("committed"):
            release.add(f["addr"])
    b = re.search(r"bogus starts? (?:at|inside it at) ((?:[0-9A-Fa-f]{8}(?:,\s*|\s+and\s+|\s*)?)+)", notes, re.I)
    if b:
        known = open("ignore_starts.txt").read() if os.path.exists("ignore_starts.txt") else ""
        with open("ignore_starts.txt", "a") as ig:
            for a in re.findall(r"[0-9A-Fa-f]{8}", b.group(1)):
                if a.upper() not in known:
                    ig.write("%s  # reported bogus start in sub_%s\n" % (a.upper(), f["addr"]))
        release.add(f["addr"])
    if not f.get("committed") and re.search(r"not attempted|skipped|too large|too complex", notes, re.I):
        release.add(f["addr"])

# agent-reported tips -> docs/matching_tips.md (exact-duplicate lines skipped)
tips_path = "docs/matching_tips.md"
tips_text = open(tips_path).read() if os.path.exists(tips_path) else ""
new_tips = []
for f in fns:
    t = (f.get("tip") or "").strip().lstrip("- ").strip()
    if t and t not in tips_text and t not in new_tips:
        new_tips.append(t)
if new_tips:
    if "## Reported by agents" not in tips_text:
        tips_text += "\n## Reported by agents (curate into the sections above)\n"
    # next id = highest T-number anywhere (incl. "(merges ...)" notes and Retired), never reused
    nid = max([int(x) for x in re.findall(r"\bT(\d+)\b", tips_text)] or [0])
    for t in new_tips:
        nid += 1
        src = next(f["addr"] for f in fns if (f.get("tip") or "").strip().lstrip("- ").strip() == t)
        tips_text += "- [T%02d] %s (from sub_%s)\n" % (nid, t, src)
    open(tips_path, "w").write(tips_text)
print("new tips:", len(new_tips))
pending = tips_text.split("## Reported by agents")[1].count("\n- [T") if "## Reported by agents" in tips_text else 0
if pending > 10:
    print("CURATION DUE: %d unclassified agent tips in docs/matching_tips.md" % pending)

with open("starts.txt", "a") as out:
    for a, parent in new:
        out.write("%s  # reported missed start in sub_%s range\n" % (a, parent))
lines = open("claims.txt").read().splitlines()
open("claims.txt", "w").write("\n".join(l for l in lines if not (l.endswith(" claimed") and l.split()[0] in release)) + "\n")
print("new starts:", [a for a, _ in new])
print("released claims:", sorted(release))
# queue this run's near-misses (unmatched, still claimed, with a saved attempt) for the permuter sweep
scratch = os.environ.get("DECOMP_SCRATCH", "")
if scratch:
    nm = [f["addr"] for f in fns if not f.get("committed") and f["addr"] not in release
          and os.path.exists(os.path.join(scratch, f["addr"] + ".c"))]
    with open("permuter/queue.txt", "a") as q:
        q.write("".join(a + "\n" for a in nm))
    print("queued for permuter:", len(nm))
subprocess.run(["python3", "tools/bandit.py", "record", d], check=False)
subprocess.run(["python3", "tools/bandit.py", "md"], check=False)  # refresh table in docs/STRATEGY.md
# tip usefulness (tips_tried / tips_helped reported per function)
sys.path.insert(0, os.path.dirname(__file__))
import tip_stats
tip_stats.tally(fns)
tip_stats.report()
