"""Pattern-catalog schemas: the joined record view handed out by the catalog tools.

``PatternRecord`` is the outbound shape of one catalog record after the layout-V8 join
(§2.3 rule 4): the main record's fields plus its joined language implementations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.enums import (
    Language,
    Paradigm,
    PatternCategory,
    PatternScope,
    Provenance,
)
from src.schemas.variants import LanguageBinding


class PatternParticipantRole(BaseModel):
    """One catalog participant role with its responsibility."""

    role: str
    responsibility: str


class PatternRecord(BaseModel):
    """A full catalog record (V8 main record + joined language files)."""

    name: str
    category: PatternCategory
    scope: PatternScope
    intent: str
    problem: str
    context: str
    aliases: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    quality_attributes: dict[str, float] = Field(default_factory=dict)
    participants: list[PatternParticipantRole] = Field(default_factory=list)
    suitable_scopes: list[str] = Field(default_factory=list)
    unsuitable_scopes: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    avoid_when: list[str] = Field(default_factory=list)
    related_patterns: list[str] = Field(default_factory=list)
    related_patterns_notes: dict[str, str] = Field(default_factory=dict)
    anti_patterns: list[str] = Field(default_factory=list)
    migration_from: list[str] = Field(default_factory=list)
    migration_to: list[str] = Field(default_factory=list)
    design_principles: list[str] = Field(default_factory=list)
    best_practices: list[str] = Field(default_factory=list)
    pitfalls: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    paradigms: list[Paradigm] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)
    version: str | None = None
    languages: dict[Language, LanguageBinding] = Field(default_factory=dict)
