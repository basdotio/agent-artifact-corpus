#!/usr/bin/env python3
"""collect.py - turn whatever you collected into one clean list for swipe.py.

New in the virality skill (Jakeschincariol/master-skills).

Finding what works starts with a messy pile: numbers read off a phone screen, a CSV from an
analytics export, yt-dlp JSON for a channel's Shorts tab. This reads all of them and writes
one normalized JSON list, one object per post:

  {"channel": "@handle", "title": "...", "hook": "...", "views": 412000, "likes": null,
   "comments": null, "shares": null, "saves": null, "url": "...", "duration": 31,
   "posted": "2026-09-01", "platform": "shorts", "followers": null, "median": null}

Accepted input, detected per file:

  JSON    a list of posts, {"entries": [...]} from `yt-dlp --flat-playlist -J`, JSON lines from
          `yt-dlp -j`, or {"posts" | "videos" | "items": [...]}. Field names are matched
          loosely: view_count, plays, channel, uploader_id, webpage_url, and so on.
  CSV/TSV with a header row: any of creator, views, hook or title, url, duration, date,
          likes, comments, shares, saves, followers, median.
  PASTE   one post per line, fields split by "|" or tabs, in this order:
              creator | views | hook or title | url | duration | date
          Only the first three are required. Lines starting with # are ignored.

Counts like 1.2M, 412K, 12,400 and 1.234 (European) are all read correctly. A Shorts title that
opens with the creator's call to action ('Comment "SETUP" and I'll send you...') gets the CTA
stripped before the hook is taken, so the formula is named from the hook, not the ask.

It reads files you already have. It never logs in, never uses cookies, never fetches anything.

Usage
  python3 collect.py pasted.txt -o candidates.json
  python3 collect.py channel_a.json channel_b.json export.csv -o candidates.json
  python3 collect.py pasted.txt --creator @someone --platform tiktok
  pbpaste | python3 collect.py - > candidates.json

Exit codes: 0 wrote at least one usable post, 1 nothing usable, 2 bad input.
"""

import argparse
import csv
import datetime
import io
import json
import os
import re
import sys

FIELDS = ["channel", "title", "hook", "views", "likes", "comments", "shares", "saves",
          "url", "duration", "posted", "platform", "followers", "median"]

ALIASES = {
    "channel": ["channel", "creator", "account", "handle", "author", "username", "user", "page",
                "profile", "owner", "channel_name", "uploader_id", "uploader"],
    "title": ["title", "caption", "text", "description", "headline", "post", "content",
              "post_text", "video_title", "fulltitle"],
    "hook": ["hook", "first_line", "spoken_hook", "opening", "opener", "first_words"],
    "views": ["views", "view_count", "plays", "play_count", "playcount", "video_views",
              "impressions", "viewcount", "plays_count"],
    "likes": ["likes", "like_count", "reactions", "hearts", "digg_count", "diggcount",
              "favorites", "reaction_count"],
    "comments": ["comments", "comment_count", "replies"],
    "shares": ["shares", "share_count", "reposts", "repost_count", "sends"],
    "saves": ["saves", "save_count", "bookmarks", "collects", "collect_count"],
    "url": ["url", "link", "webpage_url", "permalink", "post_url", "video_url", "original_url",
            "short_url"],
    "duration": ["duration", "length", "duration_seconds", "video_length", "seconds", "runtime"],
    "posted": ["posted", "date", "upload_date", "published", "published_at", "created",
               "create_time", "release_date", "timestamp", "posted_at", "publish_time"],
    "platform": ["platform", "network", "site", "source", "extractor_key", "ie_key"],
    "followers": ["followers", "follower_count", "channel_follower_count", "subscribers",
                  "subscriber_count", "fans"],
    "median": ["median", "baseline", "median_views", "typical_views"],
}
_LOOKUP = {a: f for f, names in ALIASES.items() for a in names}

COUNT_RE = re.compile(r"^(\d+(?:[.,\s]\d+)*)\s*(k|m|b|bn|mil|million|thousand|billion)?$")
# Only a real comment-for-DM call to action is stripped ("Comment X and I'll send you...",
# "Comment X for the prompt"). A hook that merely starts with "Type this..." is left alone.
CTA_PREFIX_RE = re.compile(
    r"^\s*(?:comment|reply(?: with)?|type|drop|dm me)\b[^.!?\n]{0,60}?"
    r"(?:\b(?:and|&)\s+I(?:'|’)?(?:ll| will)\s+(?:send|dm|message|share|give)\b[^.!?\n]{0,60}?"
    r"|\bfor (?:the|my|a|your)\b[^.!?\n]{0,40}?)"
    r"(?:\U0001F447|⬇️?|[.!:]|\s-\s)+\s*", re.IGNORECASE)
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+|\n+|\s+[\U0001F447⬇]")


def norm_key(k):
    return re.sub(r"[^a-z0-9]+", "_", str(k).strip().lower()).strip("_")


# -------------------------------------------------------------------------- parsing

def parse_count(v):
    """1.2M -> 1200000, 412K -> 412000, '12,400 views' -> 12400, 1.234 -> 1234. None if not a count."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(round(v)) if v >= 0 else None
    s = str(v).strip().lower()
    s = re.sub(r"\b(views?|plays?|likes?|comments?|shares?|saves?|reactions?|followers?|subscribers?|subs)\b", "", s)
    s = s.replace("+", "").replace("~", "").replace(" ", " ").strip()
    if not s or s in ("-", "n/a", "na", "none", "null", "?"):
        return None
    m = COUNT_RE.match(s)
    if not m:
        return None
    num, suf = m.group(1), (m.group(2) or "")
    mult = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mil": 1e6, "million": 1e6,
            "b": 1e9, "bn": 1e9, "billion": 1e9}.get(suf, 1)
    num = num.replace(" ", "")
    if mult != 1:
        # With a suffix a single separator is a decimal point: 1.2M, or 1,2M in Europe.
        if "," in num and "." in num:
            num = num.replace(",", "")
        elif num.count(",") == 1 and len(num.split(",")[1]) <= 2:
            num = num.replace(",", ".")
        else:
            num = num.replace(",", "")
        try:
            return int(round(float(num) * mult))
        except ValueError:
            return None
    if re.match(r"^\d{1,3}([.,])\d{3}(\1\d{3})*$", num):          # 12,400 or 1.234.567
        return int(re.sub(r"[.,]", "", num))
    if re.match(r"^\d+,\d{1,2}$", num):                           # 3,5 (decimal comma)
        return int(round(float(num.replace(",", "."))))
    try:
        return int(round(float(num.replace(",", ""))))
    except ValueError:
        return None


def parse_duration(v):
    """42, '0:42', '1:02:03', '42s', '1m 20s', 'PT1M20S' -> seconds (float)."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if v >= 0 else None
    s = str(v).strip().lower()
    if not s:
        return None
    m = re.match(r"^pt(?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?$", s)
    if m and any(m.groups()):
        h, mi, se = m.groups()
        return int(h or 0) * 3600 + int(mi or 0) * 60 + float(se or 0)
    if re.match(r"^\d+(?::\d{1,2}){1,2}(?:\.\d+)?$", s):
        parts = [float(p) for p in s.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0.0)
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    m = re.match(r"^(?:(\d+)\s*h(?:ours?|rs?)?)?\s*(?:(\d+)\s*m(?:in(?:utes?|s)?)?)?\s*"
                 r"(?:(\d+(?:\.\d+)?)\s*s(?:ec(?:onds?|s)?)?)?$", s)
    if m and any(m.groups()):
        h, mi, se = m.groups()
        return int(h or 0) * 3600 + int(mi or 0) * 60 + float(se or 0)
    try:
        return float(s)
    except ValueError:
        return None


def parse_date(v):
    """20260901, 2026-09-01, unix seconds, 'Sep 1, 2026', ISO datetimes -> 'YYYY-MM-DD'."""
    if v is None or isinstance(v, bool) or v == "":
        return None
    if isinstance(v, (int, float)):
        if v > 1e11:
            v = v / 1000.0                       # milliseconds
        if v > 1e8:
            return datetime.datetime.fromtimestamp(v, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
        v = str(int(v))
    s = str(v).strip()
    if re.match(r"^\d{8}$", s):
        s = "%s-%s-%s" % (s[:4], s[4:6], s[6:])
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return "%s-%s-%s" % m.groups()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def platform_of(url, hint=None):
    u = (url or "").lower()
    if "youtube.com/shorts" in u or "youtu.be" in u and "shorts" in u:
        return "shorts"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    for host, name in (("tiktok.com", "tiktok"), ("instagram.com", "instagram"),
                       ("linkedin.com", "linkedin"), ("x.com", "x"), ("twitter.com", "x"),
                       ("facebook.com", "facebook"), ("threads.net", "threads")):
        if host in u:
            return name
    h = (hint or "").strip().lower()
    return {"youtube": "youtube", "youtubetab": "youtube", "tiktok": "tiktok",
            "instagram": "instagram", "linkedin": "linkedin"}.get(h, h or None)


def strip_cta(text):
    """'Comment "SETUP" and I'll send you the process 👇 I use AI to...' -> 'I use AI to...'"""
    out = CTA_PREFIX_RE.sub("", text or "", count=1)
    return out if out.strip() else (text or "")


def hook_from(text):
    """First sentence of a caption or title, after any leading call to action."""
    body = strip_cta((text or "").strip())
    first = SENTENCE_END_RE.split(body.strip(), maxsplit=1)[0].strip() if body.strip() else ""
    first = re.sub(r"\s+", " ", first)
    return first[:160] or None


def canon_url(u):
    if not u:
        return None
    u = u.strip()
    m = re.search(r"(?:youtube\.com/(?:shorts/|watch\?v=)|youtu\.be/)([\w-]{6,})", u)
    if m:
        return "yt:" + m.group(1)
    return re.sub(r"[?#].*$", "", u).rstrip("/").lower()


# ------------------------------------------------------------------------ normalizing

def normalize(raw, defaults=None):
    """One raw record (any key names) -> the canonical post dict, or None if unusable."""
    defaults = defaults or {}
    keyed = {norm_key(k): v for k, v in raw.items() if v not in (None, "")}
    got = {}
    for f, names in ALIASES.items():           # alias order is priority: title before description
        for name in names:
            if name in keyed:
                got[f] = keyed[name]
                break
    handle = keyed.get("uploader_id")
    if isinstance(handle, str) and handle.startswith("@"):
        got["channel"] = handle                # yt-dlp: the @handle is the stable creator key
    for f, v in defaults.items():
        if v not in (None, "") and got.get(f) in (None, ""):
            got[f] = v
    post = {f: None for f in FIELDS}
    channel = got.get("channel")
    post["channel"] = re.sub(r"\s+", " ", str(channel)).strip() if channel not in (None, "") else None
    title = got.get("title")
    post["title"] = re.sub(r"\s+", " ", str(title)).strip() if title else None
    hook = got.get("hook")
    post["hook"] = re.sub(r"\s+", " ", str(hook)).strip() if hook else hook_from(post["title"])
    for f in ("views", "likes", "comments", "shares", "saves", "followers", "median"):
        post[f] = parse_count(got.get(f))
    post["duration"] = parse_duration(got.get("duration"))
    post["posted"] = parse_date(got.get("posted"))
    post["url"] = str(got["url"]).strip() if got.get("url") else None
    post["platform"] = platform_of(post["url"], got.get("platform"))
    if not post["channel"] or not (post["title"] or post["hook"]):
        return None
    if all(post[f] is None for f in ("views", "likes", "comments", "shares", "saves")):
        return None
    return post


def _records_from_json(data):
    """Yield (record, defaults) pairs from any of the JSON shapes we accept."""
    if isinstance(data, list):
        for r in data:
            if not isinstance(r, dict):
                continue
            if isinstance(r.get("entries"), list):              # several yt-dlp dumps in one list
                for pair in _records_from_json(r):
                    yield pair
            else:
                yield r, {}
        return
    if not isinstance(data, dict):
        return
    if isinstance(data.get("entries"), list):                   # yt-dlp playlist / channel tab
        parent = {"channel": data.get("uploader_id") or data.get("channel") or data.get("uploader"),
                  "followers": data.get("channel_follower_count"),
                  "platform": data.get("extractor_key") or data.get("ie_key")}
        for e in data["entries"]:
            if not isinstance(e, dict):
                continue
            if isinstance(e.get("entries"), list):              # nested tabs
                for pair in _records_from_json(e):
                    yield pair
                continue
            yield e, parent
        return
    for key in ("posts", "videos", "items", "data", "rows", "results"):
        if isinstance(data.get(key), list):
            for r in data[key]:
                if isinstance(r, dict):
                    yield r, {}
            return
    yield data, {}


def _records_from_table(text):
    sample = text[:4096]
    delim = "\t" if sample.count("\t") >= sample.count(",") else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        return []
    head = [norm_key(c) for c in rows[0]]
    return [dict(zip(head, r)) for r in rows[1:]]


def _records_from_paste(text):
    out = []
    order = ["channel", "views", "title", "url", "duration", "posted"]
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cells = [c.strip() for c in re.split(r"\s*\|\s*|\t", line.strip().strip("|"))]
        if len(cells) < 3:
            continue
        if parse_count(cells[1]) is None and norm_key(cells[1]) in _LOOKUP:
            order = [norm_key(c) for c in cells]                     # a header row
            continue
        out.append(dict(zip(order, cells)))
    return out


def load_file(path):
    """Return a list of raw (record, defaults) pairs from one file."""
    if path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            raw = fh.read()
    text = raw.strip()
    if not text:
        return []
    if text[:1] in "[{":
        try:
            return list(_records_from_json(json.loads(text)))
        except ValueError:
            lines = [l for l in text.splitlines() if l.strip()]
            try:                                                # JSON lines (yt-dlp -j)
                pairs = []
                for l in lines:
                    pairs.extend(_records_from_json(json.loads(l)))
                return pairs
            except ValueError:
                raise ValueError("%s looks like JSON but does not parse" % path)
    first = text.splitlines()[0]
    if "|" in first or not re.search(r"[,\t]", first):
        return [(r, {}) for r in _records_from_paste(text)]
    head = [norm_key(c) for c in re.split(r"[,\t]", first)]
    if sum(1 for h in head if h in _LOOKUP) >= 2:
        return [(r, {}) for r in _records_from_table(text)]
    return [(r, {}) for r in _records_from_paste(text)]


def collect(paths, defaults=None):
    """Load, normalize and de-duplicate posts from every path. Returns (posts, skipped)."""
    posts, seen, skipped = [], set(), 0
    for path in paths:
        for record, parent in load_file(path):
            merged_defaults = dict(parent)
            for k, v in (defaults or {}).items():
                if v not in (None, ""):
                    merged_defaults[k] = v
            post = normalize(record, merged_defaults)
            if post is None:
                skipped += 1
                continue
            key = canon_url(post["url"]) or (post["channel"].lower().lstrip("@"),
                                            (post["title"] or post["hook"] or "").lower())
            if key in seen:
                continue
            seen.add(key)
            posts.append(post)
    return posts, skipped


def creator_key(name):
    return (name or "").strip().lower().lstrip("@")


def summary(posts, skipped, min_posts, out=sys.stderr):
    by = {}
    for p in posts:
        by.setdefault(creator_key(p["channel"]), []).append(p)
    print("\n  collected %d posts from %d creators%s" % (
        len(posts), len(by), ", skipped %d unusable rows" % skipped if skipped else ""), file=out)
    for key, items in sorted(by.items(), key=lambda kv: -len(kv[1])):
        has_median = any(p.get("median") for p in items)
        note = "" if len(items) >= min_posts or has_median else \
            "   under %d: swipe.py will skip it unless you add a median" % min_posts
        print("    %3d  %s%s" % (len(items), items[0]["channel"][:40], note), file=out)
    missing = sum(1 for p in posts if p["views"] is None)
    if missing:
        print("  %d posts have no view count; rank them with swipe.py --metric likes" % missing, file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(
        description="Normalize pasted posts, CSV exports and yt-dlp JSON into one list for swipe.py.",
        epilog="Paste format, one post per line: creator | views | hook or title | url | duration | date")
    ap.add_argument("inputs", nargs="+", help="files to read, or - for stdin")
    ap.add_argument("-o", "--out", help="write the JSON here (default: stdout)")
    ap.add_argument("--creator", help="creator to use for rows that have none (one creator's list)")
    ap.add_argument("--platform", help="platform for rows that have none: shorts, tiktok, instagram, linkedin")
    ap.add_argument("--append", action="store_true", help="merge into an existing --out file")
    ap.add_argument("--min-posts", type=int, default=4,
                    help="warn about creators with fewer posts than this (default %(default)s)")
    ap.add_argument("--quiet", action="store_true", help="no summary on stderr")
    args = ap.parse_args()

    for p in args.inputs:
        if p != "-" and not os.path.exists(p):
            print("no such file: %s" % p, file=sys.stderr)
            return 2
    defaults = {"channel": args.creator, "platform": args.platform}
    try:
        posts, skipped = collect(args.inputs, defaults)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    if args.append and args.out and os.path.exists(args.out):
        old, _ = collect([args.out])
        known = {canon_url(p["url"]) for p in old if p["url"]}
        posts = old + [p for p in posts if not p["url"] or canon_url(p["url"]) not in known]
    if not posts:
        print("no usable posts. Each needs a creator, a hook or title, and at least one count "
              "(views, likes, comments, shares or saves).", file=sys.stderr)
        return 1
    payload = json.dumps(posts, indent=1, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        if not args.quiet:
            print("  wrote %s" % args.out, file=sys.stderr)
    else:
        print(payload)
    if not args.quiet:
        summary(posts, skipped, args.min_posts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
