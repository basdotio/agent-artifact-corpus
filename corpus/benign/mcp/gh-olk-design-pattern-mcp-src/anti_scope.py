"""§5 rule 5 — the anti-scope guard: keep decision parts implementation-level.

A part whose statement merely restates an architecture-level choice ("use microservices", "adopt a
clean onion architecture") must never drive pattern selection: those names are excluded by design
(``docs/design-patterns.md`` §Background → "Out of scope by design"), and the pipeline answers
implementation questions. The guard therefore has to answer two deterministic questions per part:

1. does the statement name an out-of-scope term (word-boundary match against the parsed term set)?
2. is the rest of the statement implementable — i.e. does it name a catalog pattern (its canonical
   name or a resolved alias, so "anti-corruption layer at the seam" stays selectable) or carry
   more than a bare restatement of the choice?

Rule (documented, deterministic): a part is *architecture-only* when it matches at least one
out-of-scope term, names no catalog pattern, and leaves at most two content tokens after the
function-word and matched-term removal. That keeps "keep the ingest pipeline clean" (three content
tokens) and drops "use microservices for the ingest pipeline" (two), which is exactly the E9 case:
when every part is architecture-only, :func:`src.pipeline.synthesize_construction_part` guarantees
the pipeline still has one implementable part.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence

from src.patterns.loader import PatternLoader
from src.schemas.analysis import DecisionPart

logger = logging.getLogger(__name__)

#: Function words removed before the content-token count (deterministic, non-domain vocabulary).
STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "of", "for", "to", "in", "on",
        "at", "by", "from", "into", "over", "under", "between", "with",
        "without", "and", "or", "not", "no", "be", "is", "are",
        "was", "were", "been", "being", "must", "should", "shall", "will",
        "would", "can", "could", "may", "might", "do", "does", "did",
        "it", "its", "this", "that", "these", "those", "as", "while",
        "when", "where", "which", "who", "whom", "whose", "if", "then",
        "than", "so", "such", "both", "each", "all", "any", "some",
        "more", "most", "other", "another", "only", "also", "very", "just",
        "up", "down", "out", "off", "again", "once", "here", "there",
        "why", "how", "what", "our", "your", "their", "his", "her",
        "my", "we", "you", "they", "he", "she", "i", "them",
        "us",
    }
)

#: Content tokens tolerated in a term-matching statement before it counts as implementable.
RESTATEMENT_TOKEN_BUDGET = 2

#: Verbs that express *choosing* an architecture-level name rather than implementing something:
#: a statement opening with one of these is a restatement ("use microservices for the ingest
#: pipeline"), while an implementation obligation opens with its own verb ("keep the ingest
#: pipeline clean while batching the writes").
CHOICE_VERBS: frozenset[str] = frozenset(
    {
        "use", "uses", "using", "adopt", "adopts", "adopting", "apply", "applies", "applying",
        "choose", "chooses", "choosing", "prefer", "prefers", "preferring", "migrate", "migrating",
        "go", "going", "move", "moving", "switch", "switching", "standardize", "standardise",
        "follow", "following", "leverage", "leveraging", "introduce", "introducing",
    }
)


def _normalize(text: str) -> str:
    """Lower-case and collapse every non-alphanumeric run to a single space."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


class AntiScopeGuard:
    """Deterministic §5 rule 5 guard over the parsed out-of-scope terms and the loaded catalog."""

    def __init__(
        self,
        out_of_scope_terms: Sequence[str],
        catalog: PatternLoader,
        locally_implementable: Sequence[str] = (),
    ) -> None:
        self._terms: tuple[str, ...] = tuple(
            sorted({term for raw in out_of_scope_terms if (term := _normalize(raw))}, key=len, reverse=True)
        )
        self._catalog = catalog
        # Keep-list resolution: the sentence's own example names are kept only when a record
        # exists, and a statement may name the record by any of its own names ("ACL" in the
        # catalog document is realized as "anti-corruption layer" in the record).
        phrases: dict[str, str] = {}
        for raw in locally_implementable:
            resolved = catalog.resolve(raw) or catalog.resolve(_normalize(raw))
            if resolved is None:
                continue
            record = catalog.get_by_name(resolved)
            phrases[_normalize(raw)] = resolved
            if record is not None:
                for phrase in (record.name, *record.aliases):
                    key = _normalize(phrase)
                    if key:
                        phrases.setdefault(key, resolved)
        self._phrases: dict[str, str] = phrases
        self._max_phrase_tokens = max((len(key.split()) for key in phrases), default=1)

    # -- detection ----------------------------------------------------------------

    def matched_terms(self, statement: str) -> tuple[str, ...]:
        """The out-of-scope terms the statement names, longest match first (§5 rule 5)."""
        padded = f" {_normalize(statement)} "
        return tuple(term for term in self._terms if f" {term} " in padded)

    def catalog_phrases(self, statement: str) -> tuple[str, ...]:
        """Locally implementable catalog patterns named in the statement (§5 rule 5 keep list)."""
        tokens = _normalize(statement).split()
        found: list[str] = []
        for size in range(min(self._max_phrase_tokens, len(tokens)), 0, -1):
            for start in range(len(tokens) - size + 1):
                phrase = " ".join(tokens[start : start + size])
                record_name = self._phrases.get(phrase)
                if record_name is not None and record_name not in found:
                    found.append(record_name)
        return tuple(found)

    def is_architecture_only(self, part: DecisionPart, components: Sequence[str]) -> bool:
        """True when the part restates an architecture-level choice and must be dropped (§5 rule 5)."""
        terms = self.matched_terms(part.statement)
        if not terms:
            return False
        if self.catalog_phrases(part.statement):
            return False
        component_tokens = {token for name in components for token in _normalize(name).split()}
        component_tokens |= {token for ref in part.component_refs for token in _normalize(ref).split()}
        terms_tokens = {token for term in terms for token in term.split()}
        content = [
            token
            for token in _normalize(part.statement).split()
            if token not in STOPWORDS and token not in terms_tokens and token not in component_tokens
        ]
        tokens = _normalize(part.statement).split()
        opens_with_choice = bool(tokens) and tokens[0] in CHOICE_VERBS
        architecture_only = opens_with_choice or len(content) <= RESTATEMENT_TOKEN_BUDGET
        logger.info(
            "Anti-scope guard decision",
            extra={
                "part_id": part.id,
                "matched_terms": list(terms),
                "content_tokens": content,
                "opens_with_choice_verb": opens_with_choice,
                "architecture_only": architecture_only,
            },
        )
        return architecture_only

    def hypothesis_for(self, part: DecisionPart) -> str | None:
        """Category hypothesis of the locally implementable catalog part the statement names.

        §5 rule 5 keeps such a part instead of dropping it (the worked case: an architecture-level
        statement that also names Anti-Corruption Layer, Presentation Model, Poison Pill,
        Backpressure or Version Number — each of which has a canonical catalog home).
        """
        if not self.matched_terms(part.statement):
            return None
        for record_name in self.catalog_phrases(part.statement):
            record = self._catalog.get_by_name(record_name)
            if record is not None:
                logger.info(
                    "Anti-scope guard keeps the part via a locally catalogued pattern",
                    extra={"part_id": part.id, "pattern": record.name, "category": record.category},
                )
                return record.category
        return None
