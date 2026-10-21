"""NLTK adapter: WordNet lexical-semantics lookup for English.

NLTK is optional::

    pip install 'classic-nlp-mcp[semantic]'
    python -c "import nltk; nltk.download('wordnet')"
"""

from __future__ import annotations

from typing import Any

from ..adapters.base import detect_lang, make_result, module_version, try_import

_nltk = try_import("nltk")

_wordnet = None
if _nltk is not None:
    try:
        from nltk.corpus import wordnet as _wordnet  # type: ignore[no-redef]
        _wordnet.ensure_loaded()
    except LookupError:
        _wordnet = None  # corpus data not downloaded
    except Exception:
        _wordnet = None


def package_available() -> bool:
    return _nltk is not None


def corpus_ready() -> bool:
    return _wordnet is not None


def get(lang: str) -> "NltkAdapter | None":
    if _nltk is None:
        return None
    lang = "en" if lang == "auto" else lang
    return NltkAdapter() if lang == "en" else None


class NltkAdapter:
    lang = "en"

    def _require(self) -> Any:
        if _nltk is None or _wordnet is None:
            from ..adapters.base import MissingDependency

            raise MissingDependency("nltk")
        return _wordnet

    def wordnet_lookup(self, word: str, max_synsets: int = 5) -> dict[str, Any]:
        wn = self._require()
        synsets = wn.synsets(word)[:max_synsets]
        results = []
        for syn in synsets:
            entry: dict[str, Any] = {
                "name": syn.name(),
                "pos": syn.pos(),
                "definition": syn.definition(),
                "examples": syn.examples()[:2],
                "synonyms": sorted({l.name().replace("_", " ") for l in syn.lemmas()})[:8],
            }
            hypernyms = syn.hypernyms()[:3]
            if hypernyms:
                entry["hypernyms"] = [h.lemmas()[0].name().replace("_", " ") for h in hypernyms]
            results.append(entry)
        return make_result(
            "wordnet_lookup", "en", "nltk.wordnet", module_version(_nltk),
            word=word, synsets=results, found=bool(results),
        )

    def wordnet_similarity(self, word_a: str, word_b: str) -> dict[str, Any]:
        """Best path similarity over all synset pairs of the two words."""
        wn = self._require()
        best = {"similarity": 0.0, "pair": None}
        for sa in wn.synsets(word_a):
            for sb in wn.synsets(word_b):
                sim = sa.path_similarity(sb)
                if sim is not None and sim > best["similarity"]:
                    best = {"similarity": sim, "pair": [sa.name(), sb.name()]}
        return make_result(
            "wordnet_similarity", "en", "nltk.wordnet", module_version(_nltk),
            word_a=word_a, word_b=word_b, **best,
        )
