"""Hybrid retrieval index (§2.2, §6, §15): dense + BM25 legs, fusion, cross-encoder rerank.

One document per ``JoinedPattern`` (§2.2 corpus unit — the catalog is the decision
vocabulary; no intermediate slug layer). Two legs run over the same node set:

- **Dense leg** — every pattern's ``JoinedPattern.document_text`` is embedded once at
  build time, L2-normalized, and stored in a FAISS ``IndexFlatIP``; because every
  vector is unit length, the inner product equals cosine similarity. Every pattern is
  scored for every query within the ``retrieval.dense_top_k`` cap (§6 step 2; ``0`` =
  full corpus).
- **BM25 leg** — a llama-index ``BM25Retriever`` over ``TextNode``s built by
  :mod:`src.patterns.nodes`, with ``similarity_top_k`` capped at ``retrieval.bm25_top_k``
  (§6 step 2; ``0`` = full corpus). Documents a leg does not return score 0.0 in the
  fusion stage.

Fusion (§6 steps 2–4, deterministic):
    1. Per-leg min–max normalization of each leg's raw scores over that leg's own
       observed range, to [0, 1]. A leg whose scores are all equal (or a single
       document) carries no ranking information; every present document receives
       the neutral maximum 1.0.
    2. ``fused = dense_weight * dense_norm + bm25_weight * bm25_norm`` (§6 step 3;
       the weights are ``RetrievalConfig``-validated to sum to 1.0 ±1e-3).
    3. The union is ranked by ``fused`` descending, ties broken by
       ``PatternLoader.order_index`` then name — a deterministic total order. The 1-based
       position is ``fused_rank``. Sticky reselection exclusions (§11 item 4) are
       removed BEFORE ranking so they cannot occupy rank positions.
    4. Cross-encoder rerank, MANDATORY whenever the fused pool has more than one
       entry (§6 step 4): ``query = part statement``,
       ``documents = document texts in fused order``, ``top_n = len(pool)``. The
       returned ``(document_index, score)`` pairs yield the 1-based ``rerank_rank``
       (best first). With a single-candidate pool the reranker is skipped and
       ``rerank_rank = fused_rank``. A reranker failure propagates (the caller
       decides) — no silent degradation.
    5. ``retrieval_score = RR(fused_rank) + RR(rerank_rank)`` with
       ``RR(r) = 1 / (rrf_k + r - 1)`` (Vespa-style reciprocal-rank blend, §6
       step 4; numerically identical to the architecture server's
       ``reciprocal_rank_score``). Max attainable: ``2 / rrf_k`` (0.0333 with the
       default ``rrf_k = 60``).

``retrieve()`` returns the pool ranked by ``retrieval_score`` descending (ties:
``fused_rank``, then ``rerank_rank``, then catalog order, then name), capped at
``rerank_top_n`` — the caller (pipeline §6) needs the capped survivors for scoring;
the uncapped depth is available through the ``limit`` keyword.

Blocking work (FAISS, BM25, embedder/reranker HTTP) runs in a worker thread via
``asyncio.to_thread`` so concurrent MCP requests never stall the event loop (§15).

Divergence from the sibling (``../architecture-pattern-mcp/src/patterns/retriever.py``):
that server routes both legs through upstream ``QueryFusionRetriever``; here the
fusion arithmetic is implemented directly over two per-leg-capped score maps —
identical relative-score semantics (per-leg min-max, weighted sum) without the
upstream dependency, per guide §6 steps 2–3.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Literal, cast

import faiss
import numpy as np

from src.config import DenseCacheConfig, RetrievalConfig
from src.errors import ERROR_RETRIEVAL_UNAVAILABLE, DesignPatternError
from src.patterns.dense_cache import resolve_dense_vectors
from src.patterns.embedder import EmbedderIdentity, EmbedderProtocol, l2_normalize_rows
from src.patterns.loader import PatternLoader
from src.patterns.nodes import TOKEN_PATTERN, bm25_query, build_nodes, dense_query
from src.patterns.safe_tei_rerank import RerankerProtocol

logger = logging.getLogger(__name__)


def reciprocal_rank_score(rank: int, rrf_k: int) -> float:
    """``RR(r) = 1 / (rrf_k + r - 1)`` for a 1-based rank (§6 step 4)."""
    return 1.0 / (rrf_k + rank - 1)


def _min_max(values: dict[str, float]) -> dict[str, float]:
    """Per-leg min–max normalization to [0, 1] over the leg's own score range.

    All-equal or single-value ranges carry no ranking information; every present
    document receives the neutral maximum 1.0.
    """
    if not values:
        return {}
    low = min(values.values())
    high = max(values.values())
    span = high - low
    if span <= 0.0:
        return dict.fromkeys(values, 1.0)
    return {name: (score - low) / span for name, score in values.items()}


@dataclass(frozen=True)
class RetrievalHit:
    """One candidate leaving the retrieval stage (§6).

    Attributes:
        name: canonical pattern name.
        retrieval_score: ``RR(fused_rank) + RR(rerank_rank)`` (max ``2/rrf_k``).
        fused_rank: 1-based position in the weighted fusion ranking.
        rerank_rank: 1-based position in the cross-encoder ranking; equals
            ``fused_rank`` when the reranker was skipped (single-candidate pool).
    """

    name: str
    retrieval_score: float
    fused_rank: int
    rerank_rank: int


@dataclass(frozen=True)
class PartQuery:
    """One part's retrieval query bundle for :meth:`RetrievalIndex.retrieve_many`."""

    statement: str
    constraints: Sequence[str] = ()
    scope: str = ""
    exclude: Collection[str] = ()
    limit: int | None = None


class RetrievalIndex:
    """Prebuilt two-leg index over one catalog (§2.2; built once at startup).

    Not thread-safe for concurrent ``build()`` calls on the same instance;
    ``retrieve()`` is safe to run concurrently (read-only after build).
    """

    def __init__(
        self,
        catalog: PatternLoader,
        embedder: EmbedderProtocol,
        reranker: RerankerProtocol,
        retrieval: RetrievalConfig,
        rerank_top_n: int,
        rerank_text: Literal["full", "capsule"] = "full",
    ) -> None:
        self._catalog = catalog
        self._embedder = embedder
        self._reranker = reranker
        self._retrieval = retrieval
        self._rerank_top_n = rerank_top_n
        self._rerank_text = rerank_text
        self._part_semaphore = asyncio.Semaphore(retrieval.max_concurrent_parts)
        self._names: tuple[str, ...] = ()
        self._doc_texts: tuple[str, ...] = ()
        self._capsule_texts: tuple[str, ...] = ()
        self._faiss_index: faiss.IndexFlatIP | None = None
        self._bm25: object | None = None
        self._dense_cache: DenseCacheConfig | None = None
        self._dense_identity: EmbedderIdentity | None = None

    @classmethod
    async def build(
        cls,
        catalog: PatternLoader,
        embedder: EmbedderProtocol,
        reranker: RerankerProtocol,
        retrieval: RetrievalConfig,
        rerank_top_n: int,
        *,
        rerank_text: Literal["full", "capsule"] = "full",
        dense_cache: DenseCacheConfig | None = None,
        identity: EmbedderIdentity | None = None,
    ) -> RetrievalIndex:
        """Embed the corpus, build the FAISS ``IndexFlatIP`` and the BM25 retriever.

        Idempotent-safe: each call constructs fresh FAISS/BM25 objects over the
        catalog's current records; no state leaks between builds. A failed embedder
        call propagates — startup warm-up refuses the server start (§2.2).
        """
        index = cls(catalog, embedder, reranker, retrieval, rerank_top_n, rerank_text)
        names = tuple(catalog.records)
        doc_texts = tuple(catalog.records[name].document_text for name in names)
        capsule_texts = tuple(catalog.records[name].capsule_text for name in names)
        index._names = names
        index._doc_texts = doc_texts
        index._capsule_texts = capsule_texts
        index._dense_cache = dense_cache
        index._dense_identity = identity
        if names:
            index._faiss_index = await index._build_dense(doc_texts)
            index._bm25 = await index._build_bm25()
        logger.info("Retrieval index built: %d patterns (dense + BM25)", len(names))
        return index

    async def _build_dense(self, doc_texts: Sequence[str]) -> faiss.IndexFlatIP:
        """Embed every document once, L2-normalize, index for inner product (§2.2)."""
        if self._dense_cache is not None and self._dense_identity is not None:
            vectors, source = await resolve_dense_vectors(
                config=self._dense_cache,
                embedder=self._embedder,
                names=self._names,
                doc_texts=list(doc_texts),
                identity=self._dense_identity,
            )
        else:
            vectors, source = (
                await self._embedder.embed_documents(list(doc_texts)),
                "embedded",
            )
        logger.info(
            "Dense vectors resolved",
            extra={"source": source, "documents": len(doc_texts)},
        )
        if len(vectors) != len(doc_texts):
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                f"embedder returned {len(vectors)} vectors for {len(doc_texts)} documents",
                hint="check the embedder endpoint and batch configuration (§2.2)",
            )
        normalized = await asyncio.to_thread(l2_normalize_rows, vectors)
        dimension = len(normalized[0])
        if any(len(row) != dimension for row in normalized):
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                "embedder returned ragged vectors (inconsistent dimensionality)",
                hint="all embeddings from one model must share a dimension (§2.2)",
            )
        matrix = np.ascontiguousarray(np.asarray(normalized, dtype=np.float32))
        faiss_index = faiss.IndexFlatIP(dimension)
        faiss_index.add(matrix)
        return faiss_index

    def _build_bm25_sync(self) -> object:
        """Construct the BM25 retriever over the shared node set (blocking; §2.2).

        Stage-1 recall is capped at ``retrieval.bm25_top_k`` (§6 step 2); ``0``
        means the full corpus. The cap is clamped to the corpus size, so it can
        never return fewer documents than the index holds.
        """
        from llama_index.retrievers.bm25 import BM25Retriever  # type: ignore[import-untyped]

        nodes = build_nodes(self._catalog)
        corpus_n = len(nodes)
        top_k = min(self._retrieval.bm25_top_k or corpus_n, corpus_n)
        return BM25Retriever(
            nodes=nodes,
            similarity_top_k=top_k,
            token_pattern=TOKEN_PATTERN,
        )

    async def _build_bm25(self) -> object:
        """BM25 leg construction off the event loop (§15)."""
        return await asyncio.to_thread(self._build_bm25_sync)

    async def retrieve(
        self,
        *,
        statement: str,
        constraints: Sequence[str] = (),
        scope: str = "",
        exclude: Collection[str] = (),
        limit: int | None = None,
    ) -> list[RetrievalHit]:
        """Run §6 steps 1–4 for one decision part and return the survivor pool.

        Args:
            statement: the part's decision problem (drives the reranker query).
            constraints: verbatim constraints appended to the dense query (§6 step 1).
            scope: scope phrase folded into the dense query (e.g. ``"task-lifetime"``).
            exclude: sticky reselection exclusions (§11 item 4), removed pre-ranking.
            limit: survivor cap; ``None`` defaults to ``rerank_top_n`` (§6 step 4).

        Returns:
            Hits ranked by ``retrieval_score`` desc (ties: fused_rank, rerank_rank,
            catalog order, name), capped at ``limit``.
        """
        return (
            await self.retrieve_many(
                queries=[PartQuery(statement, constraints, scope, exclude, limit)]
            )
        )[0]

    async def retrieve_many(
        self,
        queries: Sequence[PartQuery],
    ) -> list[list[RetrievalHit]]:
        """Run §6 steps 1–4 for several decision parts; batched dense leg.

        The dense embeddings of all queries are fetched in ONE embedder round trip
        (``embed_queries``) and searched against FAISS as a single N×d matrix —
        per-part results are identical to N sequential ``retrieve()`` calls. The
        BM25, fusion, rerank and blend stages stay per-part (rerank is the
        sidecar's business, see the §14 latency notes).
        """
        caps = [
            self._rerank_top_n if query.limit is None else query.limit
            for query in queries
        ]
        if all(cap < 1 for cap in caps):
            return [[] for _ in queries]

        async def _part_tail(
            query: PartQuery,
            dense_map: dict[str, float],
            bm25_map: dict[str, float],
            cap: int,
        ) -> list[RetrievalHit]:
            # The shared dense leg (embed + FAISS) runs once for all parts; this
            # tail (fuse → rerank → blend) is bounded by ``max_concurrent_parts``
            # so N parts cannot stampede the rerank sidecar.
            async with self._part_semaphore:
                pool = self._fuse(dense_map, bm25_map, query.exclude)
                rerank_order = await self._rerank(
                    query.statement, [name for name, _ in pool]
                )
                return self._blend_and_cap(pool, rerank_order, cap)

        dense_queries = [
            dense_query(query.statement, query.constraints, query.scope) for query in queries
        ]
        lexical_queries = [bm25_query(dense) for dense in dense_queries]
        dense_maps, bm25_maps = await self._leg_scores_many(dense_queries, lexical_queries)
        hits_lists = await asyncio.gather(
            *(
                _part_tail(query, dense_map, bm25_map, cap)
                for query, dense_map, bm25_map, cap in zip(
                    queries, dense_maps, bm25_maps, caps, strict=True
                )
            )
        )
        return list(hits_lists)

    async def _leg_scores_many(
        self,
        dense_queries: Sequence[str],
        lexical_queries: Sequence[str],
    ) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
        """Batched per-leg score maps, per part (§6 step 2).

        One ``embed_queries`` call covers every non-empty dense query (batched §2.2
        seam); the FAISS search runs once over the N×d query matrix. BM25 stays
        per-query but runs off the event loop concurrently.
        """
        embed_positions = [i for i, dense in enumerate(dense_queries) if dense]
        dense_maps: list[dict[str, float]] = [{} for _ in dense_queries]
        if embed_positions and self._faiss_index is not None:
            top_k = min(self._retrieval.dense_top_k or len(self._names), len(self._names))
            query_embeddings = await self._embedder.embed_queries(
                [dense_queries[i] for i in embed_positions]
            )
            normalized = await asyncio.to_thread(l2_normalize_rows, query_embeddings)
            matrix = np.ascontiguousarray(np.asarray(normalized, dtype=np.float32))
            scores, indices = await asyncio.to_thread(self._faiss_index.search, matrix, top_k)
            for row, position in enumerate(embed_positions):
                dense_maps[position] = {
                    self._names[int(idx)]: float(score)
                    for score, idx in zip(scores[row], indices[row], strict=True)
                    if int(idx) != -1
                }
        bm25_maps = await asyncio.gather(
            *(self._bm25_leg(lexical) for lexical in lexical_queries)
        )
        return dense_maps, list(bm25_maps)

    def _blend_and_cap(
        self,
        pool: list[tuple[str, float]],
        rerank_order: dict[str, int],
        cap: int,
    ) -> list[RetrievalHit]:
        """RR blend over fused and rerank positions, ranked and capped (§6 step 4)."""
        hits = self._blend(pool, rerank_order)
        hits.sort(
            key=lambda hit: (
                -hit.retrieval_score,
                hit.fused_rank,
                hit.rerank_rank,
                self._catalog.order_index(hit.name),
                hit.name,
            )
        )
        return hits[:cap]

    def _bm25_search_sync(self, query: str) -> dict[str, float]:
        """BM25 scores for the normalized query over the node set (blocking)."""
        if self._bm25 is None:
            return {}
        from llama_index.retrievers.bm25 import BM25Retriever

        retriever = cast("BM25Retriever", self._bm25)
        return {
            str(result.node.node_id): float(result.score or 0.0)
            for result in retriever.retrieve(query)
        }

    async def _bm25_leg(self, query: str) -> dict[str, float]:
        """BM25 scores off the event loop; documents not returned score 0.0 later."""
        return await asyncio.to_thread(self._bm25_search_sync, query)

    def _fuse(
        self,
        dense_scores: dict[str, float],
        bm25_scores: dict[str, float],
        exclude: Collection[str],
    ) -> list[tuple[str, float]]:
        """Weighted fusion over the union, ranked fused desc (ties: order, name).

        Missing from a leg ⇒ that leg contributes 0.0. Exclusions are applied
        BEFORE ranking (§11 item 4) so they cannot occupy fused-rank positions.
        """
        dense_norm = _min_max(dense_scores)
        bm25_norm = _min_max(bm25_scores)
        excluded = set(exclude)
        union = set(dense_scores) | set(bm25_scores)
        fused: list[tuple[str, float]] = []
        for name in union:
            if name in excluded:
                continue
            score = (
                self._retrieval.dense_weight * dense_norm.get(name, 0.0)
                + self._retrieval.bm25_weight * bm25_norm.get(name, 0.0)
            )
            if score < self._retrieval.min_fusion_score:
                continue
            fused.append((name, score))
        fused.sort(key=lambda entry: (-entry[1], self._catalog.order_index(entry[0]), entry[0]))
        return fused

    async def _rerank(self, query: str, fused_names: Sequence[str]) -> dict[str, int]:
        """Mandatory cross-encoder pass for pools > 1 (§6 step 4).

        Returns:
            pattern name → 1-based rerank rank (best first). Empty when skipped;
            then callers fall back to the fused rank. A reranker exception
            propagates to the caller by contract.
        """
        if len(fused_names) <= 1:
            return {}
        texts = self._capsule_texts if self._rerank_text == "capsule" else self._doc_texts
        documents = [texts[self._names.index(name)] for name in fused_names]
        pairs = await self._reranker.rerank(query=query, documents=documents, top_n=len(fused_names))
        order: dict[str, int] = {}
        seen: set[int] = set()
        rank = 0
        for doc_index, _score in pairs:
            if doc_index in seen or not 0 <= doc_index < len(fused_names):
                continue
            seen.add(doc_index)
            rank += 1
            order[fused_names[doc_index]] = rank
        if len(order) < len(fused_names):
            logger.warning(
                "Reranker returned %d of %d documents; missing documents keep fused-order tail ranks",
                len(order),
                len(fused_names),
            )
            tail = len(fused_names)
            for name in reversed(fused_names):
                if name not in order:
                    order[name] = tail
                    tail -= 1
        return order

    def _blend(
        self,
        pool: Sequence[tuple[str, float]],
        rerank_order: dict[str, int],
    ) -> list[RetrievalHit]:
        """RR blend over fused and rerank positions (§6 step 4)."""
        rrf_k = self._retrieval.rrf_k
        hits: list[RetrievalHit] = []
        for position, (name, _fused) in enumerate(pool, start=1):
            rerank_rank = rerank_order.get(name, position)
            hits.append(
                RetrievalHit(
                    name=name,
                    retrieval_score=reciprocal_rank_score(position, rrf_k)
                    + reciprocal_rank_score(rerank_rank, rrf_k),
                    fused_rank=position,
                    rerank_rank=rerank_rank,
                )
            )
        return hits
