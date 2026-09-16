# Chunking Plugin Guide

Chunking plugins split documents into smaller segments for embedding and search.

## When to Use

Create a chunking plugin when you need to:
- Implement custom chunking logic (semantic, hierarchical, etc.)
- Handle specific document formats (code, markdown, etc.)
- Optimize chunk sizes for your embedding model
- Preserve document structure during chunking

## Required Class Variables

```python
from typing import ClassVar

class MyChunking:
    PLUGIN_ID: ClassVar[str] = "my-chunking"
    PLUGIN_TYPE: ClassVar[str] = "chunking"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"
```

## Required Methods

### `chunk(content, config, progress_callback) -> list[dict]`

Split content into chunks:

```python
from typing import Any, Callable

def chunk(
    self,
    content: str,
    config: dict[str, Any],
    progress_callback: Callable[[float], None] | None = None,
) -> list[dict[str, Any]]:
    """Split content into chunks.

    Args:
        content: Full text to chunk.
        config: Chunking configuration.
        progress_callback: Optional callback for progress (0.0-1.0).

    Returns:
        List of chunk dictionaries.
    """
    chunk_size = config.get("chunk_size", 500)
    overlap = config.get("chunk_overlap", 50)

    chunks = []
    start = 0
    idx = 0

    while start < len(content):
        end = start + chunk_size
        chunk_text = content[start:end]

        chunks.append({
            "content": chunk_text,
            "metadata": {
                "chunk_index": idx,
                "start_offset": start,
                "end_offset": min(end, len(content)),
            },
        })

        if progress_callback:
            progress_callback(min(end / len(content), 1.0))

        start = end - overlap
        idx += 1

    return chunks
```

### `validate_content(content) -> tuple[bool, str | None]`

Validate content before chunking:

```python
def validate_content(self, content: str) -> tuple[bool, str | None]:
    """Validate content before chunking.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not content or not content.strip():
        return False, "Content cannot be empty"
    if len(content) > 10_000_000:  # 10MB
        return False, "Content too large (max 10MB)"
    return True, None
```

### `estimate_chunks(content_length, config) -> int`

Estimate number of chunks:

```python
def estimate_chunks(self, content_length: int, config: dict[str, Any]) -> int:
    """Estimate the number of chunks for given content length."""
    chunk_size = config.get("chunk_size", 500)
    overlap = config.get("chunk_overlap", 50)
    if chunk_size <= overlap:
        return 1
    return max(1, (content_length + chunk_size - overlap - 1) // (chunk_size - overlap))
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
        "display_name": "My Chunking",
        "description": "Custom chunking strategy",
    }
```

## Chunk Format (ChunkDict)

```python
{
    "content": str,              # Chunk text (required)
    "metadata": {                # Chunk metadata (required)
        "chunk_index": int,      # Position in document
        "start_offset": int,     # Start character position
        "end_offset": int,       # End character position
        "token_count": int,      # Optional: token count
        "heading_hierarchy": list[str],  # Optional: parent headings
    },
    "chunk_id": str | None,      # Optional unique ID
    "embedding": list[float] | None,  # Optional pre-computed embedding
}
```

## Config Options (ChunkConfigDict)

```python
{
    "chunk_size": int,           # Target chunk size in characters
    "chunk_overlap": int,        # Overlap between chunks
    "min_chunk_size": int,       # Minimum chunk size
    "max_chunk_size": int,       # Maximum chunk size
    "separator": str,            # Text separator
    "keep_separator": bool,      # Keep separator in chunks
    "preserve_structure": bool,  # Preserve document structure
}
```

## Complete Example

```python
from typing import ClassVar, Any, Callable
import re


class MarkdownChunking:
    """Chunk markdown documents preserving header hierarchy."""

    PLUGIN_ID: ClassVar[str] = "markdown-chunking"
    PLUGIN_TYPE: ClassVar[str] = "chunking"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"

    def chunk(
        self,
        content: str,
        config: dict[str, Any],
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[dict[str, Any]]:
        chunk_size = config.get("chunk_size", 1000)
        overlap = config.get("chunk_overlap", 100)

        # Split by headers
        sections = self._split_by_headers(content)

        chunks = []
        current_headers: list[str] = []

        for i, section in enumerate(sections):
            header, text = section

            # Track header hierarchy
            if header:
                level = header.count("#")
                current_headers = current_headers[:level-1] + [header.lstrip("# ")]

            # Split long sections
            section_chunks = self._split_section(text, chunk_size, overlap)

            for j, chunk_text in enumerate(section_chunks):
                chunks.append({
                    "content": chunk_text,
                    "metadata": {
                        "chunk_index": len(chunks),
                        "start_offset": content.find(chunk_text),
                        "end_offset": content.find(chunk_text) + len(chunk_text),
                        "heading_hierarchy": current_headers.copy(),
                        "section_title": current_headers[-1] if current_headers else None,
                    },
                })

            if progress_callback:
                progress_callback((i + 1) / len(sections))

        return chunks

    def _split_by_headers(self, content: str) -> list[tuple[str | None, str]]:
        """Split content by markdown headers."""
        pattern = r'^(#{1,6}\s+.+)$'
        parts = re.split(pattern, content, flags=re.MULTILINE)

        sections = []
        current_header = None
        current_text = ""

        for part in parts:
            if re.match(r'^#{1,6}\s+', part):
                if current_text.strip():
                    sections.append((current_header, current_text.strip()))
                current_header = part
                current_text = ""
            else:
                current_text += part

        if current_text.strip():
            sections.append((current_header, current_text.strip()))

        return sections

    def _split_section(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """Split a section into chunks with overlap."""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at paragraph
            if end < len(text):
                para_break = text.rfind("\n\n", start, end)
                if para_break > start:
                    end = para_break

            chunks.append(text[start:end].strip())
            start = end - overlap

        return chunks

    def validate_content(self, content: str) -> tuple[bool, str | None]:
        if not content or not content.strip():
            return False, "Content cannot be empty"
        return True, None

    def estimate_chunks(self, content_length: int, config: dict[str, Any]) -> int:
        chunk_size = config.get("chunk_size", 1000)
        overlap = config.get("chunk_overlap", 100)
        if chunk_size <= overlap:
            return 1
        return max(1, (content_length + chunk_size - overlap - 1) // (chunk_size - overlap))

    @classmethod
    def get_manifest(cls) -> dict[str, Any]:
        return {
            "id": cls.PLUGIN_ID,
            "type": cls.PLUGIN_TYPE,
            "version": cls.PLUGIN_VERSION,
            "display_name": "Markdown Chunking",
            "description": "Chunk markdown preserving header hierarchy",
        }
```

## Common Gotchas

1. **Not Async**: Unlike other plugins, `chunk()` is synchronous
2. **Progress Callback**: Call with float 0.0-1.0 for long operations
3. **Metadata Required**: Always include `metadata` dict in chunks
4. **Empty Chunks**: Filter out empty/whitespace-only chunks
5. **Overlap Handling**: Ensure overlap < chunk_size

## Testing

```python
import pytest
from my_chunking import MarkdownChunking

class TestMarkdownChunking:
    def test_plugin_attributes(self):
        assert MarkdownChunking.PLUGIN_ID == "markdown-chunking"
        assert MarkdownChunking.PLUGIN_TYPE == "chunking"

    def test_chunk_basic(self):
        chunker = MarkdownChunking()
        chunks = chunker.chunk(
            "# Title\n\nParagraph 1\n\nParagraph 2",
            config={"chunk_size": 100}
        )
        assert len(chunks) >= 1
        assert "content" in chunks[0]
        assert "metadata" in chunks[0]

    def test_validate_empty(self):
        chunker = MarkdownChunking()
        valid, error = chunker.validate_content("")
        assert valid is False
        assert error is not None

    def test_estimate_chunks(self):
        chunker = MarkdownChunking()
        estimate = chunker.estimate_chunks(1000, {"chunk_size": 500, "chunk_overlap": 50})
        assert estimate >= 2
```
