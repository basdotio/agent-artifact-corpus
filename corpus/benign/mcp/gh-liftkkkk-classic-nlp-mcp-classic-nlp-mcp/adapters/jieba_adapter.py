"""jieba adapter: Chinese tokenize / POS / heuristic NER / keywords /
sentence split / rule-based OpenIE triples.

jieba is the **base dependency** of classic-nlp-mcp (pure Python, small),
which makes the Chinese toolchain work out of the box.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import jieba
import jieba.analyse
import jieba.posseg

from ..adapters.base import detect_lang, make_result, make_token, module_version

_ZH_VERSION = module_version(jieba)

_ZH_NER_MAP = {"nr": "PER", "nrt": "PER", "ns": "LOC", "nt": "ORG", "nto": "ORG", "nz": "MISC"}

_SENT_SPLIT_RE = re.compile(r"(?<=[。！？；!?;])\s*")

_STOPWORDS_ZH = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
                 "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
                 "自己", "这", "那", "与", "及", "或", "对", "为", "等", "还", "被", "把", "让"}


def package_available() -> bool:
    return True


def get(lang: str) -> "JiebaAdapter | None":
    if lang == "auto":
        return JiebaAdapter()  # caller passes text; adapter is zh-focused
    return JiebaAdapter() if lang == "zh" else None


class JiebaAdapter:
    lang = "zh"

    # -- capabilities ---------------------------------------------------------

    def tokenize(self, text: str) -> dict[str, Any]:
        tokens: list[dict[str, Any]] = []
        start = 0
        for word in jieba.cut(text, HMM=True):
            if word:
                start = text.find(word, start)
                end = start + len(word)
                tokens.append(make_token(word, start, end))
                start = end
        return make_result("tokenize", "zh", "jieba", _ZH_VERSION, tokens=tokens)

    def pos_tag(self, text: str) -> dict[str, Any]:
        tokens: list[dict[str, Any]] = []
        start = 0
        for word, flag in jieba.posseg.cut(text):
            start = text.find(word, start)
            end = start + len(word)
            tokens.append(make_token(word, start, end, pos=flag))
            start = end
        return make_result("pos_tag", "zh", "jieba.posseg", _ZH_VERSION, tokens=tokens)

    def ner(self, text: str) -> dict[str, Any]:
        """Heuristic NER from POS tags (nr/ns/nt family) - no dedicated model."""
        entities: list[dict[str, Any]] = []
        start = 0
        for word, flag in jieba.posseg.cut(text):
            start = text.find(word, start)
            end = start + len(word)
            label = _ZH_NER_MAP.get(flag)
            if label:
                entities.append({"text": word, "start": start, "end": end, "label": label})
            start = end
        return make_result(
            "ner", "zh", "jieba.posseg", _ZH_VERSION, entities=entities,
            note="Heuristic mapping of POS tags (nr/ns/nt); install spaCy zh model for statistical NER.",
        )

    def keyword_extract(self, text: str, top_k: int = 10, method: str = "tfidf") -> dict[str, Any]:
        if method == "textrank":
            pairs = jieba.analyse.textrank(text, topK=top_k, withWeight=True)
            impl = "jieba.analyse.textrank"
        else:
            pairs = jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)
            impl = "jieba.analyse.tfidf"
        return make_result(
            "keyword_extract", "zh", impl, _ZH_VERSION,
            keywords=[{"text": w, "weight": round(float(s), 6)} for w, s in pairs],
        )

    def sent_split(self, text: str) -> dict[str, Any]:
        sentences: list[dict[str, Any]] = []
        start = 0
        for sent in _SENT_SPLIT_RE.split(text):
            if not sent:
                continue
            start = text.find(sent, start)
            end = start + len(sent)
            sentences.append({"text": sent, "start": start, "end": end})
            start = end
        return make_result("sent_split", "zh", "jieba+regex", _ZH_VERSION, sentences=sentences)

    # -- rule-based OpenIE ------------------------------------------------------

    _NOUN_TAGS = {"n", "nr", "ns", "nt", "nto", "nz", "nl", "nrt", "eng", "nw", "vn", "an"}
    _VERB_TAGS = {"v", "vd", "vn", "vi"}

    def openie_triples(self, text: str) -> dict[str, Any]:
        """Naive Chinese OpenIE: sliding (noun, verb, noun) patterns over POS
        sequences.  Draft quality by design - candidates for LLM/ontology
        post-processing, flagged with low confidence.
        """
        words: list[tuple[str, str, int, int]] = []
        start = 0
        for word, flag in jieba.posseg.cut(text):
            start = text.find(word, start)
            end = start + len(word)
            words.append((word, flag, start, end))
            start = end

        triples: list[dict[str, Any]] = []
        i = 0
        while i < len(words):
            word, flag, s, e = words[i]
            if flag in self._NOUN_TAGS and i + 2 < len(words):
                v, vflag, vs, ve = words[i + 1]
                o, oflag, os_, oe = words[i + 2]
                if vflag in self._VERB_TAGS and oflag in self._NOUN_TAGS and o not in _STOPWORDS_ZH:
                    triples.append({
                        "subject": word,
                        "predicate": v,
                        "object": o,
                        "confidence": 0.35,
                        "span": {"start": s, "end": oe},
                        "sentence": text[s:oe],
                    })
                    i += 3
                    continue
            i += 1
        return make_result(
            "openie_triples", "zh", "jieba-rule", _ZH_VERSION,
            triples=triples, supported=True,
            note="Naive (noun, verb, noun) pattern mining; treat as candidates and verify with an LLM or ontology.",
        )
