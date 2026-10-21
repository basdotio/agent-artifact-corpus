"""Stanza adapter (Stanford NLP group): neural pipeline with *native* OpenIE
(CoreNLP-style dependency rules ported to Python), statistical NER for
dozens of languages, and constituency parsing - the pieces no other wrapped
library provides.

Stanza is an optional dependency::

    pip install 'classic-nlp-mcp[stanford]'
    python -c "import stanza; stanza.download('en')"   # or any stanza lang code

Model files are NOT bundled; the adapter degrades gracefully when a
language's models have not been downloaded, and never auto-downloads
(no surprise multi-GB fetches from a tool call).
"""

from __future__ import annotations

from typing import Any

from ..adapters.base import make_result, make_token, try_import

_stanza = try_import("stanza")

# languages whose models have already been fetched into ~/stanza_resources
_pipelines: dict[str, Any | None] = {}
_probe: dict[str, bool] = {}

_DEFAULT_HINT = (
    "Stanza is installed but the models for this language are not downloaded. "
    "Run: python -c \"import stanza; stanza.download('<lang>')\" "
    "(e.g. processors 'tokenize,pos,lemma,ner,depparse'; add 'constituency' "
    "for constituency parsing; en also needs the mwt model, included in the default package)."
)


def package_available() -> bool:
    return _stanza is not None


def get(lang: str):
    """Return a StanzaAdapter for *lang* (stanza language code), or None when
    the package or that language's models are unavailable. 'auto' is not
    resolved here - callers should pass a concrete code (zh/en/fr/...)."""
    if _stanza is None or lang in ("auto", "", None):
        return None
    if lang not in _probe:
        _probe[lang] = _models_present(lang)
    if not _probe[lang]:
        return None
    return StanzaAdapter(lang)


def missing_models_hint(lang: str) -> str:
    return _DEFAULT_HINT.replace("<lang>", lang)


def _models_present(lang: str) -> bool:
    try:
        from stanza.resources.common import DEFAULT_MODEL_DIR

        import os

        return os.path.isdir(os.path.join(str(DEFAULT_MODEL_DIR), lang))
    except Exception:
        return False


class StanzaAdapter:
    def __init__(self, lang: str) -> None:
        self.lang = lang
        self._nlp: Any | None = None
        self._load_error: str | None = None

    def _require(self, processors: str) -> Any:
        if self._nlp is None:
            if self._load_error:
                raise RuntimeError(self._load_error)
            try:
                self._nlp = _stanza.Pipeline(
                    self.lang,
                    processors=processors,
                    download_method=None,  # never auto-download from a tool call
                    verbose=False,
                )
            except Exception as exc:
                self._load_error = _DEFAULT_HINT + f" (load error: {exc})"
                raise RuntimeError(self._load_error) from exc
        return self._nlp

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _tokens(sent: Any, offset_base: int) -> list[dict[str, Any]]:
        toks = []
        for t in sent.tokens:
            text = t.text
            start = offset_base + t.start_char if t.start_char is not None else offset_base
            end = start + len(text)
            entry = make_token(text, start, end)
            if t.words and t.words[0].upos:
                entry["pos"] = t.words[0].upos
                if t.words[0].lemma:
                    entry["lemma"] = t.words[0].lemma
            toks.append(entry)
        return toks

    @staticmethod
    def _char_span(sent: Any, tok_span, offset_base: int) -> dict[str, int]:
        """Convert a stanza token-index span to character offsets."""
        try:
            start_tok, end_tok = tok_span  # [start, end) token indices
            toks = sent.tokens[start_tok:end_tok]
            if toks and toks[0].start_char is not None:
                start = offset_base + toks[0].start_char
                last = toks[-1]
                end = offset_base + last.start_char + len(last.text)
                return {"start": start, "end": end}
        except Exception:
            pass
        return {"start": offset_base, "end": offset_base}

    # -- capabilities ----------------------------------------------------------

    def tokenize(self, text: str) -> dict[str, Any]:
        nlp = self._require("tokenize")
        tokens, base = [], 0
        for sent in nlp(text).sentences:
            tokens.extend(self._tokens(sent, base))
            last = sent.tokens[-1]
            base = tokens[-1]["end"] if tokens else base
        return make_result("tokenize", self.lang, "stanza", _stanza.__version__, tokens=tokens)

    def pos_tag(self, text: str) -> dict[str, Any]:
        nlp = self._require("tokenize,pos,lemma")
        tokens, base = [], 0
        for sent in nlp(text).sentences:
            tokens.extend(self._tokens(sent, base))
            base = tokens[-1]["end"] if tokens else base
        return make_result("pos_tag", self.lang, "stanza", _stanza.__version__, tokens=tokens)

    def ner(self, text: str) -> dict[str, Any]:
        nlp = self._require("tokenize,pos,lemma,ner")
        entities, base = [], 0
        doc = nlp(text)
        for sent in doc.sentences:
            for ent in sent.ents:
                start = base + ent.tokens[0].start_char
                end = base + ent.tokens[-1].start_char + len(ent.tokens[-1].text)
                entities.append(
                    {"text": ent.text, "start": start, "end": end, "label": ent.type}
                )
            last = sent.tokens[-1]
            base += last.start_char + len(last.text) if last.start_char is not None else base + sum(len(t.text) for t in sent.tokens)
        return make_result("ner", self.lang, "stanza", _stanza.__version__, entities=entities)

    def sent_split(self, text: str) -> dict[str, Any]:
        nlp = self._require("tokenize")
        sentences, base = [], 0
        for sent in nlp(text).sentences:
            if sent.tokens and sent.tokens[0].start_char is not None:
                start = base + sent.tokens[0].start_char
                last = sent.tokens[-1]
                end = base + last.start_char + len(last.text)
            else:  # fall back to text scan
                start = base
                end = base + sum(len(t.text) + 1 for t in sent.tokens)
            sentences.append({"text": text[start:end], "start": start, "end": end})
            base = end
        return make_result(
            "sent_split", self.lang, "stanza", _stanza.__version__, sentences=sentences
        )

    def openie_triples(self, text: str) -> dict[str, Any]:
        """Stanza (all released versions) does NOT ship OpenIE - that is a
        CoreNLP feature.  Report honestly instead of pretending."""
        return make_result(
            "openie_triples", self.lang, "stanza", getattr(_stanza, "__version__", "unknown"),
            triples=[], supported=False,
            note="Stanza does not ship OpenIE. For CoreNLP-style OpenIE use the "
                 "corenlp engine (local Stanford CoreNLP server) or spaCy dependency rules.",
        )

    def constituency_parse(self, text: str, max_trees: int = 5) -> dict[str, Any]:
        """Constituency (phrase-structure) parses - exclusive to the Stanford
        stack among the wrapped engines."""
        nlp = self._require("tokenize,pos,constituency")
        trees, base = [], 0
        doc = nlp(text)
        for sent in doc.sentences:
            start = base
            if sent.tokens and sent.tokens[0].start_char is not None:
                start = base + sent.tokens[0].start_char
            tree_str = str(sent.constituency)
            trees.append(
                {
                    "sentence": sent.text,
                    "start": start,
                    "tree": tree_str[:4000],
                    "labels": sorted({lbl for lbl in _iter_labels(sent.constituency)})[:40],
                }
            )
            last = sent.tokens[-1]
            base += last.start_char + len(last.text) if last.start_char is not None else base + sum(len(t.text) for t in sent.tokens)
            if len(trees) >= max_trees:
                break
        return make_result(
            "constituency_parse", self.lang, "stanza", _stanza.__version__, trees=trees
        )


def _iter_labels(node):
    try:
        yield node.label
        for child in node.children:
            yield from _iter_labels(child)
    except Exception:
        return
