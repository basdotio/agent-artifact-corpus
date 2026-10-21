#!/usr/bin/env python3
"""Caveman check: count every word on a screen, find its one button, flag tribe and hype
words, hold the headline to one sentence of at most 6 words, and keep a text field (if any)
right above the button.

    python3 check.py screens.txt [--max-words 15]      ('-' reads stdin)

Screen format (one file can hold a whole funnel):
    ---                        starts a new screen
    # name                     names the screen, not counted
    picture: <what it shows>   not counted, except words "in quotes" (they are on screen)
    [Button]                   the filled main button, counted
    {placeholder}              one text field (a search, an email), its placeholder counted
    (link)                     small grey text or a link, counted
    anything else              on-screen text, counted; the first line of it is the headline
    👇                         may sit between the field and the button

A word is anything with a letter or a digit in it, so "$24/month" is one word and
emoji, arrows and circled step numbers (① ② ③) are none.

Exit 0 when every screen passes, 1 when one fails, 2 on bad usage.
"""
import argparse
import re
import sys
import unicodedata

TRIBE_WORDS = [
    "actionable", "agentic", "ai-powered", "capabilities",
    "deploy", "digital transformation", "ecosystem", "empower", "end-to-end",
    "enterprise-grade", "frictionless", "game-changing", "govern", "governance", "holistic",
    "insights", "integration", "interoperability", "leverage", "mission-critical",
    "omnichannel", "optimize", "orchestrate", "orchestration", "paradigm",
    "platform", "robust", "scalable", "seamless", "seamlessly", "solution",
    "stakeholder", "streamline", "synergy", "transformative", "turnkey", "unlock", "utilize",
    "workflow",
]
# Hype: praise any site could print about itself. Cutting it removes no fact.
HYPE_WORDS = [
    "trusted", "world's best", "world-class", "leading", "#1", "best-in-class", "powerful",
    "revolutionary", "next-gen", "cutting-edge", "innovative", "all-in-one", "ultimate",
]
WEAK_BUTTONS = {
    "click here", "continue", "discover", "explore", "find out more", "get started", "go",
    "learn more", "next", "ok", "read more", "submit",
}
# Next to a field, the button names what the typing does (Search, Subscribe, Get the guide).
WEAK_FIELD_BUTTONS = WEAK_BUTTONS | {"enter", "send", "start", "try it", "done"}
TRIBE_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(w) for w in TRIBE_WORDS) + r")s?(?![\w-])", re.I
)
HYPE_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(w).replace("'", "['’]") for w in HYPE_WORDS) + r")(?![\w-])", re.I
)
FIELD_RE = re.compile(r"\{([^}]*)\}")
QUOTED_RE = re.compile(r"[\"“”]([^\"“”]+)[\"“”]")
MAX_HEADLINE_WORDS = 6


def is_word(token):
    return any(unicodedata.category(c).startswith("L") or c in "0123456789" for c in token)


def count_words(text):
    return sum(1 for t in text.split() if is_word(t))


def count_sentences(text):
    """Sentences end at . ! ? or … before a space or the end: "10.23" and "$24.99" end none."""
    return sum(1 for t in re.split(r"(?<=[.!?…])\s+", text) if count_words(t))


def parse(text):
    screens, cur = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if line == "---":
            cur = None
            continue
        if not line:
            continue
        if cur is None:
            cur = {"name": f"screen {len(screens) + 1}", "picture": False, "shown": [], "buttons": [], "text": [], "lines": []}
            screens.append(cur)
        # A heading is "#" then a space: "#1 bike shop" is a line of the screen.
        if re.match(r"#+(\s|$)", line):
            cur["name"] = line.lstrip("#").strip()
        elif line.lower().startswith("picture:"):
            cur["picture"] = True
            cur["shown"] += QUOTED_RE.findall(line)
        else:
            buttons = re.findall(r"\[([^\]]+)\]", line)
            fields = FIELD_RE.findall(line)
            cur["buttons"] += buttons
            cur["shown"].append(line)
            cur["lines"].append({"line": line, "buttons": len(buttons), "fields": len(fields)})
            link_only = re.search(r"\([^)]+\)", line) and not re.sub(r"\([^)]+\)", "", line).strip()
            text = line.replace("👇", "").strip()
            if not buttons and not fields and not link_only and count_words(text):
                cur["text"].append(text)
    return screens


def field_fails(screen):
    """One field at most, and it sits right above the button: only a 👇 may come between."""
    lines = screen["lines"]
    at = [i for i, l in enumerate(lines) if l["fields"]]
    n = sum(l["fields"] for l in lines)
    if not n:
        return []
    if n > 1:
        return [f"{n} text fields, keep one"]
    i = at[0]
    if lines[i]["buttons"] and lines[i]["line"].find("{") < lines[i]["line"].find("["):
        return []
    j = i + 1
    while j < len(lines) and not lines[j]["buttons"] and not count_words(lines[j]["line"]) and not lines[j]["fields"]:
        j += 1
    if j < len(lines) and lines[j]["buttons"]:
        return []
    return ["the text field is not right above the button: keep them together, a 👇 between at most"]


def grade(screen, max_words):
    shown = " ".join(screen["shown"])
    words = count_words(shown)
    fails, warns = [], []
    if words > max_words:
        fails.append(f"{words} words, max {max_words}")
    if len(screen["buttons"]) > 1:
        fails.append(f"{len(screen['buttons'])} filled buttons, keep one: " + ", ".join(screen["buttons"]))
    tribe = sorted({m.group(1).lower() for m in TRIBE_RE.finditer(shown)})
    if tribe:
        fails.append("tribe words: " + ", ".join(tribe))
    hype = sorted({m.group(1).lower().replace("’", "'") for m in HYPE_RE.finditer(shown)})
    if hype:
        fails.append("hype words, say what it is instead: " + ", ".join(hype))
    fails += field_fails(screen)
    if screen["text"]:
        headline = screen["text"][0]
        n = count_words(headline)
        if n > MAX_HEADLINE_WORDS:
            fails.append(f'headline {n} words, max {MAX_HEADLINE_WORDS}: "{headline}"')
        n = count_sentences(headline)
        if n > 1:
            fails.append(f'headline is {n} sentences, keep one: "{headline}"')
    if not screen["buttons"]:
        warns.append("no button (fine only on the last screen)")
    else:
        if "👇" not in shown:
            warns.append("no 👇 above the button")
        label = screen["buttons"][0].strip().lower()
        has_field = any(l["fields"] for l in screen["lines"])
        if has_field and (label in WEAK_FIELD_BUTTONS or not is_word(label)):
            warns.append(f'"{screen["buttons"][0]}" does not say what the typing does (Search, Subscribe)')
        elif label in WEAK_BUTTONS:
            warns.append(f'"{screen["buttons"][0]}" does not say what happens next')
    if not screen["picture"]:
        warns.append("no picture")
    return words, fails, warns


def main():
    ap = argparse.ArgumentParser(description="Caveman check for ads, pages and funnel screens.")
    ap.add_argument("file", help="screens file, or - for stdin")
    ap.add_argument("--max-words", type=int, default=15)
    args = ap.parse_args()
    try:
        text = sys.stdin.read() if args.file == "-" else open(args.file, encoding="utf-8").read()
    except OSError as e:
        print(f"check.py: {e}", file=sys.stderr)
        return 2
    screens = parse(text)
    if not screens:
        print("check.py: no screens found", file=sys.stderr)
        return 2
    failed = 0
    for s in screens:
        words, fails, warns = grade(s, args.max_words)
        failed += bool(fails)
        verdict = "FAIL" if fails else "PASS"
        n = len(s["buttons"])
        f = sum(l["fields"] for l in s["lines"])
        field = f", {f} field{'' if f == 1 else 's'}" if f else ""
        print(f"{verdict}  {s['name']}: {words} words, {n} button{'' if n == 1 else 's'}{field}")
        for f in fails:
            print(f"      fail: {f}")
        for w in warns:
            print(f"      warn: {w}")
    print(f"\n{len(screens) - failed} of {len(screens)} screens pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
