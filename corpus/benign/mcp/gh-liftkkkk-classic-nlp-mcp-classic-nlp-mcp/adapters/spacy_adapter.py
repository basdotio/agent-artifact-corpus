"""spaCy adapter: multilingual pipeline for tokenize / pos / ner / dep-parse
and a dependency-rule OpenIE for English.

spaCy is an *optional* dependency::

    pip install 'classic-nlp-mcp[en]'
    python -m spacy download en_core_web_sm   # English
    python -m spacy download zh_core_web_sm   # Chinese (optional)
"""

from __future__ import annotations

from typing import Any

from ..adapters.base import detect_lang, make_result, make_token, module_version, try_import

_spacy = try_import("spacy")

_MODEL_NAMES = {"zh": "zh_core_web_sm", "en": "en_core_web_sm"}
_PIPELINES: dict[str, Any] = {}

# jieba.posseg -> coarse NER mapping for Chinese (no dedicated NER model).
_ZH_NER_MAP = {"nr": "PER", "nrt": "PER", "ns": "LOC", "nt": "ORG", "nto": "ORG", "nz": "MISC"}


def package_available() -> bool:
    return _spacy is not None


def get(lang: str) -> "SpaCyAdapter | None":
    """Return an adapter for *lang*, or None when spaCy/model is missing."""
    if _spacy is None:
        return None
    lang = detect_lang("中") if lang == "auto" else lang
    if lang not in _MODEL_NAMES:
        return None
    return SpaCyAdapter(lang)


def _load_pipeline(lang: str) -> Any | None:
    if lang not in _PIPELINES:
        nlp = None
        try:
            nlp = _spacy.load(_MODEL_NAMES[lang], disable=["lemmatizer"])
        except Exception:
            model = "en_core_web_sm" if lang == "en" else "zh_core_web_sm"
            try:  # fall back to any installed *core* model of the language
                available = [
                    name
                    for name in _spacy.util.get_installed_models()
                    if name.startswith(model.split("_")[0])
                ]
                if available:
                    nlp = _spacy.load(available[0], disable=["lemmatizer"])
            except Exception:
                nlp = None
        _PIPELINES[lang] = nlp
    return _PIPELINES[lang]


class SpaCyAdapter:
    def __init__(self, lang: str) -> None:
        self.lang = lang
        self.nlp = _load_pipeline(lang)

    @property
    def available(self) -> bool:
        return self.nlp is not None

    # -- internals ----------------------------------------------------------

    def _require(self) -> Any:
        if self.nlp is None:
            from ..adapters.base import MissingDependency

            raise MissingDependency("spacy")
        return self.nlp

    @staticmethod
    def _tokens(doc: Any) -> list[dict[str, Any]]:
        return [make_token(t.text, t.idx, t.idx + len(t.text), pos=t.pos_) for t in doc]

    # -- capabilities ---------------------------------------------------------

    def tokenize(self, text: str) -> dict[str, Any]:
        doc = self._require()(text)
        return make_result(
            "tokenize", self.lang, "spacy", module_version(_spacy), tokens=self._tokens(doc)
        )

    def pos_tag(self, text: str) -> dict[str, Any]:
        doc = self._require()(text)
        return make_result(
            "pos_tag", self.lang, "spacy", module_version(_spacy), tokens=self._tokens(doc)
        )

    def ner(self, text: str) -> dict[str, Any]:
        doc = self._require()(text)
        entities = [
            {
                "text": ent.text,
                "start": ent.start_char,
                "end": ent.end_char,
                "label": ent.label_,
            }
            for ent in doc.ents
        ]
        return make_result(
            "ner", self.lang, "spacy", module_version(_spacy), entities=entities
        )

    def sent_split(self, text: str) -> dict[str, Any]:
        doc = self._require()(text)
        sentences = [
            {"text": sent.text, "start": sent.start_char, "end": sent.end_char}
            for sent in doc.sents
        ]
        return make_result(
            "sent_split", self.lang, "spacy", module_version(_spacy), sentences=sentences
        )

    # -- OpenIE -----------------------------------------------------------------

    _OBJ_DEPS = {"dobj", "obj", "dative", "iobj", "attr", "oprd"}
    _SUBJ_DEPS = {"nsubj", "nsubj:pass", "csubj", "nsubjpass"}

    def openie_triples(self, text: str) -> dict[str, Any]:
        """Dependency-rule OpenIE.

        English: walks the dependency tree of each sentence and extracts
        (subject, predicate, object) triples around verbal predicates.
        Chinese: spaCy's Chinese models use universal tags without reliable
        dependency labels, so this adapter reports ``supported: False`` for
        zh and callers should use the jieba rule adapter instead.
        """
        nlp = self._require()
        if self.lang == "zh":
            return make_result(
                "openie_triples",
                "zh",
                "spacy",
                module_version(_spacy),
                triples=[],
                supported=False,
                note="Chinese OpenIE via spaCy is unreliable; use engine='jieba' for rule-based Chinese triples.",
            )
        doc = nlp(text)
        triples: list[dict[str, Any]] = []
        for sent in doc.sents:
            for verb in sent:
                if verb.pos_ not in ("VERB", "AUX"):
                    continue
                subj = next(
                    (ch for ch in verb.children if ch.dep_ in self._SUBJ_DEPS), None
                )
                if subj is None:
                    continue
                for obj in verb.children:
                    if obj.dep_ in self._OBJ_DEPS:
                        triples.append(
                            self._triple(subj, verb, obj, sent)
                        )
                    elif obj.dep_ == "prep" or obj.dep_ in ("prep", "agent"):
                        for pobj in obj.children:
                            if pobj.dep_ == "pobj":
                                triples.append(
                                    self._triple(subj, verb, pobj, sent, relation_suffix=f" {obj.text}")
                                )
        return make_result(
            "openie_triples",
            "en",
            "spacy",
            module_version(_spacy),
            triples=triples,
            supported=True,
            note="Rule-based extraction over dependency parses; treat as candidate triples for KG construction.",
        )

    @staticmethod
    def _phrase(token: Any) -> str:
        parts = [token.text]
        for child in token.children:
            if child.dep_ in ("compound", "amod", "nmod", "poss", "nn"):
                parts.insert(-1 if parts else 0, child.text)
        return " ".join(parts)

    def _triple(self, subj: Any, verb: Any, obj: Any, sent: Any, relation_suffix: str = "") -> dict[str, Any]:
        phrase_obj = self._phrase(obj)
        start = min(subj.idx, verb.idx, obj.idx)
        end = max(subj.idx + len(subj.text), verb.idx + len(verb.text), obj.idx + len(obj.text))
        return {
            "subject": self._phrase(subj),
            "predicate": verb.lemma_ + relation_suffix,
            "object": phrase_obj,
            "confidence": 0.6,
            "span": {"start": start, "end": end},
            "sentence": sent.text.strip(),
        }
