#!/usr/bin/env python3
"""Batch helpers for a client list.

Usage:
    python3 batch.py <list.csv|list.txt> --audit [--no-lighthouse]   # run audit.py for each client missing audit.json
    python3 batch.py <list.csv|list.txt> --rank                      # score each audited client, write clients/leads.csv

List formats:
    CSV with header: name,url[,industry,contact,notes]
    or plain text: one URL (or "Name, URL") per line.
Client folders: clients/<slug>/ next to the list file's "clients" root (the list's own folder).
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def slugify(s):
    s = re.sub(r"^https?://", "", s.strip().lower())
    s = re.sub(r"^www\.", "", s).split("/")[0] if "." in s and " " not in s else s
    s = re.sub(r"\.(com|in|net|org|co|io|ae|co\.in)$", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:50]


def read_list(path):
    rows = []
    with open(path, newline="") as f:
        text = f.read()
    if text.lower().startswith("name,") or text.lower().startswith("url,"):
        for r in csv.DictReader(text.splitlines()):
            if r.get("url"):
                rows.append({k: (v or "").strip() for k, v in r.items()})
    else:
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            url = next((p for p in parts if "." in p and " " not in p), parts[-1])
            name = parts[0] if parts[0] != url else ""
            rows.append({"name": name, "url": url})
    for r in rows:
        r["slug"] = slugify(r.get("name") or r["url"])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("list")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--rank", action="store_true")
    ap.add_argument("--no-lighthouse", action="store_true")
    a = ap.parse_args()
    root = os.path.dirname(os.path.abspath(a.list))
    rows = read_list(a.list)
    print(f"{len(rows)} clients")

    if a.audit:
        for r in rows:
            out = os.path.join(root, r["slug"])
            if os.path.exists(os.path.join(out, "audit.json")):
                print(f"skip {r['slug']} (audited)")
                continue
            print(f"audit {r['slug']} <- {r['url']}", flush=True)
            cmd = [sys.executable, os.path.join(HERE, "audit.py"), r["url"], "--out", out]
            if a.no_lighthouse:
                cmd.append("--no-lighthouse")
            rc = subprocess.run(cmd).returncode
            if rc == 2:
                print(f"  UNREACHABLE: {r['url']}")
            if r.get("industry") or r.get("notes") or r.get("contact"):
                with open(os.path.join(out, "intake.json"), "w") as f:
                    json.dump(r, f, indent=2)

    if a.rank:
        sys.path.insert(0, HERE)
        import score as S
        R = S.load(S.RUBRIC_PATH)
        out_rows = []
        for r in rows:
            cdir = os.path.join(root, r["slug"])
            audit = S.load(os.path.join(cdir, "audit.json"))
            if not audit:
                out_rows.append({**r, "status": "not audited"})
                continue
            if audit.get("reachable") is False:
                out_rows.append({**r, "status": "unreachable", "lead_score": 70, "lead_offer": "website rebuild (site down)"})
                continue
            manual = S.load(os.path.join(cdir, "manual.json"), {}) or {}
            res = S.score(audit, manual, R)
            with open(os.path.join(cdir, "scores.json"), "w") as f:
                json.dump(res, f, indent=2)
            pdfs = [p for p in os.listdir(cdir) if p.endswith(".pdf")]
            out_rows.append({**r, "status": "deck ready" if pdfs else ("scored" if manual else "scored (no manual.json)"),
                             "overall": res["overall"], "grade": res["grade"], "lead_score": res["lead_score"],
                             "lead_offer": res["fit"]["primary"], "fit_reason": res["fit"]["reason"],
                             "top_issue": res["top_findings"][0]["title"] if res["top_findings"] else "",
                             "critical": res["finding_count"]["critical"], "high": res["finding_count"]["high"],
                             "pdf": pdfs[0] if pdfs else ""})
        out_rows.sort(key=lambda x: -(x.get("lead_score") or 0))
        fields = ["slug", "name", "url", "status", "lead_score", "overall", "grade", "lead_offer", "fit_reason",
                  "top_issue", "critical", "high", "pdf", "industry", "contact", "notes"]
        lp = os.path.join(root, "leads.csv")
        with open(lp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(out_rows)
        print(f"wrote {lp}")
        for x in out_rows[:10]:
            print(f"  {x.get('lead_score', '-'):>4}  {x['slug']:<30} {x.get('overall', '-'):>4}  {x.get('lead_offer', '')}  {x.get('top_issue', '')[:50]}")


if __name__ == "__main__":
    main()
