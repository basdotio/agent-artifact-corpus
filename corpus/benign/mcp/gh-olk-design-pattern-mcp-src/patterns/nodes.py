"""Corpus and query text construction for the two retrieval legs (§2.2, §6 step 1).

One node per ``JoinedPattern`` — the catalog record is the retrieval unit (§2.2 corpus unit).
The dense leg embeds each record's ``document_text`` (name + aliases + intent + problem +
context + use_cases; ``avoid_when`` EXCLUDED — it is a veto signal only, §2.2/§6); the BM25
leg indexes each record's ``bm25_text`` (name + aliases + problem). Query text is built per
decision part from the part statement, its constraints and the scope phrase.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from llama_index.core.schema import TextNode

from src.patterns.loader import PatternLoader

_TOKEN_RE = re.compile(r"[a-z0-9]+")

#: Analyzer pattern handed to the upstream BM25 retriever (two-or-more word characters).
TOKEN_PATTERN = r"(?u)\b\w\w+\b"


def tokenize(text: str) -> list[str]:
    """Lower-cased alphanumeric word tokens; hyphens read as separators (§6 step 1)."""
    return _TOKEN_RE.findall(text.lower().replace("-", " "))


def dense_query(statement: str, constraints: Sequence[str], scope: str) -> str:
    """Dense-leg query: statement + constraints + scope phrase (§6 step 1)."""
    parts = [statement, *constraints]
    if scope:
        parts.append(scope)
    return " ".join(part for part in parts if part)


def bm25_query(dense: str) -> str:
    """BM25-leg query: the dense query normalized (lowercase, hyphens→spaces)."""
    return " ".join(tokenize(dense))


def build_nodes(catalog: PatternLoader) -> list[TextNode]:
    """One BM25 ``TextNode`` per catalog record, carrying the record metadata (§2.2)."""
    return [
        TextNode(
            id_=name,
            text=record.bm25_text,
            metadata={
                "name": name,
                "category": record.category,
                "subgroup": record.subgroup,
                "scope": record.scope or "",
                "paradigm": ",".join(record.paradigms),
                "provenance": ",".join(record.provenance),
                "support": ",".join(
                    f"{language}:{entry.support}"
                    for language, entry in record.language_implementations.items()
                ),
            },
        )
        for name, record in catalog.records.items()
    ]
