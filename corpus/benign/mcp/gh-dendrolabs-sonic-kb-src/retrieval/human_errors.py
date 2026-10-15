"""Human error detection retrieval for sonic-kb."""

from __future__ import annotations

import re

from ._loader import load_human_error, load_human_error_index


def detect_human_error(description: str, context: str | None = None) -> list[dict]:
    """Match a free-text description against known human error patterns."""
    index = load_human_error_index()
    desc_lower = description.lower()
    matches = []
    for error_id, meta in index.items():
        score = 0
        keywords = meta.get("keywords", [])
        for kw in keywords:
            if kw.lower() in desc_lower:
                score += 1
        if context:
            ctx_keywords = meta.get("context_keywords", [])
            for ck in ctx_keywords:
                if ck.lower() in context.lower():
                    score += 1
        if score > 0:
            error_data = load_human_error(error_id)
            if error_data:
                matches.append({"score": score, **error_data})
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches


def get_human_error(error_id: str) -> dict | None:
    return load_human_error(error_id)


def list_human_errors() -> list[dict]:
    index = load_human_error_index()
    return [{"error_id": eid, **meta} for eid, meta in index.items()]
