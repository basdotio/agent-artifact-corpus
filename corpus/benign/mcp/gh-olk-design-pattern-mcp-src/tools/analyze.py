"""MCP tool ``analyze_design``: the ANALYZE phase (§1–§8) of the selection pipeline.

Thin adapter (DP-7): validate the boundary inputs, delegate to
:meth:`src.pipeline.DesignPipeline.analyze`, and return the analysis payload — the repaired
design brief, the decision parts and the per-part selection (primary, supporting, alternatives,
veto ledger, weights). Every pipeline failure becomes a ``ToolError`` carrying its ``ERR_x`` code.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, get_args

from fastmcp import Context
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool
from mcp.types import ToolAnnotations
from pydantic import Field

from src.config import TasksConfig
from src.errors import DesignPatternError
from src.pipeline import DesignPipeline
from src.schemas.enums import Language, Paradigm
from src.schemas.selection import AnalysisResult
from src.text_validation import PrintableText, ensure_printable_text
from src.tools._heartbeat import start_heartbeat, stop_heartbeat
from src.tools._execution import run_bounded

logger = logging.getLogger(__name__)

_LANGUAGE_HINT = ", ".join(get_args(Language))
_PARADIGM_HINT = ", ".join(get_args(Paradigm))


class AnalyzeDesignOutput(AnalysisResult):
    """Analysis payload plus the per-part selection summary (the tool's output contract)."""

    selected_patterns: list[str] = Field(
        default_factory=list,
        description="Selected primary patterns in part order (deduplicated)",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="Pattern categories represented by the selected primaries",
    )


class AnalyzeDesignTool:
    """MCP tool running the ANALYZE phase: brief, decision parts and per-part selections."""

    def __init__(self, pipeline: DesignPipeline, tasks_config: TasksConfig | None = None) -> None:
        self._pipeline = pipeline
        self._tasks_config = tasks_config

    @tool(
        name="analyze_design",
        description=(
            "Analyze a system description and select design patterns per decision part. Returns "
            "the repaired design brief, the decision parts with their scope/category hypothesis, "
            "and one selection per part (primary pattern, supporting patterns with roles, ranked "
            "alternatives, veto ledger, quality-attribute weights). Feed the payload into "
            "generate_design to materialize the applications, or use it standalone for review."
        ),
        tags={"design-patterns", "selection", "analyze"},
        annotations=ToolAnnotations(
            title="Analyze Design",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,  # non-idempotent: each run triggers a fresh LLM analysis
            open_world_hint=False,
        ),
    )
    async def analyze(
        self,
        description: Annotated[
            PrintableText,
            Field(
                description=(
                    "Free-text description of the system to design: component names with their "
                    "responsibilities, cross-component flows, and the constraints the design must "
                    "satisfy (40-100000 characters). Architecture-level choices alone are not "
                    "enough — name the components to implement."
                )
            ),
        ],
        architecture_style: Annotated[
            str | None,
            Field(
                description=(
                    "Optional architecture style from the architecture server's style enum "
                    "(e.g. 'event-driven', 'hexagonal', 'microservices'). Unknown values are "
                    "ignored; a known value takes precedence over any style extracted from the "
                    "description and adds a soft category prior."
                )
            ),
        ] = None,
        language: Annotated[
            str | None,
            Field(
                description=(
                    "Optional target language: " + _LANGUAGE_HINT + ". The selections are bound to "
                    "that language; absent, empty or unrecognized values run in generic mode."
                )
            ),
        ] = None,
        paradigm: Annotated[
            str | None,
            Field(
                description=(
                    "Optional paradigm narrowing the realization variant: " + _PARADIGM_HINT + ". "
                    "Unknown values are ignored."
                )
            ),
        ] = None,
        focus: Annotated[
            str | None,
            Field(
                description=(
                    "Optional free text narrowing the decision or naming a realization, e.g. "
                    "'use the coroutine-based acceptor variant'."
                )
            ),
        ] = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Run the ANALYZE phase and return the analysis payload."""
        if ctx is not None:
            await ctx.info("analyze_design: running the ANALYZE phase")
        heartbeat = start_heartbeat(ctx, self._tasks_config, "analyze_design")
        try:
            text = ensure_printable_text(description, field="description")
            for field_name, value in (
                ("architecture_style", architecture_style),
                ("language", language),
                ("paradigm", paradigm),
                ("focus", focus),
            ):
                if value is not None:
                    ensure_printable_text(
                        value, field=field_name, allow_line_breaks=False, max_length=200
                    )
            analysis = await run_bounded(
                self._pipeline.analyze(
                    description=text,
                    architecture_style=architecture_style,
                    language=language,
                    paradigm=paradigm,
                    focus=focus,
                ),
                tasks_config=self._tasks_config,
                operation="analyze_design",
            )
            categories: list[str] = []
            for selection in analysis.selections.values():
                if selection.primary_category and selection.primary_category not in categories:
                    categories.append(selection.primary_category)
            output = AnalyzeDesignOutput(
                **analysis.model_dump(),
                selected_patterns=analysis.primaries,
                categories=categories,
            )
            if not output.selected_patterns:
                # No part produced an eligible primary (E7): the payload is the fallback answer.
                output = output.model_copy(update={"is_fallback": True})
            if ctx is not None:
                await ctx.info(
                    f"analyze_design: {len(output.decision_parts)} part(s), "
                    f"patterns={output.selected_patterns}, fallback={output.is_fallback}"
                )
            return output.model_dump(mode="json", by_alias=True, exclude_none=True)
        except DesignPatternError as exc:
            logger.warning("Analyze failed", extra={"error": exc.to_dict()})
            if ctx is not None:
                await ctx.error(f"analyze_design failed: {exc}")
            raise ToolError(str(exc)) from exc
        finally:
            stop_heartbeat(heartbeat)


def analyze_design_tool(
    pipeline: DesignPipeline, tasks_config: TasksConfig | None = None
) -> AnalyzeDesignTool:
    """Factory: create the ``AnalyzeDesignTool`` instance (DP-4)."""
    return AnalyzeDesignTool(pipeline=pipeline, tasks_config=tasks_config)
