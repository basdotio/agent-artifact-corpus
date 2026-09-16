# Advanced Guide

Health checks, plugin dependencies, ABC migration, and extended data formats.

## Health Checks

Health checks verify that your plugin is operational. Semantik calls these to validate configuration and connectivity.

### Implementing Health Checks

```python
from typing import ClassVar, Any


class MyPlugin:
    PLUGIN_ID: ClassVar[str] = "my-plugin"
    PLUGIN_TYPE: ClassVar[str] = "embedding"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"

    @classmethod
    async def health_check(cls, config: dict[str, Any] | None = None) -> bool:
        """Return True if the plugin is operational.

        Health checks should:
        - Complete within 5 seconds (timeout enforced)
        - Not modify any state
        - Verify external dependencies are accessible
        """
        if not config:
            return False

        api_key = config.get("api_key")
        if not api_key:
            return False

        try:
            import aiohttp
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=3)
            ) as session:
                async with session.get(
                    "https://api.example.com/health",
                    headers={"Authorization": f"Bearer {api_key}"},
                ) as response:
                    return response.status == 200
        except Exception:
            return False
```

### Health Check Best Practices

1. **Keep it fast** - Complete within 3 seconds
2. **Handle missing config** - Return `False` if config is None or incomplete
3. **Don't modify state** - Health checks should be read-only
4. **Verify connectivity** - Test that external services are reachable
5. **Catch all exceptions** - Never raise, always return `False` on error

### Testing Health Checks

```python
import pytest

class TestMyPlugin:
    @pytest.mark.asyncio
    async def test_health_check_no_config(self):
        result = await MyPlugin.health_check(None)
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_missing_api_key(self):
        result = await MyPlugin.health_check({})
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_valid(self, mock_api):
        result = await MyPlugin.health_check({"api_key": "test-key"})
        assert result is True
```

---

## Plugin Dependencies

Declare dependencies on other plugins using the `requires` field in your manifest.

### Simple Dependencies

```python
@classmethod
def get_manifest(cls) -> dict[str, Any]:
    return {
        "id": cls.PLUGIN_ID,
        "type": cls.PLUGIN_TYPE,
        "version": cls.PLUGIN_VERSION,
        "display_name": "My Plugin",
        "description": "Depends on another plugin",
        "requires": ["other-plugin"],  # Simple: just the plugin ID
    }
```

### Versioned Dependencies

```python
@classmethod
def get_manifest(cls) -> dict[str, Any]:
    return {
        "id": cls.PLUGIN_ID,
        "type": cls.PLUGIN_TYPE,
        "version": cls.PLUGIN_VERSION,
        "display_name": "My Plugin",
        "description": "Depends on specific versions",
        "requires": [
            {
                "plugin_id": "embedding-provider",
                "min_version": "1.0.0",
                "max_version": "2.0.0",
            },
            {
                "plugin_id": "optional-feature",
                "optional": True,  # Won't fail if missing
            },
        ],
    }
```

### Dependency Resolution

- Dependencies are validated at load time
- Missing required dependencies log warnings but don't block loading
- Version constraints use semantic versioning comparison
- Optional dependencies are silently skipped if not found

---

## Migrating from ABC-Based Plugins

If you have plugins that inherit from semantik base classes, you can migrate to protocol-based for zero dependencies.

### Before (ABC-Based)

```python
from shared.connectors.base import BaseConnector
from shared.dtos.ingestion import IngestedDocument


class MyConnector(BaseConnector):
    PLUGIN_ID = "my-connector"
    PLUGIN_TYPE = "connector"
    PLUGIN_VERSION = "1.0.0"

    async def load_documents(self, source_id=None):
        for doc in self._fetch_documents():
            yield IngestedDocument(
                content=doc["text"],
                unique_id=doc["id"],
                source_type=self.PLUGIN_ID,
                metadata={},
                content_hash=self._compute_hash(doc["text"]),
            )
```

### After (Protocol-Based)

```python
import hashlib
from typing import ClassVar, Any, AsyncIterator


class MyConnector:  # No inheritance!
    PLUGIN_ID: ClassVar[str] = "my-connector"
    PLUGIN_TYPE: ClassVar[str] = "connector"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"
    METADATA: ClassVar[dict[str, Any]] = {
        "name": "My Connector",
        "description": "Custom document source",
    }

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    async def authenticate(self) -> bool:
        return True

    async def load_documents(
        self, source_id: int | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        for doc in self._fetch_documents():
            content = doc["text"]
            yield {
                "content": content,
                "unique_id": doc["id"],
                "source_type": self.PLUGIN_ID,
                "metadata": {},
                "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            }

    @classmethod
    def get_config_fields(cls) -> list[dict[str, Any]]:
        return []

    @classmethod
    def get_secret_fields(cls) -> list[dict[str, Any]]:
        return []

    @classmethod
    def get_manifest(cls) -> dict[str, Any]:
        return {
            "id": cls.PLUGIN_ID,
            "type": cls.PLUGIN_TYPE,
            "version": cls.PLUGIN_VERSION,
            "display_name": cls.METADATA["name"],
            "description": cls.METADATA["description"],
        }

    def _fetch_documents(self):
        # Your implementation
        ...
```

### Migration Checklist

- [ ] Remove base class inheritance
- [ ] Add `ClassVar` type annotations to class variables
- [ ] Add `METADATA` class variable if needed
- [ ] Replace dataclass returns with dict returns
- [ ] Add `__init__` that accepts config dict
- [ ] Add `get_config_fields()` classmethod
- [ ] Add `get_secret_fields()` classmethod
- [ ] Add `get_manifest()` classmethod
- [ ] Replace `IngestedDocument` with dict
- [ ] Use `hashlib.sha256(...).hexdigest()` for content hashes
- [ ] Remove semantik from dependencies

---

## Extended Data Formats

### ChunkMetadataDict (Complete)

All optional fields for chunk metadata:

```python
{
    # Position
    "chunk_id": str,                    # Unique chunk identifier
    "document_id": str,                 # Parent document ID
    "chunk_index": int,                 # Position in document (0-indexed)
    "start_offset": int,                # Start character position
    "end_offset": int,                  # End character position

    # Content analysis
    "token_count": int,                 # Number of tokens
    "strategy_name": str,               # Chunking strategy used

    # Quality metrics
    "semantic_score": float | None,     # Semantic coherence (0.0-1.0)
    "semantic_density": float,          # Information density
    "confidence_score": float,          # Chunk quality confidence
    "overlap_percentage": float,        # Overlap with adjacent chunks

    # Structure
    "hierarchy_level": int | None,      # Heading level (1-6)
    "section_title": str | None,        # Current section title
    "heading_hierarchy": list[str],     # Parent headings ["H1", "H2", ...]

    # Custom
    "custom_attributes": dict[str, Any], # Plugin-specific data
}
```

### ChunkConfigDict (Complete)

All configuration options for chunking:

```python
{
    # Size limits (characters)
    "chunk_size": int,           # Target chunk size (default: 500)
    "chunk_overlap": int,        # Overlap between chunks (default: 50)
    "min_chunk_size": int,       # Minimum chunk size
    "max_chunk_size": int,       # Maximum chunk size

    # Size limits (tokens)
    "min_tokens": int,           # Minimum tokens per chunk
    "max_tokens": int,           # Maximum tokens per chunk
    "overlap_tokens": int,       # Overlap in tokens

    # Behavior
    "separator": str,            # Text separator
    "keep_separator": bool,      # Keep separator in chunks
    "preserve_structure": bool,  # Preserve document structure

    # Semantic chunking
    "semantic_threshold": float, # Semantic similarity threshold

    # Hierarchy
    "hierarchy_levels": int,     # Heading hierarchy depth to track
}
```

### AgentCapabilitiesDict (Complete)

All capability declarations for agents:

```python
{
    # Streaming and response
    "supports_streaming": bool,           # Can stream responses
    "supports_interruption": bool,        # Can be interrupted mid-response

    # Tools
    "supports_tools": bool,               # Can use tools
    "supports_parallel_tools": bool,      # Can call multiple tools at once
    "max_tools": int | None,              # Maximum tools per request

    # Sessions
    "supports_sessions": bool,            # Maintains conversation history
    "supports_session_fork": bool,        # Can fork sessions

    # Advanced features
    "supports_extended_thinking": bool,   # Extended thinking mode
    "supports_thinking_budget": bool,     # Can limit thinking tokens
    "supports_subagents": bool,           # Can delegate to sub-agents
    "supports_handoffs": bool,            # Can hand off to other agents

    # Limits
    "max_context_tokens": int | None,     # Maximum context window
    "max_output_tokens": int | None,      # Maximum output size

    # Models
    "supported_models": list[str],        # Supported model identifiers
    "default_model": str | None,          # Default model to use
}
```

### TokenUsageDict (Complete)

Token usage statistics for agents:

```python
{
    "input_tokens": int,         # Input/prompt tokens
    "output_tokens": int,        # Output/completion tokens
    "cache_read_tokens": int,    # Tokens read from cache
    "cache_write_tokens": int,   # Tokens written to cache
    "reasoning_tokens": int,     # Tokens used for reasoning/thinking
}
```

### AgentContextDict (Complete)

Runtime context passed to agent execute():

```python
{
    # Request identification
    "request_id": str,                     # Unique request identifier
    "user_id": str | None,                 # User identifier
    "trace_id": str | None,                # Distributed trace ID
    "parent_span_id": str | None,          # Parent span for tracing

    # Collection context
    "collection_id": str | None,           # Collection identifier
    "collection_name": str | None,         # Collection name

    # Query context
    "original_query": str | None,          # Original search query
    "retrieved_chunks": [                  # Retrieved context
        {
            "content": str,
            "score": float,
            "metadata": dict,
        },
    ],

    # Session context
    "session_id": str | None,              # Session identifier
    "conversation_history": [              # Prior messages
        {...},  # AgentMessageDict
    ],

    # Tool context
    "available_tools": list[str] | None,   # Available tool names
    "tool_configs": dict[str, dict] | None, # Tool configurations

    # Limits
    "max_tokens": int | None,              # Token limit
    "timeout_seconds": float | None,       # Execution timeout
}
```

### EmbeddingProviderDefinitionDict (Complete)

Provider definition for embedding plugins:

```python
{
    # Identifiers
    "api_id": str,                         # External API identifier
    "internal_id": str,                    # Internal registry identifier
    "display_name": str,                   # Human-readable name
    "description": str,                    # Provider description

    # Type
    "provider_type": str,                  # "local", "remote", or "hybrid"

    # Capabilities
    "supports_quantization": bool,         # Supports int8/float16
    "supports_instruction": bool,          # Supports instruction prefixes
    "supports_batch_processing": bool,     # Efficient batching
    "supports_asymmetric": bool,           # Different query/doc processing

    # Models
    "supported_models": list[str],         # Supported model names
    "default_config": dict[str, Any],      # Default configuration

    # Plugin marker
    "is_plugin": bool,                     # True for external plugins
}
```

---

## Lifecycle Methods

### Initialize and Cleanup

For plugins that need to acquire/release resources:

```python
class MyPlugin:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._client = None
        self._initialized = False

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize plugin resources.

        Called before first use. May be called multiple times.
        """
        if config:
            self._config.update(config)

        self._client = await self._create_client()
        self._initialized = True

    async def cleanup(self) -> None:
        """Clean up plugin resources.

        Called when plugin is being unloaded or reconfigured.
        """
        if self._client:
            await self._client.close()
            self._client = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if plugin has been initialized."""
        return self._initialized
```

### Context Manager Pattern

For plugins that wrap external clients:

```python
class MyPlugin:
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        return False

# Usage
async with MyPlugin(config) as plugin:
    result = await plugin.process(data)
```

---

## Async Patterns

### Async Generators

For connectors and agents that stream data:

```python
from typing import AsyncIterator

async def load_documents(
    self, source_id: int | None = None
) -> AsyncIterator[dict[str, Any]]:
    """Yield documents as they're fetched."""
    async for page in self._paginate_api():
        for item in page["items"]:
            yield self._transform_item(item)
```

### Parallel Processing

For plugins that can parallelize work:

```python
import asyncio

async def embed_texts(
    self, texts: list[str], mode: str = "document"
) -> list[list[float]]:
    """Embed texts in parallel batches."""
    batch_size = 32
    batches = [texts[i:i+batch_size] for i in range(0, len(texts), batch_size)]

    # Process batches in parallel
    results = await asyncio.gather(*[
        self._embed_batch(batch, mode)
        for batch in batches
    ])

    # Flatten results
    return [emb for batch_result in results for emb in batch_result]
```

### Timeouts

Always use timeouts for external calls:

```python
import asyncio
import aiohttp

async def _call_api(self, data: dict) -> dict:
    """Call API with timeout."""
    try:
        async with asyncio.timeout(30):
            async with aiohttp.ClientSession() as session:
                async with session.post(self._url, json=data) as resp:
                    return await resp.json()
    except asyncio.TimeoutError:
        raise PluginError("API call timed out after 30 seconds")
```

---

## Error Handling

### Custom Exceptions

Define clear error types:

```python
class PluginError(Exception):
    """Base error for plugin operations."""
    pass

class ConfigurationError(PluginError):
    """Invalid or missing configuration."""
    pass

class AuthenticationError(PluginError):
    """Authentication failed."""
    pass

class RateLimitError(PluginError):
    """Rate limit exceeded."""
    pass
```

### Error Recovery

```python
async def embed_texts(self, texts: list[str], mode: str = "document"):
    """Embed with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await self._embed_batch(texts, mode)
        except RateLimitError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                await asyncio.sleep(wait_time)
            else:
                raise
```
