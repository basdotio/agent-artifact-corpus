"""Shared by the checkers: the project's store folder, its configuration, the languages App Store Connect knows."""
import json, os, re, sys

sys.dont_write_bytecode = True
from fnmatch import fnmatch

STORE = os.path.abspath(os.environ.get("STORE_DIR", "store"))

# A language's code in the store folder (lower case) and the name App Store Connect lists it under. The store has one
# Latin American Spanish, "Spanish (Mexico)". Apple adds languages: the language menu in App Store Connect is the
# authority, and a code that is missing here is simply shown as its code.
CONNECT = {
    "ar": "Arabic", "ca": "Catalan", "zh": "Chinese (Simplified)", "zh-hant": "Chinese (Traditional)", "hr": "Croatian",
    "cs": "Czech", "da": "Danish", "nl": "Dutch", "en-au": "English (Australia)", "en-ca": "English (Canada)",
    "en-gb": "English (U.K.)", "en": "English (U.S.)", "fi": "Finnish", "fr": "French", "fr-ca": "French (Canada)",
    "de": "German", "el": "Greek", "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian", "id": "Indonesian", "it": "Italian",
    "ja": "Japanese", "ko": "Korean", "ms": "Malay", "no": "Norwegian", "pl": "Polish", "pt-br": "Portuguese (Brazil)",
    "pt": "Portuguese (Portugal)", "ro": "Romanian", "ru": "Russian", "sk": "Slovak", "es-419": "Spanish (Mexico)",
    "es-mx": "Spanish (Mexico)", "es": "Spanish (Spain)", "sv": "Swedish", "th": "Thai", "tr": "Turkish",
    "uk": "Ukrainian", "vi": "Vietnamese", "bn": "Bangla", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam",
    "mr": "Marathi", "or": "Odia", "pa": "Punjabi", "sl": "Slovenian", "ta": "Tamil", "te": "Telugu", "ur": "Urdu",
}

def path(*parts):
    return os.path.join(STORE, *parts)

def shown(file):
    return os.path.relpath(file)

def read(*parts):
    with open(path(*parts), encoding="utf-8") as f:
        return json.load(f)

def config():
    if not os.path.exists(path("store.config.json")):
        sys.exit(f"no {shown(path('store.config.json'))}: run this from the project's root (or set STORE_DIR)")
    return read("store.config.json")

def exempt(cfg, where):
    """Whether a text's place (frames.2.ownName, video.cards.task.title) is listed in "notAppText"."""
    return any(fnmatch(where, pattern) for pattern in cfg.get("notAppText", []))

# ---- the app's own texts ---------------------------------------------------------------------------------------------
PLACEHOLDER = re.compile(r"%(?:\d+\$)?(?:#@\w+@|[-+0 #]*\d*(?:\.\d+)?(?:ll|l|h)?[@dDuUxXfFeEgGcCsSi])|\{\{?\w*\}?\}|\$\{\w+\}")

def app_texts(code):
    """store/app-texts/<code>.json as (keyed texts, the set of all texts, patterns of the ones with placeholders);
    None when the project has not provided the file."""
    if not os.path.exists(path("app-texts", f"{code}.json")):
        return None
    raw = read("app-texts", f"{code}.json")
    keyed = raw if isinstance(raw, dict) else {}
    texts = set()
    for value in (raw.values() if isinstance(raw, dict) else raw):
        texts.update(value if isinstance(value, list) else [value])
    patterns = []
    for text in texts:
        if PLACEHOLDER.search(text):
            pieces = [re.escape(piece) for piece in PLACEHOLDER.split(text)]
            if any(piece.strip() for piece in PLACEHOLDER.split(text)):
                patterns.append(re.compile("(.+?)".join(pieces), re.S))
    return keyed, texts, patterns

def said_by_app(text, known, joiners=(" · ", " • ", " | ")):
    """Whether the app says this: one of its texts as it stands, one with its placeholders filled, or several of them
    joined the way a screen joins them."""
    _, texts, patterns = known
    bare = {t.rstrip(".。") for t in texts}
    def one(piece):
        # as it stands, without its full stop, or with the one the app's text ends on
        forms = (piece, piece.rstrip(".。"), piece + ".", piece + "。")
        return any(form in texts or form in bare for form in forms[:2]) or any(p.fullmatch(form) for p in patterns for form in forms)
    if one(text):
        return True
    return any(joiner in text and all(one(piece) for piece in text.split(joiner)) for joiner in joiners)

def quoted_in(said, text):
    """Whether a text quotes what the app says: the app's text without its full stop, its placeholders filled."""
    said = said.rstrip(".。")
    if not PLACEHOLDER.search(said):
        return said in text
    return re.search(".+?".join(re.escape(piece) for piece in PLACEHOLDER.split(said)), text) is not None
