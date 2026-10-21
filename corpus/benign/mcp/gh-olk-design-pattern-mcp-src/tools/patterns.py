"""MCP tools ``list_design_patterns`` and ``get_design_pattern``: direct catalog access.

Read-only, low-latency alternatives to the ``design-patterns://variants`` resource for clients
that struggle with custom URI schemes. Both tools load from the already-joined catalog
(:class:`~src.patterns.loader.PatternLoader`); failures surface as ``ERR_013``.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, get_args

from fastmcp.exceptions import ToolError
from fastmcp.tools import tool
from mcp.types import ToolAnnotations
from pydantic import Field

from src.design_normalization import as_category, as_language, as_scope, as_support, truncate
from src.errors import ERROR_PATTERN_CATALOG
from src.patterns.loader import JoinedPattern, PatternLoader
from src.schemas.enums import Language, Paradigm, PatternCategory, Provenance
from src.schemas.patterns import PatternParticipantRole, PatternRecord
from src.schemas.variants import LanguageBinding
from src.variants import variant_summaries

logger = logging.getLogger(__name__)

_VALID_CATEGORIES: tuple[str, ...] = get_args(PatternCategory)
_VALID_LANGUAGES: tuple[str, ...] = get_args(Language)
_PARADIGMS: frozenset[str] = frozenset(get_args(Paradigm))
_PROVENANCES: frozenset[str] = frozenset(get_args(Provenance))


def _language_binding(record: JoinedPattern, language: str) -> LanguageBinding:
    """The record's joined language entry as its ``LanguageBinding`` view (§8.4 data half)."""
    entry = record.language_implementations[language]
    return LanguageBinding(
        language=as_language(entry.language),
        support=as_support(entry.support),
        idiom_name=entry.idiom_name,
        implementation_notes=entry.implementation_notes,
        code_sketch=entry.code_sketch,
        alternative=entry.alternative,
        bound_variant=entry.default_variant,
        variants=variant_summaries(entry, entry.default_variant),
    )


def pattern_record(record: JoinedPattern) -> dict[str, Any]:
    """The full catalog record as the ``PatternRecord`` wire dict (V8 join included)."""
    model = PatternRecord(
        name=record.name,
        category=as_category(record.category),
        scope=as_scope(record.scope),
        intent=record.intent,
        problem=record.problem,
        context=record.context,
        aliases=list(record.aliases),
        benefits=list(record.benefits),
        tradeoffs=list(record.tradeoffs),
        quality_attributes=dict(record.quality_attributes),
        participants=[
            PatternParticipantRole(role=role, responsibility=responsibility)
            for role, responsibility in record.participants
        ],
        suitable_scopes=list(record.suitable_scopes),
        unsuitable_scopes=list(record.unsuitable_scopes),
        use_cases=list(record.use_cases),
        avoid_when=list(record.avoid_when),
        related_patterns=list(record.related_patterns),
        related_patterns_notes=dict(record.related_patterns_notes),
        anti_patterns=list(record.anti_patterns),
        migration_from=list(record.migration_from),
        migration_to=list(record.migration_to),
        design_principles=list(record.design_principles),
        best_practices=list(record.best_practices),
        pitfalls=list(record.pitfalls),
        sources=list(record.sources),
        paradigms=[p for p in record.paradigms if p in _PARADIGMS],  # type: ignore[misc]
        provenance=[p for p in record.provenance if p in _PROVENANCES],  # type: ignore[misc]
        version=record.version,
        languages={
            as_language(language): _language_binding(record, language)
            for language in record.language_implementations
        },
    )
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


class ListDesignPatternsTool:
    """MCP tool listing the design patterns known to the server (name, category, description)."""

    def __init__(self, pattern_loader: PatternLoader) -> None:
        self._loader = pattern_loader
        logger.debug("ListDesignPatternsTool initialized")

    @tool(
        name="list_design_patterns",
        description=(
            "List all design patterns known to the server. Returns a minimal view with 'name', "
            "'category' and 'description' for each pattern. Optional filters: 'category' (one of: "
            + ", ".join(_VALID_CATEGORIES)
            + ") and 'language' (one of: "
            + ", ".join(_VALID_LANGUAGES)
            + "; keeps patterns with a joined implementation for that language)."
        ),
        tags={"design-patterns", "patterns", "read"},
        annotations=ToolAnnotations(
            title="List Design Patterns",
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def list_patterns(
        self,
        category: Annotated[
            str | None,
            Field(
                description=(
                    "Optional category filter. Valid values: "
                    + ", ".join(_VALID_CATEGORIES)
                    + ". Unknown values return an empty list."
                )
            ),
        ] = None,
        language: Annotated[
            str | None,
            Field(description="Optional language filter: keeps patterns with an implementation entry."),
        ] = None,
        _ctx: Any = None,
    ) -> list[dict[str, str]]:
        """List the catalog's patterns, optionally filtered by category and/or language."""
        try:
            category_lc = category.lower().strip() if category else None
            if category_lc and category_lc not in _VALID_CATEGORIES:
                return []
            language_lc = language.lower().strip() if language else None
            if language_lc and language_lc not in _VALID_LANGUAGES:
                return []
            entries: list[dict[str, str]] = []
            for name, record in self._loader.records.items():
                if category_lc and record.category != category_lc:
                    continue
                if language_lc and record.entry(language_lc) is None:
                    continue
                entries.append(
                    {
                        "name": name,
                        "category": record.category,
                        "description": truncate(record.intent or record.problem, 120),
                    }
                )
            return entries
        except Exception as exc:  # noqa: BLE001 — catalog access failure is a tool-boundary error
            raise ToolError(f"{ERROR_PATTERN_CATALOG}: Failed to list the pattern catalog: {exc}") from exc


class GetDesignPatternTool:
    """MCP tool retrieving the full JSON of one design pattern (alias names resolve)."""

    def __init__(self, pattern_loader: PatternLoader) -> None:
        self._loader = pattern_loader
        logger.debug("GetDesignPatternTool initialized")

    @tool(
        name="get_design_pattern",
        description=(
            "Get the full JSON of a single design pattern by its name or a resolved alias "
            "(e.g. 'singleton', 'borg'). Returns the complete record: intent, problem, context, "
            "benefits, tradeoffs, quality_attributes, participants, use cases, related patterns, "
            "principles, pitfalls, sources, and the joined per-language implementations with their "
            "variants. Raises ERR_013 when the pattern is unknown."
        ),
        tags={"design-patterns", "patterns", "read"},
        annotations=ToolAnnotations(
            title="Get Design Pattern",
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def get_pattern(
        self,
        name: Annotated[str, Field(description="Pattern name or alias, e.g. 'singleton', 'borg'")],
        _ctx: Any = None,
    ) -> dict[str, Any]:
        """Retrieve the full record of one pattern; ``ERR_013`` for unknown names."""
        try:
            canonical = self._loader.resolve(name.strip().lower())
            if canonical is None:
                raise ToolError(f"{ERROR_PATTERN_CATALOG}: unknown design pattern {name!r}")
            record = self._loader.get_by_name(canonical)
            if record is None:  # pragma: no cover — resolve() only returns loaded names
                raise ToolError(f"{ERROR_PATTERN_CATALOG}: unknown design pattern {name!r}")
            return pattern_record(record)
        except ToolError:
            raise
        except Exception as exc:  # noqa: BLE001 — catalog access failure is a tool-boundary error
            raise ToolError(f"{ERROR_PATTERN_CATALOG}: Failed to load the pattern: {exc}") from exc


def list_design_patterns_tool(pattern_loader: PatternLoader) -> ListDesignPatternsTool:
    """Factory: create the ``ListDesignPatternsTool`` instance (DP-4)."""
    return ListDesignPatternsTool(pattern_loader=pattern_loader)


def get_design_pattern_tool(pattern_loader: PatternLoader) -> GetDesignPatternTool:
    """Factory: create the ``GetDesignPatternTool`` instance (DP-4)."""
    return GetDesignPatternTool(pattern_loader=pattern_loader)
