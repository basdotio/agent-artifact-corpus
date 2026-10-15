"""The catalog: a user's accumulated library of ingested repositories.

Data layer first. `Catalog` is the API every frontend shares -- CLI, TUI, GUI
and MCP -- and it returns plain records rather than database handles, so none
of them are coupled to how it is stored.
"""

from __future__ import annotations

from .models import (
    CapabilityRecord,
    ComponentRecord,
    FactRecord,
    RepoRecord,
    SearchHit,
)
from .store import Catalog, content_id, default_root

__all__ = [
    "CapabilityRecord", "Catalog", "ComponentRecord", "FactRecord",
    "RepoRecord", "SearchHit", "content_id", "default_root",
]
