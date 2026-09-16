# Reranker Plugin Guide

Reranker plugins reorder search results by relevance to the query.

## When to Use

Create a reranker plugin when you need to:
- Integrate a cross-encoder reranking model
- Use a reranking API (Cohere, Jina, etc.)
- Implement custom relevance scoring
- Add domain-specific reranking logic

## Required Class Variables

```python
from typing import ClassVar

class MyReranker:
    PLUGIN_ID: ClassVar[str] = "my-reranker"
    PLUGIN_TYPE: ClassVar[str] = "reranker"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"
```

## Required Methods

### `__init__(config: dict | None = None)`

Initialize with configuration:

```python
def __init__(self, config: dict[str, Any] | None = None) -> None:
    self._config = config or {}
    self._model = self._config.get("model", "default-model")
    self._api_key = self._config.get("api_key")
```

### `rerank(query, documents, top_k, metadata) -> list[dict]`

Rerank documents for a query:

```python
async def rerank(
    self,
    query: str,
    documents: list[str],
    top_k: int | None = None,
    metadata: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Rerank documents by relevance to query.

    Args:
        query: Search query string.
        documents: List of document texts to rerank.
        top_k: Optional limit on results.
        metadata: Optional metadata for each document.

    Returns:
        List of RerankResultDict sorted by score descending.
    """
    # Score each document
    scores = await self._score_documents(query, documents)

    # Build results
    results = []
    for i, (doc, score) in enumerate(zip(documents, scores)):
        results.append({
            "index": i,
            "score": score,
            "text": doc,
            "metadata": metadata[i] if metadata else None,
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    # Apply top_k limit
    if top_k:
        results = results[:top_k]

    return results
```

### `get_capabilities() -> dict`

Declare reranker capabilities:

```python
@classmethod
def get_capabilities(cls) -> dict[str, Any]:
    return {
        "max_documents": 100,      # Max docs per request
        "max_query_length": 512,   # Max query length
        "max_doc_length": 4096,    # Max document length
        "supports_batching": True, # Batch processing support
        "models": ["model-a", "model-b"],  # Supported models
    }
```

### `get_manifest() -> dict`

Return plugin metadata:

```python
@classmethod
def get_manifest(cls) -> dict[str, Any]:
    return {
        "id": cls.PLUGIN_ID,
        "type": cls.PLUGIN_TYPE,
        "version": cls.PLUGIN_VERSION,
        "display_name": "My Reranker",
        "description": "Cross-encoder reranking",
        "capabilities": cls.get_capabilities(),
    }
```

## Result Format (RerankResultDict)

```python
{
    "index": int,           # Original document index (required)
    "score": float,         # Relevance score, higher = better (required)
    "text": str | None,     # Document text (optional)
    "metadata": dict | None, # Associated metadata (optional)
}
```

## Complete Example

```python
from typing import ClassVar, Any
import aiohttp


class CohereReranker:
    PLUGIN_ID: ClassVar[str] = "cohere-rerank"
    PLUGIN_TYPE: ClassVar[str] = "reranker"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._api_key = self._config.get("api_key")
        self._model = self._config.get("model", "rerank-english-v3.0")

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
        metadata: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if not self._api_key:
            raise ValueError("API key required")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.cohere.ai/v1/rerank",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "query": query,
                    "documents": documents,
                    "model": self._model,
                    "top_n": top_k or len(documents),
                },
            ) as resp:
                data = await resp.json()

        results = []
        for item in data.get("results", []):
            idx = item["index"]
            results.append({
                "index": idx,
                "score": item["relevance_score"],
                "text": documents[idx],
                "metadata": metadata[idx] if metadata else None,
            })

        return results

    @classmethod
    def get_capabilities(cls) -> dict[str, Any]:
        return {
            "max_documents": 1000,
            "max_query_length": 512,
            "max_doc_length": 4096,
            "supports_batching": True,
            "models": ["rerank-english-v3.0", "rerank-multilingual-v3.0"],
        }

    @classmethod
    def get_manifest(cls) -> dict[str, Any]:
        return {
            "id": cls.PLUGIN_ID,
            "type": cls.PLUGIN_TYPE,
            "version": cls.PLUGIN_VERSION,
            "display_name": "Cohere Rerank",
            "description": "Cohere rerank-v3 models",
            "capabilities": cls.get_capabilities(),
        }
```

## Common Gotchas

1. **Score Direction**: Higher scores = more relevant
2. **Original Index**: `index` must be the original position in input list
3. **Sort Results**: Results should be sorted by score descending
4. **Empty Input**: Handle empty document list gracefully
5. **Truncation**: Truncate long documents to `max_doc_length`

## Testing

```python
import pytest
from my_reranker import CohereReranker

class TestCohereReranker:
    def test_plugin_attributes(self):
        assert CohereReranker.PLUGIN_ID == "cohere-rerank"
        assert CohereReranker.PLUGIN_TYPE == "reranker"

    def test_capabilities(self):
        caps = CohereReranker.get_capabilities()
        assert "max_documents" in caps
        assert "max_query_length" in caps
        assert caps["max_documents"] > 0

    @pytest.mark.asyncio
    async def test_rerank_format(self, mock_api):
        reranker = CohereReranker(config={"api_key": "test"})
        results = await reranker.rerank(
            query="test query",
            documents=["doc 1", "doc 2", "doc 3"],
            top_k=2,
        )
        assert len(results) == 2
        assert "index" in results[0]
        assert "score" in results[0]
        assert results[0]["score"] >= results[1]["score"]
```
