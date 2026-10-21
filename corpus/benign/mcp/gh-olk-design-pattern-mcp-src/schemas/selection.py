"""Stage C/D/E selection models (§6–§8): retrieval/scoring annotations and the per-part outcome.

``AnnotatedCandidate`` is what leaves the §7 scoring stage; ``PartSelection`` is the Stage E
outcome for one decision part — or the E7 structured failure payload.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.schemas.analysis import DecisionPart, DesignBrief
from src.schemas.enums import Language, PatternCategory


class Adjustment(BaseModel):
    """One applied §7.3 delta; the ledger entry behind ``fit_score``."""

    label: str
    delta: float


class AnnotatedCandidate(BaseModel):
    """A pattern with its retrieval, scoring and adjustment annotations (§7)."""

    name: str
    category: PatternCategory
    retrieval_score: float
    analysis_score: float
    fusion_score_normalized: float
    blended: float
    fit_score: float
    adjustments: list[Adjustment] = Field(default_factory=list)
    fused_rank: int = 0
    rerank_rank: int = 0
    catalog_order: int = 0


class SupportingChoice(BaseModel):
    """A supporting pattern with the distinct constraint it solves (§8.3)."""

    pattern: str
    role: str
    fit_score: float = 0.0


class PartSelection(BaseModel):
    """Stage E outcome for one part (or the E7 structured failure payload)."""

    part: DecisionPart
    weights: dict[str, float] = Field(default_factory=dict)
    candidates: list[AnnotatedCandidate] = Field(default_factory=list)
    primary: str | None = None
    primary_category: PatternCategory | None = None
    is_fallback: bool = False
    fallback_reason: str | None = None
    fallback_candidates: list[dict[str, Any]] = Field(default_factory=list)
    supporting: list[SupportingChoice] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    ambiguous: bool = False
    near_tie: list[str] = Field(default_factory=list)
    veto_ledger: list[str] = Field(default_factory=list)
    weights_source: str = "llm"


class AnalysisResult(BaseModel):
    """ANALYZE phase outcome (§4–§8): the repaired brief, its decision parts and the per-part
    selections handed to GENERATE.

    ``selections`` is keyed by part id; ``technology_tokens`` carries the §8.4 layer-3 evidence
    for the capability floor, and ``focus`` the request's variant-narrowing hint.
    """

    design_brief: DesignBrief
    decision_parts: list[DecisionPart] = Field(default_factory=list)
    selections: dict[str, PartSelection] = Field(default_factory=dict)
    effective_language: Language = "generic"
    focus: str | None = None
    technology_tokens: list[str] = Field(default_factory=list)
    is_fallback: bool = False

    @property
    def primaries(self) -> list[str]:
        """Selected primary patterns in part order, deduplicated."""
        seen: list[str] = []
        for part in self.decision_parts:
            selection = self.selections.get(part.id)
            if selection is not None and selection.primary and selection.primary not in seen:
                seen.append(selection.primary)
        return seen
