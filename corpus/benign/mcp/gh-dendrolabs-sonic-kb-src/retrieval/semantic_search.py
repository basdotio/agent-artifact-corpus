"""Semantic search over the sonic-kb knowledge base.

Loads pre-computed embeddings from _vector_index.json, encodes queries with
sentence-transformers, and returns ranked results via brute-force cosine similarity.
"""

from __future__ import annotations

from ._loader import load_vector_index

_model_cache: dict = {}
_embeddings_cache: dict = {}


def search_kb(
    query: str,
    top_k: int = 5,
    content_type: str | None = None,
) -> list[dict]:
    """Search the KB by natural language query.

    Returns a ranked list of {id, type, title, text, score} dicts.
    Raises RuntimeError if sentence-transformers or numpy is not installed.
    Returns [] with kb_coverage='not_built' if vector index doesn't exist.
    """
    try:
        import numpy as np
    except ImportError:
        raise RuntimeError(
            "numpy is required for semantic search. "
            "Install with: pip install sonic-knowledge-base[vector]"
        )
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise RuntimeError(
            "sentence-transformers is required for semantic search. "
            "Install with: pip install sonic-knowledge-base[vector]"
        )

    index = load_vector_index()
    if index is None:
        return []

    if "chunks" not in index:
        return []

    chunks = index["chunks"]
    if content_type:
        chunks = [c for c in chunks if c["type"] == content_type]
    if not chunks:
        return []

    top_k = max(1, min(top_k, 20))

    model_name = index.get("model", "all-MiniLM-L6-v2")
    if model_name not in _model_cache:
        _model_cache[model_name] = SentenceTransformer(model_name)
    model = _model_cache[model_name]

    query_emb = model.encode([query], normalize_embeddings=True)[0]

    chunk_ids = tuple(c["id"] for c in chunks)
    cache_key = (model_name, chunk_ids)
    if cache_key not in _embeddings_cache:
        _embeddings_cache[cache_key] = np.array(
            [c["embedding"] for c in chunks], dtype=np.float32
        )
    embeddings = _embeddings_cache[cache_key]

    scores = embeddings @ query_emb.astype(np.float32)
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        idx = int(idx)
        c = chunks[idx]
        results.append({
            "id": c["id"],
            "type": c["type"],
            "title": c["title"],
            "text": c["text"],
            "score": round(float(scores[idx]), 4),
        })
    return results
