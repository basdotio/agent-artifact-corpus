"""Cross-encoder rerank leg (§6 step 4) with its offline fallback implementation.

* :class:`TEIReranker` — direct HTTP client for the TEI ``/rerank`` endpoint. Robustness
  mirrors the sibling server's ``_safe_tei_rerank_call``: HTTP status ≥ 400 and
  malformed/non-list bodies surface as :class:`DesignPatternError`
  ``ERROR_RETRIEVAL_UNAVAILABLE`` — never as a raw ``json.JSONDecodeError``.
* :class:`LexicalReranker` — deterministic token-overlap reranker, no network; the
  ``--health`` path and the test battery.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any, Protocol, cast

import httpx

from src.config import RerankerConfig
from src.errors import ERROR_RETRIEVAL_UNAVAILABLE, DesignPatternError
from src.patterns.nodes import tokenize


class RerankerProtocol(Protocol):
    """Cross-encoder seam (§6 step 4): (document_index, score) pairs, best first."""

    async def rerank(self, query: str, documents: Sequence[str], top_n: int) -> list[tuple[int, float]]: ...


class TEIReranker:
    """Direct HTTP client for the TEI ``/rerank`` endpoint (§6 step 4).

    Robustness mirrors the sibling's ``_safe_tei_rerank_call``: HTTP status ≥ 400
    and malformed/non-list bodies surface as
    :class:`DesignPatternError` ``ERROR_RETRIEVAL_UNAVAILABLE`` — never as a raw
    ``json.JSONDecodeError``. Response items are ``{"index": int, "score": float}``;
    they are sorted score-desc and capped at ``top_n``. Batching respects
    ``config.config.max_batch_size``; batches are issued sequentially (deterministic
    ordering, no server-side concurrent-batch pressure) and scores are comparable
    within a query.
    """

    def __init__(self, config: RerankerConfig) -> None:
        inner = config.config
        self._base_url = inner.base_url.rstrip("/")
        self._api_key = inner.api_key
        self._timeout = inner.timeout
        self._max_batch_size = inner.max_batch_size

    async def rerank(self, query: str, documents: Sequence[str], top_n: int) -> list[tuple[int, float]]:
        """Score ``documents`` against ``query``; best-first ``(index, score)`` capped at ``top_n``."""
        if not documents or top_n < 1:
            return []
        pairs: list[tuple[int, float]] = []
        for start in range(0, len(documents), self._max_batch_size):
            batch = documents[start : start + self._max_batch_size]
            body = await asyncio.to_thread(self._post, query, list(batch))
            pairs.extend((start + int(item["index"]), float(item["score"])) for item in body)
        pairs.sort(key=lambda pair: -pair[1])
        return pairs[:top_n]

    def _post(self, query: str, texts: list[str]) -> list[dict[str, Any]]:
        """One ``POST {base_url}/rerank`` with status/shape validation (blocking)."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self._base_url}/rerank",
                    headers=headers,
                    json={"query": query, "texts": texts},
                    timeout=self._timeout,
                )
        except httpx.HTTPError as exc:
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                f"TEI reranker {self._base_url}/rerank unreachable: {exc}",
                hint="verify the reranker sidecar is running (§2.2)",
            ) from exc
        if response.status_code >= 400:
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                f"TEI reranker {self._base_url}/rerank returned HTTP {response.status_code}: {response.text[:500]}",
                hint="verify the reranker sidecar model and endpoint (§2.2)",
            )
        try:
            body: object = response.json()
        except ValueError as exc:
            # Malformed/empty 200 body is a TEI error signal: must surface as the
            # structured retrieval error, never leak a raw JSONDecodeError.
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                f"TEI reranker {self._base_url}/rerank returned malformed JSON (HTTP {response.status_code}): {exc}",
            ) from exc
        if not isinstance(body, list):
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                f"TEI reranker {self._base_url}/rerank returned non-list response (HTTP {response.status_code}): {str(body)[:500]}",
            )
        items: list[dict[str, Any]] = []
        for entry in body:
            if not isinstance(entry, dict) or "index" not in entry or "score" not in entry:
                raise DesignPatternError(
                    ERROR_RETRIEVAL_UNAVAILABLE,
                    f"TEI reranker response item missing index/score: {str(entry)[:200]}",
                )
            typed_entry = cast("dict[str, Any]", entry)
            items.append({"index": typed_entry["index"], "score": typed_entry["score"]})
        return items


class LexicalReranker:
    """Deterministic token-overlap reranker, no network (§15 test seam).

    Scores each document by the overlap coefficient
    ``|query ∩ document| / min(|query|, |document|)`` over alphanumeric tokens,
    returning ``(index, score)`` sorted score-desc with ties broken by index
    (stable original order), capped at ``top_n``.
    """

    async def rerank(self, query: str, documents: Sequence[str], top_n: int) -> list[tuple[int, float]]:
        """Overlap-score the documents; best-first ``(index, score)`` capped at ``top_n``."""
        if not documents or top_n < 1:
            return []
        query_tokens = frozenset(tokenize(query))
        scored: list[tuple[int, float]] = []
        for index, document in enumerate(documents):
            doc_tokens = frozenset(tokenize(document))
            denominator = min(len(query_tokens), len(doc_tokens))
            score = len(query_tokens & doc_tokens) / denominator if denominator else 0.0
            scored.append((index, score))
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return scored[:top_n]


def build_reranker(config: RerankerConfig) -> RerankerProtocol:
    """TEI reranker for ``config``; refuses an empty ``base_url`` at construction (§2.2)."""
    if not config.config.base_url.strip():
        raise DesignPatternError(
            ERROR_RETRIEVAL_UNAVAILABLE,
            "reranker base_url is empty — the mandatory cross-encoder pass cannot start",
            hint="set DESIGN_PATTERN_RERANKER_BASE_URL or config/config.json reranker.config.base_url",
        )
    return TEIReranker(config)
