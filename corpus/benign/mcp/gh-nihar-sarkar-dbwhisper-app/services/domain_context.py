"""Domain context loader with optional RAG-based retrieval."""

import os
import glob
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


async def load_domain_context(context_dir: str = "./context") -> str:
    """Scan context_dir for .md files, read them, and return concatenated text."""
    if not os.path.exists(context_dir):
        return ""

    md_files = sorted(glob.glob(os.path.join(context_dir, "*.md")))
    if not md_files:
        return ""

    parts = []
    for filepath in md_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                parts.append(f"=== File: {filename} === {content}")
        except Exception as e:
            logger.warning("Failed to read domain context file %s: %s", filename, e)

    return "".join(parts)


class DomainContextRAG:
    """Retrieve only relevant domain context paragraphs based on query keywords."""

    def __init__(self, context_dir: str = "./context"):
        self.context_dir = context_dir
        self._chunks: List[Dict[str, str]] = []
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        if not os.path.exists(self.context_dir):
            self._loaded = True
            return

        for filepath in sorted(glob.glob(os.path.join(self.context_dir, "*.md"))):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                # Split by headers
                paragraphs = content.split("#")
                for p in paragraphs:
                    p = p.strip()
                    if p:
                        self._chunks.append({"source": os.path.basename(filepath), "text": p})
            except Exception as e:
                logger.warning("Failed to chunk %s: %s", filepath, e)
        self._loaded = True

    def retrieve(self, user_query: str, top_k: int = 3) -> str:
        """Return top-k relevant context chunks."""
        self._load()
        if not self._chunks:
            return ""

        query_lower = user_query.lower()
        query_tokens = set(query_lower.split())

        scored = []
        for chunk in self._chunks:
            text_lower = chunk["text"].lower()
            score = sum(1 for tok in query_tokens if tok in text_lower)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = scored[:top_k]

        parts = []
        for _, chunk in selected:
            parts.append(f"=== From {chunk['source']} ==={chunk['text']}")

        return "".join(parts)
