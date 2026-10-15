#!/usr/bin/env python3
"""Checks the texts of the frames, the header and the video in every language against the source language.

    python3 texts.py            every language of store.config.json
    python3 texts.py de fr      only these

Run it from the project's root. For each language it reads store/frames/texts/<code>.json,
store/header/texts/<code>.json and store/video/texts/<code>.json and reports:

  * a file, a frame, a scene, a card or a field the source has and the language has not (or the other way round);
  * a claim with another number of lines than the source's, an empty text, a stray space, a character the project
    forbids ("forbid" in store.config.json);
  * a text on a drawn screen or card that the app does not say in that language. App Store materials have to show the
    app: when store/app-texts/<code>.json exists (a JSON object of the app's texts by key, or a list of them), every
    text of a screen or a card must be one of them, word for word. The claim, the header and the scene texts are the
    store's own and are not checked; other places that are not the app's text (the app's name on a frame, an example
    the person would type) are listed in "notAppText" by their place, as this script prints places: "frames.2.title"
    is the field "title" of the second frame, "video.cards.<card>.<field>" a field of a card; "*" stands for anything
    ("frames.*.app").

What fits where is not checked here: the renderers measure every line and warn."""
import os, sys
sys.dont_write_bytecode = True
from store import app_texts, config, exempt, path, read, said_by_app, shown

def leaves(node, where):
    """Every text of a nested structure with its place: ("frames.1.title", "…")."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from leaves(value, f"{where}.{key}")
    elif isinstance(node, list):
        for number, value in enumerate(node, start=1):
            yield from leaves(value, f"{where}.{number}")
    else:
        yield where, node

def shape(node):
    """The structure without the texts and without the number of lines of a list of lines."""
    if isinstance(node, dict):
        return {key: shape(value) for key, value in node.items()}
    if isinstance(node, list):
        return "lines" if all(isinstance(v, str) for v in node) else [shape(v) for v in node]
    return "text"

def differences(ours, source, where):
    if where == "header.lines":                   # a longer slogan may take one line more
        if not isinstance(ours, list) or not ours:
            return [f"{where}: a list of lines is needed"]
        return [f"{where}.{n}: needs {sorted(source[0])}" for n, line in enumerate(ours, start=1)
                if not isinstance(line, dict) or sorted(line) != sorted(source[0])]
    if type(ours) is not type(source):
        return [f"{where}: the source has {shape(source)!r} here"]
    if isinstance(source, dict):
        found = [f"{where}.{key} is missing" for key in source if key not in ours]
        found += [f"{where}.{key} is not in the source language" for key in ours if key not in source]
        for key in source:
            if key in ours:
                found += differences(ours[key], source[key], f"{where}.{key}")
        return found
    if isinstance(source, list) and shape(source) != "lines":
        if len(ours) != len(source):
            return [f"{where}: {len(ours)} items, the source has {len(source)}"]
        return [d for n, (a, b) in enumerate(zip(ours, source), start=1) for d in differences(a, b, f"{where}.{n}")]
    return []

def check(cfg, code):
    source, problems, notes = cfg["source"], [], []
    loaded = {}
    for part in ("frames", "header", "video"):
        if not os.path.exists(path(part, "texts", f"{source}.json")):
            continue                                  # the project does not make this asset
        if not os.path.exists(path(part, "texts", f"{code}.json")):
            problems.append(f"no file {shown(path(part, 'texts', f'{code}.json'))}")
            continue
        ours, theirs = read(part, "texts", f"{code}.json"), read(part, "texts", f"{source}.json")
        loaded[part] = ours
        # A place is named the same way everywhere: frames.2.title, header.lines.1.text, video.cards.<card>.<field>.
        ours_at, theirs_at = (ours.get("frames", []), theirs.get("frames", [])) if part == "frames" else (ours, theirs)
        problems += differences(ours_at, theirs_at, part)
        if part == "frames":
            for n, (a, b) in enumerate(zip(ours.get("frames", []), theirs.get("frames", [])), start=1):
                if len(a.get("claim", [])) != len(b.get("claim", [])):
                    problems.append(f"frames.{n}.claim: {len(a.get('claim', []))} lines, the source has {len(b.get('claim', []))}")
        for where, text in leaves(ours_at, part):
            if not isinstance(text, str):
                continue
            if not text.strip():
                problems.append(f"{where} is empty")
            elif text != text.strip() or "  " in text:
                problems.append(f"{where}: stray space in “{text}”")
            for mark in cfg.get("forbid", []):
                if mark in text:
                    problems.append(f"{where}: “{mark}” in “{text}”")
    known = app_texts(code)
    if known is None:
        notes.append(f"no {shown(path('app-texts', f'{code}.json'))}: the texts on the screens and cards were not compared with the app's")
    else:
        screens = []
        for n, frame in enumerate(loaded.get("frames", {}).get("frames", []), start=1):
            screens += [(f"frames.{n}.{key}", value) for key, value in frame.items() if key != "claim"]
        for name, card in loaded.get("video", {}).get("cards", {}).items():
            screens += [(f"video.cards.{name}.{key}", value) for key, value in card.items()]
        for where, text in screens:
            if isinstance(text, str) and text.strip() and not exempt(cfg, where) and not said_by_app(text, known):
                problems.append(f"{where}: the app does not say “{text}” in this language")
    return problems, notes

if __name__ == "__main__":
    cfg = config()
    failed = False
    for code in sys.argv[1:] or cfg["languages"]:
        problems, notes = check(cfg, code)
        failed = failed or bool(problems)
        print(f"{code}: {len(problems)} problem(s)")
        for line in problems:
            print("  " + line)
        for line in notes:
            print("  note: " + line)
    sys.exit(1 if failed else 0)
