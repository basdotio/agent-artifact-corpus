#!/usr/bin/env python3
"""Lint deck-data.json before rendering: structure, text budget, and fact-trace.

Usage:
    python3 lint_deck.py <client_dir> [--profile DIR]

1. Structure: every slide has a known layout and its required fields; unknown fields are flagged.
2. Text budget (visual-first decks): headline ≤ 8 words, body/subtitle ≤ 15, impact ≤ 12, card body ≤ 14.
   Over the soft limit = WARN, over 1.5× = FAIL.
3. Fact-trace: every number shown on a slide must exist in a source: audit.json, scores.json, manual.json,
   research.md, page_text.txt or the company profile (catalog/proof/company). Illustrative mockup data and
   small counting numbers (≤ 10 without a unit) are exempt. Untraceable number = FAIL.
   Note: the trace proves a number exists in the sources, not that it is the right metric. Claude still
   checks meaning (e.g. that "9.9s" is the mobile LCP and not another timing that rounds the same).
Exit code 1 on any FAIL.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import profile as P  # noqa: E402

COMMON = {"layout", "eyebrow", "title", "body", "chips", "image", "footnote", "glow", "size", "photo", "brand", "hide_logo",
          "hide_counter", "top", "title_size", "text_width"}
LAYOUTS = {
    "cover": ({"title"}, {"subtitle", "footer", "image_mobile"}),
    "statement": ({"title"}, {"image_side", "live", "tiles", "tile_cols"}),
    "stats": ({"title", "stats"}, {"group_label", "num_size"}),
    "scorecard": ({"title", "overall", "categories"}, {"grade"}),
    "score_gaps": ({"title", "overall", "categories", "gaps"}, {"grade", "ring_caption"}),
    "finding": ({"title"}, {"metric", "evidence", "impact", "filmstrip"}),
    "process": ({"title", "steps"}, {"highlight"}),
    "cards": ({"title", "cards"}, {"columns", "highlight", "grid_top", "grid_gap_top"}),
    "solutions": ({"title", "items"}, {"highlight", "grid_top"}),
    "tiers": ({"title", "tiers"}, {"highlight"}),
    "compare": ({"title", "columns", "groups"}, {"highlight"}),
    "proof": ({"title"}, {"stats", "clients", "cases", "grid_top"}),
    "center": ({"title"}, set()),
    "contact": (set(), {"cta", "contact", "footer", "first_step", "proof"}),
    "offer": ({"title"}, {"product", "facts", "includes", "includes_label", "outcome", "next", "mockup", "modules"}),
}
# Phrases that make a deck sound generic or machine-written. Edit freely; matching is case-insensitive.
SLOP = ["growth opportunities", "let's talk", "one clear fix", "made real", "unlock", "seamless", "leverage", "elevate",
        "empower", "game-changer", "game changer", "cutting-edge", "cutting edge", "world-class", "next level", "next-level",
        "supercharge", "revolutionary", "synergy", "in today's", "look no further", "best-in-class", "robust", "streamline",
        "transform your", "take your business", "digital landscape", "ever-evolving", "unleash", "harness the power",
        "tailored solutions", "end-to-end solution", "drive growth", "boost your", "skyrocket", "a testament to"]
SMALL = {"a", "an", "the", "and", "or", "but", "of", "in", "on", "at", "to", "for", "by", "with", "is", "it", "as", "vs", "per"}

BUDGET = {"title": 8, "subtitle": 15, "body": 15, "impact": 12, "card_body": 14, "gap_body": 10}
NUM = re.compile(r"(?<![\w#])[$€£₹]?\d[\d,]*(?:\.\d+)?\s?(?:%|\+|[KkMm]\b|ms\b|s\b|MB\b|KB\b|x\b)?")


def words(t):
    return len(re.sub(r"[*\n]", " ", str(t or "")).split())


def texts(slide):
    """(field, text) pairs that appear on the slide, excluding illustrative mockup data."""
    out = []

    def walk(v, path):
        if path.startswith("mockup") or path in ("image.src", "photo.src", "image.label") or path.endswith((".src", ".icon", ".tone", ".frame", ".mode", ".pos", ".dim")):
            return
        if isinstance(v, str):
            out.append((path, v))
        elif isinstance(v, (int, float)) and not isinstance(v, bool) and path in ("overall",) or path.endswith(".score"):
            out.append((path, str(v)))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{path}[{i}]" if not isinstance(x, (dict, list)) else f"{path}")
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(x, f"{path}.{k}" if path else k)
    for k, v in slide.items():
        if k not in ("layout", "glow", "size", "top", "title_size", "text_width", "highlight", "columns", "tile_cols",
                     "num_size", "grid_top", "grid_gap_top", "hide_logo", "hide_counter", "image_side", "live", "brand"):
            walk(v, k)
    return out


def num_value(tok):
    t = tok.strip().replace(",", "")
    m = re.match(r"[$€£₹]?(\d+(?:\.\d+)?)\s?(%|\+|[KkMm]|ms|s|MB|KB|x)?$", t)
    if not m:
        return None, None
    v = float(m.group(1))
    u = (m.group(2) or "").lower()
    return v, u


MS_KEYS = ("lcp_ms", "fcp_ms", "tbt_ms", "si_ms", "tti_ms", "ttfb_ms", "load_ms")


def source_numbers(cdir, prof):
    """Human-written numbers (≤ 2 decimals as written) from every source, plus real timing metrics in ms."""
    blobs = []
    for f in ("audit.json", "scores.json", "manual.json", "research.md", "page_text.txt", "images/filmstrip.json"):
        fp = os.path.join(cdir, f)
        if os.path.exists(fp):
            blobs.append(open(fp, errors="ignore").read())
    if prof:
        for f in ("company.yaml", "catalog.yaml", "proof.yaml", "notes.md"):
            fp = os.path.join(prof["dir"], f)
            if os.path.exists(fp):
                blobs.append(open(fp, errors="ignore").read())
    big = "\n".join(blobs)
    vals = set()
    for m in re.finditer(r"(?<![\d.])\d[\d,]*(?:\.\d{1,2})?(?![\d.]*\d)", big):
        try:
            vals.add(float(m.group(0).replace(",", "")))
        except ValueError:
            pass
    ms = set()
    ap = os.path.join(cdir, "audit.json")
    if os.path.exists(ap):
        a = json.load(open(ap))
        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in MS_KEYS and isinstance(v, (int, float)):
                        ms.add(float(v))
                    walk(v)
            elif isinstance(o, list):
                for x in o:
                    walk(x)
        walk(a)
    return big, (vals, ms)


def traced(tok, big, pools):
    vals, ms = pools
    v, u = num_value(tok)
    if v is None:
        return True
    raw = tok.strip()
    if raw in big or raw.replace(" ", "") in big:
        return True
    d = len(raw.split(".")[1].rstrip("%+KkMmsBx ")) if "." in raw else 0
    rnd = lambda x: round(x, d)
    if u == "s":
        return any(rnd(x / 1000) == v for x in ms) or any(rnd(x) == v for x in vals)
    if u == "k":
        return any(rnd(x / 1000) == v for x in vals if x >= 1000)
    if u == "m":
        return any(rnd(x / 1_000_000) == v for x in vals if x >= 1_000_000)
    if u in ("mb",):
        return any(rnd(x / 1_000_000) == v or rnd(x / 1048576) == v for x in vals if x >= 100_000)
    return any(rnd(x) == v for x in vals)


def visible(slide):
    return [(f, t) for f, t in texts(slide) if not f.startswith(("image", "photo"))]


def slop_checks(slides, fails, warns):
    """Catch the tells of template-written decks: stock phrases, em dashes, Title Case, one headline formula."""
    formula, titlecase = [], []
    for n, s in enumerate(slides, 1):
        for field, text in visible(s):
            low = re.sub(r"\s+", " ", text.replace("*", "")).lower()
            for ph in SLOP:
                if ph in low:
                    fails.append(f"slide {n} {field}: generic phrase \"{ph}\". Say the specific thing instead")
            if "\u2014" in text:  # em dash
                fails.append(f"slide {n} {field}: em dash. Use a full stop, comma or colon")
        t = s.get("title") or ""
        lines = [l.strip(" *") for l in re.sub(r"[*]", "*", t).split("\n") if l.strip(" *")]
        if re.fullmatch(r"[^*]+?\.\s*\n?\s*\*[^*]+?\.\*\s*", t.strip(), re.S):
            formula.append(n)
        words_ = [w for w in re.sub(r"[*\n.,:;!?]", " ", t).split() if w.isalpha() and w.lower() not in SMALL]
        if len(words_) >= 3 and sum(w[0].isupper() for w in words_) / len(words_) > 0.8:
            titlecase.append(n)
    if len(formula) > 2:
        fails.append(f"slides {formula}: {len(formula)} headlines use the same 'Claim. *Payoff.*' formula. Keep it for at most 2; "
                     "vary the rest (a question, a number, the prospect's own words, a plain statement)")
    if len(titlecase) > 2:
        fails.append(f"slides {titlecase}: Title Case Headlines. Use sentence case (capitalise the first word and names only)")
    grams = {}
    for n, s in enumerate(slides, 1):
        toks = re.findall(r"[a-z']+", " ".join(t for _, t in visible(s)).lower())
        for g in {" ".join(toks[i:i + 3]) for i in range(len(toks) - 2)}:
            grams.setdefault(g, set()).add(n)
    for g, ns in grams.items():
        if len(ns) >= 3 and not set(g.split()) <= SMALL:
            warns.append(f"phrase \"{g}\" repeats on slides {sorted(ns)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("client_dir")
    ap.add_argument("--profile")
    a = ap.parse_args()
    cdir = os.path.abspath(a.client_dir)
    deck = json.load(open(os.path.join(cdir, "deck-data.json")))
    prof = P.load_profile(a.profile, client_dir=cdir, required=False)
    fails, warns = [], []
    big, vals = source_numbers(cdir, prof)

    slides = deck.get("slides") or []
    if not slides:
        fails.append("deck has no slides")
    if len(slides) > 10:
        warns.append(f"{len(slides)} slides: the visual-first outline targets about 8")
    for n, s in enumerate(slides, 1):
        lay = s.get("layout")
        if lay not in LAYOUTS:
            fails.append(f"slide {n}: unknown layout {lay!r} (known: {', '.join(LAYOUTS)})")
            continue
        req, opt = LAYOUTS[lay]
        for k in req - set(s):
            fails.append(f"slide {n} ({lay}): missing `{k}`")
        for k in set(s) - req - opt - COMMON:
            warns.append(f"slide {n} ({lay}): unknown field `{k}` (ignored by the renderer)")
        for k, img in (("image", s.get("image")),):
            if isinstance(img, dict) and img.get("src") and not img.get("frame") == "phone" and not img.get("alt"):
                warns.append(f"slide {n}: image has no `alt` text")
            if isinstance(img, dict) and img.get("src") and not re.match(r"^https?:", img["src"]) and not os.path.exists(os.path.join(cdir, img["src"])):
                fails.append(f"slide {n}: image not found: {img['src']}")
        ph = s.get("photo")
        if isinstance(ph, dict) and ph.get("src") and not os.path.exists(os.path.join(cdir, ph["src"])):
            warns.append(f"slide {n}: photo not found: {ph['src']}. Rendering with the plain theme background (fetch_image.py to add one)")

        # text budget
        def budget(field, text, key):
            lim = BUDGET[key]
            w = words(text)
            if lay == "cover" and field == "title":
                lim = 8
            if w > lim * 1.5:
                fails.append(f"slide {n} {field}: {w} words (limit {lim}). Cut it: \"{str(text)[:60]}\"")
            elif w > lim:
                warns.append(f"slide {n} {field}: {w} words (aim ≤ {lim})")
        if s.get("title"):
            budget("title", s["title"], "title")
        for f in ("subtitle", "body"):
            if s.get(f):
                budget(f, s[f], f)
        if s.get("impact"):
            budget("impact", s["impact"], "impact")
        for c in s.get("cards", []) or []:
            if c.get("body"):
                budget("card body", c["body"], "card_body")
        for g in s.get("gaps", []) or []:
            if g.get("body"):
                budget("gap body", g["body"], "gap_body")
        if s.get("evidence") and len(s["evidence"]) > 3:
            warns.append(f"slide {n}: {len(s['evidence'])} evidence bullets (max 3; prefer a screenshot)")

        # fact-trace
        for field, text in texts(s):
            clean = re.sub(r"[*]", "", text)
            for m in NUM.finditer(clean):
                tok = m.group(0).strip()
                v, u = num_value(tok)
                if v is None:
                    continue
                if v <= 10 and not u and not re.match(r"[$€£₹]", tok):
                    continue  # small counting numbers ("3 gaps", "Gap 01")
                if not traced(tok, big, vals):
                    fails.append(f"slide {n} {field}: number \"{tok}\" not found in any source (audit, scores, manual, research, profile)")

    slop_checks(slides, fails, warns)
    print(f"Deck lint: {len(slides)} slides")
    for x in fails:
        print("  FAIL " + x)
    for x in warns:
        print("  WARN " + x)
    if not fails:
        print("  OK" + (" (see warnings)" if warns else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
