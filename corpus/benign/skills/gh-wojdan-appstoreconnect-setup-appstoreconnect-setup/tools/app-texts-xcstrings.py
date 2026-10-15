#!/usr/bin/env python3
"""Writes store/app-texts/<code>.json, the app's own texts in each language, from Xcode String Catalogs.

    python3 app-texts-xcstrings.py <Localizable.xcstrings> [more catalogs…]

Run it from the project's root, with all of the app's catalogs in one call (each run writes the files anew). Every
language a catalog holds gets one file: a JSON object from the text's key to the
text, or to the list of its forms when it has several (plural forms, device variations). The checkers use it to make
sure a screen drawn for the store says what the app says. An app that keeps its texts elsewhere (.strings, strings.xml,
ARB, i18n JSON) needs its own few lines that write the same file."""
import json, os, sys
sys.dont_write_bytecode = True
from store import path, shown

# Xcode's code of a language and the code its folder has here.
CODES = {"zh-hans": "zh", "zh-hant": "zh-hant", "pt-pt": "pt", "pt-br": "pt-br", "nb": "no", "es-mx": "es-419"}

def values(node):
    """Every string of one localization: its own value and the values of its variations and substitutions."""
    if isinstance(node, dict):
        if isinstance(node.get("stringUnit"), dict) and isinstance(node["stringUnit"].get("value"), str):
            yield node["stringUnit"]["value"]
        for key, value in node.items():
            if key != "stringUnit":
                yield from values(value)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    texts = {}
    for catalog in sys.argv[1:]:
        with open(catalog, encoding="utf-8") as f:
            data = json.load(f)
        source = data.get("sourceLanguage", "en")
        for key, entry in data.get("strings", {}).items():
            localizations = entry.get("localizations", {})
            if source not in localizations and key.strip():
                texts.setdefault(source, {})[key] = key          # the key is the source text
            for language, node in localizations.items():
                found = list(dict.fromkeys(values(node)))
                if found:
                    texts.setdefault(language, {})[key] = found[0] if len(found) == 1 else found
    os.makedirs(path("app-texts"), exist_ok=True)
    for language, entries in sorted(texts.items()):
        code = CODES.get(language.lower(), language.lower())
        with open(path("app-texts", f"{code}.json"), "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
        print(f"{shown(path('app-texts', f'{code}.json'))}  {len(entries)} texts")
