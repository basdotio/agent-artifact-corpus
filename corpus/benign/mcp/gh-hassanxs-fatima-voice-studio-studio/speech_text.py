"""What the voice actually reads: the script with the pronunciation dictionary applied and numbers spelled out.

The script itself is never changed: subtitles and the batch keep your text ("CJNG", "1913"), and only the text
sent to the engine is rewritten ("ce jota ene ge", "mil novecientos trece").

Numbers are spelled out in English, Spanish, French, German, Italian and Portuguese. Russian, Japanese, Korean
and Chinese are left as digits: the voice model reads them itself, and spelling them out correctly needs grammar
(case, counters) that a rule can't guess.
"""
import csv
import datetime as dt
import io
import json
import re
import threading
import uuid
from pathlib import Path

from . import config

NUM_LANGS = {"en": "en", "es": "es", "fr": "fr", "de": "de", "it": "it", "pt": "pt"}

WORDS = {  # per language: percent, "to" in ranges, scale words for k / M / bn, joiner before a currency, currencies
    "en": {"and": "and", "pct": "percent", "to": "to", "scale": ("thousand", "million", "billion"), "of": "",
           "cur": {"$": ("dollar", "dollars"), "€": ("euro", "euros"), "£": ("pound", "pounds")}},
    "es": {"and": "con", "pct": "por ciento", "to": "a", "scale": ("mil", "millones", "mil millones"), "of": "de",
           "cur": {"$": ("dólar", "dólares"), "€": ("euro", "euros"), "£": ("libra", "libras")}},
    "fr": {"and": "et", "pct": "pour cent", "to": "à", "scale": ("mille", "millions", "milliards"), "of": "de",
           "cur": {"$": ("dollar", "dollars"), "€": ("euro", "euros"), "£": ("livre", "livres")}},
    "de": {"and": "und", "pct": "Prozent", "to": "bis", "scale": ("tausend", "Millionen", "Milliarden"), "of": "",
           "cur": {"$": ("Dollar", "Dollar"), "€": ("Euro", "Euro"), "£": ("Pfund", "Pfund")}},
    "it": {"and": "e", "pct": "per cento", "to": "al", "scale": ("mila", "milioni", "miliardi"), "of": "di",
           "cur": {"$": ("dollaro", "dollari"), "€": ("euro", "euro"), "£": ("sterlina", "sterline")}},
    "pt": {"and": "e", "pct": "por cento", "to": "a", "scale": ("mil", "milhões", "bilhões"), "of": "de",
           "cur": {"$": ("dólar", "dólares"), "€": ("euro", "euros"), "£": ("libra", "libras")}},
}
SCALE = {"k": 0, "mil": 0, "thousand": 0, "m": 1, "mm": 1, "million": 1, "millones": 1, "millón": 1, "mio": 1,
         "bn": 2, "b": 2, "billion": 2, "mil millones": 2}

# A number: 1,234,567.89 / 1.234.567,89 / 1 234 567 / 3,5 / 3.5 / 42
NUM = r"\d{1,3}(?:[.,   ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?"


def _parse(token: str, lang: str) -> float | int | None:
    """Read a number written the way that language (or Mexico/US) writes it. A group of exactly 3 digits after a
    separator means thousands; anything else after a separator is decimals."""
    t = token.replace(" ", " ").replace(" ", " ")
    seps = [c for c in t if c in ".,  "]
    if not seps:
        return int(t)
    groups = re.split(r"[.,  ]", t)
    last_sep = seps[-1]
    if len(seps) == 1 and len(groups[-1]) != 3:  # 3,5  3.25  -> decimal
        return float(t.replace(",", ".").replace(" ", ""))
    if len(seps) >= 1 and all(len(g) == 3 for g in groups[1:]):  # 1,000  1.000.000  1 000
        if len(seps) == 1 and lang == "en" and last_sep == ".":
            return float(t)  # "1.500" in English text is a decimal
        return int("".join(groups))
    # 1.234,56 or 1,234.56: the last separator is the decimal point
    whole = "".join(groups[:-1])
    return float(f"{whole}.{groups[-1]}")


DECIMAL = {"en": ("point", "point"), "es": ("coma", "punto"), "fr": ("virgule", "point"), "de": ("Komma", "Punkt"),
           "it": ("virgola", "punto"), "pt": ("vírgula", "ponto")}  # (written with a comma, written with a dot)
CENTS = {"en": {"$": "cents", "€": "cents", "£": "pence"}, "es": {"$": "centavos", "€": "céntimos", "£": "peniques"},
         "fr": {"$": "cents", "€": "centimes", "£": "pence"}, "de": {"$": "Cent", "€": "Cent", "£": "Pence"},
         "it": {"$": "centesimi", "€": "centesimi", "£": "penny"}, "pt": {"$": "centavos", "€": "cêntimos", "£": "pence"}}


def number(token: str, value, lang: str) -> str:
    """A number in words; decimals are read the way they're written: "3,5" -> tres coma cinco."""
    if isinstance(value, float) and not value.is_integer() and lang != "en":
        decimals = re.split(r"[.,]", token)[-1]
        word = DECIMAL[lang][0 if token.rfind(",") > token.rfind(".") else 1]
        tail = " ".join(_words(int(c), lang) for c in decimals) if decimals.startswith("0") else _words(int(decimals), lang)
        return f"{_words(int(value), lang)} {word} {tail}"
    return _words(value, lang)


def _words(value, lang: str, to: str = "cardinal") -> str:
    from num2words import num2words
    code = NUM_LANGS[lang]
    try:
        return num2words(value, lang=code, to=to)
    except (NotImplementedError, OverflowError, ValueError, TypeError):
        return num2words(value, lang=code)


def spell_numbers(text: str, lang: str) -> str:
    if lang not in NUM_LANGS:
        return text
    w = WORDS[lang]

    def money(m):
        sym, num, scale = m["sym"] or m["sym2"], m["num"], (m["scale"] or "").lower().strip()
        value = _parse(num, lang)
        if value is None:
            return m[0]
        unit_one, unit_many = w["cur"][sym]
        # "$5 millones de dólares", "$300 USD": the currency is already said after the amount
        of = rf"(?:{w['of']}\s+)?" if w["of"] else ""
        named = re.match(rf"\s+{of}(?:{unit_one}|{unit_many}|USD|EUR|GBP|dlls?\.?)\b",
                         m.string[m.end():], re.IGNORECASE)
        if scale in SCALE:
            words = f"{number(num, value, lang)} {w['scale'][SCALE[scale]]}"
            if named:  # "$5 millones de dólares": the currency is already said
                return words
            joiner = f" {w['of']} " if w["of"] and SCALE[scale] > 0 else " "
            return f"{words}{joiner}{unit_many}"
        if named:
            return number(num, value, lang)
        if isinstance(value, float) and not value.is_integer():
            whole, cents = int(value), round((value - int(value)) * 100)
            cent_word = CENTS[lang][sym]
            unit = unit_many if whole != 1 else unit_one
            return f"{_words(whole, lang)} {unit} {w['and']} {_words(cents, lang)} {cent_word}"
        return f"{_words(value, lang)} {unit_one if value == 1 else unit_many}"

    scale_words = r"(?:k|K|M|MM|bn|B|million|millones|millón|mil millones|thousand|billion|mio)"
    text = re.sub(rf"(?P<sym>[$€£])\s?(?P<num>{NUM})(?:\s?(?P<scale>{scale_words})\b)?"
                  rf"|(?P<num2>{NUM})\s?(?P<sym2>[$€£])", lambda m: money(m) if m["num"] else
                  money_suffix(m, lang), text)
    # 25% / 25 %
    text = re.sub(rf"({NUM})\s?%", lambda m: f"{number(m[1], _parse(m[1], lang), lang)} {w['pct']}", text)
    # 5:30 (times)
    text = re.sub(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", lambda m: _time(int(m[1]), int(m[2]), lang), text)
    # ordinals: 1st 2nd 3rd 4th / 1º 1ª 1.º / 1er 2e
    if lang == "en":
        text = re.sub(r"\b(\d+)(st|nd|rd|th)\b", lambda m: _words(int(m[1]), lang, "ordinal"), text)
    elif lang in ("es", "pt", "it"):
        text = re.sub(r"\b(\d+)\.?([ºª°])", lambda m: _ordinal_romance(int(m[1]), m[2], lang), text)
    elif lang == "fr":
        text = re.sub(r"\b(\d+)(er|re|e|ème)\b", lambda m: _words(int(m[1]), lang, "ordinal"), text)
    # year ranges: 1990-1995
    text = re.sub(r"\b(1[1-9]\d\d|20\d\d)\s?[-–]\s?(1[1-9]\d\d|20\d\d)\b",
                  lambda m: f"{_words(int(m[1]), lang, 'year')} {w['to']} {_words(int(m[2]), lang, 'year')}", text)
    # other numbers
    def plain(m):
        token = m[0]
        value = _parse(token, lang)
        if value is None:
            return token
        after = text_after(m)
        # Spanish/Portuguese/Italian/French words ending in 1 agree with the noun's gender: leave those to the model.
        if lang in ("es", "pt", "it", "fr") and isinstance(value, int) and value % 10 == 1 and value % 100 != 11 \
                and re.match(r"\s+[^\W\d_]", after):
            return token
        if isinstance(value, int) and re.fullmatch(r"1[1-9]\d\d|20\d\d", token):
            return _words(value, lang, "year")  # a bare four-digit number from 1100 to 2099 is almost always a year
        return number(token, value, lang)

    def text_after(m):
        return m.string[m.end(): m.end() + 30]

    return re.sub(rf"(?<![\w.,])(?<![\w]-)(?:{NUM})(?![\w])", plain, text)  # not 1000 in T-1000


def money_suffix(m, lang: str) -> str:
    """'5 €' / '5€' (amount before the symbol)."""
    value = _parse(m["num2"], lang)
    one, many = WORDS[lang]["cur"][m["sym2"]]
    return f"{_words(value, lang)} {one if value == 1 else many}"


def _time(h: int, mins: int, lang: str) -> str:
    hw, mw = _words(h, lang), _words(mins, lang)
    if lang == "en":
        return f"{hw} o'clock" if mins == 0 else f"{hw} oh {mw}" if mins < 10 else f"{hw} {mw}"
    if lang == "es":
        return f"{hw} en punto" if mins == 0 else f"{hw} y media" if mins == 30 else f"{hw} y {mw}"
    if lang == "fr":
        return f"{hw} heures" if mins == 0 else f"{hw} heures {mw}"
    if lang == "de":
        return f"{hw} Uhr" if mins == 0 else f"{hw} Uhr {mw}"
    return f"{hw}" if mins == 0 else f"{hw} e {mw}"  # it, pt


def _ordinal_romance(n: int, mark: str, lang: str) -> str:
    word = _words(n, lang, "ordinal")
    if mark == "ª":  # feminine: primero -> primera, vigésimo primero -> vigésima primera
        word = " ".join(re.sub(r"o$", "a", w) for w in word.split())
    elif lang == "es" and n in (1, 3):  # "1.º lugar" -> primer
        word = {"primero": "primer", "tercero": "tercer"}.get(word, word)
    return word


# ---- the pronunciation dictionary ------------------------------------------------

DEFAULTS = [  # a few to start with; all editable on the Pronunciation page
    ("EE.UU.", "Estados Unidos", "es", True), ("EEUU", "Estados Unidos", "es", True),
    ("Sr.", "señor", "es", True), ("Sra.", "señora", "es", True), ("Dr.", "doctor", "es", True),
    ("km", "kilómetros", "es", True), ("kg", "kilos", "es", True),
    ("Dr.", "Doctor", "en", True), ("Mr.", "Mister", "en", True), ("Mrs.", "Missus", "en", True),
    ("vs.", "versus", "en", False), ("e.g.", "for example", "en", False), ("etc.", "et cetera", "en", False),
    ("km", "kilometres", "en", True), ("kg", "kilograms", "en", True),
]


class Dictionary:
    """data/dictionary.json: [{id, from, to, language ("" = every language), case (match capitals exactly)}]"""

    def __init__(self, path: Path = config.DATA / "dictionary.json"):
        self.path = path
        self._lock = threading.Lock()
        if not path.exists():
            self.entries = [{"id": uuid.uuid4().hex[:8], "from": f, "to": t, "language": lang, "case": case,
                             "created": dt.datetime.now().isoformat(timespec="seconds")} for f, t, lang, case in DEFAULTS]
            self._save()
        else:
            self.entries = json.loads(path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.entries, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def add(self, src: str, dst: str, language: str = "", case: bool = False) -> dict:
        src, dst = src.strip(), dst.strip()
        if not src or not dst:
            raise ValueError("Fill in both the written form and how to say it.")
        if language and language not in config.LANGUAGE_NAMES:
            raise ValueError("Unsupported language")
        with self._lock:
            if any(e["from"].lower() == src.lower() and e["language"] == language for e in self.entries):
                raise ValueError(f"“{src}” is already in the dictionary for that language. Edit it instead.")
            e = {"id": uuid.uuid4().hex[:8], "from": src, "to": dst, "language": language, "case": bool(case),
                 "created": dt.datetime.now().isoformat(timespec="seconds")}
            self.entries.append(e)
            self._save()
        return e

    def update(self, eid: str, **fields) -> dict:
        with self._lock:
            e = next((x for x in self.entries if x["id"] == eid), None)
            if not e:
                raise KeyError(eid)
            for k in ("from", "to"):
                if fields.get(k) is not None:
                    if not str(fields[k]).strip():
                        raise ValueError("Fill in both the written form and how to say it.")
                    e[k] = str(fields[k]).strip()
            if fields.get("language") is not None:
                e["language"] = fields["language"]
            if fields.get("case") is not None:
                e["case"] = bool(fields["case"])
            self._save()
            return e

    def delete(self, eid: str) -> None:
        with self._lock:
            self.entries = [x for x in self.entries if x["id"] != eid]
            self._save()

    # ---- import / export ----

    def export(self, fmt: str = "csv", language: str | None = None) -> bytes:
        """CSV (UTF-8 with BOM, so Excel shows accents) or JSON; one language or all."""
        rows = [e for e in sorted(self.entries, key=lambda e: (e["language"], e["from"].lower()))
                if language is None or e["language"] in (language, "")]
        if fmt == "json":
            return json.dumps([{"written": e["from"], "said": e["to"], "language": e["language"] or "all",
                                "exact_capitals": e["case"]} for e in rows], indent=2, ensure_ascii=False).encode("utf-8")
        out = io.StringIO()
        w = csv.writer(out, lineterminator="\r\n")
        w.writerow(["written", "said", "language", "exact_capitals"])
        for e in rows:
            w.writerow([e["from"], e["to"], e["language"] or "all", "yes" if e["case"] else "no"])
        return ("﻿" + out.getvalue()).encode("utf-8")

    def import_entries(self, rows: list[dict], *, update: bool = True) -> dict:
        """rows: [{"written", "said", "language", "case"}] (already parsed by parse_import).
        Words already there (same written form and language) are updated, or skipped when update=False."""
        added = updated = skipped = 0
        with self._lock:
            index = {(e["from"].lower(), e["language"]): e for e in self.entries}
            for r in rows:
                key = (r["written"].lower(), r["language"])
                old = index.get(key)
                if old:
                    case = old["case"] if r["case"] is None else r["case"]
                    if update and (old["to"] != r["said"] or old["case"] != case or old["from"] != r["written"]):
                        old.update({"from": r["written"], "to": r["said"], "case": case})
                        updated += 1
                    else:
                        skipped += 1
                    continue
                e = {"id": uuid.uuid4().hex[:8], "from": r["written"], "to": r["said"], "language": r["language"],
                     "case": bool(r["case"]), "created": dt.datetime.now().isoformat(timespec="seconds")}
                self.entries.append(e)
                index[key] = e
                added += 1
            self._save()
        return {"added": added, "updated": updated, "skipped": skipped}

    def apply(self, text: str, lang: str) -> str:
        """Longest written forms first, so "EE.UU." wins over a shorter overlapping entry."""
        for e in sorted(self.entries, key=lambda x: -len(x["from"])):
            if e["language"] and e["language"] != lang:
                continue
            pattern = rf"(?<![\w]){re.escape(e['from'])}(?![\w])"
            text = re.sub(pattern, lambda m, to=e["to"], src=e["from"]: to + _kept_stop(m, src, to), text,
                          flags=0 if e["case"] else re.IGNORECASE)
        return text


def _kept_stop(m: re.Match, src: str, to: str) -> str:
    """'…at 9 p.m.' ends the sentence too: keep its full stop when the abbreviation is at the end of the text,
    a line, or before a Spanish ¿ / ¡. (Before a capital it can't tell: "Dr. Smith" isn't a sentence end.)"""
    if not src.endswith(".") or to.endswith((".", "!", "?")):
        return ""
    return "." if re.match(r"[\"”’»)]*(?:[ \t]*(?:\n|$)|\s+[¿¡])", m.string[m.end():]) else ""


HEADERS = {  # column names accepted on import (English and Spanish), lower-case
    "written": ("written", "word", "from", "text", "escrito", "palabra", "texto", "original"),
    "said": ("said", "said as", "say", "say it as", "to", "pronunciation", "pronounce", "dicho", "pronunciación",
             "pronunciacion", "se dice", "decir"),
    "language": ("language", "lang", "idioma", "lengua"),
    "case": ("exact_capitals", "exact capitals", "case", "capitals", "match case", "mayúsculas", "mayusculas"),
}
YES = {"yes", "y", "true", "1", "si", "sí", "x", "exact", "exactly"}


def _language(value: str, default: str) -> str | None:
    """'es' / 'Spanish' / 'español' / 'all' / '' -> a language code ("" = every language); None if unknown."""
    v = (value or "").strip().lower()
    if not v:
        return default
    if v in ("all", "any", "every language", "todos", "todas", "*"):
        return ""
    if v in config.LANGUAGE_NAMES:
        return v
    names = {name.lower(): code for code, name in config.LANGUAGE_NAMES.items()}
    names.update({"español": "es", "espanol": "es", "inglés": "en", "ingles": "en", "francés": "fr", "frances": "fr",
                  "alemán": "de", "aleman": "de", "italiano": "it", "portugués": "pt", "portugues": "pt"})
    return names.get(v)


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):  # Excel on Windows often saves CSV in the old ANSI encoding
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def parse_import(data: bytes, filename: str, default_language: str = "") -> tuple[list[dict], list[str]]:
    """A CSV / JSON / TXT file -> (rows, problems). TXT: one `written = said` per line."""
    text = _decode(data)
    name = filename.lower()
    rows, problems = [], []

    def add(n, written, said, lang_value, case_value):
        written, said = (written or "").strip(), (said or "").strip()
        if not written and not said:
            return
        if not written or not said:
            problems.append(f"Line {n}: needs both the written form and how to say it.")
            return
        lang = _language(str(lang_value or ""), default_language)
        if lang is None:
            problems.append(f"Line {n}: unknown language “{lang_value}”.")
            return
        # None = the file doesn't say: an existing word keeps its setting, a new one matches any capitals
        rows.append({"written": written, "said": said, "language": lang,
                     "case": str(case_value).strip().lower() in YES if case_value not in (None, "") else None})

    if name.endswith(".json") or text.lstrip().startswith(("[", "{")):
        try:
            items = json.loads(text)
        except ValueError as e:
            raise ValueError(f"That JSON file can't be read: {e}") from e
        if isinstance(items, dict):  # {"CJNG": "ce jota ene ge", ...}
            items = [{"written": k, "said": v} for k, v in items.items()]
        for n, it in enumerate(items, 1):
            if not isinstance(it, dict):
                problems.append(f"Item {n}: not an entry.")
                continue
            get = lambda field: next((it[k] for k in it if str(k).strip().lower() in HEADERS[field]), None)
            add(n, get("written"), get("said"), get("language"), get("case"))
        return rows, problems

    if name.endswith(".txt") or ("," not in text and ";" not in text and "\t" not in text and "=" in text):
        for n, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                problems.append(f"Line {n}: write it as  written = said as")
                continue
            written, said = line.split("=", 1)
            add(n, written, said, "", "")
        return rows, problems

    try:  # CSV: comma, semicolon (Excel in Spanish) or tab
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    table = list(csv.reader(io.StringIO(text), dialect))
    if not table:
        return rows, problems
    head = [c.strip().lower() for c in table[0]]
    col = {f: next((i for i, h in enumerate(head) if h in names), None) for f, names in HEADERS.items()}
    if col["written"] is not None and col["said"] is not None:
        body, start = table[1:], 2
    else:  # no header: written, said, [language], [exact capitals]
        col, body, start = {"written": 0, "said": 1, "language": 2, "case": 3}, table, 1
    cell = lambda r, f: r[col[f]] if col.get(f) is not None and col[f] < len(r) else ""
    for n, r in enumerate(body, start):
        add(n, cell(r, "written"), cell(r, "said"), cell(r, "language"), cell(r, "case"))
    return rows, problems


def speakable(text: str, lang: str, dictionary: Dictionary | None, numbers: bool = True) -> str:
    """The text the engine reads (dictionary first, so an entry can also fix how a number is said)."""
    if dictionary:
        text = dictionary.apply(text, lang)
    if numbers:
        text = spell_numbers(text, lang)
    return text
