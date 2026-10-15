#!/usr/bin/env python3
"""Checks the text of the App Store product page in every language and writes the page it is copied from.

    python3 listing.py            checks every language of store.config.json and writes store/LISTING.md
    python3 listing.py de fr      checks only these, writes nothing
    python3 listing.py --check    checks every language, writes nothing

Run it from the project's root. One file per language, store/listing/<code>.json:

    {"name": "…",              optional, at most 30 characters; the app's name in that language's store
     "subtitle": "…",          at most 30, under the name
     "promotional": "…",       at most 170, above the description; the only text that changes without a new version
     "keywords": "a,b,c",      at most 100, commas without spaces; the store searches the name, the subtitle and this
     "description": ["…", ""]} at most 4000 once joined with line breaks; one item per line, "" is an empty line

A description follows the source language's line for line: a paragraph, a "• " point or an empty line in the same
place, so that every language can be compared and corrected as one text. "listing" in store.config.json adds the
project's own rules: "mustMention" (fields that have to contain the app's name, "app" in the configuration; leave it
empty when the name is written differently in some language), "quotedKeys" (keys of store/app-texts/<code>.json
whose texts the description quotes: where it quotes a button, it quotes the button the app shows in that language).
"forbid" lists characters the project never uses."""
import os, re, sys
sys.dont_write_bytecode = True
from store import CONNECT, app_texts, config, path, read, quoted_in, shown

LIMITS = {"name": 30, "subtitle": 30, "promotional": 170, "keywords": 100, "description": 4000}
REQUIRED = ["subtitle", "promotional", "keywords", "description"]

def kind(line):
    return "empty" if line == "" else "point" if line.startswith("• ") else "text"

def check(cfg, code):
    rules = cfg.get("listing", {})
    if not os.path.exists(path("listing", f"{code}.json")):
        return [f"no file {shown(path('listing', f'{code}.json'))}"]
    source, ours, problems = read("listing", f"{cfg['source']}.json"), read("listing", f"{code}.json"), []
    missing = [key for key in REQUIRED if key not in ours]
    unknown = [key for key in ours if key not in LIMITS]
    if missing or unknown:
        return [f"missing {missing}, unknown {unknown}; the keys are {list(LIMITS)}"]
    if not isinstance(ours["description"], list) or not all(isinstance(line, str) for line in ours["description"]):
        return ["description must be a list of lines"]
    app, name = cfg.get("app", ""), ours.get("name") or cfg.get("app", "")
    fields = {**ours, "description": "\n".join(ours["description"])}
    for field, text in fields.items():
        if not isinstance(text, str) or not text.strip():
            problems.append(f"{field} is empty")
            continue
        if len(text) > LIMITS[field]:
            problems.append(f"{field}: {len(text)} characters, the store allows {LIMITS[field]}")
        for mark in cfg.get("forbid", []):
            if mark in text:
                problems.append(f"{field}: “{mark}”")
    for field in ("name", "subtitle", "promotional", "keywords"):
        text = fields.get(field, "")
        if text != text.strip() or "\n" in text or "  " in text:
            problems.append(f"{field}: stray space or line break")
    kinds, theirs = [kind(line) for line in source["description"]], [kind(line) for line in ours["description"]]
    if kinds != theirs:
        problems.append(f"description: the lines are {theirs}, the source has {kinds}")
    for number, line in enumerate(ours["description"], start=1):
        if line != line.strip() or "  " in line:
            problems.append(f"description, line {number}: stray space")
    for field in rules.get("mustMention", []):
        if app and app not in fields.get(field, ""):
            problems.append(f"{field}: the name {app} is missing")
    quoted = rules.get("quotedKeys", [])
    if quoted:
        known = app_texts(code)
        if known is None:
            problems.append(f"no {shown(path('app-texts', f'{code}.json'))}: cannot check what the description quotes")
        else:
            for key in quoted:
                said = known[0].get(key)
                said = said[0] if isinstance(said, list) else said
                if said is None:
                    problems.append(f"the app has no text “{key}” in this language")
                elif not quoted_in(said, fields["description"]):
                    problems.append(f"description: the app says “{said.rstrip('.。')}” ({key}), the text does not quote it")
    keywords = fields["keywords"].split(",")
    if any(word != word.strip() or not word for word in keywords):
        problems.append("keywords: commas without spaces, no empty word")
    lowered = [word.casefold() for word in keywords]
    if len(set(lowered)) != len(lowered):
        problems.append("keywords: a word twice")
    taken = set(re.split(r"[\s,.;:·–—-]+", (fields["subtitle"] + " " + name + " " + app).casefold())) - {""}
    for word in lowered:
        if word in taken:
            problems.append(f"keywords: “{word}” already stands in the name or the subtitle, which the store searches anyway")
    return problems

def block(text):
    return "\n".join("    " + line if line else "" for line in text.split("\n"))

def document(cfg):
    """The page the texts are copied from into App Store Connect, each with its length and the store's limit."""
    out = ["# App Store product page: the texts in every language", "",
           "Generated by `listing.py`; change a text in `store/listing/<code>.json`, never here. The number in brackets is",
           "the text's length and the store's limit. A language's pictures and video are in `store/out/<code>/`.", ""]
    for code in cfg["languages"]:
        listing = read("listing", f"{code}.json")
        out += [f"## {CONNECT.get(code, code)} (`{code}`)", ""]
        for title, field in (("Name", "name"), ("Subtitle", "subtitle"), ("Promotional Text", "promotional"), ("Keywords", "keywords"), ("Description", "description")):
            if field not in listing:
                continue
            text = "\n".join(listing[field]) if field == "description" else listing[field]
            out += [f"**{title}** ({len(text)} / {LIMITS[field]})", "", block(text), ""]
    return "\n".join(out).rstrip("\n") + "\n"

if __name__ == "__main__":
    cfg = config()
    arguments = [a for a in sys.argv[1:] if a != "--check"]
    failed = False
    for code in arguments or cfg["languages"]:
        found = check(cfg, code)
        failed = failed or bool(found)
        print(f"{code}: {len(found)} problem(s)")
        for problem in found:
            print("  " + problem)
    if failed:
        sys.exit(1)
    if not arguments and "--check" not in sys.argv:
        with open(path("LISTING.md"), "w", encoding="utf-8") as f:
            f.write(document(cfg))
        print(f"written: {shown(path('LISTING.md'))}")
