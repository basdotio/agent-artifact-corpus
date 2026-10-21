"""MCP tool ``evaluate_design``: the EVALUATE phase (§11 item 2).

Scores a caller-supplied design draft against the requirement text (or a prior
``analyze_design`` payload), and returns the evaluation together with the advisory offline
integrity findings of the design. A design below the minimum contract (no application at all)
is rejected with ``ERR_004``; a malformed design payload is rejected with ``ERR_002``.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastmcp import Context
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from src.config import TasksConfig
from src.design_normalization import truncate
from src.errors import (
    ERROR_DESCRIPTION_INVALID,
    ERROR_MIN_REQUIREMENTS,
    DesignPatternError,
    MalformedDesignOverviewError,
)
from src.pipeline import DesignPipeline
from src.schemas.analysis import DecisionPart
from src.schemas.evaluation import EvaluationFinding, EvaluationSummary
from src.schemas.quality import QualityMetrics
from src.text_validation import PrintableText, ensure_printable_text
from src.tools._adapters import analysis_to_pydantic, design_from_dict, design_integrity_findings
from src.tools._heartbeat import start_heartbeat, stop_heartbeat
from src.tools._execution import run_bounded

logger = logging.getLogger(__name__)

_STRONG_AXIS = 70.0
_WEAK_AXIS = 50.0


class EvaluateDesignOutput(BaseModel):
    """Output schema of ``evaluate_design``."""

    score: float = Field(ge=0.0, le=100.0, description="Overall design score (0-100)")
    summary: EvaluationSummary = Field(description="High-level evaluation summary")
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Per-axis scores of the eight design axes (0-100 each)",
    )
    quality_metrics: QualityMetrics | None = Field(
        default=None,
        description=(
            "The design's own quality attributes on the catalog 0-10 scale, when the design "
            "carries them (comparable to pattern quality_attributes)"
        ),
    )
    findings: list[EvaluationFinding] = Field(
        default_factory=list,
        description="Evaluation findings; a 'selection' finding names the offending pattern",
    )
    integrity_findings: list[str] = Field(
        default_factory=list,
        description=(
            "Advisory offline integrity findings of the supplied design (empty when the design "
            "is internally consistent); never blocks the evaluation"
        ),
    )


class EvaluateDesignTool:
    """MCP tool running the EVALUATE phase for a caller-supplied design draft."""

    def __init__(self, pipeline: DesignPipeline, tasks_config: TasksConfig | None = None) -> None:
        self._pipeline = pipeline
        self._tasks_config = tasks_config

    @tool(
        name="evaluate_design",
        description=(
            "Evaluate a design draft against the requirements it must serve: scores 0-100 with "
            "per-axis ratings, findings (a 'selection' finding names the offending pattern and "
            "drives reselection upstream), and advisory integrity findings of the design itself. "
            "Pass the design returned by generate_design or select_design_patterns, plus the "
            "requirement text or a prior analyze_design payload."
        ),
        tags={"design-patterns", "selection", "evaluate"},
        annotations=ToolAnnotations(
            title="Evaluate Design",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,  # non-idempotent: each run triggers a fresh LLM analysis
            open_world_hint=False,
        ),
    )
    async def evaluate(
        self,
        design_json: Annotated[
            dict[str, Any],
            Field(description="The design draft to score (docs/result-schema.json shape)"),
        ],
        requirements: Annotated[
            PrintableText,
            Field(description="The requirement text the design must serve (40-100000 characters)"),
        ],
        analysis: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional prior analyze_design payload: its decision parts drive the axis "
                    "weighting; without it the requirement text becomes a single decision part"
                )
            ),
        ] = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Run the EVALUATE phase and return the scored evaluation."""
        if ctx is not None:
            await ctx.info("evaluate_design: running the EVALUATE phase")
        heartbeat = start_heartbeat(ctx, self._tasks_config, "evaluate_design")
        try:
            try:
                design = design_from_dict(design_json)
            except MalformedDesignOverviewError as exc:
                raise ToolError(f"{ERROR_DESCRIPTION_INVALID}: {exc}") from exc
            if not design.applications:
                raise DesignPatternError(
                    ERROR_MIN_REQUIREMENTS,
                    "the design carries no application to evaluate",
                    hint="generate_design returns a complete draft; a bare overview is not enough",
                )
            text = ensure_printable_text(requirements, field="requirements")
            parts = (
                analysis_to_pydantic(analysis).decision_parts
                if analysis is not None
                else [
                    DecisionPart(
                        id="requirements",
                        statement=truncate(text, 400),
                        priority=1.0,
                    )
                ]
            )
            integrity_findings = design_integrity_findings(design)
            evaluation = await run_bounded(
                self._pipeline.evaluate(design, parts),
                tasks_config=self._tasks_config,
                operation="evaluate_design",
            )
            summary = EvaluationSummary(
                overall_score=evaluation.score,
                strengths=[
                    f"{axis}: {score:g}"
                    for axis, score in evaluation.axis_scores.items()
                    if score >= _STRONG_AXIS
                ],
                weaknesses=[
                    f"{axis}: {score:g}"
                    for axis, score in evaluation.axis_scores.items()
                    if score < _WEAK_AXIS
                ],
                critical_findings=[
                    finding.detail
                    for finding in evaluation.findings
                    if finding.kind in {"selection", "consistency"}
                ],
            )
            output = EvaluateDesignOutput(
                score=evaluation.score,
                summary=summary,
                metrics=dict(evaluation.axis_scores),
                quality_metrics=(
                    QualityMetrics(**design.quality_attributes) if design.quality_attributes else None
                ),
                findings=list(evaluation.findings),
                integrity_findings=integrity_findings,
            )
            if ctx is not None:
                await ctx.info(
                    f"evaluate_design: score={output.score:g}, "
                    f"findings={len(output.findings)}, integrity={len(output.integrity_findings)}"
                )
            return output.model_dump(mode="json", by_alias=True, exclude_none=True)
        except DesignPatternError as exc:
            logger.warning("Evaluate failed", extra={"error": exc.to_dict()})
            if ctx is not None:
                await ctx.error(f"evaluate_design failed: {exc}")
            raise ToolError(str(exc)) from exc
        finally:
            stop_heartbeat(heartbeat)


def evaluate_design_tool(
    pipeline: DesignPipeline, tasks_config: TasksConfig | None = None
) -> EvaluateDesignTool:
    """Factory: create the ``EvaluateDesignTool`` instance (DP-4)."""
    return EvaluateDesignTool(pipeline=pipeline, tasks_config=tasks_config)
