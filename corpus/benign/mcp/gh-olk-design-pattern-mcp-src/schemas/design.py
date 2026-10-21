"""Outbound design models (mirrors docs/result-schema.json field for field).

``DesignResult`` is the tool payload; the surrounding models are its parts.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.enums import Language, PatternCategory
from src.schemas.variants import LanguageBinding


class Participant(BaseModel):
    """Role → concrete entity mapping."""

    role: str
    maps_to: str
    responsibility: str


class ApplicationInteraction(BaseModel):
    """Collaboration inside one application (``from`` is a Python keyword)."""

    from_: str = Field(alias="from")
    to: str
    description: str

    model_config = ConfigDict(populate_by_name=True)


class PatternApplication(BaseModel):
    """One concrete application of a pattern to one part (§9 rule 3)."""

    id: str
    pattern: str
    category: PatternCategory | None = None
    name: str
    problem: str
    solution: str
    participants: list[Participant] = Field(default_factory=list)
    interactions: list[ApplicationInteraction] = Field(default_factory=list)
    implementation_steps: list[str] = Field(default_factory=list)
    code_sketch: str | None = None
    language_binding: LanguageBinding | None = None
    test_notes: str | None = None
    alternatives_considered: list[str] = Field(default_factory=list)


class SupportingPattern(BaseModel):
    """Overview-level supporting pattern with its role string (§8.3)."""

    pattern: str
    role: str


class DesignOverview(BaseModel):
    """``DesignResult.overview`` — dominant decision plus request echo and trace."""

    reasoning: str
    primary_pattern: str
    category: PatternCategory
    supporting_patterns: list[SupportingPattern] = Field(default_factory=list)
    principles: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    score: float | None = None


class Interaction(BaseModel):
    """Cross-application interaction."""

    source: str
    target: str
    type: str
    description: str


class Risk(BaseModel):
    """Design risk with mitigation."""

    risk: str
    mitigation: str


class TestStrategy(BaseModel):
    """Testing approach plus the seams the design exposes."""

    approach: str
    test_seams: list[str] = Field(default_factory=list)


class DesignResult(BaseModel):
    """The tool payload; field-for-field the shape of ``docs/result-schema.json``."""

    overview: DesignOverview
    applications: list[PatternApplication]
    interactions: list[Interaction] = Field(default_factory=list)
    quality_attributes: dict[str, float] = Field(default_factory=dict)
    test_strategy: TestStrategy | None = None
    risks: list[Risk] = Field(default_factory=list)
