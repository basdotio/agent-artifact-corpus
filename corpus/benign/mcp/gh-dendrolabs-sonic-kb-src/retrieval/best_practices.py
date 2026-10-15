"""Best practices retrieval for sonic-kb."""

from __future__ import annotations

from ._loader import load_best_practices


def get_best_practices(topic: str | None = None) -> dict | None:
    data = load_best_practices()
    if data is None:
        return None
    if topic:
        topic_lower = topic.lower()
        filtered = []
        for entry in data.get("practices", []):
            if topic_lower in entry.get("topic", "").lower():
                filtered.append(entry)
            elif topic_lower in entry.get("title", "").lower():
                filtered.append(entry)
            elif any(topic_lower in t.lower() for t in entry.get("tags", [])):
                filtered.append(entry)
        return {"practices": filtered} if filtered else None
    return data
