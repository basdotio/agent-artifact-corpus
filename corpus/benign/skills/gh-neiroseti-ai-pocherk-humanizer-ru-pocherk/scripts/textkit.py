"""Разбор русского текста для самопроверки скилла pocherk.

Самодостаточная копия нужных частей конвейера исследования
(analysis/normalise.py, textproc.py, morph.py, registry.py, features.py).
Из папки исследования ничего не импортируется.

razdel и pymorphy3 необязательны:
* без razdel фразы и токены режутся регулярками;
* без pymorphy3 отключаются проверки, которым нужна морфология (вид и время
  глагола, деепричастные хвосты, цепочки родительных), а функция тире
  определяется упрощённо.
Переменные окружения POCHERK_NO_RAZDEL=1 и POCHERK_NO_MORPH=1 включают
запасной режим принудительно (для тестов).

Слово — токен, в котором есть буква или цифра. Предложение не переходит через
перенос строки. Абзац — кусок между пустыми строками.
"""
from __future__ import annotations

import os
import re
from collections import Counter
from functools import lru_cache
from typing import NamedTuple

WARNINGS: list[str] = []

# --------------------------------------------------------------- зависимости
_rz_sentenize = _rz_tokenize = None
if os.environ.get("POCHERK_NO_RAZDEL") != "1":
    try:
        from razdel import sentenize as _rz_sentenize, tokenize as _rz_tokenize  # type: ignore
    except Exception:  # pragma: no cover - зависит от окружения
        _rz_sentenize = _rz_tokenize = None
HAS_RAZDEL = _rz_sentenize is not None

_MORPH = None
_MORPH_TRIED = False


def analyzer():
    """pymorphy3.MorphAnalyzer или None, если библиотеки нет."""
    global _MORPH, _MORPH_TRIED
    if _MORPH_TRIED:
        return _MORPH
    _MORPH_TRIED = True
    if os.environ.get("POCHERK_NO_MORPH") == "1":
        return None
    try:
        import pymorphy3  # type: ignore
        _MORPH = pymorphy3.MorphAnalyzer()
    except Exception:  # pragma: no cover - зависит от окружения
        _MORPH = None
    return _MORPH


def has_morph() -> bool:
    return analyzer() is not None


def dependency_warnings() -> list[str]:
    out = []
    if not HAS_RAZDEL:
        out.append("razdel не установлен: фразы режутся регуляркой, длины фраз приблизительные "
                   "(pip install razdel).")
    if not has_morph():
        out.append("pymorphy3 не установлен: пропущены вид и время глаголов, деепричастные хвосты, "
                   "цепочки родительных, склейки фраз через запятую; сочинительные союзы считаются только после "
                   "запятой; функция тире определяется упрощённо (pip install pymorphy3).")
    return out


# --------------------------------------------------------------- нормализация
SPACE_CHARS = "              　"
ZERO_WIDTH = "​‌﻿⁠­"
DQUOTES = "«»„“”‟\"″〝〞＂"
SQUOTES = "‘’‚‛"
DASHES = "—―‒–−"
HYPHENS = "‐‑"

_SPACE_TR = str.maketrans({c: " " for c in SPACE_CHARS} | {c: None for c in ZERO_WIDTH})
_CANON_TR_KEEP_YO = str.maketrans(
    {"…": "..."}
    | {c: '"' for c in DQUOTES}
    | {c: "'" for c in SQUOTES}
    | {c: "—" for c in DASHES}
    | {c: "-" for c in HYPHENS}
)
_SPACED_HYPHEN = re.compile(r"(?<=\s)-{1,2}(?=\s)")
_LINE_HYPHEN = re.compile(r"^([ \t]*)-{1,2}(?=[ \t])", re.M)
_DOUBLE_HYPHEN = re.compile(r"(?<=\w)--(?=\w)")


def fold_yo(s: str) -> str:
    return s.replace("ё", "е").replace("Ё", "Е")


def canon_keep_yo(text: str) -> str:
    """Кавычки → ", любое тире и дефис с пробелами → «—», «…» → «...», экзотические пробелы → пробел."""
    t = text.translate(_SPACE_TR).translate(_CANON_TR_KEEP_YO)
    t = _SPACED_HYPHEN.sub("—", t)
    t = _LINE_HYPHEN.sub(r"\1—", t)
    t = _DOUBLE_HYPHEN.sub("—", t)
    return t


def canon(text: str) -> str:
    """Копия текста для регулярок: то же, что canon_keep_yo, плюс ё→е."""
    return fold_yo(canon_keep_yo(text))


# markdown: заголовки, жирный и курсив, код, ссылки, цитаты, линии; маркеры «* пункт» → «- пункт»
_MD_RULES = [
    (re.compile(r"^([ \t]*)#{1,6}[ \t]+", re.M), r"\1"),
    (re.compile(r"^([ \t]*)>[ \t]?", re.M), r"\1"),
    (re.compile(r"^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$", re.M), ""),
    (re.compile(r"^([ \t]*)[*+][ \t]+(?=\S)", re.M), r"\1- "),
    (re.compile(r"\*\*(?=\S)([^\n]+?)(?<=\S)\*\*"), r"\1"),
    (re.compile(r"__(?=\S)([^\n]+?)(?<=\S)__"), r"\1"),
    (re.compile(r"(?<![\w*])\*(?=[^\s*])([^*\n]+?)(?<=[^\s*])\*(?![\w*])"), r"\1"),
    (re.compile(r"`([^`\n]+)`"), r"\1"),
    (re.compile(r"!?\[([^\]\n]+)\]\([^)\s]+\)"), r"\1"),
]


def strip_markdown(text: str) -> str:
    """Текст без markdown-разметки (для сверки следа правки: «**Что делать?**» и «Что делать?» — одна фраза)."""
    for r, sub in _MD_RULES:
        text = r.sub(sub, text)
    return text


# заголовок: «## Позиция Facebook» или строка, целиком набранная жирным («**Позиция Facebook**», в том числе
# после эмодзи: «🚀 **Кейс агентства…**»)
MD_HEADER_LINE_RX = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+\S.*|(?:[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿️][ \t]*)*"
    r"(?:\*\*|__)[^*_\n]+(?:\*\*|__)[ \t]*:?)[ \t]*$")


def md_header_texts(text: str) -> set[str]:
    """Тексты markdown-заголовков (без разметки, нижний регистр, ё→е): чтобы узнать тот же заголовок в результате,
    где разметку сняли, а строку оставили."""
    out = set()
    for line in text.replace("\r\n", "\n").split("\n"):
        if MD_HEADER_LINE_RX.match(line):
            t = canon(strip_markdown(line)).strip().strip(":").strip().lower()
            if t:
                out.add(t)
    return out


def strip_md_headers(text: str, also: set[str] | frozenset = frozenset()) -> str:
    """Текст без строк-заголовков: markdown-заголовков и строк, совпадающих с заголовками из also
    (заголовок исходника, у которого в результате сняли «##» или «**»). Строка заменяется пустой —
    заголовок не склеивает соседние абзацы."""
    out = []
    for line in text.replace("\r\n", "\n").split("\n"):
        plain = canon(strip_markdown(line)).strip().strip(":").strip().lower()
        if MD_HEADER_LINE_RX.match(line) or (plain and plain in also):
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


# --------------------------------------------------------------- морфология
class W(NamedTuple):
    lemma: str
    pos: str
    tags: frozenset
    known: bool
    yo_word: bool


_PROPER = frozenset({"Name", "Surn", "Patr", "Geox", "Orgn", "Trad"})
_NOMINAL = frozenset({"NOUN", "ADJF", "NPRO", "PRTF", "NUMR"})
PREDICATE_POS = frozenset({"VERB", "PRED", "PRTS"})


@lru_cache(maxsize=None)
def parse(word: str) -> W | None:
    """Лучший разбор pymorphy3 (е-форма слова); None без pymorphy3."""
    m = analyzer()
    if m is None:
        return None
    w = word.lower().replace("ё", "е")
    ps = m.parse(w)
    p = ps[0]
    tags = frozenset(str(p.tag).replace(" ", ",").split(","))
    lemma = p.normal_form.replace("ё", "е")
    yo_word = bool(p.is_known) and all("ё" in q.word for q in ps)
    return W(lemma, p.tag.POS or "", tags, bool(p.is_known), yo_word)


@lru_cache(maxsize=None)
def nomn_possible(word: str) -> bool:
    m = analyzer()
    if m is None:
        return False
    w = word.lower().replace("ё", "е")
    return any(p.tag.POS in _NOMINAL and "nomn" in p.tag for p in m.parse(w))


@lru_cache(maxsize=None)
def can_be_noun(word: str) -> bool:
    m = analyzer()
    if m is None:
        return False
    w = word.lower().replace("ё", "е")
    return any(p.tag.POS == "NOUN" for p in m.parse(w))


def is_proper(w: W | None) -> bool:
    return bool(w and (w.tags & _PROPER))


def is_predicate(w: W | None) -> bool:
    return bool(w and w.pos in PREDICATE_POS)


# --------------------------------------------------------------- токены
URL_RX = re.compile(
    r"(?:https?://|www\.)\S+|(?<![\w@.])(?:[a-z0-9-]+\.)+(?:ru|com|org|net|io|me|su|info|dev|ai|рф|ly|cc|tv|app)(?:/\S*)?",
    re.I)
EMAIL_RX = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
MENTION_RX = re.compile(r"(?<![\w@])@[A-Za-z0-9_]{2,}")
HASHTAG_RX = re.compile(r"(?<![\w#&])#[^\W\d_][\w]*")
EMOJI_RX = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿]")
_HAS_ALNUM = re.compile(r"[^\W_]")
_HAS_CYR = re.compile(r"[а-яё]", re.I)
_HAS_LAT = re.compile(r"[a-z]", re.I)
_NUMERIC = re.compile(r"^[\d.,:–—/%-]*\d[\d.,:–—/%-]*$")
_FALLBACK_TOKEN = re.compile(
    r"\d+(?:[.,:]\d+)*(?:[–—-]\d+(?:[.,]\d+)*)?%?|[^\W\d_]+(?:[-'][^\W_]+)*(?:-\d+)?|\d+[^\W\d_]+|\S", re.U)


class Tok(NamedTuple):
    text: str
    low: str          # нижний регистр, ё→е
    is_word: bool
    is_num: bool
    is_latin: bool
    w: W | None


def make_tok(t: str) -> Tok:
    is_word = bool(_HAS_ALNUM.search(t))
    low = fold_yo(t.lower())
    is_num = bool(_NUMERIC.match(t))
    is_latin = bool(_HAS_LAT.search(t)) and not _HAS_CYR.search(t)
    w = parse(t.lower()) if (is_word and _HAS_CYR.search(t)) else None
    return Tok(t, low, is_word, is_num, is_latin, w)


def tokenize(s: str) -> list[str]:
    if _rz_tokenize is not None:
        return [t.text for t in _rz_tokenize(s)]
    return _FALLBACK_TOKEN.findall(s)


_ABBR_END = re.compile(
    r"(?:\b(?:т\.\s?[едкпн]|и\s?т\.\s?[дп]|т\.\s?ч|т|г|гг|руб|тыс|млн|млрд|др|пр|см|ул|стр|рис|им|ок|напр|св|ср|вв|в)\."
    r"|\b[А-ЯЁA-Z]\.)$", re.I)
_FALLBACK_SPLIT = re.compile(r"(?<=[.!?…])[\"»)\]]*\s+(?=[\"«(\[—–-]?\s*[A-ZА-ЯЁ0-9])")


def sentence_spans(line: str) -> list[tuple[int, int]]:
    """Границы предложений внутри одной строки."""
    if _rz_sentenize is not None:
        return [(s.start, s.stop) for s in _rz_sentenize(line)]
    spans = []
    start = 0
    for m in _FALLBACK_SPLIT.finditer(line):
        end = m.start()
        piece = line[start:end].rstrip()
        if _ABBR_END.search(piece[-12:]):
            continue
        spans.append((start, end))
        start = m.end()
    if line[start:].strip():
        spans.append((start, len(line)))
    out = []
    for a, b in spans:
        seg = line[a:b]
        lead = len(seg) - len(seg.lstrip())
        trail = len(seg.rstrip())
        if trail > lead:
            out.append((a + lead, a + trail))
    return out


def _mask_same_len(text: str) -> tuple[str, dict]:
    counts = {}
    for name, rx in (("urls", URL_RX), ("emails", EMAIL_RX), ("mentions", MENTION_RX), ("hashtags", HASHTAG_RX)):
        counts[name] = len(rx.findall(text))
        text = rx.sub(lambda m: " " * len(m.group(0)), text)
    return text, counts


class Sent:
    __slots__ = ("raw", "soft", "norm", "toks", "words", "para", "line_start", "line", "start", "end")

    def __init__(self, raw, soft, norm, toks, para, line_start, line, start, end):
        self.raw = raw            # как в исходном файле
        self.soft = soft          # canon_keep_yo
        self.norm = norm          # canon (ё→е)
        self.toks = toks
        self.words = [t for t in toks if t.is_word]
        self.para = para
        self.line_start = line_start
        self.line = line
        self.start = start
        self.end = end

    @property
    def n_words(self) -> int:
        return len(self.words)


class Doc:
    """Разобранный текст: строки → предложения → токены (с морфологией, если есть)."""

    def __init__(self, text: str):
        text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        self.text = text
        self.masked, self.art = _mask_same_len(text)
        self.norm = canon(self.masked)
        self.has_paragraphs = bool(re.search(r"\n[ \t]*\n", text.strip()))
        self.sents: list[Sent] = []
        self.lines: list[tuple[str, str]] = []      # (исходная строка, нормализованная)
        self.mlines: list[str] = []                 # строки без URL, e-mail, @, # (для перечней)
        self.line_paras: list[int] = []
        self.paras: list[list[int]] = []
        para = -1
        prev_end = None
        cur: list[int] = []
        for li, m in enumerate(re.finditer(r"[^\n]+", self.masked)):
            line_masked = m.group(0)
            if not line_masked.strip():
                continue
            gap = self.masked[prev_end:m.start()] if prev_end is not None else "\n\n"
            if prev_end is None or gap.count("\n") >= 2:
                if cur:
                    self.paras.append(cur)
                cur = []
                para += 1
            prev_end = m.end()
            raw_line = text[m.start():m.end()]
            self.lines.append((raw_line, canon(line_masked)))
            self.mlines.append(line_masked)
            self.line_paras.append(para)
            for j, (a, b) in enumerate(sentence_spans(line_masked)):
                seg_masked = line_masked[a:b]
                soft = canon_keep_yo(seg_masked)
                toks = [make_tok(t) for t in tokenize(soft)]
                if not any(t.is_word for t in toks):
                    continue
                s = Sent(text[m.start() + a:m.start() + b], soft, fold_yo(soft), toks, len(self.paras),
                         j == 0, len(self.lines) - 1, m.start() + a, m.start() + b)
                cur.append(len(self.sents))
                self.sents.append(s)
        if cur:
            self.paras.append(cur)
        # индекс абзаца у предложений — порядковый номер непустого абзаца
        for pi, ids in enumerate(self.paras):
            for i in ids:
                self.sents[i].para = pi
        self.words: list[Tok] = [t for s in self.sents for t in s.words]
        self.n_words = len(self.words)
        self.n_emoji = len(EMOJI_RX.findall(text))

    @property
    def n_sents(self) -> int:
        return len(self.sents)

    def sent_at(self, pos: int) -> int | None:
        for i, s in enumerate(self.sents):
            if s.start <= pos < s.end:
                return i
        return None

    def last_paras_sents(self, k: int = 2) -> list[int]:
        if self.has_paragraphs and self.paras:
            return [i for p in self.paras[-k:] for i in p]
        n = len(self.sents)
        return list(range(max(n - (3 if k == 2 else 2), 0), n))


# --------------------------------------------------------------- функция тире (§164–179)
SPEECH_LEMMAS = frozenset(
    "сказать говорить ответить отвечать спросить спрашивать отметить отмечать заявить заявлять "
    "добавить добавлять уточнить уточнять признаться признаваться вспоминать вспомнить подчеркнуть "
    "подчеркивать сообщить сообщать рассказать рассказывать пояснить пояснять крикнуть кричать "
    "улыбнуться усмехнуться вздохнуть возразить написать писать заметить замечать продолжить "
    "продолжать согласиться пошутить объяснить объяснять буркнуть прошептать шепнуть воскликнуть".split())
_SPEECH_FORMS_RX = re.compile(
    r"^(?:сказал|сказала|сказали|говорит|говорил|говорила|ответил|ответила|спросил|спросила|отметил|отметила|"
    r"заявил|заявила|добавил|добавила|уточнил|уточнила|признался|призналась|пояснил|пояснила|подчеркнул|"
    r"подчеркнула|написал|написала|пишет|заметил|заметила|рассказал|рассказала|объяснил|объяснила)$")
TURN_FIRST = frozenset("и а но да зато причем однако или либо ведь хотя именно".split())
_WORD = re.compile(r"[^\W_]+(?:-[^\W_]+)*")
_PRED_WORDS = frozenset({"есть", "нет", "было", "будет", "будут", "были", "была", "надо", "нужно", "можно", "нельзя"})
_NOMINAL_POS = frozenset({"NOUN", "ADJF", "NPRO", "NUMR", "INFN", "PRTF"})
_SKIP_BEFORE_NOMINAL = frozenset({"не", "же", "ли", "лишь", "только", "просто", "тоже", "еще", "уже", "почти",
                                  "всего", "именно", "полностью", "совсем", "вовсе", "очень", "абсолютно",
                                  "практически", "действительно"})
_SUBORD_RX = re.compile(
    r",\s*(?:(?:в|на|о|об|по|с|со|к|ко|у|из|за|от|до|для|при|через|про|под|над|без)\s+)?"
    r"(?:котор\w+|где|куда|откуда|когда|кто|что|чтобы|если|хотя|поскольку|потому|пока|словно|будто|ибо)\b",
    re.I)
_PAREN_RX = re.compile(r"\([^()]*\)")
_SUBORD_START = re.compile(
    r"^\s*(?:(?:в|на|о|об|по|с|со|к|ко|у|из|за|от|до|для|при|через|про|под|над|без)\s+)?"
    r"(?:котор\w+|где|куда|откуда|когда|кто|что|чтобы|если|хотя|поскольку|пока|словно|будто|ибо)\b",
    re.I)
_PAREN_FIRST = frozenset("причем кстати впрочем конечно например правда кажется видимо разумеется возможно "
                         "наверное пожалуй".split())
_PERS_NOMN = frozenset("я мы ты вы он она оно они".split())
_SUBORD_FIRST = frozenset("если когда раз пока хотя поскольку чтобы который которая которое которые "
                          "где куда откуда что кто".split())
_COND_FIRST = frozenset("если когда раз пока хотя поскольку".split())
_ADVERBIAL_POS = frozenset({"ADVB", "COMP", "CONJ", "PRCL", "PREP"})


def _words(s: str) -> list[str]:
    return _WORD.findall(s)


def _p(w: str) -> W:
    r = parse(w)
    return r if r is not None else W(w, "", frozenset(), False, False)


def _has_pred(words: list[str]) -> bool:
    low = [w.lower() for w in words]
    for j, lw in enumerate(low):
        if lw in _PRED_WORDS:
            return True
        p = _p(lw)
        if is_predicate(p) or (p.pos == "ADJS" and not can_be_noun(lw)):
            return True
        if p.pos == "ADVB" and "Prdx" in p.tags and any(_p(x).pos == "INFN" for x in low[j + 1:j + 4]):
            return True
    return False


def _clause_start(words: list[str]) -> bool:
    return bool(words) and words[0].lower() in _PERS_NOMN


def _starts_nominal(words: list[str], infn: bool = True) -> bool:
    ws = [w for w in words if w.lower() not in _SKIP_BEFORE_NOMINAL]
    if not ws:
        return False
    if re.match(r"[A-Za-z]", ws[0]):
        return True
    p = _p(ws[0].lower())
    if p.pos == "INFN":
        return infn
    if p.pos in _NOMINAL_POS and ("nomn" in p.tags or p.pos in {"NUMR"} or "Fixd" in p.tags):
        return True
    if p.pos in ("NOUN", "ADJF", "PRTF") and nomn_possible(ws[0]):
        return True
    return ws[0][:1].isdigit()


def _left_clause(seg: str, rel_subject: bool = False) -> str:
    if seg.count("(") > seg.count(")"):
        seg = seg[seg.rfind("(") + 1:]
    seg = _PAREN_RX.sub(" ", seg)
    closed = seg.rstrip().endswith(",")
    seg = seg.rstrip().rstrip(",").rstrip()
    parts = [p for p in re.split(r"[,;:]", seg) if _words(p)]
    if not parts:
        return seg
    if len(parts) > 1 and _SUBORD_START.match(parts[-1]):
        prev_w = _words(parts[-2])
        if closed or (rel_subject and re.match(r"\s*(?:что|кто|котор\w+)\b", parts[-1], re.I)
                      and len(prev_w) <= 4 and not _has_pred(prev_w)):
            return parts[-2]
    return parts[-1]


def _right_clause(seg: str) -> str:
    seg = _PAREN_RX.sub(" ", seg)
    seg = re.split(r"[:;]", seg, maxsplit=1)[0]
    m = _SUBORD_RX.search(seg)
    return seg[:m.start()] if m else seg


def _only_pred_word(words: list[str]) -> bool:
    ws = [w.lower() for w in words if w.lower() not in _SKIP_BEFORE_NOMINAL | {"весьма", "вполне", "довольно"}]
    if len(ws) != 1:
        return False
    p = _p(ws[0])
    return p.pos in ("PRED", "PRTS") or (p.pos == "ADJS" and not can_be_noun(ws[0])) or (
        p.pos == "ADVB" and "Prdx" in p.tags)


def _oblique_start(words: list[str]) -> bool:
    ws = [w for w in words if w.lower() not in _SKIP_BEFORE_NOMINAL]
    if not ws or re.match(r"[A-Za-z\d]", ws[0]):
        return False
    p = _p(ws[0].lower())
    return p.pos in ("NOUN", "ADJF", "PRTF") and not nomn_possible(ws[0])


def _pp_only(words: list[str]) -> bool:
    ws = [w for w in words if _p(w.lower()).pos not in ("CONJ", "PRCL")]
    if not ws or _p(ws[0].lower()).pos != "PREP":
        return False
    return not any(nomn_possible(w) or re.match(r"[A-Za-z]", w) for w in ws[1:])


def _paired(s: str, prev: int, i: int, nxt: int) -> bool:
    inner = s[i + 1:nxt].rstrip()
    closing_comma = inner.endswith(",")
    core = inner.rstrip(",")
    iw, lw, aw = _words(core), _words(_left_clause(s[prev:i])), _words(s[nxt + 1:])
    if not (lw and aw and 1 <= len(iw) <= (12 if closing_comma else 8)):
        return False
    commas = core.count(",")
    if iw[0].lower() in _PAREN_FIRST and re.match(r"\s*[^\W_]+\s*,", core):
        commas -= 1
    if commas and not closing_comma:
        return False
    return not (_has_pred(lw) and (_has_pred(iw) or _clause_start(iw)))


def _classify_simple(s: str, line_initial: bool) -> list[str]:
    """Функция тире без морфологии: только то, что видно по знакам и первому слову."""
    out = []
    for m in re.finditer("—", s):
        i = m.start()
        before, after = s[:i], s[i + 1:]
        rlow = [w.lower() for w in _words(after)]
        if (re.search(r"\d\s*$", before) and re.match(r"\s*\d", after)) or (
                re.search(r"\b[IVXLC]+\s*$", before) and re.match(r"\s*[IVXLC]+\b", after)):
            out.append("range")
        elif not before.strip():
            out.append("line_initial" if line_initial else "dialogue")
        elif re.search(r":\s*$", before) and re.match(r"\s*[\"(]?[А-ЯЁA-Z]", after):
            out.append("dialogue")
        elif re.search(r"[,!?]\s*\"?\s*$|\"\s*$", before) and rlow and any(_SPEECH_FORMS_RX.match(w) for w in rlow[:3]):
            out.append("dialogue")
        elif rlow and rlow[0] in ("это", "вот"):
            out.append("copula_eto")
        elif rlow and rlow[0] in TURN_FIRST:
            out.append("turn")
        else:
            out.append("other")
    return out


def classify_dash_sentence(s: str, line_initial: bool = False) -> list[str]:
    """Классы всех «—» в одном предложении нормализованного текста (см. canon).

    С pymorphy3 — порт analysis/normalise.classify_dash_sentence; без него — упрощённо.
    """
    if not has_morph():
        return _classify_simple(s, line_initial)
    pos = [m.start() for m in re.finditer("—", s)]
    out: list[str | None] = [None] * len(pos)
    for k, i in enumerate(pos):
        if out[k] is not None:
            continue
        before, after = s[:i], s[i + 1:]
        prev = pos[k - 1] + 1 if k > 0 else 0
        nxt = pos[k + 1] if k + 1 < len(pos) else len(s)
        lseg, rseg = s[prev:i], s[i + 1:nxt]
        rw = _words(_right_clause(rseg))
        rel_subject = bool(rw) and not _has_pred(rw) and (_starts_nominal(rw) or _only_pred_word(rw))
        lw = _words(_left_clause(lseg, rel_subject))
        rlow = [w.lower() for w in _words(rseg)]
        rfirst = _words(rseg.split(",", 1)[0])
        if (re.search(r"\d\s*$", before) and re.match(r"\s*\d", after)) or (
                re.search(r"\b[IVXLC]+\s*$", before) and re.match(r"\s*[IVXLC]+\b", after)):
            out[k] = "range"
        elif not before.strip():
            out[k] = "line_initial" if line_initial else "dialogue"
        elif re.search(r":\s*$", before) and re.match(r"\s*[\"(]?[А-ЯЁA-Z]", after):
            out[k] = "dialogue"
        elif re.search(r"[,!?]\s*\"?\s*$|\"\s*$", before) and rlow and (
                any(_p(w).lemma in SPEECH_LEMMAS for w in rlow[:3]) or s.lstrip().startswith("—")):
            out[k] = "dialogue"
        elif k + 1 < len(pos) and _paired(s, prev, i, nxt):
            out[k] = out[k + 1] = "paired"
        elif (rlow and rlow[0] == "это" and _has_pred(rfirst[1:]) and not _starts_nominal(rfirst[1:])
              and not (len(rfirst) > 1 and rfirst[1].lower() in _SUBORD_FIRST)):
            out[k] = "bessoyuz"
        elif rlow and rlow[0] in ("это", "вот"):
            out[k] = "copula_eto"
        elif rlow and rlow[0] in TURN_FIRST:
            out[k] = "turn"
        elif rlow[:2] in (["все", "это"], ["все", "эти"], ["все", "они"]) and "," in lseg:
            out[k] = "apposition"
        elif rlow[:2] == ["то", "есть"]:
            out[k] = "apposition"
        else:
            lp = _has_pred(lw)
            rp = _has_pred(rw) or _clause_start(rw)
            lwords = _words(lseg)
            if lp and rp:
                out[k] = "bessoyuz"
            elif rp and lwords and lwords[0].lower() in _COND_FIRST:
                out[k] = "bessoyuz"
            elif _clause_start(rw) and _has_pred(rw):
                out[k] = "bessoyuz"
            elif not lp and rw and (
                    (1 <= len(lw) <= 3 and (
                        (not rp and (_p(rlow[0]).pos == "PREP"
                                     or (_p(rlow[0]).pos == "ADVB" and not _starts_nominal(rw[1:], infn=False))))
                        or all(_p(w.lower()).pos in _ADVERBIAL_POS for w in lw)))
                    or (not rp and _pp_only(lw))
                    or (not rp and len(lw) <= 6 and _oblique_start(rw)
                        and not any(_p(w.lower()).pos == "INFN" for w in lw))):
                out[k] = "omission"
            elif not lp and (_starts_nominal(rw) or _only_pred_word(rw)
                             or any(_p(w.lower()).pos == "INFN" for w in lw)):
                out[k] = "copula"
            elif lp and not rp:
                out[k] = "apposition"
            elif not lp and not rp and rw:
                out[k] = "apposition"
            else:
                out[k] = "other"
    return [c or "other" for c in out]


NON_PROSE_DASH = frozenset({"range", "line_initial", "dialogue"})


def dash_tail_hits(sent: Sent) -> list[str]:
    """Короткий хвост «…, — X.» (DASH-02): тире-пояснение, справа до конца фразы ≤ 3 слов."""
    s = sent.norm
    if "—" not in s:
        return []
    classes = classify_dash_sentence(s, sent.line_start)
    pos = [m.start() for m in re.finditer("—", s)]
    out = []
    for k, (i, c) in enumerate(zip(pos, classes)):
        if k != len(pos) - 1:
            continue                      # хвост — только последнее тире фразы
        right = s[i + 1:]
        rw = _words(right)
        if not (1 <= len(rw) <= 3) or not re.search(r"[.!?…]\s*[\"»)]*\s*$|^[^.!?]*$", right):
            continue
        if has_morph():
            # «Без подсветки дисплея — более 20 часов.» (пропуск глагола) тоже попадает сюда; исключать не стали:
            # такие безглагольные хвосты у Opus в 2,3 раза чаще, чем у людей (28 против 12 на 500 текстов dev)
            if c != "apposition":
                continue
        else:
            if c != "other" or len(_words(_left_clause(s[:i]))) < 4:
                continue
        out.append(s[max(0, i - 40):].strip())
    return out


# --------------------------------------------------------------- частицы (H16)
IDENTITY_BEFORE_ZHE = frozenset(
    "тот та то те того тому тем том той ту теми тех тою такой такая такое такие такого такому таким таком такую "
    "таких такими так там тогда тут туда сюда оттуда отсюда здесь столько стольких этот эта эти этого этому этим "
    "этом эту этих этими сам сама само сами".split())
INDEF_BASES = frozenset(
    "кто кого кому кем ком что чего чему чем как какой какая какое какие какого какому каким каком какую каких "
    "какими где когда куда откуда почему зачем чей чья чье чьи чьего чьей чьему чьим чьих чьими сколько отчего".split())


def particles(sent: Sent) -> list[str]:
    """Частицы «же, ведь, вот, ну, уж, -то, вообще-то, -таки, -ка, мол» (без тождества и неопределённых местоимений)."""
    out = []
    ws = sent.words
    for i, t in enumerate(ws):
        low = t.low
        prev = ws[i - 1].low if i > 0 else None
        nxt = ws[i + 1].low if i + 1 < len(ws) else ""
        if low in ("же", "ж") and prev not in IDENTITY_BEFORE_ZHE:
            out.append(low)
        elif low == "ведь":
            out.append(low)
        elif low == "вот" and nxt not in ("как", "что", "почему", "зачем"):
            out.append(low)
        elif low == "ну" or (low.startswith("ну-") and not low.endswith("-ка")):
            out.append(low)
        elif low == "уж":
            out.append(low)
        elif low == "вообще-то":
            out.append(low)
        elif low.endswith("-то") and low.count("-") >= 1:
            base = low[:-3]
            if base == "то" or (base and base not in INDEF_BASES and not base.startswith("кое")):
                out.append(low)
        elif (low.endswith("-таки") and len(low) > 5) or (low == "таки" and prev in ("все", "опять", "так")):
            out.append(low)
        elif low.endswith("-ка") and len(low) > 3:
            out.append(low)
        elif low in ("мол", "дескать"):
            out.append(low)
    return out


# --------------------------------------------------------------- морфологические счётчики
FROZEN_GRND = frozenset("судя исходя начиная кончая заканчивая смотря считая говоря погодя спустя благодаря "
                        "включая невзирая учитывая".split())
SUBORD_WORDS = frozenset("который где куда откуда когда кто что чтобы если хотя поскольку потому пока словно "
                         "будто ибо чем".split())
MAIN_PRED_POS = frozenset({"VERB", "PRED", "PRTS", "ADJS", "INFN"})


def _skip_parens(toks, m):
    depth = 0
    while m < len(toks):
        if toks[m].text == "(":
            depth += 1
        elif toks[m].text == ")":
            depth -= 1
            if depth <= 0:
                return m + 1
        m += 1
    return m


def _main_pred_after(toks, m) -> bool:
    n = len(toks)
    while m < n:
        t = toks[m]
        if t.text == "(":
            m = _skip_parens(toks, m)
            continue
        if t.text == ",":
            ws = [x for x in toks[m + 1:m + 4] if x.is_word][:2]
            if ws and (ws[0].low in SUBORD_WORDS or (ws[0].w and ws[0].w.lemma == "который")
                       or (len(ws) > 1 and ws[0].w and ws[0].w.pos == "PREP" and ws[1].w
                           and ws[1].w.lemma == "который")):
                m += 1
                while m < n and toks[m].text != ",":
                    m = _skip_parens(toks, m) if toks[m].text == "(" else m + 1
                continue
        if t.w and t.w.pos in MAIN_PRED_POS:
            return True
        m += 1
    return False


def trailing_gerund(sent: Sent) -> bool:
    """Деепричастный хвост G03: «…, позволяя получать сталь.» (нужен pymorphy3)."""
    toks = sent.toks
    n = len(toks)
    for j, t in enumerate(toks):
        if t.text != ",":
            continue
        k, seen_words, gk = j + 1, 0, None
        while k < n and seen_words < 5:
            x = toks[k]
            if not x.is_word:
                if x.text in (",", ";", ":", "—", "(", ")", "?", "!", "."):
                    break
                k += 1
                continue
            seen_words += 1
            if x.w and x.w.pos == "GRND":
                gk = k
                break
            if (x.w and x.w.pos in ("VERB", "INFN", "PRED", "CONJ")) or x.low in SUBORD_WORDS:
                break
            k += 1
        if gk is None or toks[gk].low in FROZEN_GRND:
            continue
        m = gk + 1
        coordinated = False
        while m < n and toks[m].text not in (",", ";", ":", "—"):
            if toks[m].low in ("и", "а", "но", "да") and any(
                    x.w and x.w.pos == "VERB" for x in toks[m + 1:m + 4] if x.is_word):
                coordinated = True
            m = _skip_parens(toks, m) if toks[m].text == "(" else m + 1
        if coordinated:
            continue
        if m >= n or not _main_pred_after(toks, m):
            return True
    return False


def gen_chains(sent: Sent) -> int:
    """Цепочки из 3+ существительных, где второе и дальше в родительном (G07)."""
    chains = 0
    run = 0
    for t in sent.words:
        if t.w and t.w.pos == "NOUN" and (run == 0 or "gent" in t.w.tags):
            run += 1
        else:
            if run >= 3:
                chains += 1
            run = 1 if (t.w and t.w.pos == "NOUN") else 0
    if run >= 3:
        chains += 1
    return chains


# --------------------------------------------------------------- склейка фраз (P3 DEV-замера)
COORD_CONJ = frozenset("и а но или либо зато однако".split())


def _next_words(toks, k: int, n: int = 3) -> list:
    """До n слов после позиции k, не переходя через знак препинания."""
    out = []
    for x in toks[k + 1:]:
        if not x.is_word:
            if x.text in (",", ";", ":", "—", "–", "(", ")", ".", "!", "?", '"'):
                break
            continue
        out.append(x)
        if len(out) >= n:
            break
    return out


def _correlative_i(toks, k: int) -> bool:
    """Второе «и» в «и внешне, и внутренне»: перед запятой стоит «и X» (1–2 слова без глагола)."""
    if k < 2 or toks[k - 1].text != ",":
        return False
    between = []
    for x in reversed(toks[:k - 1]):
        if not x.is_word:
            return False
        if x.low == "и":
            return 1 <= len(between) <= 2 and not any(y.w is not None and y.w.pos == "VERB" for y in between)
        between.append(x)
        if len(between) > 2:
            return False
    return False


def coord_conj_count(sent: Sent) -> int:
    """Сочинительные союзы, которые соединяют части фразы: после запятой («…, и мы», «…, а сейчас») или
    перед сказуемым («распылялся и занимался»). Однородные члены без глагола («звук, свет и интернет»),
    союз в начале фразы, «и т. д.» и второе слово «но и / а и / да и» не считаются.
    Без pymorphy3 — только союзы после запятой."""
    toks = sent.toks
    first = next((k for k, t in enumerate(toks) if t.is_word), None)
    n = 0
    prev_word = None
    for k, t in enumerate(toks):
        if not t.is_word:
            continue
        pw, prev_word = prev_word, t
        if k == first or t.low not in COORD_CONJ:
            continue
        if t.low == "и" and pw is not None and pw.low in ("но", "а", "да", "так", "вот", "ну"):
            continue                      # «но и», «вот и сегодня» — частица, не союз
        if t.low == "и" and _correlative_i(toks, k):
            continue
        nxt = _next_words(toks, k, 2)
        if t.low == "и" and nxt and nxt[0].low in ("т", "др", "пр"):
            continue
        if t.low in ("а", "но") and nxt and nxt[0].low == "не":
            continue                      # «…, а не Y» — граница охвата, а не склейка частей
        before = toks[k - 1].text if k > 0 else ""
        if before == ",":
            n += 1
            continue
        if has_morph() and nxt:
            x = nxt[0]
            if x.w is not None and x.w.pos in ("ADVB", "PRCL") and len(nxt) > 1:
                x = nxt[1]
            if x.w is not None and x.w.pos == "VERB":
                n += 1
    return n


_SPLICE_STOP = frozenset(
    "и а но или либо да зато однако то тем что чтобы который которая которое которые которого которой которым "
    "которых которую котором которыми где куда откуда когда если хотя пока как чем будто словно ибо поскольку потому "
    "поэтому так тогда иначе значит следовательно причем притом ведь раз именно например кстати впрочем конечно "
    "правда кажется видимо разумеется возможно наверное пожалуй во-первых во-вторых в-третьих итак кто чей сколько "
    "почему зачем ли бы также тоже а-то нежели особенно даже кроме включая".split())
_SUBORD_LEFT = frozenset(
    "что чтобы который которая которое которые которого которой которым которых которую котором которыми где куда "
    "откуда когда если хотя пока как чем будто словно ибо поскольку потому раз кто насколько почему зачем отчего "
    "сколько".split())
_LEAD_PARTICLES = frozenset("вот ну же вон".split())
# короткая главная часть — рамка или речь: «Я думаю, это правильно», «Он говорит, всё готово» — не склейка
_FRAME_LEMMAS = frozenset("думать считать казаться знать понимать видеть верить надеяться уверить сказать говорить "
                          "писать признаться помнить слышать бояться полагать".split())
_FRAME_PREDS = frozenset("уверен уверена уверены видно ясно понятно известно жаль кажется".split())


def _comma_segments(sent: Sent) -> list[tuple[str, list]]:
    """Части фразы между запятыми вне скобок и кавычек: [(граница перед частью, слова)].
    Граница ',' — запятая; 'hard' — начало фразы, «;», «—»; ':' — двоеточие (за ним части-перечень)."""
    segs: list[tuple[str, list]] = [("hard", [])]
    depth, quote = 0, False
    for t in sent.toks:
        if t.text == "(":
            depth += 1
        elif t.text == ")":
            depth = max(0, depth - 1)
        elif t.text == '"':
            quote = not quote
        elif depth == 0 and not quote and t.text == ",":
            segs.append((",", []))
            continue
        elif depth == 0 and not quote and t.text in (";", ":", "—", "–"):
            segs.append((":" if t.text == ":" else "hard", []))
            continue
        if t.is_word and depth == 0 and not quote:
            segs[-1][1].append(t)
    return segs


_REL_LEMMAS = frozenset("который что кто какой чей сколько каков".split())
_LEAD_SKIP = frozenset("и а но да или вот ну же ведь даже только лишь".split())


def _starts_dependent(ws: list) -> bool:
    """Придаточное, косвенный вопрос или оборот: «когда…», «чего…», «каким должен…», «укладывается ли…»,
    «в котором…», деепричастие или причастие в начале. Начальные «и / а / но / вот» пропускаются
    («А когда жена ворчит, …» — тоже придаточное)."""
    ws = list(ws)
    while len(ws) > 1 and ws[0].low in _LEAD_SKIP:
        ws = ws[1:]
    if not ws:
        return True
    f = ws[0]
    if f.low in _SUBORD_LEFT or (f.w is not None and f.w.lemma in _REL_LEMMAS):
        return True
    if f.w is not None and f.w.pos == "PREP" and len(ws) > 1 and (
            ws[1].low in _SUBORD_LEFT or (ws[1].w is not None and ws[1].w.lemma in _REL_LEMMAS)):
        return True
    if any(t.low == "ли" for t in ws[1:4]):
        return True                       # «проверяете, укладывается ли сотрудник в срок»
    return f.w is not None and f.w.pos in ("GRND", "PRTF", "PRTS")


_FRONTED_SUBORD = frozenset("если когда пока хотя раз поскольку чтобы едва пусть хоть как после перед прежде "
                            "покуда коль".split())


def _fronted_subord(ws: list) -> bool:
    """Придаточное, которое стоит перед своей главной частью: «(и / даже) если…», «когда…», «пока…»."""
    ws = [t for t in ws if t.low not in _LEAD_SKIP]
    return bool(ws) and ws[0].low in _FRONTED_SUBORD


def _interrupted_subord(segs: list, i: int) -> bool:
    """Часть segs[i] — продолжение придаточного, прерванного вводным словом: левее (до жёсткой границы) стоит
    «хотя / если / когда…» без сказуемого, а между ними только части без сказуемого."""
    for k in range(i - 1, -1, -1):
        bk, lw = segs[k]
        if _fronted_subord(lw):
            return not _has_finite(lw)
        if _has_finite(lw) or bk != ",":
            return False
    return False


def _has_finite(ws: list) -> bool:
    return any(t.w is not None and (t.w.pos in ("VERB", "PRED", "ADJS", "COMP", "PRTS")) for t in ws)


def _number(w: W) -> str | None:
    return "sing" if "sing" in w.tags else "plur" if "plur" in w.tags else None


def _independent(ws: list) -> str | None:
    """Самостоятельная часть: подлежащее перед глаголом («мама готовила ужин»), повелительное наклонение
    («будьте готовы») или безглагольная часть со сказуемым-наречием при существительном («котиков меньше»)."""
    ws = list(ws)
    while ws and ws[0].low in _LEAD_PARTICLES:
        ws = ws[1:]
    if not ws:
        return None
    f = ws[0]
    if f.low in _SPLICE_STOP or _starts_dependent(ws) or (f.w is not None and f.w.pos in ("CONJ", "INTJ")):
        return None
    verbs = [k for k, t in enumerate(ws) if t.w is not None and t.w.pos == "VERB"]
    if verbs:
        v = ws[verbs[0]]
        if "impr" in v.w.tags:
            return "impr"
        for k in range(verbs[0]):
            t = ws[k]
            if t.w is None or t.w.pos not in ("NOUN", "NPRO") or "Apro" in t.w.tags:
                continue
            if k > 0 and ws[k - 1].w is not None and ws[k - 1].w.pos == "PREP":
                continue
            if t.w.pos == "NPRO" and "nomn" not in t.w.tags:
                continue
            if t.w.pos == "NOUN" and not nomn_possible(t.text):
                continue
            ns, nv = _number(t.w), _number(v.w)
            if ns and nv and ns != nv and t.low not in ("вы",):
                continue
            return "decl"
        return None
    # безглагольная часть: «котиков меньше», «дела больше» — начинается с существительного
    # («…яснее, четче и структурирован» — однородные сказуемые, не отдельная фраза)
    if (len(ws) <= 8 and f.w is not None and f.w.pos in ("NOUN", "NPRO")
            and any(t.w is not None and t.w.pos in ("PRED", "COMP", "ADJS") for t in ws[1:])):
        return "nominal"
    return None


def comma_splices(sent: Sent, after_colon: bool = False) -> list[str]:
    """Две самостоятельные фразы, соединённые только запятой: «…котиков меньше, а дела больше» — нет,
    «…не отрабатывают в речи, вот дети и ищут готовые ответы» — да. Нужен pymorphy3; без него пусто.
    Справа от запятой — самостоятельная часть (без союза и союзного слова), слева — главная часть со сказуемым,
    а не придаточное («Когда он пришёл, мама готовила ужин» — не склейка). Части-перечень после двоеточия
    не считаются; after_colon=True считает и их (для исходника: «…: что-то идёт не так, поддержка молчит» →
    «…. Что-то идёт не так, поддержка молчит» — запятая не новая)."""
    if not has_morph():
        return []
    segs = _comma_segments(sent)
    out = []
    for j in range(1, len(segs)):
        kind, ws = segs[j]
        if kind != ",":
            continue
        ind = _independent(ws)
        if ind is None:
            continue
        main, main_bk, main_i = None, None, None
        for i in range(j - 1, -1, -1):
            bk, lw = segs[i]
            if lw and lw[0].low in COORD_CONJ | {"да"} and not _has_finite(lw):
                break                 # «…, и скорее всего, его можно…»: союз стоит перед вводным словом
            if _fronted_subord(lw):
                break                 # «…, и если X, Y»: Y — главная часть при «если», а не склейка
            if _starts_dependent(lw) or not lw:
                if bk != ",":
                    break
                continue
            if _has_finite(lw):
                main, main_bk, main_i = lw, bk, i
                break
            if bk != ",":
                break
        if main is None or (main_bk == ":" and not after_colon):
            continue                  # «Процесс занял дни: бот сделан легко, база освоена быстро» — перечень
        if main_bk == "," and _interrupted_subord(segs, main_i):
            continue                  # «Хотя версия, скорее всего, будет другой, хакеры…» — «хотя» прервано вводным
        if ind == "impr" and any(t.w is not None and ("impr" in t.w.tags or {"2per", "plur"} <= t.w.tags)
                                 for t in main):
            continue                  # «Откройте настройки, нажмите кнопку» — однородные повелительные
        content = [t for t in main if t.w is None or t.w.pos not in ("PRCL", "CONJ")]
        if len(content) <= 1:
            continue                  # «Получается, …», «Оказалось, …», «Заметим, …» — вводное слово
        is_frame = [t.w is not None and (t.w.lemma in _FRAME_LEMMAS or t.low in _FRAME_PREDS) for t in content]
        if (len(content) <= 3 and any(is_frame)) or any(is_frame[-2:]):
            continue                  # «Я думаю, это правильно», «…размышлял и уверен, она окажется полезной»
        out.append(" ".join(t.text for t in main[-4:]) + ", " + " ".join(t.text for t in ws[:5]))
    return out


NOMINAL_SUFFIX = ("ние", "ция", "ость", "ство", "тие")


def nominal_share(doc: Doc) -> float | None:
    nouns = [t for t in doc.words if t.w and t.w.pos == "NOUN"]
    if not nouns:
        return None
    return sum(1 for t in nouns if t.w.lemma.endswith(NOMINAL_SUFFIX)) / len(nouns)


GREETING_LEMMAS = frozenset("привет здравствуйте итак ну да нет спасибо ок окей вот так".split())


def is_rubric_period(doc: Doc, i: int) -> bool:
    """Рубрика «Метка. Пояснение.» (CL-02): строка начинается фразой из 1–4 слов без сказуемого,
    за ней в той же строке идёт пояснение не короче 3 слов."""
    s = doc.sents[i]
    if not s.line_start or not s.words:
        return False
    first = s.words[0]
    if not first.text[:1].isupper():
        return False
    if first.low in GREETING_LEMMAS or (first.w and first.w.pos in ("INTJ", "CONJ", "PRCL")):
        return False
    txt = s.norm.strip()
    if not (1 <= s.n_words <= 4 and txt.endswith(".") and not txt.endswith("..")):
        return False
    if any(t.low in ("есть", "нет") for t in s.words):
        return False
    # «Отдельная история — новички.» тоже рубрика: у Opus таких фраз втрое больше, чем у людей
    # (55 против 19 на 500 текстов dev), поэтому фразы со связкой-тире не исключаются
    if has_morph():
        if any(t.w and is_predicate(t.w) for t in s.words):
            return False
    else:
        if any(re.search(r"(?:ла|ли|ло|ет|ит|ут|ют|ат|ят|ем|им|ешь|ишь)$", t.low) and len(t.low) > 3 for t in s.words):
            return False
    nxt = i + 1
    return (nxt < len(doc.sents) and doc.sents[nxt].line == s.line and doc.sents[nxt].n_words >= 3)


# --------------------------------------------------------------- ключи слов для сверки
CONTENT_POS = frozenset({"NOUN", "ADJF", "ADJS", "COMP", "VERB", "INFN", "PRTF", "PRTS", "GRND", "ADVB", "NUMR"})
STOP_LEMMAS = frozenset("быть мочь стать это этот весь свой такой который очень так также ещё еще уже тоже только "
                        "просто вот там тут здесь сейчас потом тогда же ли бы ну да нет".split())
_STOP_FALLBACK = frozenset(
    "это этот эта эти этого этой этому этим этом того тому тем том всё все всех всем весь вся было была были быть "
    "будет будут есть который которая которое которые которых которым свой своя свои своих такой такая такие "
    "очень также еще ещё уже тоже только просто тогда потом сейчас здесь когда если чтобы потому поэтому "
    "можно нужно надо или либо даже ведь вот".split())


def stem(low: str) -> str:
    low = fold_yo(low.lower())
    if len(low) >= 6:
        return low[:5]
    if len(low) <= 3:
        return low
    return low[:len(low) - 1]


def word_key(t: Tok) -> str:
    """Ключ слова для сверки исходника и результата: лемма (pymorphy3) или усечённая основа."""
    if t.w is not None:
        return t.w.lemma
    return stem(t.low) if not t.is_latin else t.low


def is_content(t: Tok) -> bool:
    if not t.is_word or t.is_num:
        return False
    if t.w is not None:
        return t.w.pos in CONTENT_POS and t.w.lemma not in STOP_LEMMAS
    if t.is_latin:
        return len(t.low) >= 2
    return len(t.low) >= 4 and t.low not in _STOP_FALLBACK


def content_keys(toks) -> set[str]:
    return {word_key(t) for t in toks if is_content(t)}


def all_keys(doc: Doc) -> set[str]:
    """Все ключи слов документа (леммы и основы — чтобы сверка не зависела от разбора)."""
    out = set()
    for t in doc.words:
        out.add(word_key(t))
        out.add(stem(t.low) if not t.is_latin else t.low)
    return out


def tok_variants(t: Tok) -> set[str]:
    return {word_key(t), stem(t.low) if not t.is_latin else t.low}


def strong_pairs(a: Doc, b: Doc, thr: float = 0.5) -> set[tuple[int, int]]:
    """Выровненные пары фраз (i из a, j из b) по общим знаменательным леммам: доля общих ключей от меньшей
    фразы не ниже thr и общих ключей не меньше двух (у фразы из одного-двух знаменательных слов — все).
    Фраза может входить в несколько пар: так ловится деление и склейка фраз."""
    ak = [content_keys(s.words) for s in a.sents]
    bk = [content_keys(s.words) for s in b.sents]
    out = set()
    for i, ki in enumerate(ak):
        if not ki:
            continue
        for j, kj in enumerate(bk):
            if not kj:
                continue
            inter = len(ki & kj)
            small = min(len(ki), len(kj))
            if inter >= min(2, small) and inter / small >= thr:
                out.add((i, j))
    return out


# --------------------------------------------------------------- ярлык, ставший фразой (P1 DEV-замера v2)
_EVAL_FALLBACK_RX = re.compile(
    r"^(?:прост|непрост|знаком|понятн|очевидн|интересн|любопытн|важн|главн|сложн|банальн|типичн|классическ|"
    r"нехитр|щадящ|грустн|печальн|забавн|стандартн|обычн|привычн|показательн|отличн|хорош|плох|странн)\w*$"
    r"|^(?:такая|такой|такое|такие|таков|такова|таково)$")
_LABEL_SKIP = frozenset("очень довольно вполне совсем весьма тут здесь вот же и всё все тоже".split())
# краткие прилагательные-модальности: «Сильная химия не нужна.» — утверждение, а не ярлык
_MODAL_ADJ = frozenset("нужный должный готовый рад обязанный способный согласный необходимый возможный достойный "
                       "виноватый видный".split())
# оценочные прилагательные без пометы Qual в словаре pymorphy3
_EVAL_EXTRA = frozenset("классический нехитрый стандартный типовой банальный".split())
# фраза-указатель или вывод, а не ярлык: «Вот отредактированный вариант.», «Ниже — подборка.», «Значит, …»
_LABEL_FIRST_STOP = frozenset("вот ниже выше итак значит далее так это теперь".split())


def _evaluative_adj(t: Tok) -> bool:
    """Оценочное прилагательное в роли сказуемого: краткое («проста») или полное в именительном («простая»,
    «щадящий»); порядковые («первая») и местоименные («мой»), кроме «такой», не считаются."""
    if t.w is None:
        return bool(_EVAL_FALLBACK_RX.match(t.low))
    tags = t.w.tags
    if t.w.pos in ("PRTF", "PRTS"):       # «Метод щадящий.»; «отредактированный вариант» — не оценка
        return {"actv", "pres"} <= tags and nomn_possible(t.text)
    if t.w.pos in ("ADJF", "ADJS"):
        if t.w.lemma in ("такой", "таков"):
            return t.w.pos == "ADJS" or nomn_possible(t.text)
        if "Qual" not in tags and t.w.lemma not in _EVAL_EXTRA:
            return False                  # «Первая часть.», «Моя история.», «последний день» — не оценка
        return t.w.pos == "ADJS" or nomn_possible(t.text)   # «идеального текста» — определение, а не сказуемое
    return False


def label_sentence(doc: Doc, i: int) -> bool:
    """Ярлык двоеточия, оставленный отдельной короткой фразой: «Суть простая.», «Сцена знакомая.»,
    «Метод щадящий для психики.» — до 4 слов, оценочное прилагательное и существительное, без глагола,
    кончается точкой, а за ней в том же абзаце идёт раскрытие."""
    s = doc.sents[i]
    txt = s.norm.strip()
    if not (2 <= s.n_words <= 4) or not txt.endswith(".") or txt.endswith(".."):
        return False
    if i + 1 >= len(doc.sents) or doc.sents[i + 1].para != s.para or doc.sents[i + 1].n_words < 2:
        return False
    if s.words[0].low in _LABEL_FIRST_STOP or re.search(r"[—:;,(]", txt) or txt.startswith('"'):
        return False                      # ярлык — два-четыре слова без знаков внутри, не реплика в кавычках
    ws = [t for t in s.words if t.low not in _LABEL_SKIP]
    if any(t.is_num or t.is_latin or t.low in ("не", "ни", "нет") for t in ws):
        return False                      # ярлык — утвердительная оценка; «… не нужна» — уже утверждение
    if any(t.w is not None and t.w.lemma in _MODAL_ADJ for t in ws):
        return False
    if not any(_evaluative_adj(t) for t in ws):
        return False
    if has_morph():
        pred = any(t.w is not None and (t.w.pos in ("VERB", "INFN", "GRND", "COMP", "PRED")
                                        and not can_be_noun(t.text)) for t in ws)
        if pred:
            return False                  # «Регулярность важнее идеального текста.» — сравнение, не ярлык
        # оценка — сказуемое: краткая форма или полная после существительного в именительном
        # («Суть простая», «Метод щадящий»); «Магнитная лента», «Бюджет на конкретный канал» — названия
        for k, t in enumerate(ws):
            if not _evaluative_adj(t):
                continue
            if t.w is not None and t.w.pos in ("ADJS", "PRTS") and any(
                    x.w is not None and (x.w.pos == "NOUN" or can_be_noun(x.text)) and nomn_possible(x.text)
                    for x in ws if x is not t):
                return True
            before = ws[:k]
            if before and before[-1].w is not None and before[-1].w.pos == "PREP":
                continue
            if any(x.w is not None and (x.w.pos == "NOUN" or can_be_noun(x.text)) and nomn_possible(x.text)
                   and not _evaluative_adj(x) for x in before):
                return True
        return False
    # без морфологии: нет слов с глагольным окончанием, кроме оценочного прилагательного
    others = [t for t in ws if not _evaluative_adj(t)]
    return bool(others) and not any(
        re.search(r"(?:ла|ли|ло|ет|ит|ут|ют|ат|ят|ем|им|ешь|ишь|ть|ться)$", t.low) and len(t.low) > 3 for t in others)


def counter_of(items) -> Counter:
    return Counter(items)
