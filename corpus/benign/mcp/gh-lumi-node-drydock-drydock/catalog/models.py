"""Catalog record types.

Plain frozen dataclasses, JSON-serialisable through `drydock.core.output`.
These are the objects every frontend sees -- CLI, TUI, GUI and MCP alike -- so
they are deliberately dumb: no database handles, no lazy loading, nothing that
only works while a connection is open. A GUI can hold one for as long as it
likes, and an agent can be handed one as JSON without further translation.

Ids are content-addressed rather than autoincremented. Re-ingesting the same
repository at the same commit therefore updates rows in place instead of
accumulating near-duplicates, and an id stays meaningful when it is copied into
a bug report, an agent's notes, or another machine's catalog.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

__all__ = [
    "RepoRecord",
    "ComponentRecord",
    "FactRecord",
    "CapabilityRecord",
    "SearchHit",
]

SourceKind = Literal["path", "git", "unknown"]
ComponentKind = Literal["seam", "cluster", "directory", "manual"]


@dataclass(frozen=True, slots=True)
class RepoRecord:
    """One ingested repository, at one commit."""

    id: str
    name: str
    source: str
    source_kind: SourceKind = "path"
    commit_sha: str | None = None
    branch: str | None = None
    ingested_at: str = ""
    drydock_ver: str = ""
    languages: tuple[str, ...] = ()
    file_count: int = 0
    notes: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def short_commit(self) -> str:
        return (self.commit_sha or "")[:12]

    @property
    def label(self) -> str:
        return f"{self.name}@{self.short_commit}" if self.commit_sha else self.name


@dataclass(frozen=True, slots=True)
class ComponentRecord:
    """A reusable unit identified in a repository, optionally stored on disk."""

    id: str
    repo_id: str
    name: str
    kind: ComponentKind
    contract: str | None = None
    selection: dict[str, Any] = field(default_factory=dict)
    cohesion: float | None = None
    verdict: str | None = None
    file_count: int = 0
    languages: tuple[str, ...] = ()
    external_deps: dict[str, list[str]] = field(default_factory=dict)
    content_path: str | None = None
    """Where the extracted tree lives under the catalog, if it was stored."""
    stored_at: str | None = None
    summary: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def is_stored(self) -> bool:
        """True when the catalog holds the code, not merely a description.

        The distinction matters for composition: you can only build from parts
        you actually have.
        """
        return bool(self.content_path)

    def path(self, catalog_root: Path) -> Path | None:
        return (catalog_root / self.content_path) if self.content_path else None


@dataclass(frozen=True, slots=True)
class FactRecord:
    """One architectural finding about a repository, with its evidence."""

    id: str
    repo_id: str
    principle: str
    name: str
    verdict: str
    summary: str
    derived: str = "deterministic"
    evidence: dict[str, Any] = field(default_factory=dict)
    recorded_at: str = ""


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    """One public symbol a component exposes.

    This is what makes "do I already have something that does X?" answerable.
    A component's identity is its contract; its *capability* is the set of
    names and signatures it offers, which is what someone composing a new
    application actually searches on.
    """

    id: str
    component_id: str
    repo_id: str
    module: str
    symbol: str
    kind: str
    signature: str | None = None
    doc: str | None = None
    lang: str | None = None


@dataclass(frozen=True, slots=True)
class SearchHit:
    """A full-text match, with enough context to render without a second query."""

    subject_id: str
    subject_kind: Literal["repo", "component", "capability", "fact"]
    repo_id: str
    title: str
    snippet: str
    rank: float = 0.0


def utc_now() -> str:
    """Timestamp for records. Timezone-aware, RFC 3339, trailing Z."""
    from datetime import timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
