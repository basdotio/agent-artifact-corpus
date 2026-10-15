"""Data types for extraction.

An extraction is a *plan* first and a filesystem operation second. The plan is
fully JSON-serialisable, so it can be printed, reviewed, handed to an agent,
stored next to the result as provenance, and re-executed later against a
different checkout.

That split is deliberate. Extraction is the only part of Drydock that writes,
and the builders shipped four data-loss bugs by doing irreversible work before
establishing whether it was safe. Here nothing is written until a plan exists
and its breakages have been surfaced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..core.models import FileId

__all__ = [
    "Severity",
    "Breakage",
    "PlannedFile",
    "ExtractionPlan",
]

Severity = Literal["blocking", "warning", "info"]


@dataclass(frozen=True, slots=True)
class Breakage:
    """Something that will not work in the extracted copy.

    Reported rather than silently repaired. An extraction that quietly drops a
    dependency produces a package that imports fine and fails at runtime, which
    is worse than one that refuses to be created.
    """

    kind: Literal[
        "missing-internal-dep",
        "external-dependent",
        "unresolved-import",
        "ambiguous-import",
        "relative-escape",
        "package-init-missing",
        "name-collision",
    ]
    severity: Severity
    file: FileId
    detail: str
    target: str | None = None
    """The dependency or symbol involved, when there is one."""

    hint: str | None = None
    """What the operator can do about it."""


@dataclass(frozen=True, slots=True)
class PlannedFile:
    """One file that will be copied, and where it lands."""

    source: FileId
    """Path relative to the source project root."""

    destination: str
    """Path relative to the extraction output root."""

    reason: Literal["selected", "closure", "package-init", "test", "asset"]
    """Why this file is included. `closure` means it was pulled in because
    something selected depends on it -- surfaced so a reviewer can see the
    difference between what they asked for and what came along."""

    lang: str | None = None
    rewrites: int = 0
    """Number of import statements rewritten in this file."""

    synthesized: bool = False
    """True when the engine writes this file rather than copying it.

    Used for package ``__init__.py`` files that exist only to make the
    extracted tree importable. Copying the original is usually wrong: a
    re-exporting ``__init__`` drags its whole package along, so extracting one
    subpackage of Drydock pulled in all 25 files instead of 11. A minimal stub
    keeps the extraction minimal, which is what the workflow asks for."""


@dataclass(slots=True)
class ExtractionPlan:
    """Everything the engine needs, and everything a reviewer should see."""

    project: str
    source_root: str
    component: str
    """Name of the extracted component; becomes the root package name."""

    files: list[PlannedFile] = field(default_factory=list)
    breakages: list[Breakage] = field(default_factory=list)

    external_deps: dict[str, list[str]] = field(default_factory=dict)
    """Third-party requirements by ecosystem, e.g. {"python": ["httpx"]}."""

    module_map: dict[str, str] = field(default_factory=dict)
    """Old module path -> new module path, applied by the rewriters."""

    languages: list[str] = field(default_factory=list)
    selection: dict[str, object] = field(default_factory=dict)
    """How the file set was chosen, recorded for reproducibility."""

    source_commit: str | None = None

    @property
    def blocking(self) -> list[Breakage]:
        return [b for b in self.breakages if b.severity == "blocking"]

    @property
    def is_safe(self) -> bool:
        """True when nothing blocking stands in the way of a clean extraction."""
        return not self.blocking

    @property
    def selected_count(self) -> int:
        return sum(1 for f in self.files if f.reason == "selected")

    @property
    def closure_count(self) -> int:
        return sum(1 for f in self.files if f.reason == "closure")

    def summary(self) -> dict[str, object]:
        return {
            "project": self.project,
            "component": self.component,
            "files_total": len(self.files),
            "files_selected": self.selected_count,
            "files_pulled_by_closure": self.closure_count,
            "languages": sorted(self.languages),
            "external_deps": {k: sorted(v) for k, v in sorted(self.external_deps.items())},
            "breakages": len(self.breakages),
            "blocking": len(self.blocking),
            "safe_to_extract": self.is_safe,
        }
