"""MCP tool ``select_design_patterns``: select design patterns for a described system.

The tool is a thin adapter (DP-7): validate the boundary inputs, delegate to
:class:`src.pipeline.DesignPipeline`, re-validate the payload against
:class:`src.schemas.DesignResult` and return it as a plain dict. Every pipeline failure becomes a
``ToolError`` carrying its ``ERR_x`` code (docs/implementation-guide.md §12).
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
from src.schemas.design import DesignResult
from src.schemas.evaluation import PipelineResult
from src.schemas.enums import Language, Paradigm
from src.text_validation import PrintableText, ensure_printable_text
from src.tools._heartbeat import start_heartbeat, stop_heartbeat
from src.tools._execution import run_bounded

logger = logging.getLogger(__name__)

_LANGUAGE_HINT = ", ".join(get_args(Language))
_PARADIGM_HINT = ", ".join(get_args(Paradigm))


class SelectDesignPatternsOutput(DesignResult):
    """Serializable result of ``select_design_patterns`` (the ``DesignResult`` contract)."""


def pipeline_result_to_output(result: PipelineResult) -> dict[str, Any]:
    """Serialize a pipeline result into the ``DesignResult`` wire payload.

    The tool boundary returns the field-for-field shape of ``docs/result-schema.json``;
    loop metadata (attempts, quality metrics, alternatives) stays on the
    :class:`~src.schemas.evaluation.PipelineResult` and never leaks into the wire payload.
    """
    return result.design.model_dump(by_alias=True, exclude_none=True)


class SelectDesignPatternsTool:
    """MCP tool selecting the design patterns for an architecture-derived description."""

    def __init__(self, pipeline: DesignPipeline, tasks_config: TasksConfig | None = None) -> None:
        self._pipeline = pipeline
        self._tasks_config = tasks_config

    @tool(
        name="select_design_patterns",
        description=(
            "Select the design patterns to apply to a described system, with per-application "
            "language bindings and a traceable reasoning trail. Send the components, their "
            "responsibilities and the constraints derived from an architecture result. Returns "
            "applications (pattern, participants, implementation steps, bound language variant), "
            "supporting patterns, interactions, quality attributes, a test strategy and risks."
        ),
        tags={"design-patterns", "selection"},
        annotations=ToolAnnotations(
            title="Select Design Patterns",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,  # non-idempotent: each run triggers a fresh LLM analysis
            open_world_hint=False,
        ),
    )
    async def select(
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
                    "Optional target language: " + _LANGUAGE_HINT + ". The patterns are returned "
                    "realized in that language; absent, empty or unrecognized values run in generic "
                    "(language-neutral) mode."
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
                    "'use the coroutine-based acceptor variant'. A verbatim variant_id is bound "
                    "exactly; readable ids come from the design-patterns://variants resource."
                )
            ),
        ] = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Run the selection pipeline and return the ``DesignResult`` as a dict."""
        if ctx is not None:
            await ctx.info("select_design_patterns: running the selection pipeline")
        heartbeat = start_heartbeat(ctx, self._tasks_config, "select_design_patterns")
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
            result = await run_bounded(
                self._pipeline.run_design(
                    description=text,
                    architecture_style=architecture_style,
                    language=language,
                    paradigm=paradigm,
                    focus=focus,
                ),
                tasks_config=self._tasks_config,
                operation="select_design_patterns",
            )
            output = SelectDesignPatternsOutput.model_validate(pipeline_result_to_output(result))
            if ctx is not None:
                await ctx.info(
                    f"select_design_patterns: {len(output.applications)} application(s), "
                    f"primary={output.overview.primary_pattern}"
                )
            return output.model_dump(by_alias=True, exclude_none=True)
        except DesignPatternError as exc:
            logger.warning("Selection failed", extra={"error": exc.to_dict()})
            if ctx is not None:
                await ctx.error(f"select_design_patterns failed: {exc}")
            raise ToolError(str(exc)) from exc
        except ToolError:
            raise
        except Exception as exc:
            logger.error("Unexpected error in select_design_patterns", extra={"details": str(exc)})
            if ctx is not None:
                await ctx.error(f"Unexpected error: {exc}")
            raise ToolError(f"ERR_999: {exc}") from exc
        finally:
            stop_heartbeat(heartbeat)


def select_design_patterns_tool(
    pipeline: DesignPipeline, tasks_config: TasksConfig | None = None
) -> SelectDesignPatternsTool:
    """Factory: create the ``SelectDesignPatternsTool`` instance (DP-4)."""
    return SelectDesignPatternsTool(pipeline=pipeline, tasks_config=tasks_config)
