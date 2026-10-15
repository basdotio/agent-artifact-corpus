#!/usr/bin/env python3
"""Mechanical pre-flight for prose: flags, never decides.

Usage:
  python3 .claude/skills/human-copywriting/scripts/prose_check.py draft.md
  cat draft.md | python3 .claude/skills/human-copywriting/scripts/prose_check.py -
  python3 .../prose_check.py draft.md --json

Checks: em/en dashes (house style, hard fail), Oxford commas, stock AI phrases, not-X-but-Y
contrasts, trailing -ing riders, repeated sentence openers, and the sentence-length band.
Code blocks, inline code, URLs and markdown link targets are ignored. Exit 1 when a dash is
found, else 0. Everything else is advisory: read the sentence before changing it.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys

DASHES = {"—": "em dash", "–": "en dash"}

STOCK = [
    r"\bdelv(e|es|ing)\b", r"\bleverag(e|es|ing)\b", r"\butili[sz](e|es|ing)\b", r"\bseamless(ly)?\b",
    r"\brobust\b", r"\bpivotal\b", r"\bcrucial\b", r"\bmultifaceted\b", r"\blandscape\b", r"\brealm\b",
    r"\btapestry\b", r"\btestament\b", r"\belevat(e|es|ing)\b", r"\bunlock(s|ing)?\b",
    r"\bempower(s|ing)?\b", r"\bsupercharg(e|es|ing)\b", r"\bgame[- ]changer\b", r"\bmeticulous(ly)?\b",
    r"\bintricate\b", r"\bunderscor(e|es|ing)\b", r"\bshowcas(e|es|ing)\b", r"\bfoster(s|ing)?\b",
    r"\bin today's\b", r"\bwhen it comes to\b", r"\bit'?s worth noting\b", r"\bit is important to note\b",
    r"\bat the end of the day\b", r"\bin conclusion\b", r"\bfurthermore\b", r"\bmoreover\b",
    r"\blet'?s dive in\b", r"\bhere'?s the thing\b", r"\bat its core\b", r"\bthe real question\b",
    r"\bstudies (show|suggest)\b", r"\bexperts (agree|believe|say)\b", r"\bserves as\b",
    r"\bstands as\b", r"\bplays a (pivotal|crucial|key|vital) role\b", r"\bbest[- ]in[- ]class\b",
    r"\bworld[- ]class\b", r"\bcutting[- ]edge\b", r"\bnext level\b", r"\bdesigned to help\b",
    r"\bhope this helps\b", r"\bfeel free to\b", r"\bgreat question\b",
]
NOT_X_BUT_Y = [
    r"\bnot (just|only|merely|simply)\b[^.?!]{0,80}\bbut\b",
    r"\bit'?s not\b[^.?!]{0,60}[,;] it'?s\b",
    r"\bisn'?t (just|about)\b[^.?!]{0,80}[.;,] (it'?s|it is)\b",
    r"\bthis (doesn'?t|does not) mean\b",
]
ING_RIDER = r",\s(making|allowing|ensuring|enabling|highlighting|giving|helping|providing|creating|leading)\b"
OXFORD = re.compile(r"\b(\w+), (\w+(?: \w+){0,3}), (and|or) ")


def clean(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"^\s*(---|\|.*\|)\s*$", " ", text, flags=re.M)  # rules and table rows
    return text


def sentences(text: str) -> list[str]:
    # Rejoin hard-wrapped lines so one sentence across two lines counts once; headings and list
    # items stay separate units.
    units: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        marker = re.match(r"^(#+|[-*>]|\d+[.)])\s+", stripped)
        if not stripped:
            units.append("")
        elif marker or not units or not units[-1]:
            units.append(re.sub(r"^(#+|[-*>]|\d+[.)])\s+", "", stripped))
        else:
            units[-1] += " " + stripped
    out = []
    for u in units:
        out.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+", u) if s.strip())
    return out


def check(raw: str) -> dict:
    text = clean(raw)
    lines = text.split("\n")
    findings: dict[str, list] = {"dashes": [], "oxford": [], "stock": [], "not_x_but_y": [], "ing_rider": []}
    for n, line in enumerate(lines, 1):
        for ch, name in DASHES.items():
            if ch in line:
                findings["dashes"].append({"line": n, "kind": name, "text": line.strip()[:140]})
        for m in OXFORD.finditer(line):
            findings["oxford"].append({"line": n, "text": m.group(0)})
        for pat in STOCK:
            for m in re.finditer(pat, line, re.I):
                findings["stock"].append({"line": n, "phrase": m.group(0)})
        for pat in NOT_X_BUT_Y:
            for m in re.finditer(pat, line, re.I):
                findings["not_x_but_y"].append({"line": n, "text": m.group(0)[:100]})
        for m in re.finditer(ING_RIDER, line, re.I):
            findings["ing_rider"].append({"line": n, "text": line[max(0, m.start() - 40): m.end() + 30].strip()})

    sents = sentences(text)
    lengths = [len(s.split()) for s in sents]
    openers = []
    for i in range(len(sents) - 2):
        firsts = {s.split()[0].lower().strip('"\'') for s in sents[i: i + 3] if s.split()}
        if len(firsts) == 1:
            openers.append({"word": firsts.pop(), "sentence": sents[i][:80]})
    n = len(lengths)
    stats = {
        "words": sum(lengths),
        "sentences": n,
        "mean_sentence_words": round(statistics.fmean(lengths), 1) if n else 0,
        "band_12_26_share": round(sum(1 for x in lengths if 12 <= x <= 26) / n, 2) if n else 0,
        "short_share_le8": round(sum(1 for x in lengths if x <= 8) / n, 2) if n else 0,
        "burstiness_cv": round(statistics.pstdev(lengths) / statistics.fmean(lengths), 2) if n > 1 else None,
    }
    findings["repeated_openers"] = openers
    return {"stats": stats, "findings": findings}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="file to check, or - for stdin")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    raw = sys.stdin.read() if a.path == "-" else open(a.path, encoding="utf-8").read()
    r = check(raw)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        s = r["stats"]
        print(f"{s['words']} words, {s['sentences']} sentences, mean {s['mean_sentence_words']} words")
        print(f"12-26 word band {s['band_12_26_share']:.0%} (inspect rhythm if well over 60%), "
              f"short <=8 {s['short_share_le8']:.0%}, burstiness {s['burstiness_cv']}")
        for key, label in [("dashes", "DASHES (house style, must fix)"), ("oxford", "Oxford comma?"),
                           ("not_x_but_y", "Not X but Y"), ("ing_rider", "Trailing -ing rider"),
                           ("stock", "Stock phrase"), ("repeated_openers", "3 sentences, same opener")]:
            items = r["findings"][key]
            if items:
                print(f"\n{label}: {len(items)}")
                for it in items[:25]:
                    print("  ", json.dumps(it, ensure_ascii=False))
    return 1 if r["findings"]["dashes"] else 0


if __name__ == "__main__":
    sys.exit(main())
