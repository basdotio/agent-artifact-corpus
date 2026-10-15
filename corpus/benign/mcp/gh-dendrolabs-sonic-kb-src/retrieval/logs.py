"""Log message lookup retrieval for sonic-kb."""

from __future__ import annotations

import re

from ._loader import load_all_log_catalogs, load_log_catalog


def get_log_message(pattern: str, daemon: str | None = None) -> list[dict]:
    """Search log catalogs for messages matching a pattern or keyword."""
    pattern_lower = pattern.lower()
    results = []

    if daemon:
        for catalog in load_all_log_catalogs():
            if catalog.get("daemon", "").lower() == daemon.lower():
                results.extend(_search_catalog(catalog, pattern_lower))
    else:
        for catalog in load_all_log_catalogs():
            results.extend(_search_catalog(catalog, pattern_lower))

    return results


def _search_catalog(catalog: dict, pattern_lower: str) -> list[dict]:
    matches = []
    daemon_name = catalog.get("daemon", "unknown")
    for msg in catalog.get("messages", []):
        score = 0
        msg_pattern = msg.get("pattern", "")
        msg_meaning = msg.get("meaning", "")
        if pattern_lower in msg_pattern.lower():
            score += 3
        if pattern_lower in msg_meaning.lower():
            score += 1
        try:
            if re.search(msg_pattern, pattern_lower, re.IGNORECASE):
                score += 2
        except re.error:
            pass
        if score > 0:
            matches.append({"daemon": daemon_name, "score": score, **msg})
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches
