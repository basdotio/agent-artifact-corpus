"""Stage H evaluation models and the full-pipeline result (§11 items 2 and 4).

``DesignEvaluation`` is the EVALUATE call payload; ``PipelineResult`` combines the final
design, its evaluation, and the loop metadata for callers of the full pipeline.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.design import DesignResult
from src.schemas.quality import QualityMetrics


class EvaluationFinding(BaseModel):
    """One EVALUATE finding; ``pattern`` names the offending candidate, if any."""

    kind: str = Field(default="quality")
    detail: str = Field(default="")
    pattern: str | None = Field(default=None)

    model_config = ConfigDict(extra="ignore")


class DesignEvaluation(BaseModel):
    """EVALUATE call payload (§11 item 2)."""

    score: float = Field(default=0.0, ge=0.0, le=100.0)
    findings: list[EvaluationFinding] = Field(default_factory=list)
    axis_scores: dict[str, float] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

    @property
    def selection_defect(self) -> bool:
        """True when at least one finding blames a *selection* decision (§11 item 4)."""
        return any(
            f.kind == "selection" and bool(f.pattern) for f in self.findings
        )

    @property
    def offending_patterns(self) -> list[str]:
        """Candidates named by selection defects, in finding order (exclusions are sticky)."""
        seen: list[str] = []
        for finding in self.findings:
            if finding.kind == "selection" and finding.pattern and finding.pattern not in seen:
                seen.append(finding.pattern)
        return seen


class MetricResult(BaseModel):
    """Individual quality-metric assessment result (0–100 per axis)."""

    name: str = Field(description="Metric name, one of the eight scoring axes")
    score: float = Field(ge=0.0, le=100.0, description="Assessment score (0-100)")
    description: str = Field(default="", description="Metric description")
    findings: list[str] = Field(default_factory=list, description="Supporting findings")
    recommendations: list[str] = Field(
        default_factory=list, description="Recommendations to improve this metric"
    )
    reasoning: str = Field(
        default="",
        description=(
            "Step-by-step rubric application: which requirements, components and pattern "
            "expectations were checked, what was found, and why the score is what it is — "
            "written before findings/recommendations."
        ),
    )


class EvaluationSummary(BaseModel):
    """High-level evaluation summary with score and key findings."""

    overall_score: float = Field(ge=0.0, le=100.0, description="Overall design quality score")
    strengths: list[str] = Field(default_factory=list, description="Design strengths")
    weaknesses: list[str] = Field(default_factory=list, description="Design weaknesses")
    critical_findings: list[str] = Field(
        default_factory=list, description="Critical findings that must be addressed"
    )


class PipelineResult(BaseModel):
    """Complete pipeline output combining design, evaluation, and metadata.

    Returned by the full design pipeline (analyze → generate → evaluate → design_loop).
    """

    design: DesignResult = Field(description="The final design result")
    evaluation: DesignEvaluation = Field(description="The evaluation of the final design")
    attempts: int = Field(ge=1, description="Total generate attempts made (initial + retries)")
    final_pattern: str | None = Field(
        default=None, description="Final dominant pattern of the design"
    )
    quality_metrics: QualityMetrics | None = Field(
        default=None, description="Aggregated quality metrics of the applied patterns"
    )
    final_quality_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Final quality score after the best attempt"
    )
    matched_categories: list[str] = Field(
        default_factory=list,
        description="Pattern categories represented by the selected parts (deduplicated)",
    )
    is_fallback: bool = Field(
        default=False,
        description="True when no eligible candidate existed and a category fallback was used",
    )
    alternative_patterns: list[str] = Field(
        default_factory=list,
        description=(
            "Runner-up patterns from the selection phase that scored below the final selection; "
            "excludes the final dominant pattern. Empty when is_fallback is True."
        ),
    )
