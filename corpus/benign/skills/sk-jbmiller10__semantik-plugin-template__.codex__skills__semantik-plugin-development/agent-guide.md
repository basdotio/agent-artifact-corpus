# Agent Plugin Guide

Agent plugins provide LLM-powered capabilities for agentic search, summarization, and more.

## When to Use

Create an agent plugin when you need to:
- Integrate an LLM API (Claude, GPT, etc.)
- Implement HyDE (Hypothetical Document Embeddings)
- Add query expansion or understanding
- Build answer synthesis from search results
- Create specialized AI assistants

## Required Class Variables

```python
from typing import ClassVar

class MyAgent:
    PLUGIN_ID: ClassVar[str] = "my-agent"
    PLUGIN_TYPE: ClassVar[str] = "agent"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"
```

## Required Methods

### `__init__(config: dict | None = None)`

Initialize with configuration:

```python
def __init__(self, config: dict[str, Any] | None = None) -> None:
    self._config = config or {}
    self._api_key = self._config.get("api_key")
    self._model = self._config.get("model", "default-model")
```

### `execute(prompt, ...) -> AsyncIterator[dict]`

Execute the agent and stream responses:

```python
from typing import AsyncIterator
from datetime import datetime, timezone
import uuid

async def execute(
    self,
    prompt: str,
    *,
    context: dict[str, Any] | None = None,
    system_prompt: str | None = None,
    tools: list[str] | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    session_id: str | None = None,
    stream: bool = True,
) -> AsyncIterator[dict[str, Any]]:
    """Execute the agent and stream responses.

    Args:
        prompt: User prompt to process.
        context: Runtime context with retrieved chunks, etc.
        system_prompt: Optional system prompt override.
        tools: Names of available tools.
        model: Model identifier.
        temperature: Sampling temperature.
        max_tokens: Maximum output tokens.
        session_id: Session ID for conversation continuity.
        stream: Whether to stream partial responses.

    Yields:
        AgentMessageDict dictionaries.
    """
    # Generate response
    response = await self._call_llm(prompt, system_prompt)

    yield {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "type": "text",
        "content": response,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_partial": False,
        "sequence_number": 0,
    }
```

### `get_capabilities() -> dict`

Declare agent capabilities:

```python
@classmethod
def get_capabilities(cls) -> dict[str, Any]:
    return {
        "supports_streaming": True,
        "supports_tools": False,
        "supports_sessions": True,
        "supports_extended_thinking": False,
        "max_context_tokens": 100000,
        "max_output_tokens": 4096,
        "supported_models": ["model-a", "model-b"],
        "default_model": "model-a",
    }
```

### `supported_use_cases() -> list[str]`

List supported use cases:

```python
@classmethod
def supported_use_cases(cls) -> list[str]:
    return ["assistant", "summarization", "answer_synthesis"]
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
        "display_name": "My Agent",
        "description": "Custom AI agent",
        "capabilities": cls.get_capabilities(),
    }
```

## Message Format (AgentMessageDict)

```python
{
    "id": str,                   # Unique message ID (required)
    "role": str,                 # See MESSAGE_ROLES (required)
    "type": str,                 # See MESSAGE_TYPES (required)
    "content": str,              # Message content (required)
    "timestamp": str,            # ISO 8601 (required)
    "tool_name": str | None,     # For tool_use messages
    "tool_call_id": str | None,  # Tool call identifier
    "tool_input": dict | None,   # Tool arguments
    "tool_output": dict | None,  # Tool result
    "model": str | None,         # Model used
    "usage": {                   # Token usage (optional)
        "input_tokens": int,
        "output_tokens": int,
    },
    "is_partial": bool,          # Streaming partial (optional)
    "sequence_number": int,      # Message order (optional)
}
```

## MESSAGE_ROLES

| Value | Description |
|-------|-------------|
| `user` | User message |
| `assistant` | Assistant response |
| `system` | System message |
| `tool_call` | Tool invocation request |
| `tool_result` | Tool execution result |
| `error` | Error message |

## MESSAGE_TYPES

| Value | Description |
|-------|-------------|
| `text` | Regular text content |
| `thinking` | Reasoning/thinking content |
| `tool_use` | Tool invocation |
| `tool_output` | Tool result |
| `partial` | Streaming partial response |
| `final` | Final complete response |
| `error` | Error content |
| `metadata` | Metadata message |

## Use Cases

| Use Case | Description |
|----------|-------------|
| `hyde` | Hypothetical Document Embeddings |
| `query_expansion` | Query expansion/rewriting |
| `query_understanding` | Query analysis and intent |
| `summarization` | Text summarization |
| `reranking` | Result reranking |
| `answer_synthesis` | Answer generation from context |
| `tool_use` | Tool-using agent |
| `agentic_search` | Multi-step search agent |
| `reasoning` | Complex reasoning tasks |
| `assistant` | General assistant |
| `code_generation` | Code generation |
| `data_analysis` | Data analysis |

## Context Format (AgentContextDict)

```python
{
    "request_id": str,           # Request identifier
    "user_id": str | None,       # User identifier
    "collection_id": str | None, # Collection identifier
    "collection_name": str | None,
    "original_query": str | None,  # Original search query
    "retrieved_chunks": [        # Retrieved context
        {"content": str, "score": float, "metadata": dict},
    ],
    "session_id": str | None,    # Session for continuity
    "conversation_history": [...],  # Prior messages
    "available_tools": [...],    # Tool names
}
```

## Complete Example

```python
from typing import ClassVar, Any, AsyncIterator
from datetime import datetime, timezone
import uuid
import aiohttp


class ClaudeAgent:
    PLUGIN_ID: ClassVar[str] = "claude-agent"
    PLUGIN_TYPE: ClassVar[str] = "agent"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._api_key = self._config.get("api_key")
        self._model = self._config.get("model", "claude-sonnet-4-20250514")

    async def execute(
        self,
        prompt: str,
        *,
        context: dict[str, Any] | None = None,
        system_prompt: str | None = None,
        tools: list[str] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        session_id: str | None = None,
        stream: bool = True,
    ) -> AsyncIterator[dict[str, Any]]:
        model = model or self._model
        max_tokens = max_tokens or 4096

        # Build messages
        messages = []

        # Add context from retrieved chunks
        if context and context.get("retrieved_chunks"):
            chunks = context["retrieved_chunks"]
            context_text = "\n\n".join(c["content"] for c in chunks)
            messages.append({
                "role": "user",
                "content": f"Context:\n{context_text}\n\nQuestion: {prompt}"
            })
        else:
            messages.append({"role": "user", "content": prompt})

        # Call Claude API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "system": system_prompt or "You are a helpful assistant.",
                    "messages": messages,
                },
            ) as resp:
                data = await resp.json()

        # Extract response
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        # Yield response message
        yield {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "type": "text",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "usage": {
                "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                "output_tokens": data.get("usage", {}).get("output_tokens", 0),
            },
            "is_partial": False,
            "sequence_number": 0,
        }

    @classmethod
    def get_capabilities(cls) -> dict[str, Any]:
        return {
            "supports_streaming": True,
            "supports_tools": True,
            "supports_sessions": True,
            "supports_extended_thinking": True,
            "max_context_tokens": 200000,
            "max_output_tokens": 8192,
            "supported_models": [
                "claude-sonnet-4-20250514",
                "claude-opus-4-20250514",
            ],
            "default_model": "claude-sonnet-4-20250514",
        }

    @classmethod
    def supported_use_cases(cls) -> list[str]:
        return [
            "assistant",
            "summarization",
            "answer_synthesis",
            "query_expansion",
            "reasoning",
        ]

    @classmethod
    def get_manifest(cls) -> dict[str, Any]:
        return {
            "id": cls.PLUGIN_ID,
            "type": cls.PLUGIN_TYPE,
            "version": cls.PLUGIN_VERSION,
            "display_name": "Claude Agent",
            "description": "Claude-powered AI agent",
            "capabilities": cls.get_capabilities(),
        }
```

## Common Gotchas

1. **Async Iterator**: `execute()` must be an async generator
2. **Required Fields**: Each message needs `id`, `role`, `type`, `content`, `timestamp`
3. **Valid Roles**: Use only MESSAGE_ROLES values
4. **Valid Types**: Use only MESSAGE_TYPES values
5. **ISO Timestamp**: Use `datetime.now(timezone.utc).isoformat()`
6. **Streaming**: For streaming, yield partial messages with `is_partial: True`

## Testing

```python
import pytest
from my_agent import ClaudeAgent

class TestClaudeAgent:
    def test_plugin_attributes(self):
        assert ClaudeAgent.PLUGIN_ID == "claude-agent"
        assert ClaudeAgent.PLUGIN_TYPE == "agent"

    def test_capabilities(self):
        caps = ClaudeAgent.get_capabilities()
        assert "supports_streaming" in caps
        assert "max_context_tokens" in caps

    def test_use_cases(self):
        cases = ClaudeAgent.supported_use_cases()
        assert "assistant" in cases

    @pytest.mark.asyncio
    async def test_execute_message_format(self, mock_api):
        agent = ClaudeAgent(config={"api_key": "test"})
        async for msg in agent.execute("Hello"):
            assert "id" in msg
            assert "role" in msg
            assert msg["role"] == "assistant"
            assert "type" in msg
            assert msg["type"] == "text"
            assert "content" in msg
            assert "timestamp" in msg
            break
```
