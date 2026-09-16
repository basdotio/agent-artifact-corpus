# Embedding Plugin Guide

Embedding plugins convert text into vector representations for semantic search.

## When to Use

Create an embedding plugin when you need to:
- Integrate a new embedding API (OpenAI, Cohere, Voyage, etc.)
- Use a custom/fine-tuned embedding model
- Add local embedding models (sentence-transformers, etc.)
- Implement hybrid embedding strategies

## Required Class Variables

```python
from typing import ClassVar, Any

class MyEmbedding:
    PLUGIN_ID: ClassVar[str] = "my-embedding"
    PLUGIN_TYPE: ClassVar[str] = "embedding"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"
    INTERNAL_NAME: ClassVar[str] = "my_embedding"   # Internal registry ID
    API_ID: ClassVar[str] = "my-embedding"          # External API ID
    PROVIDER_TYPE: ClassVar[str] = "remote"         # local, remote, or hybrid
    METADATA: ClassVar[dict[str, Any]] = {
        "display_name": "My Embedding",
        "description": "Custom embedding provider",
    }
```

### Provider Types

| Type | Description | Example |
|------|-------------|---------|
| `local` | Runs on local GPU/CPU | sentence-transformers |
| `remote` | Calls external API | OpenAI, Cohere |
| `hybrid` | Can run locally or remotely | Custom implementation |

## Required Methods

### `__init__(config: dict | None = None)`

Initialize with configuration:

```python
def __init__(self, config: dict[str, Any] | None = None) -> None:
    self._config = config or {}
    self._model_name: str | None = None
    self._dimension: int = 768
    self._initialized: bool = False
```

### `embed_texts(texts: list[str], mode: str) -> list[list[float]]`

Generate embeddings:

```python
async def embed_texts(
    self,
    texts: list[str],
    mode: str = "document",
) -> list[list[float]]:
    """Generate embeddings for texts.

    Args:
        texts: List of text strings to embed.
        mode: "query" or "document".

    Returns:
        List of embedding vectors.
    """
    # Call your embedding API/model
    embeddings = []
    for text in texts:
        if mode == "query":
            text = f"query: {text}"  # For asymmetric models
        embedding = await self._get_embedding(text)
        embeddings.append(embedding)
    return embeddings
```

### `get_definition() -> dict`

Return provider definition:

```python
@classmethod
def get_definition(cls) -> dict[str, Any]:
    return {
        "api_id": cls.API_ID,
        "internal_id": cls.INTERNAL_NAME,
        "display_name": cls.METADATA["display_name"],
        "description": cls.METADATA["description"],
        "provider_type": cls.PROVIDER_TYPE,
        "supports_asymmetric": True,  # Query/doc different processing
        "is_plugin": True,
    }
```

### `supports_model(model_name: str) -> bool`

Check model support:

```python
SUPPORTED_MODELS = ["my-model-small", "my-model-large"]

@classmethod
def supports_model(cls, model_name: str) -> bool:
    return model_name in cls.SUPPORTED_MODELS
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
        "display_name": cls.METADATA["display_name"],
        "description": cls.METADATA["description"],
    }
```

## Embedding Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `query` | Processing search queries | May apply query prefixes |
| `document` | Processing documents for indexing | Typically no prefix |

Asymmetric models (like E5, BGE) need different processing:

```python
async def embed_texts(self, texts: list[str], mode: str = "document"):
    if mode == "query":
        texts = [f"query: {t}" for t in texts]
    else:
        texts = [f"passage: {t}" for t in texts]
    return await self._embed(texts)
```

## Definition Format (EmbeddingProviderDefinitionDict)

```python
{
    "api_id": str,                    # External API identifier
    "internal_id": str,               # Internal registry ID
    "display_name": str,              # Human-readable name
    "description": str,               # Provider description
    "provider_type": str,             # local, remote, or hybrid
    "supports_quantization": bool,    # Optional
    "supports_instruction": bool,     # Optional
    "supports_batch_processing": bool, # Optional
    "supports_asymmetric": bool,      # Query/doc different processing
    "supported_models": list[str],    # Optional list of models
    "is_plugin": bool,                # Mark as external plugin
}
```

## Complete Example

```python
from typing import ClassVar, Any
import aiohttp


class CohereEmbedding:
    PLUGIN_ID: ClassVar[str] = "cohere-embed"
    PLUGIN_TYPE: ClassVar[str] = "embedding"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"
    INTERNAL_NAME: ClassVar[str] = "cohere_embed"
    API_ID: ClassVar[str] = "cohere-embed"
    PROVIDER_TYPE: ClassVar[str] = "remote"
    METADATA: ClassVar[dict[str, Any]] = {
        "display_name": "Cohere Embeddings",
        "description": "Cohere embed-v3 models",
    }

    SUPPORTED_MODELS: ClassVar[dict[str, int]] = {
        "embed-english-v3.0": 1024,
        "embed-multilingual-v3.0": 1024,
        "embed-english-light-v3.0": 384,
        "embed-multilingual-light-v3.0": 384,
    }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._api_key = self._config.get("api_key")
        self._model = self._config.get("model", "embed-english-v3.0")
        self._initialized = False

    async def embed_texts(
        self,
        texts: list[str],
        mode: str = "document",
    ) -> list[list[float]]:
        if not self._api_key:
            raise ValueError("API key required")

        # Cohere uses input_type for asymmetric
        input_type = "search_query" if mode == "query" else "search_document"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.cohere.ai/v1/embed",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "texts": texts,
                    "model": self._model,
                    "input_type": input_type,
                },
            ) as resp:
                data = await resp.json()
                return data["embeddings"]

    def get_dimension(self) -> int:
        return self.SUPPORTED_MODELS.get(self._model, 1024)

    @classmethod
    def get_definition(cls) -> dict[str, Any]:
        return {
            "api_id": cls.API_ID,
            "internal_id": cls.INTERNAL_NAME,
            "display_name": cls.METADATA["display_name"],
            "description": cls.METADATA["description"],
            "provider_type": cls.PROVIDER_TYPE,
            "supports_asymmetric": True,
            "supported_models": list(cls.SUPPORTED_MODELS.keys()),
            "is_plugin": True,
        }

    @classmethod
    def supports_model(cls, model_name: str) -> bool:
        return model_name in cls.SUPPORTED_MODELS

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "api_key_env": {
                    "type": "string",
                    "description": "Environment variable for API key",
                },
                "model": {
                    "type": "string",
                    "enum": list(cls.SUPPORTED_MODELS.keys()),
                    "default": "embed-english-v3.0",
                },
            },
            "required": ["api_key_env"],
        }

    @classmethod
    def get_manifest(cls) -> dict[str, Any]:
        return {
            "id": cls.PLUGIN_ID,
            "type": cls.PLUGIN_TYPE,
            "version": cls.PLUGIN_VERSION,
            "display_name": cls.METADATA["display_name"],
            "description": cls.METADATA["description"],
            "capabilities": {
                "models": list(cls.SUPPORTED_MODELS.keys()),
                "dimensions": list(cls.SUPPORTED_MODELS.values()),
            },
        }
```

## Common Gotchas

1. **Dimension Consistency**: Embeddings must always have the same dimension
2. **Batch Size Limits**: Most APIs limit batch size (e.g., 96 texts)
3. **Rate Limiting**: Implement backoff for API rate limits
4. **Mode Handling**: Always check the `mode` parameter for asymmetric models
5. **Type Consistency**: Return `list[list[float]]`, not numpy arrays

## Testing

```python
import pytest
from my_embedding import CohereEmbedding

class TestCohereEmbedding:
    def test_plugin_attributes(self):
        assert CohereEmbedding.PLUGIN_ID == "cohere-embed"
        assert CohereEmbedding.PLUGIN_TYPE == "embedding"

    def test_supports_model(self):
        assert CohereEmbedding.supports_model("embed-english-v3.0")
        assert not CohereEmbedding.supports_model("unknown-model")

    def test_definition_format(self):
        defn = CohereEmbedding.get_definition()
        assert "api_id" in defn
        assert "internal_id" in defn
        assert "provider_type" in defn

    @pytest.mark.asyncio
    async def test_embed_texts(self, mock_api):
        embedding = CohereEmbedding(config={"api_key": "test"})
        results = await embedding.embed_texts(["hello"], mode="query")
        assert len(results) == 1
        assert len(results[0]) == 1024  # Expected dimension
```
