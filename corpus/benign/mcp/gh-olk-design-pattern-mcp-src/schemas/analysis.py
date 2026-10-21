"""Stage A/B analysis models (§4–§5): the tolerant ``Raw*`` LLM boundary, their repaired strict
forms, and the per-part requirement weights of §7.1.

Two strictness levels, deliberately:

* ``Raw*`` models are the LLM boundary. Enum-valued fields are plain ``str`` there because the
  guide requires a *deterministic repair* of off-enum values (§5 rules 3 and 5, E10) instead of a
  parse failure: unknown ``scope`` falls back to ``module``, unknown ``category_hypothesis`` to
  ``null``, unknown ``paradigm`` is dropped.
* Everything else is the strict internal contract.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.enums import QUALITY_AXES, Language, Paradigm, PatternCategory, PatternScope


class RequirementWeights(BaseModel):
    """Per-part quality-attribute weights (§7.1) over the eight scoring axes, each in [0, 1].

    Extraction is batched per request: ONE call maps every decision-part id to its own weight
    vector, so the per-part ratings stay independent while the provider is called once.
    Each vector is consumed by the §7.2 blend and carried into the GENERATE seed.
    """

    testability: float = Field(default=0.0, ge=0.0, le=1.0)
    extensibility: float = Field(default=0.0, ge=0.0, le=1.0)
    maintainability: float = Field(default=0.0, ge=0.0, le=1.0)
    simplicity: float = Field(default=0.0, ge=0.0, le=1.0)
    performance: float = Field(default=0.0, ge=0.0, le=1.0)
    reliability: float = Field(default=0.0, ge=0.0, le=1.0)
    security: float = Field(default=0.0, ge=0.0, le=1.0)
    scalability: float = Field(default=0.0, ge=0.0, le=1.0)

    def as_dict(self) -> dict[str, float]:
        """The weight vector in :data:`~src.schemas.enums.QUALITY_AXES` order."""
        return {axis: float(getattr(self, axis)) for axis in QUALITY_AXES}


class RequirementWeightsBatch(BaseModel):
    """Internal §7.1 response contract: one weight vector per supplied decision-part id.

    Strict by design — a missing or extra part id is a provider error the repair path
    must see, not a silently dropped part. Internal: it never crosses the MCP wire contract.
    """

    weights: dict[str, RequirementWeights] = Field(default_factory=dict)


class RawBriefComponent(BaseModel):
    """Component restated by the Stage A call."""

    name: str = Field(default="")
    type: str = Field(default="")
    responsibilities: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class RawBriefFlow(BaseModel):
    """Component relationship restated by the Stage A call."""

    source: str = Field(default="")
    target: str = Field(default="")
    kind: str = Field(default="sync")

    model_config = ConfigDict(extra="ignore")


class RawDesignBrief(BaseModel):
    """Stage A output before deterministic normalization (§4)."""

    restated_goal: str = Field(default="")
    architecture_style: str | None = Field(default=None)
    constraints: list[str] = Field(default_factory=list)
    components: list[RawBriefComponent] = Field(default_factory=list)
    flows: list[RawBriefFlow] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    quality_attributes: dict[str, float] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class RawDecisionPart(BaseModel):
    """Stage B output before deterministic repair (§5 rules 2–4)."""

    id: str = Field(default="")
    statement: str = Field(default="")
    component_refs: list[str] = Field(default_factory=list)
    scope: str | None = Field(default=None)
    category_hypothesis: str | None = Field(default=None)
    constraints: list[str] = Field(default_factory=list)
    priority: float = Field(default=0.0)
    negative_signals: list[str] = Field(default_factory=list)
    is_contract_part: bool = Field(default=False)

    model_config = ConfigDict(extra="ignore")


class RawBriefAndParts(BaseModel):
    """The combined Stage A+B structured call (§3.1: one call, two stages)."""

    design_brief: RawDesignBrief = Field(default_factory=RawDesignBrief)
    decision_parts: list[RawDecisionPart] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class BriefComponent(BaseModel):
    """Repaired component entry."""

    name: str
    type: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class BriefFlow(BaseModel):
    """Repaired component relationship."""

    source: str
    target: str
    kind: str = "sync"


class DesignBrief(BaseModel):
    """Repaired Stage A result. ``language`` is the effective language (§1.3)."""

    restated_goal: str = ""
    architecture_style: str | None = None
    constraints: list[str] = Field(default_factory=list)
    components: list[BriefComponent] = Field(default_factory=list)
    flows: list[BriefFlow] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    quality_attributes: dict[str, float] = Field(default_factory=dict)
    language: Language = "generic"
    paradigm: Paradigm | None = None


class DecisionPart(BaseModel):
    """Repaired Stage B decision part."""

    id: str
    statement: str
    component_refs: list[str] = Field(default_factory=list)
    scope: PatternScope = "module"
    category_hypothesis: PatternCategory | None = None
    constraints: list[str] = Field(default_factory=list)
    priority: float = 0.0
    negative_signals: list[str] = Field(default_factory=list)
    is_contract_part: bool = False
    is_fallback: bool = False


class BriefAndParts(BaseModel):
    """Repaired Stage A+B result."""

    design_brief: DesignBrief
    decision_parts: list[DecisionPart]
