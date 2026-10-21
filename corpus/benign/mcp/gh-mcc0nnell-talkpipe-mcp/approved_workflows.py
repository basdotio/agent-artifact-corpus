"""Approved, bounded TalkPipe workflows.

No arbitrary ChatterLang, Python, imports, filesystem access, network access or
model-provider calls are exposed to MCP clients.
"""
from __future__ import annotations

from itertools import islice
from typing import Any

from talkpipe.pipe import core

MAX_ITEMS = 100
MAX_ITEM_CHARS = 4_096
MAX_TOTAL_CHARS = 65_536
MAX_RESULT_ITEMS = 50
MAX_NEEDLE_CHARS = 128
WORKFLOWS = ("normalize", "keyword_filter", "text_statistics")


@core.segment()
def normalize(items):
    """Normalize Unicode whitespace without modifying word content."""
    for item in items:
        yield " ".join(item.split())


@core.segment()
def keyword_filter(items, keyword: str):
    """Casefolded literal substring filter. Never evaluates an expression."""
    term = keyword.casefold()
    for item in items:
        if term in item.casefold():
            yield item


@core.segment()
def text_statistics(items):
    """Generate structured metadata from each normalized text item."""
    for item in items:
        yield {
            "words": len(item.split()),
            "characters": len(item),
            "preview": item[:160],
        }


def run_pipeline(
    workflow: str, items: list[str], *, needle: str = "", limit: int = MAX_RESULT_ITEMS
) -> dict[str, Any]:
    """Execute only declared TalkPipe pipelines on bounded in-memory input."""
    if workflow not in WORKFLOWS:
        raise ValueError("Unsupported workflow; choose from capabilities")
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise ValueError(f"items must be a list of at most {MAX_ITEMS} strings")
    if any(not isinstance(item, str) or len(item) > MAX_ITEM_CHARS for item in items):
        raise ValueError(f"Every item must be a string of at most {MAX_ITEM_CHARS} characters")
    if sum(len(item) for item in items) > MAX_TOTAL_CHARS:
        raise ValueError("Total input length exceeds permitted bound")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RESULT_ITEMS:
        raise ValueError(f"limit must be an integer from 1 to {MAX_RESULT_ITEMS}")
    if not isinstance(needle, str) or len(needle) > MAX_NEEDLE_CHARS:
        raise ValueError("needle must be a short string")
    if workflow == "keyword_filter" and not needle:
        raise ValueError("keyword_filter requires a nonempty needle")

    pipeline = normalize()
    if workflow == "keyword_filter":
        pipeline = pipeline | keyword_filter(keyword=needle)
    elif workflow == "text_statistics":
        pipeline = pipeline | text_statistics()

    # Lazy TalkPipe execution, with an explicit cap on produced results.
    iterator = iter(pipeline.transform(iter(items)))
    results = list(islice(iterator, limit + 1))
    truncated = len(results) > limit
    if truncated:
        results = results[:limit]
    return {
        "workflow": workflow,
        "input_count": len(items),
        "result_count": len(results),
        "truncated": truncated,
        "results": results,
        "engine": "talkpipe",
    }
