#!/usr/bin/env python3
"""Batch-generate product images from a CSV, reusing gen.py.

CSV: a header row is required. Recognised columns (others ignored):
  name       product subject / description        (required)
  template   pdd-main | pdd-scene | pdd-sellingpoint | pdd-detail | pdd-poster
  preset     3c-white | home | guochao | ...       (optional)
  text       selling points, separate with |       (optional)
  model      override model                        (optional)
  size       override size, e.g. 1024x1024         (optional)
  quality    low | medium | high | auto            (optional)
  background transparent | opaque | auto           (optional)
  n          images for this row (default 1)       (optional)
  ref        reference image path(s), separate with |  (optional; edit mode)
  slug       filename hint (optional; default from name)

Usage:
  python3 batch.py --sample > products.csv     # write a starter CSV
  python3 batch.py --dry-run products.csv      # show what would be generated
  python3 batch.py products.csv --out product-images/ --workers 3

Outputs go to <out>/NNN-<slug>[-<template>][-<preset>].png and a manifest is
written to <out>/batch-manifest.csv.
"""
import argparse
import csv
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

import gen  # same directory

COLUMNS = ["name", "template", "preset", "text", "model", "size",
           "quality", "background", "n", "ref", "slug"]

SAMPLE = """name,template,preset,text,n
无线蓝牙耳机充电仓,pdd-main,3c-white,,1
编织棉绳收纳筐,pdd-scene,home,,1
陶瓷茶杯礼盒,pdd-poster,guochao,国潮好物|匠心传承,1
不锈钢保温杯,pdd-sellingpoint,3c-white,24小时保温|316不锈钢|弹盖设计,1
"""


def read_rows(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    rows = []
    for i, raw in enumerate(reader, start=1):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not row.get("name"):
            continue
        row["_n"] = i
        rows.append(row)
    return rows


def build_job(row):
    """Turn a CSV row into a (namespace, filename, meta) tuple."""
    subject = row["name"]
    tname = row.get("template") or None
    pname = row.get("preset") or None
    if tname and tname not in gen.TEMPLATES:
        raise ValueError("unknown template '%s'" % tname)
    if pname and pname not in gen.PRESETS:
        raise ValueError("unknown preset '%s'" % pname)
    tpl = gen.TEMPLATES.get(tname, {}) if tname else {}
    preset = gen.PRESETS.get(pname, {}) if pname else {}

    text = row.get("text") or None
    prompt = gen.compose_prompt(tpl, preset, subject, text) if (tpl or preset or text) else subject

    n = int(row.get("n") or 1)
    ns = SimpleNamespace(
        prompt=prompt,
        model=gen._pick(row.get("model"), tpl.get("model"), preset.get("model"), gen.DEFAULT_MODEL),
        size=gen._pick(row.get("size"), tpl.get("size"), preset.get("size")),
        quality=gen._pick(row.get("quality"), tpl.get("quality"), preset.get("quality")),
        background=gen._pick(row.get("background"), tpl.get("background"), preset.get("background")),
        n=n,
        ref=[r for r in (x.strip() for x in (row.get("ref") or "").split("|")) if r],
        mask=None,
    )
    stem = row.get("slug") or "-".join(x for x in (tname, pname, subject) if x)
    return ns, gen.slugify(stem), {"template": tname, "preset": pname}


def run_job(idx, ns, slug, meta, out_dir, retries):
    headers = {"Authorization": "Bearer " + gen.API_KEY}
    is_edit = len(ns.ref) > 0
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = gen.call_edit(ns, headers) if is_edit else gen.call_generation(ns, headers)
        except Exception as e:
            last_err = "request failed: %s" % e
            time.sleep(1.5 * (attempt + 1))
            continue
        if resp.status_code != 200:
            last_err = "http %s: %s" % (resp.status_code, resp.text[:300])
            continue
        j = resp.json()
        if j.get("error"):
            last_err = "api error: %s" % j["error"]
            continue
        items = j.get("data") or []
        if not items:
            last_err = "empty data"
            continue
        files = []
        for k, item in enumerate(items):
            suffix = "" if len(items) == 1 else "-%d" % (k + 1)
            path = out_dir / ("%03d-%s%s.png" % (idx, slug, suffix))
            try:
                gen.download_image(item, path)
                files.append(str(path.resolve()))
            except Exception as e:
                last_err = "download failed: %s" % e
        if files:
            return {"files": files, "error": ""}
    return {"files": [], "error": last_err or "unknown error"}


def main():
    ap = argparse.ArgumentParser(description="Batch product image generation from CSV.")
    ap.add_argument("csv", nargs="?", help="input CSV path")
    ap.add_argument("--out", default="generated-images", help="output directory")
    ap.add_argument("--workers", type=int, default=2, help="parallel requests (default 2)")
    ap.add_argument("--retries", type=int, default=1, help="retries per row (default 1)")
    ap.add_argument("--limit", type=int, default=0, help="only process first N rows")
    ap.add_argument("--dry-run", action="store_true", help="print composed prompts, do not call the API")
    ap.add_argument("--sample", action="store_true", help="print a starter CSV and exit")
    args = ap.parse_args()

    if args.sample:
        sys.stdout.write(SAMPLE)
        return
    if not args.csv:
        ap.error("csv path is required (or use --sample)")
    if not gen.API_KEY:
        sys.exit("ERROR: IMAGE_API_KEY not set (see %s/.env)" % gen.SCRIPT_DIR)

    rows = read_rows(args.csv)
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        sys.exit("ERROR: no rows with a 'name' column found in %s" % args.csv)

    jobs = []
    for row in rows:
        try:
            ns, slug, meta = build_job(row)
            jobs.append((row["_n"], ns, slug, meta, row))
        except Exception as e:
            print("row %d SKIP: %s" % (row["_n"], e))

    if args.dry_run:
        for idx, ns, slug, meta, row in jobs:
            print("[%03d] %s" % (idx, slug))
            print("      model=%s size=%s quality=%s bg=%s n=%d ref=%s"
                  % (ns.model, ns.size, ns.quality, ns.background, ns.n, ns.ref or "-"))
            print("      prompt: %s" % ns.prompt.replace("\n\n", " ⏎ "))
        print("\n%d job(s), dry-run only." % len(jobs))
        return

    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    print("batch: %d job(s) -> %s (workers=%d)" % (len(jobs), out_dir.resolve(), args.workers))

    results = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {ex.submit(run_job, idx, ns, slug, meta, out_dir, args.retries): (idx, row)
                for idx, ns, slug, meta, row in jobs}
        done = 0
        for fut in as_completed(futs):
            idx, row = futs[fut]
            done += 1
            try:
                res = fut.result()
            except Exception as e:
                res = {"files": [], "error": str(e)}
            results[idx] = (row, res)
            status = "OK  " if res["files"] else "FAIL"
            detail = ", ".join(Path(f).name for f in res["files"]) or res["error"]
            print("  [%d/%d] %s row%03d %s" % (done, len(jobs), status, idx, detail))

    manifest = out_dir / "batch-manifest.csv"
    with manifest.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["row", "name", "template", "preset", "status", "files", "error"])
        for idx in sorted(results):
            row, res = results[idx]
            w.writerow([idx, row["name"], row.get("template", ""), row.get("preset", ""),
                        "ok" if res["files"] else "fail", " | ".join(res["files"]), res["error"]])

    ok = sum(1 for _, r in results.values() if r["files"])
    print("\ndone: %d/%d ok. manifest: %s" % (ok, len(results), manifest.resolve()))
    if ok < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
