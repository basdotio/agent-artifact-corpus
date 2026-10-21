"""Stage F/G generation models (§9–§11 item 1): the deterministic GENERATE seed, its catalog
context slices, and the tolerant ``Raw*`` GENERATE payload.

``Raw*`` models are the LLM boundary with ``extra="ignore"``; every deterministic field
(ids, pattern echoes, language bindings) is re-attached afterwards (§9 rule 3).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.enums import Language, PatternCategory
from src.schemas.variants import LanguageBinding


class ParticipantSpec(BaseModel):
    """Catalog participant role handed to GENERATE."""

    role: str
    responsibility: str


class CatalogSlice(BaseModel):
    """Per-application catalog context handed to GENERATE (never the whole record).

    ``language_binding`` is built by the deterministic §8.4 binder, never by the model.
    """

    pattern: str
    category: PatternCategory
    intent: str
    problem: str
    context: str
    benefits: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    participants: list[ParticipantSpec] = Field(default_factory=list)
    avoid_when: list[str] = Field(default_factory=list)
    best_practices: list[str] = Field(default_factory=list)
    test_notes: str = ""
    language_binding: LanguageBinding | None = None


class ApplicationSeed(BaseModel):
    """One (part, pattern) pair promoted to a ``PatternApplication`` seed (§9 rule 3)."""

    id: str
    pattern: str
    category: PatternCategory
    part_id: str
    part_statement: str
    constraints: list[str] = Field(default_factory=list)
    component_refs: list[str] = Field(default_factory=list)
    is_primary: bool = True
    role: str | None = None


class InteractionSeed(BaseModel):
    """Brief flow between components of two applications (§9 rule 5, §10.2)."""

    source: str
    target: str
    type: str
    description: str


class GenerationSeed(BaseModel):
    """Deterministic input of the GENERATE call (§11 item 1)."""

    restated_goal: str = ""
    constraints: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    language: Language = "generic"
    applications: list[ApplicationSeed] = Field(default_factory=list)
    catalog_slices: dict[str, CatalogSlice] = Field(default_factory=dict)
    interaction_seeds: list[InteractionSeed] = Field(default_factory=list)
    part_weights: dict[str, dict[str, float]] = Field(default_factory=dict)


class RawParticipant(BaseModel):
    """Participant proposed by GENERATE."""

    role: str = Field(default="")
    maps_to: str = Field(default="")
    responsibility: str = Field(default="")

    model_config = ConfigDict(extra="ignore")


class RawApplicationInteraction(BaseModel):
    """Intra-application collaboration proposed by GENERATE."""

    from_: str = Field(default="client", alias="from")
    to: str = Field(default="")
    description: str = Field(default="")

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class RawApplication(BaseModel):
    """Application proposed by GENERATE (deterministic fields are re-attached afterwards)."""

    id: str = Field(default="")
    pattern: str = Field(default="")
    name: str = Field(default="")
    problem: str = Field(default="")
    solution: str = Field(default="")
    participants: list[RawParticipant] = Field(default_factory=list)
    interactions: list[RawApplicationInteraction] = Field(default_factory=list)
    implementation_steps: list[str] = Field(default_factory=list)
    code_sketch: str | None = Field(default=None)
    test_notes: str | None = Field(default=None)
    alternatives_considered: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class RawGeneration(BaseModel):
    """GENERATE call payload."""

    applications: list[RawApplication] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")
