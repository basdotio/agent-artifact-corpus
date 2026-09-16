# Extractor Plugin Guide

Extractor plugins extract structured information from text (entities, keywords, sentiment, etc.).

## When to Use

Create an extractor plugin when you need to:
- Extract named entities (people, organizations, locations)
- Identify keywords and key phrases
- Detect language or sentiment
- Generate summaries
- Extract custom metadata

## Required Class Variables

```python
from typing import ClassVar

class MyExtractor:
    PLUGIN_ID: ClassVar[str] = "my-extractor"
    PLUGIN_TYPE: ClassVar[str] = "extractor"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"
```

## Required Methods

### `__init__(config: dict | None = None)`

Initialize with configuration:

```python
def __init__(self, config: dict[str, Any] | None = None) -> None:
    self._config = config or {}
    self._model = self._config.get("model")
```

### `extract(text, extraction_types, options) -> dict`

Extract information from text:

```python
async def extract(
    self,
    text: str,
    extraction_types: list[str] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract information from text.

    Args:
        text: Input text to extract from.
        extraction_types: Types to extract (entities, keywords, etc.).
        options: Additional extraction options.

    Returns:
        ExtractionResultDict with requested extractions.
    """
    types = extraction_types or ["keywords", "entities"]
    result: dict[str, Any] = {}

    if "entities" in types:
        result["entities"] = await self._extract_entities(text)

    if "keywords" in types:
        result["keywords"] = await self._extract_keywords(text)

    if "language" in types:
        lang, conf = await self._detect_language(text)
        result["language"] = lang
        result["language_confidence"] = conf

    if "sentiment" in types:
        result["sentiment"] = await self._analyze_sentiment(text)

    if "summary" in types:
        result["summary"] = await self._summarize(text)

    return result
```

### `supported_extractions() -> list[str]`

List supported extraction types:

```python
@classmethod
def supported_extractions(cls) -> list[str]:
    return ["entities", "keywords", "language", "sentiment", "summary"]
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
        "display_name": "My Extractor",
        "description": "Extract entities and keywords",
        "capabilities": {"extractions": cls.supported_extractions()},
    }
```

## Extraction Types

| Type | Description | Return Field |
|------|-------------|--------------|
| `entities` | Named entity recognition | `entities: list[EntityDict]` |
| `keywords` | Keyword extraction | `keywords: list[str]` |
| `language` | Language detection | `language: str`, `language_confidence: float` |
| `topics` | Topic identification | `topics: list[str]` |
| `sentiment` | Sentiment analysis | `sentiment: float` (-1.0 to 1.0) |
| `summary` | Text summarization | `summary: str` |
| `custom` | Custom extractions | `custom: dict` |

## Result Format (ExtractionResultDict)

```python
{
    "entities": [              # Named entities
        {
            "text": str,       # Entity text
            "type": str,       # PERSON, ORG, LOC, DATE, etc.
            "start": int,      # Start offset (optional)
            "end": int,        # End offset (optional)
            "confidence": float,  # 0.0-1.0 (optional)
        },
    ],
    "keywords": ["keyword1", "keyword2"],
    "language": "en",
    "language_confidence": 0.99,
    "topics": ["technology", "ai"],
    "sentiment": 0.5,          # -1.0 (negative) to 1.0 (positive)
    "summary": "Brief summary of the text...",
    "custom": {},              # Custom extraction results
}
```

## Complete Example

```python
from typing import ClassVar, Any
import re


class SimpleExtractor:
    """Simple extractor using regex and basic NLP."""

    PLUGIN_ID: ClassVar[str] = "simple-extractor"
    PLUGIN_TYPE: ClassVar[str] = "extractor"
    PLUGIN_VERSION: ClassVar[str] = "1.0.0"

    # Simple patterns for demo
    ENTITY_PATTERNS = {
        "EMAIL": r'\b[\w.-]+@[\w.-]+\.\w+\b',
        "URL": r'https?://\S+',
        "PHONE": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "DATE": r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
    }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    async def extract(
        self,
        text: str,
        extraction_types: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        types = extraction_types or self.supported_extractions()
        result: dict[str, Any] = {}

        if "entities" in types:
            result["entities"] = self._extract_entities(text)

        if "keywords" in types:
            result["keywords"] = self._extract_keywords(text)

        if "language" in types:
            result["language"] = "en"  # Simplified
            result["language_confidence"] = 0.9

        if "sentiment" in types:
            result["sentiment"] = self._simple_sentiment(text)

        if "summary" in types:
            result["summary"] = self._simple_summary(text)

        return result

    def _extract_entities(self, text: str) -> list[dict[str, Any]]:
        entities = []
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            for match in re.finditer(pattern, text):
                entities.append({
                    "text": match.group(),
                    "type": entity_type,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9,
                })
        return entities

    def _extract_keywords(self, text: str, top_n: int = 10) -> list[str]:
        # Simple word frequency approach
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        stopwords = {"this", "that", "with", "from", "have", "been", "were", "will"}
        words = [w for w in words if w not in stopwords]

        from collections import Counter
        counts = Counter(words)
        return [word for word, _ in counts.most_common(top_n)]

    def _simple_sentiment(self, text: str) -> float:
        positive = ["good", "great", "excellent", "amazing", "love", "happy"]
        negative = ["bad", "terrible", "awful", "hate", "sad", "angry"]

        text_lower = text.lower()
        pos_count = sum(1 for word in positive if word in text_lower)
        neg_count = sum(1 for word in negative if word in text_lower)

        total = pos_count + neg_count
        if total == 0:
            return 0.0
        return (pos_count - neg_count) / total

    def _simple_summary(self, text: str, max_length: int = 200) -> str:
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return ""

        # Take first sentence(s) up to max_length
        summary = sentences[0]
        for sentence in sentences[1:]:
            if len(summary) + len(sentence) + 2 > max_length:
                break
            summary += ". " + sentence

        return summary + "." if not summary.endswith(".") else summary

    @classmethod
    def supported_extractions(cls) -> list[str]:
        return ["entities", "keywords", "language", "sentiment", "summary"]

    @classmethod
    def get_manifest(cls) -> dict[str, Any]:
        return {
            "id": cls.PLUGIN_ID,
            "type": cls.PLUGIN_TYPE,
            "version": cls.PLUGIN_VERSION,
            "display_name": "Simple Extractor",
            "description": "Basic entity and keyword extraction",
            "capabilities": {"extractions": cls.supported_extractions()},
        }
```

## Common Gotchas

1. **Supported Types**: Only return results for types in `extraction_types`
2. **Entity Format**: Entities must have `text` and `type` fields
3. **Sentiment Range**: Sentiment must be -1.0 to 1.0
4. **Optional Fields**: Include `start`/`end` offsets when available
5. **Empty Results**: Return empty lists/None for unavailable extractions

## Testing

```python
import pytest
from my_extractor import SimpleExtractor

class TestSimpleExtractor:
    def test_plugin_attributes(self):
        assert SimpleExtractor.PLUGIN_ID == "simple-extractor"
        assert SimpleExtractor.PLUGIN_TYPE == "extractor"

    def test_supported_extractions(self):
        types = SimpleExtractor.supported_extractions()
        assert "entities" in types
        assert "keywords" in types

    @pytest.mark.asyncio
    async def test_extract_entities(self):
        extractor = SimpleExtractor()
        result = await extractor.extract(
            "Contact me at test@example.com",
            extraction_types=["entities"]
        )
        assert "entities" in result
        assert len(result["entities"]) >= 1
        assert result["entities"][0]["type"] == "EMAIL"

    @pytest.mark.asyncio
    async def test_extract_sentiment(self):
        extractor = SimpleExtractor()
        result = await extractor.extract(
            "This is great and amazing!",
            extraction_types=["sentiment"]
        )
        assert "sentiment" in result
        assert result["sentiment"] > 0
```
