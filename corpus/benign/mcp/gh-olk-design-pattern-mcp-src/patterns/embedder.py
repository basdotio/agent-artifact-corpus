"""Embedding seams and the TEI/offline embedder implementations (§2.2, §15).

The dense leg embeds every document once at build time, L2-normalized, so FAISS
``IndexFlatIP`` inner products equal cosine similarity. Two implementations:

* :class:`TEIEmbedder` — LiteLLM-backed TEI client with asymmetric instruction prefixes
  (mirrors the sibling server's ``InstructionAwareEmbedding``).
* :class:`OfflineHashEmbedder` — deterministic hashed bag-of-words, no network; the
  ``--health`` path and the test battery.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, cast

import numpy as np

from src.config import EmbedderConfig
from src.errors import ERROR_RETRIEVAL_UNAVAILABLE, DesignPatternError
from src.patterns.nodes import tokenize

logger = logging.getLogger(__name__)

#: Hash dimensionality of the offline bag-of-words embedder (``--health`` + tests).
OFFLINE_EMBEDDING_DIM = 512


def l2_normalize_rows(vectors: Sequence[Sequence[float]]) -> list[list[float]]:
    """Row-wise L2 normalization to unit length; zero vectors pass through unchanged."""
    arr = np.asarray(vectors, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    return cast("list[list[float]]", (arr / norms).tolist())


class EmbedderProtocol(Protocol):
    """Embedding seam (§2.2): batch document texts, single and batched query texts."""

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...

    async def embed_queries(self, texts: Sequence[str]) -> list[list[float]]: ...


class TEIEmbedder:
    """LiteLLM-backed TEI embedder with instruction prefixes and L2-normalized output.

    Mirrors the sibling's ``InstructionAwareEmbedding``: asymmetric query/text
    instruction prefixes, every embedding-producing path normalized to unit length
    so FAISS ``IndexFlatIP`` inner products equal cosine similarity. Both protocol
    methods delegate through ``asyncio.to_thread`` (§15).
    """

    def __init__(self, config: EmbedderConfig) -> None:
        from llama_index.embeddings.litellm import LiteLLMEmbedding  # type: ignore[import-untyped]

        inner = config.config
        self._query_instruction = inner.query_instruction
        self._text_instruction = inner.text_instruction
        self._doc_attempts = inner.document_embed_attempts
        self._doc_backoff = inner.document_embed_backoff_seconds
        self._config = config
        self._embedding = LiteLLMEmbedding(
            model_name=inner.model,
            api_base=inner.base_url,
            api_key=inner.api_key or None,
            embed_batch_size=inner.embed_batch_size,
        )

    def _format_query(self, query: str) -> str:
        return f"{self._query_instruction}{query}" if self._query_instruction else query

    def _format_text(self, text: str) -> str:
        return f"{self._text_instruction}{text}" if self._text_instruction else text

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Batch-embed document texts with bounded startup retry; L2-normalized (§2.2).

        Retries are scoped to build-time document embedding (including the cache builder):
        a TEI sidecar that is still warming or restarting must not fail the warm-up.
        ``embed_query`` stays fail-fast — request latency must not absorb an outage.
        """
        formatted = [self._format_text(text) for text in texts]
        delay = self._doc_backoff
        last_error: Exception | None = None
        for attempt in range(1, self._doc_attempts + 1):
            try:
                raw = await asyncio.to_thread(self._embedding.get_text_embedding_batch, formatted)
            except Exception as exc:  # provider-agnostic retry wrapper
                last_error = exc
                if attempt == self._doc_attempts:
                    break
                logger.warning(
                    "Embedder unavailable (attempt %d/%d): %s; retrying in %.1fs",
                    attempt,
                    self._doc_attempts,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2.0, 30.0)
                continue
            return await asyncio.to_thread(l2_normalize_rows, raw)
        assert last_error is not None
        raise last_error

    async def embed_query(self, text: str) -> list[float]:
        """Embed one query with the query instruction; L2-normalized."""
        raw = await asyncio.to_thread(self._embedding.get_query_embedding, self._format_query(text))
        return (await asyncio.to_thread(l2_normalize_rows, [raw]))[0]

    async def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        """Batch-embed query texts with the query instruction; L2-normalized.

        One ``get_text_embedding_batch`` round trip for all queries — the batched
        form of ``embed_query`` with identical per-text semantics: every text is
        formatted with the query instruction and embedded by the same TEI endpoint
        (the server applies its query prompt to every batch input), then rows are
        L2-normalized. Fail-fast like ``embed_query`` — no retry: request latency
        must not absorb an outage (retry is build-time-only, see ``embed_documents``).
        """
        formatted = [self._format_query(text) for text in texts]
        raw = await asyncio.to_thread(self._embedding.get_text_embedding_batch, formatted)
        return await asyncio.to_thread(l2_normalize_rows, raw)


class OfflineHashEmbedder:
    """Deterministic hashed bag-of-words embedder with no network (§15 test seam).

    Each token hashes (blake2b, stable across processes) to one of
    ``OFFLINE_EMBEDDING_DIM`` dimensions with sublinear term weighting
    ``1 + log(count)``, then the vector is L2-normalized — the same contract as the
    production embedder, so ``IndexFlatIP`` inner products equal cosine similarity.
    """

    def __init__(self, dimension: int = OFFLINE_EMBEDDING_DIM) -> None:
        self._dimension = dimension

    def _embed(self, text: str) -> list[float]:
        vector = np.zeros(self._dimension, dtype=np.float32)
        counts: dict[int, int] = {}
        for token in tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            slot = int.from_bytes(digest, "big") % self._dimension
            counts[slot] = counts.get(slot, 0) + 1
        for slot, count in counts.items():
            vector[slot] = 1.0 + math.log(count)
        norm = float(np.linalg.norm(vector))
        if norm > 0.0:
            vector /= norm
        return vector.tolist()

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Hash-embed document texts (CPU-bound work in a thread, §15)."""
        return await asyncio.to_thread(lambda: [self._embed(text) for text in texts])

    async def embed_query(self, text: str) -> list[float]:
        """Hash-embed one query text."""
        return await asyncio.to_thread(self._embed, text)

    async def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        """Hash-embed query texts (CPU-bound work in a thread, §15)."""
        return await asyncio.to_thread(lambda: [self._embed(text) for text in texts])


@dataclass(frozen=True)
class EmbedderIdentity:
    """Identity of the embedding space a configured embedder produces (cache fingerprint input)."""

    model: str
    text_instruction: str = ""
    model_repo: str = ""
    onnx_variant: str = ""


def embedder_identity(config: EmbedderConfig) -> EmbedderIdentity:
    """Snapshot the configured embedder's identity (cache fingerprint input, §2.2)."""
    inner = config.config
    return EmbedderIdentity(
        model=inner.model,
        text_instruction=inner.text_instruction,
        model_repo=inner.model_repo,
        onnx_variant=inner.onnx_variant,
    )


def build_embedder(config: EmbedderConfig) -> EmbedderProtocol:
    """TEI embedder for ``config``; refuses an empty ``base_url`` at construction (§2.2)."""
    if not config.config.base_url.strip():
        raise DesignPatternError(
            ERROR_RETRIEVAL_UNAVAILABLE,
            "embedder base_url is empty — the dense leg cannot start",
            hint="set DESIGN_PATTERN_EMBEDDER_BASE_URL or config/config.json embedder.config.base_url",
        )
    return TEIEmbedder(config)
