# Connector Plugin Guide

Connector plugins ingest documents from external sources into Semantik.

## When to Use

Create a connector when you need to:
- Pull documents from an API (Notion, Confluence, Slack, etc.)
- Import files from cloud storage (S3, GCS, Dropbox)
- Sync from databases or data warehouses
- Integrate with custom internal systems

## Required Class Variables

```python
from typing import ClassVar, Any

class MyConnector:
    PLUGIN_ID: ClassVar[str] = "my-connector"
    PLUGIN_TYPE: ClassVar[str] = "connector"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"
    METADATA: ClassVar[dict[str, Any]] = {
        "name": "My Connector",
        "description": "Connects to My Service",
        "icon": "database",  # For UI
        "supports_sync": True,  # Supports incremental sync
    }
```

## Required Methods

### `__init__(config: dict[str, Any])`

Initialize with configuration from the UI:

```python
def __init__(self, config: dict[str, Any]) -> None:
    self._config = config
    self._api_key = config.get("api_key")
    self._base_url = config.get("base_url", "https://api.example.com")
```

### `authenticate() -> bool`

Verify credentials are valid:

```python
async def authenticate(self) -> bool:
    if not self._api_key:
        return False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._base_url}/me",
                headers={"Authorization": f"Bearer {self._api_key}"},
            ) as resp:
                return resp.status == 200
    except Exception:
        return False
```

### `load_documents(source_id: int | None = None) -> AsyncIterator[dict]`

Yield documents from the source:

```python
async def load_documents(
    self, source_id: int | None = None
) -> AsyncIterator[dict[str, Any]]:
    async for page in self._fetch_pages():
        content = page["content"]
        yield {
            "content": content,
            "unique_id": page["id"],
            "source_type": self.PLUGIN_ID,
            "metadata": {
                "title": page["title"],
                "url": page["url"],
                "created_at": page["created_at"],
            },
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
        }
```

### `get_config_fields() -> list[dict]`

Define configuration fields for the UI:

```python
@classmethod
def get_config_fields(cls) -> list[dict[str, Any]]:
    return [
        {
            "name": "base_url",
            "type": "text",
            "label": "Base URL",
            "description": "API endpoint URL",
            "required": True,
            "placeholder": "https://api.example.com",
        },
        {
            "name": "workspace_id",
            "type": "text",
            "label": "Workspace ID",
            "description": "Optional workspace to limit scope",
            "required": False,
        },
    ]
```

### `get_secret_fields() -> list[dict]`

Define secret fields (encrypted at rest):

```python
@classmethod
def get_secret_fields(cls) -> list[dict[str, Any]]:
    return [
        {
            "name": "api_key",
            "label": "API Key",
            "description": "API key for authentication",
            "required": True,
        },
    ]
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
        "display_name": cls.METADATA["name"],
        "description": cls.METADATA["description"],
    }
```

## Document Format (IngestedDocumentDict)

Each yielded document must have:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | `str` | Yes | Full text content |
| `unique_id` | `str` | Yes | Source-specific identifier |
| `source_type` | `str` | Yes | Your PLUGIN_ID |
| `metadata` | `dict` | Yes | Source metadata (title, url, dates, etc.) |
| `content_hash` | `str` | Yes | SHA-256 hash (64 lowercase hex chars) |
| `file_path` | `str \| None` | No | Local file path if applicable |

**Important:** `content_hash` must be exactly 64 lowercase hexadecimal characters:

```python
import hashlib
content_hash = hashlib.sha256(content.encode()).hexdigest()
```

## Complete Example

```python
from typing import ClassVar, Any, AsyncIterator
import hashlib
import aiohttp


class NotionConnector:
    PLUGIN_ID: ClassVar[str] = "notion"
    PLUGIN_TYPE: ClassVar[str] = "connector"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"
    METADATA: ClassVar[dict[str, Any]] = {
        "name": "Notion",
        "description": "Import pages from Notion workspaces",
        "icon": "notion",
        "supports_sync": True,
    }

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._api_key = config.get("api_key")
        self._database_id = config.get("database_id")

    async def authenticate(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.notion.com/v1/users/me",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Notion-Version": "2022-06-28",
                    },
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def load_documents(
        self, source_id: int | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.notion.com/v1/databases/{self._database_id}/query"
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Notion-Version": "2022-06-28",
            }

            async with session.post(url, headers=headers, json={}) as resp:
                data = await resp.json()

            for page in data.get("results", []):
                page_id = page["id"]
                content = await self._get_page_content(session, page_id)

                yield {
                    "content": content,
                    "unique_id": page_id,
                    "source_type": self.PLUGIN_ID,
                    "metadata": {
                        "title": self._extract_title(page),
                        "url": page["url"],
                        "created_time": page["created_time"],
                        "last_edited_time": page["last_edited_time"],
                    },
                    "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                }

    async def _get_page_content(self, session, page_id: str) -> str:
        # Fetch and combine page blocks
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Notion-Version": "2022-06-28",
        }
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()

        texts = []
        for block in data.get("results", []):
            if text := self._extract_text(block):
                texts.append(text)
        return "\n\n".join(texts)

    def _extract_title(self, page: dict) -> str:
        props = page.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                titles = prop.get("title", [])
                return "".join(t.get("plain_text", "") for t in titles)
        return "Untitled"

    def _extract_text(self, block: dict) -> str:
        block_type = block.get("type")
        if block_type in ("paragraph", "heading_1", "heading_2", "heading_3"):
            rich_text = block.get(block_type, {}).get("rich_text", [])
            return "".join(t.get("plain_text", "") for t in rich_text)
        return ""

    @classmethod
    def get_config_fields(cls) -> list[dict[str, Any]]:
        return [
            {
                "name": "database_id",
                "type": "text",
                "label": "Database ID",
                "description": "Notion database to sync from",
                "required": True,
                "placeholder": "abc123...",
            },
        ]

    @classmethod
    def get_secret_fields(cls) -> list[dict[str, Any]]:
        return [
            {
                "name": "api_key",
                "label": "Integration Token",
                "description": "Notion internal integration token",
                "required": True,
            },
        ]

    @classmethod
    def get_manifest(cls) -> dict[str, Any]:
        return {
            "id": cls.PLUGIN_ID,
            "type": cls.PLUGIN_TYPE,
            "version": cls.PLUGIN_VERSION,
            "display_name": cls.METADATA["name"],
            "description": cls.METADATA["description"],
            "author": "Semantik Team",
            "homepage": "https://github.com/semantik/semantik-plugin-notion",
        }
```

## Common Gotchas

1. **Async Iterator Required**: `load_documents` must be an async generator
2. **Content Hash Format**: Must be exactly 64 lowercase hex characters
3. **Source Type Match**: `source_type` in documents must match `PLUGIN_ID`
4. **Handle Pagination**: Most APIs paginate - handle all pages
5. **Rate Limiting**: Implement backoff for API rate limits
6. **Error Handling**: Catch and log errors, don't crash the generator

## Testing

```python
import pytest
from my_connector import NotionConnector

class TestNotionConnector:
    def test_plugin_attributes(self):
        assert NotionConnector.PLUGIN_ID == "notion"
        assert NotionConnector.PLUGIN_TYPE == "connector"

    @pytest.mark.asyncio
    async def test_authenticate_without_key(self):
        connector = NotionConnector(config={})
        assert await connector.authenticate() is False

    @pytest.mark.asyncio
    async def test_document_format(self):
        connector = NotionConnector(config={"api_key": "test", "database_id": "test"})
        async for doc in connector.load_documents():
            assert "content" in doc
            assert "unique_id" in doc
            assert "source_type" in doc
            assert "metadata" in doc
            assert "content_hash" in doc
            assert len(doc["content_hash"]) == 64
            break
```
