"""Zero-dependency fallbacks so basic capabilities never hard-fail.

These are honest fallbacks: the result envelope states the true engine
(``regex-fallback``) so agents know statistical quality is not available.
"""

from __future__ import annotations

import re
from collections import Counter

from .adapters.base import detect_lang, make_result, make_token

_WORD_RE = re.compile(r"\w+(?:[-']\w+)*|[^\w\s]", re.UNICODE)
_ZH_SPLIT_RE = re.compile(r"(?<=[。！？；!?;])\s*")
_EN_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")

# Small built-in stopword list for the English keyword fallback.
_STOPWORDS_EN = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "at", "for",
    "with", "without", "is", "are", "was", "were", "be", "been", "being", "it", "its",
    "this", "that", "these", "those", "as", "by", "from", "has", "have", "had", "do",
    "does", "did", "not", "no", "so", "such", "than", "then", "there", "their", "we",
    "our", "you", "your", "he", "she", "they", "them", "i", "me", "my", "will", "can",
}


def fallback_tokenize(text: str, lang: str) -> dict:
    tokens: list[dict] = []
    if lang == "zh":
        # character-level split keeps offsets exact without any dependency
        for i, ch in enumerate(text):
            if not ch.isspace():
                tokens.append(make_token(ch, i, i + 1))
        engine = "regex-fallback-char"
    else:
        for m in _WORD_RE.finditer(text):
            tokens.append(make_token(m.group(0), m.start(), m.end()))
        engine = "regex-fallback"
    return make_result("tokenize", lang, engine, "builtin", tokens=tokens,
                       note="Install spaCy (en) for statistical tokenization quality.")


def fallback_sent_split(text: str, lang: str) -> dict:
    pattern = _ZH_SPLIT_RE if lang == "zh" else _EN_SPLIT_RE
    sentences: list[dict] = []
    start = 0
    for sent in pattern.split(text):
        if not sent or not sent.strip():
            continue
        start = text.find(sent, start)
        end = start + len(sent)
        sentences.append({"text": sent, "start": start, "end": end})
        start = end
    return make_result("sent_split", lang, "regex-fallback", "builtin", sentences=sentences)


def fallback_keyword_extract(text: str, lang: str, top_k: int) -> dict:
    if lang == "zh":
        from .adapters.jieba_adapter import JiebaAdapter  # jieba is a base dependency

        return JiebaAdapter().keyword_extract(text, top_k=top_k)
    words = [w.lower() for w in _WORD_RE.findall(text) if w.isalpha() and w.lower() not in _STOPWORDS_EN]
    counts = Counter(words).most_common(top_k)
    total = sum(c for _, c in counts) or 1
    return make_result(
        "keyword_extract", "en", "regex-frequency-fallback", "builtin",
        keywords=[{"text": w, "weight": round(c / total, 6)} for w, c in counts],
        note="Plain word frequency; install spaCy or use Chinese jieba for TF-IDF/TextRank.",
    )
