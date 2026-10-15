#!/usr/bin/env python3
"""Download a free stock photo into a client's images/ folder and record the credit.

Usage:
    python3 fetch_image.py <client_dir> <unsplash-or-pexels-url-or-id> --name cover [--width 1920]
    python3 fetch_image.py <client_dir> --search "fuel tanker truck night" [--orientation landscape]
        needs UNSPLASH_ACCESS_KEY and/or PEXELS_API_KEY; downloads ~12 small candidates into
        images/_candidates/ plus sheet.png (numbered) so you can look and pick, then fetch the chosen URL.
Without API keys: find photo pages with web search (unsplash.com / pexels.com) and pass their URLs.

Sources (free licences only, commercial use allowed, no attribution required but we record it anyway):
  - Unsplash:  https://unsplash.com/photos/<slug-or-id>   (Unsplash+ photos return 403: those are paid, skip them)
  - Pexels:    https://www.pexels.com/photo/<slug>-<id>/
Writes <client_dir>/images/<name>.jpg and appends to <client_dir>/images/CREDITS.md.
"""
import argparse
import os
import re
import sys
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/129 Safari/537.36"


def resolve(ref, width):
    ref = ref.strip()
    if "pexels.com" in ref or ref.startswith("pexels:"):
        pid = re.findall(r"(\d{5,})", ref)[-1]
        return ("Pexels", f"https://www.pexels.com/photo/{pid}/",
                f"https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg?auto=compress&cs=tinysrgb&w={width}")
    m = re.search(r"unsplash\.com/photos/(?:[^/?#]*-)?([A-Za-z0-9_-]{11})(?:[/?#]|$)", ref)
    uid = m.group(1) if m else ref
    return ("Unsplash", f"https://unsplash.com/photos/{uid}", f"https://unsplash.com/photos/{uid}/download?force=true&w={width}")


def get_json(url, headers=None):
    import json as _j
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return _j.loads(r.read())


def search(client_dir, query, orientation):
    """Official APIs: Unsplash (free licence) and Pexels. Returns candidates with page URL + credit."""
    from PIL import Image, ImageDraw
    import io
    q = urllib.parse.quote(query)
    cands = []
    uk, pk = os.environ.get("UNSPLASH_ACCESS_KEY"), os.environ.get("PEXELS_API_KEY")
    if not (uk or pk):
        sys.exit("--search needs UNSPLASH_ACCESS_KEY or PEXELS_API_KEY. Without keys: web-search unsplash.com / pexels.com and pass photo URLs.")
    if uk:
        d = get_json(f"https://api.unsplash.com/search/photos?query={q}&orientation={orientation}&per_page=8&content_filter=high",
                     {"Authorization": f"Client-ID {uk}", "Accept-Version": "v1"})
        for r in d.get("results", []):
            if r.get("premium") or r.get("plus"):
                continue  # Unsplash+ is paid
            cands.append({"src": "Unsplash", "page": r["links"]["html"], "thumb": r["urls"]["small"], "by": r["user"]["name"], "alt": r.get("alt_description")})
    if pk:
        d = get_json(f"https://api.pexels.com/v1/search?query={q}&orientation={orientation}&per_page=8", {"Authorization": pk})
        for r in d.get("photos", []):
            cands.append({"src": "Pexels", "page": r["url"], "thumb": r["src"]["medium"], "by": r["photographer"], "alt": r.get("alt")})
    out = os.path.join(client_dir, "images", "_candidates")
    os.makedirs(out, exist_ok=True)
    tiles = []
    for i, c in enumerate(cands[:12], 1):
        try:
            data = urllib.request.urlopen(urllib.request.Request(c["thumb"], headers={"User-Agent": UA}), timeout=30).read()
            im = Image.open(io.BytesIO(data)).convert("RGB")
            im.thumbnail((400, 260))
            tile = Image.new("RGB", (400, 290), (20, 20, 20))
            tile.paste(im, ((400 - im.width) // 2, 0))
            ImageDraw.Draw(tile).text((8, 268), f"#{i} {c['src']} · {c['by'][:30]}", fill=(255, 255, 255))
            tiles.append(tile)
            print(f"#{i}  {c['page']}  ({c['src']}, {c['by']}){' , ' + c['alt'][:60] if c.get('alt') else ''}")
        except Exception:  # noqa: BLE001
            continue
    if tiles:
        cols = 4
        sheet = Image.new("RGB", (cols * 405, ((len(tiles) + cols - 1) // cols) * 295), (0, 0, 0))
        for k, t in enumerate(tiles):
            sheet.paste(t, ((k % cols) * 405, (k // cols) * 295))
        sheet.save(os.path.join(out, "sheet.png"))
        print(f"contact sheet: {os.path.join(out, 'sheet.png')}  → pick one, then: fetch_image.py {client_dir} <page-url> --name cover")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("client_dir")
    ap.add_argument("ref", nargs="?")
    ap.add_argument("--name")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--search")
    ap.add_argument("--orientation", default="landscape")
    a = ap.parse_args()
    if a.search:
        search(a.client_dir, a.search, a.orientation)
        return
    if not (a.ref and a.name):
        sys.exit("give a photo URL and --name, or --search \"query\"")
    src, page, url = resolve(a.ref, a.width)
    if src == "Unsplash" and os.environ.get("UNSPLASH_ACCESS_KEY"):
        try:  # API guideline: trigger the download endpoint for photos you use
            uid = page.rstrip("/").split("/")[-1]
            get_json(f"https://api.unsplash.com/photos/{uid}/download", {"Authorization": f"Client-ID {os.environ['UNSPLASH_ACCESS_KEY']}"})
        except Exception:  # noqa: BLE001
            pass
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data, final = r.read(), r.geturl()
    except Exception as e:  # noqa: BLE001
        sys.exit(f"download failed ({e}). Unsplash+ (paid) photos return 403: pick a free one.")
    if not data[:3] == b"\xff\xd8\xff":
        sys.exit("not a JPEG; pick another photo")
    out_dir = os.path.join(a.client_dir, "images")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{a.name}.jpg")
    with open(path, "wb") as f:
        f.write(data)
    author = ""
    m = re.search(r"dl=([a-z0-9-]+?)-[A-Za-z0-9_-]{11}-unsplash", final)
    if m:
        author = m.group(1).replace("-", " ").title()
    with open(os.path.join(out_dir, "CREDITS.md"), "a") as f:
        f.write(f"- `{a.name}.jpg`: {('photo by ' + author + ' ') if author else ''}on {src}, {page} ({src} License, free commercial use)\n")
    print(f"saved {path} ({len(data) // 1024} KB) {('by ' + author) if author else ''}")


if __name__ == "__main__":
    main()
