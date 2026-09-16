# Testing Guide

Comprehensive guide to testing Semantik plugins using contract tests, mocks, and fixtures.

## Overview

This template provides a testing framework that helps you:

1. **Verify contract compliance** - Ensure your plugin implements all required methods
2. **Use standardized fixtures** - Common test data and mock services
3. **Write isolated tests** - Mock dependencies without real services

## Quick Start

### 1. Install Test Dependencies

```bash
pip install -e ".[dev]"
# Or: pip install pytest pytest-asyncio
```

### 2. Use Contract Test Mixins

```python
# tests/test_my_plugin.py
import pytest
from tests.contract import EmbeddingContractMixin
from my_plugin import MyEmbeddingPlugin


class TestMyEmbeddingPlugin(EmbeddingContractMixin):
    """Test suite for MyEmbeddingPlugin.

    Inheriting from EmbeddingContractMixin automatically runs
    all contract verification tests.
    """

    @pytest.fixture
    def plugin_class(self):
        return MyEmbeddingPlugin

    @pytest.fixture
    def plugin_config(self):
        """Provide configuration for tests."""
        return {
            "model_name": "my-model",
            "batch_size": 32,
        }

    # Contract tests run automatically!

    # Add custom tests below:
    def test_my_custom_feature(self, plugin_instance):
        """Test a custom feature of your plugin."""
        assert plugin_instance.supports_feature_x()
```

### 3. Run Tests

```bash
pytest tests/ -v
```

---

## Contract Test Mixins

### BaseContractMixin (All Plugins)

All plugins must pass these tests:

| Test | Description |
|------|-------------|
| `test_has_plugin_id` | PLUGIN_ID class attribute exists |
| `test_plugin_id_format` | PLUGIN_ID is lowercase with hyphens |
| `test_has_plugin_type` | PLUGIN_TYPE class attribute exists |
| `test_plugin_type_valid` | PLUGIN_TYPE is one of 6 valid types |
| `test_has_plugin_version` | PLUGIN_VERSION exists |
| `test_plugin_version_is_semver` | PLUGIN_VERSION follows semver |
| `test_has_get_manifest` | get_manifest() method exists |
| `test_manifest_has_required_fields` | Manifest contains id, type, version |
| `test_can_instantiate` | Plugin can be instantiated |

### ConnectorContractMixin

Additional tests for connector plugins:

| Test | Description |
|------|-------------|
| `test_plugin_type_is_connector` | PLUGIN_TYPE == "connector" |
| `test_has_authenticate_method` | Has authenticate() async method |
| `test_has_load_documents_method` | Has load_documents() async generator |
| `test_has_get_config_fields` | Has get_config_fields() classmethod |
| `test_has_get_secret_fields` | Has get_secret_fields() classmethod |
| `test_authenticate_returns_bool` | authenticate() returns boolean |

### EmbeddingContractMixin

Additional tests for embedding plugins:

| Test | Description |
|------|-------------|
| `test_plugin_type_is_embedding` | PLUGIN_TYPE == "embedding" |
| `test_has_embed_texts_method` | Has embed_texts() async method |
| `test_has_get_definition_method` | Has get_definition() classmethod |
| `test_has_supports_model_method` | Has supports_model() classmethod |
| `test_definition_has_required_fields` | Definition contains required keys |

### ChunkingContractMixin

Additional tests for chunking plugins:

| Test | Description |
|------|-------------|
| `test_plugin_type_is_chunking` | PLUGIN_TYPE == "chunking" |
| `test_has_chunk_method` | Has chunk() method |
| `test_has_validate_content_method` | Has validate_content() method |
| `test_has_estimate_chunks_method` | Has estimate_chunks() method |
| `test_chunk_returns_list` | chunk() returns list of dicts |
| `test_validate_content_returns_tuple` | Returns (bool, str|None) |

### RerankerContractMixin

Additional tests for reranker plugins:

| Test | Description |
|------|-------------|
| `test_plugin_type_is_reranker` | PLUGIN_TYPE == "reranker" |
| `test_has_rerank_method` | Has rerank() async method |
| `test_has_get_capabilities_method` | Has get_capabilities() classmethod |
| `test_capabilities_has_required_fields` | Capabilities dict is valid |

### ExtractorContractMixin

Additional tests for extractor plugins:

| Test | Description |
|------|-------------|
| `test_plugin_type_is_extractor` | PLUGIN_TYPE == "extractor" |
| `test_has_extract_method` | Has extract() async method |
| `test_has_supported_extractions_method` | Has supported_extractions() classmethod |
| `test_supported_extractions_returns_list` | Returns list of strings |

### AgentContractMixin

Additional tests for agent plugins:

| Test | Description |
|------|-------------|
| `test_plugin_type_is_agent` | PLUGIN_TYPE == "agent" |
| `test_has_execute_method` | Has execute() async generator |
| `test_has_get_capabilities_method` | Has get_capabilities() classmethod |
| `test_has_supported_use_cases_method` | Has supported_use_cases() classmethod |
| `test_capabilities_has_required_fields` | Capabilities dict is valid |
| `test_use_cases_returns_list` | Returns list of strings |

---

## Available Fixtures

### Core Fixtures (conftest.py)

```python
@pytest.fixture
def plugin_class(self):
    """Override this to provide your plugin class."""
    raise NotImplementedError("Subclasses must provide plugin_class fixture")

@pytest.fixture
def plugin_config(self):
    """Override to provide plugin configuration."""
    return {}

@pytest.fixture
def plugin_instance(self, plugin_class, plugin_config):
    """Create a plugin instance with config."""
    return plugin_class(plugin_config)
```

### Sample Data Fixtures

Create these in your `tests/conftest.py`:

```python
import pytest

@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """Apple Inc. is an American multinational technology company
    headquartered in Cupertino, California. Apple is the world's largest
    technology company by revenue and one of the world's most valuable companies."""

@pytest.fixture
def sample_documents():
    """List of sample documents for batch testing."""
    return [
        "Machine learning is a subset of artificial intelligence.",
        "Natural language processing enables computers to understand text.",
        "Deep learning uses neural networks with many layers.",
        "Computer vision allows machines to interpret images.",
        "Reinforcement learning trains agents through rewards.",
    ]

@pytest.fixture
def sample_query():
    """Sample search query."""
    return "How do machines learn from data?"

@pytest.fixture
def sample_long_document():
    """Long document for chunking tests."""
    paragraphs = [
        f"This is paragraph {i}. It contains several sentences about topic {i}. "
        f"The content is designed to test chunking behavior with longer documents. "
        f"Each paragraph adds more context to ensure proper segmentation."
        for i in range(10)
    ]
    return "\n\n".join(paragraphs)
```

---

## Mock Classes

### MockEmbeddingService

For testing plugins that depend on embeddings:

```python
class MockEmbeddingService:
    """Mock embedding service for testing."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.embed_calls: list[str] = []
        self.batch_calls: list[list[str]] = []

    async def embed_single(self, text: str) -> list[float]:
        """Generate deterministic embedding based on text hash."""
        self.embed_calls.append(text)
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Create deterministic vector from hash
        return [float(b) / 255.0 for b in hash_bytes[:self.dimension]]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Batch embed texts."""
        self.batch_calls.append(texts)
        return [await self.embed_single(t) for t in texts]

    def get_dimension(self) -> int:
        return self.dimension
```

### MockReranker

For testing search result reranking:

```python
class MockReranker:
    """Mock reranker that scores by word overlap."""

    def __init__(self):
        self.rerank_calls: list[tuple[str, list[str]]] = []

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
    ) -> list[dict]:
        self.rerank_calls.append((query, documents))

        # Score by word overlap
        query_words = set(query.lower().split())
        results = []
        for i, doc in enumerate(documents):
            doc_words = set(doc.lower().split())
            overlap = len(query_words & doc_words)
            score = overlap / max(len(query_words), 1)
            results.append({"index": i, "score": score, "text": doc})

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        if top_k:
            results = results[:top_k]

        return results
```

### MockExtractor

For testing metadata extraction:

```python
class MockExtractor:
    """Mock extractor returning simple results."""

    def __init__(self):
        self.extract_calls: list[str] = []

    async def extract(
        self,
        text: str,
        extraction_types: list[str] | None = None,
    ) -> dict:
        self.extract_calls.append(text)

        # Extract first 3 words as mock entities
        words = text.split()[:3]
        entities = [
            {"text": word, "type": "UNKNOWN", "confidence": 0.8}
            for word in words
        ]

        return {
            "entities": entities,
            "keywords": words,
            "language": "en",
            "language_confidence": 0.99,
        }
```

---

## Writing Custom Tests

### Async Tests

```python
import pytest

class TestMyPlugin(EmbeddingContractMixin):
    @pytest.fixture
    def plugin_class(self):
        return MyPlugin

    @pytest.mark.asyncio
    async def test_batch_embedding(self, plugin_instance, sample_documents):
        """Test batch embedding works correctly."""
        embeddings = await plugin_instance.embed_texts(sample_documents)

        assert len(embeddings) == len(sample_documents)
        assert all(len(e) == 384 for e in embeddings)
```

### Testing Configuration

```python
class TestMyPlugin(EmbeddingContractMixin):
    @pytest.fixture
    def plugin_class(self):
        return MyPlugin

    @pytest.fixture
    def plugin_config(self):
        return {"model_name": "custom-model", "batch_size": 16}

    def test_config_is_applied(self, plugin_instance):
        """Verify configuration was applied."""
        assert plugin_instance._config["model_name"] == "custom-model"
```

### Testing Health Checks

```python
class TestMyPlugin(ExtractorContractMixin):
    @pytest.fixture
    def plugin_class(self):
        return MyPlugin

    @pytest.mark.asyncio
    async def test_health_check_without_config(self, plugin_class):
        """Health check should return False with missing API key."""
        result = await plugin_class.health_check(config={})
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_with_valid_config(self, plugin_class, monkeypatch):
        """Health check should return True with valid config."""
        monkeypatch.setenv("TEST_API_KEY", "test-key-12345")
        result = await plugin_class.health_check(
            config={"api_key_env": "TEST_API_KEY"}
        )
        assert result is True
```

### Testing Error Handling

```python
class TestMyPlugin(RerankerContractMixin):
    @pytest.fixture
    def plugin_class(self):
        return MyPlugin

    @pytest.mark.asyncio
    async def test_handles_empty_documents(self, plugin_instance):
        """Plugin should handle empty document list gracefully."""
        results = await plugin_instance.rerank(
            query="test",
            documents=[],
            top_k=10
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_handles_very_long_query(self, plugin_instance, sample_documents):
        """Plugin should handle very long queries."""
        long_query = "test " * 1000
        results = await plugin_instance.rerank(
            query=long_query,
            documents=sample_documents,
        )
        assert len(results) <= len(sample_documents)
```

---

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Contract Tests Only

```bash
pytest tests/ -v -k "contract"
```

### Run Specific Plugin Type Tests

```bash
pytest tests/ -v -k "embedding"
pytest tests/ -v -k "connector"
```

### Run with Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

### Run Async Tests

```bash
# With auto mode (recommended - set in pyproject.toml)
pytest tests/ -v

# Or explicitly
pytest tests/ -v --asyncio-mode=auto
```

---

## Best Practices

### 1. Always Test Edge Cases

```python
def test_empty_input(self, plugin_instance):
    result = plugin_instance.process("")
    assert result is not None  # Should not crash

def test_unicode_input(self, plugin_instance):
    result = plugin_instance.process("Hello ")
    assert result is not None

def test_very_long_input(self, plugin_instance, sample_long_document):
    result = plugin_instance.process(sample_long_document * 100)
    assert result is not None
```

### 2. Use Fixtures for Common Setup

```python
@pytest.fixture
async def initialized_plugin(self, plugin_instance):
    """Provide an initialized plugin with cleanup."""
    await plugin_instance.initialize()
    yield plugin_instance
    await plugin_instance.cleanup()

async def test_something(self, initialized_plugin):
    # Plugin is already initialized and will be cleaned up
    result = await initialized_plugin.do_something()
```

### 3. Mock External Services

```python
def test_with_mock_embedding(self, plugin_instance):
    """Use mock instead of real embedding service."""
    mock_service = MockEmbeddingService(dimension=384)
    plugin_instance._embedding_service = mock_service

    result = plugin_instance.process_with_embeddings("test")

    assert mock_service.embed_calls == ["test"]
```

### 4. Test Both Success and Failure Paths

```python
@pytest.mark.asyncio
async def test_authentication_success(self, plugin_instance):
    """Test successful authentication."""
    plugin_instance._config = {"api_key": "valid-key"}
    result = await plugin_instance.authenticate()
    assert result is True

@pytest.mark.asyncio
async def test_authentication_failure(self, plugin_instance):
    """Test failed authentication."""
    plugin_instance._config = {}  # No API key
    result = await plugin_instance.authenticate()
    assert result is False
```

---

## Troubleshooting

### "Plugin class not set"

Make sure you provide the `plugin_class` fixture:

```python
class TestMyPlugin(EmbeddingContractMixin):
    @pytest.fixture
    def plugin_class(self):
        return MyPlugin  # Required!
```

### "Async tests not running"

Ensure pytest-asyncio is installed and configured:

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Or add markers:

```python
@pytest.mark.asyncio
async def test_async_method(self):
    ...
```

### "Fixture not found"

Make sure your `tests/conftest.py` imports the contract mixins:

```python
# tests/conftest.py
from tests.contract import *  # or specific imports
```

### "Import errors"

Ensure your package is installed in development mode:

```bash
pip install -e ".[dev]"
```
