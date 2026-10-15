#!/usr/bin/env python3
"""
Sound effects from Openverse (Freesound and others), CC0 and CC BY only.

  run.sh sfx.py search OUT.json "bubble pop" "water drop" [--max-dur 6] [--pages 2]
  run.sh sfx.py fetch DIR KEY=OPENVERSE_ID ... [--music KEY=OPENVERSE_ID ...]
  run.sh sfx.py fetch DIR --refetch

search  prints a table of short CC0 / CC BY sounds and saves them to OUT.json.
fetch   re-reads each record from Openverse (the licence comes from the record, not the search),
        downloads it to DIR/sfx/KEY.ext (--music items to DIR/music/), and merges DIR/manifest.json:
        title, creator, source page, download URL, licence, credit line, sha256 and the raw peak
        offset (loudest 10 ms RMS window) that mix.py aligns on. Writes DIR/CREDITS.txt.
        --refetch downloads every manifest file missing from DIR and checks its sha256.
Creators named deleted_user_N are refused: the account is gone, so the licence cannot be checked.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

from common import load_json, save_json

API = "https://api.openverse.org/v1/audio/"
UA = {"User-Agent": "onetake-videogen/1.0"}
OK = {"cc0", "by"}
SR = 48000
DELETED = re.compile(r"^deleted_user_\d+$")
EXT = (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus", ".aiff", ".aif")


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def api(url):
    """Openverse JSON. Anonymous limits are 20 requests/min and 200/day; waits out a 429.
    format=json: the CDN can serve a cached HTML page regardless of the Accept header."""
    url += ("&" if "?" in url else "?") + "format=json"
    for _ in range(4):
        try:
            req = urllib.request.Request(url, headers={**UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            wait = int(e.headers.get("Retry-After") or 60)
            print(f"openverse rate limit, waiting {wait} s")
            time.sleep(wait)
    raise SystemExit("openverse keeps rate-limiting; try again later")


def licence(x):
    return "CC0 1.0" if x["license"] == "cc0" else f"CC BY {x.get('license_version') or ''}".strip()


def peak_offset(path):
    """Seconds from the file start to its loudest 10 ms RMS window."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    y = np.frombuffer(raw, np.float32).astype(np.float64)
    env = np.convolve(y ** 2, np.ones(480) / 480, "same")
    return round(int(np.argmax(env)) / SR, 4), round(len(y) / SR, 3)


def search(a):
    found, deleted = {}, 0
    for q in a.queries:
        for page in range(1, a.pages + 1):
            qs = urllib.parse.urlencode({"q": q, "license": "cc0,by", "page_size": 20, "page": page})
            res = api(API + "?" + qs).get("results", [])
            for x in res:
                dur = (x.get("duration") or 0) / 1000
                if x["license"] not in OK or not 0 < dur <= a.max_dur or x["id"] in found:
                    continue
                if DELETED.match(x.get("creator") or ""):
                    deleted += 1
                    continue
                found[x["id"]] = {"query": q, "id": x["id"], "title": x["title"], "creator": x.get("creator"),
                                  "license": x["license"], "license_version": x.get("license_version"),
                                  "source": x["source"], "page": x.get("foreign_landing_url"), "duration": dur}
                print(f"{x['id']}  {licence(x):10s} {dur:4.1f}s {x['source'][:10]:10s} "
                      f"{x['title'][:40]:40s} {x.get('creator')}")
            if len(res) < 20:
                break
    save_json(list(found.values()), a.out)
    print(f"{len(found)} sounds -> {a.out}" + (f" ({deleted} by deleted users skipped)" if deleted else ""))


def write_credits(d, man):
    lines, cc0 = [], []
    for kind in ("music", "sfx"):
        for e in man.get(kind, {}).values():
            (cc0 if e["license"].startswith("CC0") else lines).append(e)
    out = [e["credit"] for e in lines]
    if cc0:
        out += ["", "Sound effects, CC0 1.0 (no credit required, listed for provenance):"]
        out += [f"\"{e['title']}\" by {e['creator']} - {e['source_url']}" for e in cc0]
    (d / "CREDITS.txt").write_text("\n".join(out).strip() + "\n")


def fetch(a):
    d = Path(a.dir)
    mpath = d / "manifest.json"
    man = load_json(mpath) if mpath.exists() else {}
    if a.refetch:
        bad = 0
        for kind in ("music", "sfx"):
            for key, e in man.get(kind, {}).items():
                f = d / e["file"]
                if not f.exists():
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_bytes(get(e["download_url"], 300))
                ok = hashlib.sha256(f.read_bytes()).hexdigest() == e.get("sha256")
                bad += not ok
                print(f"{key:24s} {'ok' if ok else 'SHA256 MISMATCH (source changed?)'}  {f}")
        sys.exit(1 if bad else 0)
    refused = 0
    for kind, spec in [("sfx", s) for s in a.items] + [("music", s) for s in a.music]:
        key, _, oid = spec.partition("=")
        if not oid:
            raise SystemExit(f"expected KEY=OPENVERSE_ID, got {spec!r}")
        x = api(API + oid + "/")
        creator = x.get("creator") or ""
        if DELETED.match(creator):
            print(f"REFUSED {key}: creator {creator} is a deleted account, provenance unverifiable")
            refused += 1
            continue
        if x["license"] not in OK:
            print(f"REFUSED {key}: licence {x['license']} (only cc0 and by)")
            refused += 1
            continue
        ext = Path(urllib.parse.urlparse(x["url"]).path).suffix.lower()
        if ext not in EXT:  # Jamendo URLs carry no suffix; their filetype is "mp32"
            ext = next((e for e in EXT if e[1:] in (x.get("filetype") or "")), ".mp3")
        rel = f"{kind}/{key}{ext}"
        f = d / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(get(x["url"], 300))
        lic = licence(x)
        page = x.get("foreign_landing_url") or x["url"]
        credit = f"\"{x['title']}\" by {creator} ({x['source']}), {lic}"
        if x["license"] == "by":
            credit += f" - {page} - licence: {x.get('license_url')}"
        e = {**man.get(kind, {}).get(key, {}),
             "file": rel, "title": x["title"], "creator": creator, "source": x["source"], "source_url": page,
             "download_url": x["url"], "openverse_id": x["id"], "license": lic,
             "license_url": x.get("license_url"), "credit": credit,
             "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
        if kind == "sfx":
            e["peak_offset_s_raw"], e["duration_s"] = peak_offset(f)
        man.setdefault(kind, {})[key] = e
        save_json(man, mpath)
        note = "  <- CC BY: check the source page states the same licence, credit is required" \
            if x["license"] == "by" else ""
        peak = f"peak@{e['peak_offset_s_raw']}s" if kind == "sfx" else "music"
        print(f"{key:24s} {lic:10s} {peak:14s} {x['title'][:40]} by {creator}{note}")
    save_json(man, mpath)
    write_credits(d, man)
    print(f"manifest -> {mpath}\ncredits  -> {d / 'CREDITS.txt'}")
    if refused:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("out")
    s.add_argument("queries", nargs="+")
    s.add_argument("--max-dur", type=float, default=6, help="longest sound in seconds")
    s.add_argument("--pages", type=int, default=2, help="pages of 20 results per query")
    f = sub.add_parser("fetch")
    f.add_argument("dir")
    f.add_argument("items", nargs="*", help="KEY=OPENVERSE_ID")
    f.add_argument("--music", nargs="+", default=[], metavar="KEY=OPENVERSE_ID",
                   help="music tracks, stored under music/ (no peak offset)")
    f.add_argument("--refetch", action="store_true", help="download missing manifest files, check sha256")
    a = ap.parse_args()
    search(a) if a.cmd == "search" else fetch(a)


if __name__ == "__main__":
    main()
