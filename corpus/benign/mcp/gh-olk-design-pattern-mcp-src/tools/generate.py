"""MCP tool ``generate_design``: the GENERATE phase (§9–§11 item 1).

Two input paths, validated as a union:

* ``analysis`` — a prior ``analyze_design`` payload (the pipeline path: brief, parts and
  per-part selections travel together);
* ``patterns`` + ``description`` — explicit catalog names (the deterministic path): each name
  resolves through :class:`~src.patterns.loader.PatternLoader` (``ERR_003`` when unknown) and
  becomes one decision part whose statement is the record's intent.

Either way the deterministic composition (§9) runs first, then the GENERATE call materializes
the applications.
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
from src.design_normalization import as_category, as_language, as_scope, kebab, truncate
from src.errors import ERROR_PATTERNS_NOT_FOUND, DesignPatternError
from src.pipeline import DesignPipeline
from src.patterns.loader import PatternLoader
from src.schemas.analysis import DecisionPart, DesignBrief
from src.schemas.design import DesignResult
from src.schemas.enums import Language
from src.schemas.selection import AnalysisResult, AnnotatedCandidate, PartSelection
from src.text_validation import ensure_printable_text
from src.tools._adapters import analysis_to_pydantic
from src.tools._heartbeat import start_heartbeat, stop_heartbeat
from src.tools._execution import run_bounded

logger = logging.getLogger(__name__)

_LANGUAGE_HINT = ", ".join(get_args(Language))
_MIN_DESCRIPTION = 40


class GenerateDesignOutput(DesignResult):
    """Serializable result of ``generate_design`` (the ``DesignResult`` contract)."""


def _resolve_patterns(loader: PatternLoader, patterns: list[str]) -> list[tuple[str, str]]:
    """Resolve pattern names/aliases to ``(canonical name, category)``; ``ERR_003`` when unknown."""
    resolved: list[tuple[str, str]] = []
    unknown: list[str] = []
    for raw in patterns:
        canonical = loader.resolve(raw.strip().lower())
        record = loader.get_by_name(canonical) if canonical is not None else None
        if record is None:
            unknown.append(raw)
            continue
        if all(name != record.name for name, _ in resolved):
            resolved.append((record.name, record.category))
    if unknown:
        raise DesignPatternError(
            ERROR_PATTERNS_NOT_FOUND,
            f"unknown design pattern name(s): {', '.join(sorted(unknown))}",
            hint="list_design_patterns returns every valid name; get_design_pattern resolves aliases",
        )
    return resolved


def _explicit_analysis(
    loader: PatternLoader,
    resolved: list[tuple[str, str]],
    description: str,
    language: str | None,
) -> AnalysisResult:
    """Deterministic analysis payload for the explicit-patterns path (§9 inputs only)."""
    effective_language = as_language(language or "generic")
    brief = DesignBrief(
        restated_goal=truncate(description, 300),
        language=effective_language,
    )
    parts: list[DecisionPart] = []
    selections: dict[str, PartSelection] = {}
    total = len(resolved)
    for index, (name, category) in enumerate(resolved):
        record = loader.get_by_name(name)
        if record is None:  # pragma: no cover — resolved names come from this loader
            continue
        priority = max(0.1, 1.0 - index / max(total, 1))
        part = DecisionPart(
            id=kebab(name) or f"part-{index + 1}",
            statement=truncate(record.intent or record.problem, 400),
            scope=as_scope(record.scope),
            category_hypothesis=as_category(category),
            priority=priority,
        )
        parts.append(part)
        selections[part.id] = PartSelection(
            part=part,
            candidates=[
                AnnotatedCandidate(
                    name=name,
                    category=as_category(category),
                    retrieval_score=1.0,
                    analysis_score=1.0,
                    fusion_score_normalized=1.0,
                    blended=1.0,
                    fit_score=100.0,
                    catalog_order=loader.order_index(name),
                )
            ],
            primary=name,
            primary_category=as_category(category),
            weights_source="explicit",
        )
    return AnalysisResult(
        design_brief=brief,
        decision_parts=parts,
        selections=selections,
        effective_language=effective_language,
        is_fallback=False,
    )


class GenerateDesignTool:
    """MCP tool running the GENERATE phase for an analysis payload or explicit pattern names."""

    def __init__(
        self,
        pipeline: DesignPipeline,
        pattern_loader: PatternLoader,
        tasks_config: TasksConfig | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._loader = pattern_loader
        self._tasks_config = tasks_config

    @tool(
        name="generate_design",
        description=(
            "Materialize the pattern applications for a design: either pass the payload of a "
            "prior analyze_design call ('analysis'), or pass explicit catalog pattern names "
            "('patterns') together with the system 'description'. Returns a complete design draft "
            "— applications with participants, interactions, implementation steps, code sketches "
            "and language bindings, plus interactions, quality attributes, a test strategy and "
            "risks. Unknown pattern names raise ERR_003."
        ),
        tags={"design-patterns", "selection", "generate"},
        annotations=ToolAnnotations(
            title="Generate Design",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,  # non-idempotent: each run triggers a fresh LLM analysis
            open_world_hint=False,
        ),
    )
    async def generate(
        self,
        analysis: Annotated[
            dict[str, Any] | None,
            Field(description="A prior analyze_design payload (brief, parts, per-part selections)"),
        ] = None,
        patterns: Annotated[
            list[str] | None,
            Field(description="Explicit catalog pattern names or aliases to realize (explicit path)"),
        ] = None,
        description: Annotated[
            str | None,
            Field(
                description=(
                    "System description (40-100000 characters); required with 'patterns', ignored "
                    "when 'analysis' is supplied"
                )
            ),
        ] = None,
        language: Annotated[
            str | None,
            Field(description="Optional target language: " + _LANGUAGE_HINT + " (explicit path)"),
        ] = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Run the GENERATE phase and return the design draft."""
        if ctx is not None:
            await ctx.info(
                "generate_design: "
                + ("analysis payload" if analysis is not None else f"patterns={patterns}")
            )
        heartbeat = start_heartbeat(ctx, self._tasks_config, "generate_design")
        try:
            if analysis is not None:
                parsed = analysis_to_pydantic(analysis)
            else:
                if not patterns:
                    raise DesignPatternError(
                        ERROR_PATTERNS_NOT_FOUND,
                        "no input: pass an 'analysis' payload or a non-empty 'patterns' list",
                        hint="run analyze_design first, or name patterns explicitly",
                    )
                if description is None:
                    raise DesignPatternError(
                        ERROR_PATTERNS_NOT_FOUND,
                        "'description' is required when generating from explicit pattern names",
                        hint="pass the system description the patterns must be realized for",
                    )
                text = ensure_printable_text(description, field="description")
                if len(text.strip()) < _MIN_DESCRIPTION:
                    raise DesignPatternError(
                        ERROR_PATTERNS_NOT_FOUND,
                        f"description is shorter than {_MIN_DESCRIPTION} characters",
                    )
                resolved = _resolve_patterns(self._loader, patterns)
                parsed = _explicit_analysis(self._loader, resolved, text, language)
            design = await run_bounded(
                self._pipeline.generate(parsed),
                tasks_config=self._tasks_config,
                operation="generate_design",
            )
            output = GenerateDesignOutput.model_validate(
                design.model_dump(by_alias=True, exclude_none=True)
            )
            if ctx is not None:
                await ctx.info(
                    f"generate_design: {len(output.applications)} application(s), "
                    f"primary={output.overview.primary_pattern}"
                )
            return output.model_dump(mode="json", by_alias=True, exclude_none=True)
        except DesignPatternError as exc:
            logger.warning("Generate failed", extra={"error": exc.to_dict()})
            if ctx is not None:
                await ctx.error(f"generate_design failed: {exc}")
            raise ToolError(str(exc)) from exc
        finally:
            stop_heartbeat(heartbeat)


def generate_design_tool(
    pipeline: DesignPipeline,
    pattern_loader: PatternLoader,
    tasks_config: TasksConfig | None = None,
) -> GenerateDesignTool:
    """Factory: create the ``GenerateDesignTool`` instance (DP-4)."""
    return GenerateDesignTool(
        pipeline=pipeline, pattern_loader=pattern_loader, tasks_config=tasks_config
    )
