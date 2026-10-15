#!/usr/bin/env python3
"""Collect every agent's notes per function from all workflow journals into decomp/notes/ADDR.txt.
Usage: tools/collect_notes.py WORKFLOWS_DIR   (e.g. ~/.claude/projects/<proj>/<session>/subagents/workflows)"""
import glob, json, os, sys
os.makedirs("decomp/notes", exist_ok=True)
notes = {}
for j in sorted(glob.glob(os.path.join(sys.argv[1], "*", "journal.jsonl")), key=os.path.getmtime):
    for line in open(j):
        e = json.loads(line)
        r = e.get("result")
        if e.get("type") == "result" and isinstance(r, dict):
            for f in r.get("functions", []):
                if not f.get("committed") and f.get("notes"):
                    notes.setdefault(f["addr"].upper(), []).append(f["notes"])
for a, ns in notes.items():
    open("decomp/notes/%s.txt" % a, "w").write("\n\n---\n\n".join(ns) + "\n")
print("notes for", len(notes), "functions")
