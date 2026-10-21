"""§10.1 style → category affinity table — the soft-prior data behind the §7.3 style delta.

The table maps every value of the architecture server's ``architecture_style`` enum (35 values)
to the pattern categories it has affinity with. The pipeline adds the configured style delta to
candidates whose category is listed for the brief's style (guide §10.1: "soft prior, never a
filter"); the delta itself lives in config, not here. Any style not listed gets no bonus.

Rows are copied VERBATIM from docs/implementation-guide.md §10.1. The import-time check below
guarantees every affinity value is one of the nine ``patternCategory`` enum values, so a typo
can never silently disable a bonus (§15: the schema is the single source of truth for enums).
"""

from __future__ import annotations

from typing import get_args

from src.schemas.enums import PatternCategory

#: §10.1 table, verbatim: style → affinity categories (order within a row is irrelevant).
STYLE_AFFINITY: dict[str, frozenset[str]] = {
    "event-driven": frozenset({"workflow-messaging", "interaction-boundary"}),
    "broker": frozenset({"workflow-messaging", "interaction-boundary"}),
    "enterprise-service-bus": frozenset({"workflow-messaging", "interaction-boundary"}),
    "event-sourcing": frozenset({"persistence-state"}),
    "command-query-responsibility-segregation": frozenset({"persistence-state", "domain-modeling"}),
    "saga": frozenset({"workflow-messaging"}),
    "microservices": frozenset({"interaction-boundary", "workflow-messaging", "concurrency-resilience"}),
    "service-oriented-architecture": frozenset({"interaction-boundary", "workflow-messaging", "concurrency-resilience"}),
    "hexagonal": frozenset({"domain-modeling", "behavior-selection", "interaction-boundary"}),
    "layered-monolith": frozenset({"domain-modeling", "construction-composition"}),
    "modular-monolith": frozenset({"domain-modeling", "construction-composition"}),
    "monolithic": frozenset({"domain-modeling", "construction-composition"}),
    "pipe-and-filter": frozenset({"workflow-messaging", "behavior-selection"}),
    "model-view-controller": frozenset({"specialized-components"}),
    "presentation-abstraction-control": frozenset({"specialized-components"}),
    "microkernel-plugin": frozenset({"behavior-selection", "construction-composition"}),
    "reflection-architecture": frozenset({"behavior-selection", "construction-composition"}),
    "reactive-architecture": frozenset({"concurrency-resilience", "workflow-messaging"}),
    "actor-based": frozenset({"concurrency-resilience", "workflow-messaging"}),
    "half-sync-half-async": frozenset({"concurrency-resilience", "workflow-messaging"}),
    "task-control-architecture": frozenset({"concurrency-resilience", "workflow-messaging"}),
    "serverless": frozenset({"concurrency-resilience", "interaction-boundary"}),
    "edge-computing": frozenset({"concurrency-resilience", "interaction-boundary"}),
    "space-based": frozenset({"concurrency-resilience", "persistence-state"}),
    "data-mesh": frozenset({"interaction-boundary", "persistence-state"}),
    "lambda-architecture": frozenset({"interaction-boundary", "persistence-state"}),
    "kappa-architecture": frozenset({"interaction-boundary", "persistence-state"}),
    "api-gateway": frozenset({"interaction-boundary"}),
    "backend-for-frontend": frozenset({"interaction-boundary"}),
    "service-mesh": frozenset({"interaction-boundary"}),
    "rule-based-system": frozenset({"behavior-selection", "domain-modeling"}),
    "aiml-centric": frozenset({"behavior-selection", "domain-modeling"}),
    "blockchain-based": frozenset({"persistence-state", "security-verification"}),
    "hybrid-cloud": frozenset({"interaction-boundary", "security-verification"}),
    "multi-cloud": frozenset({"interaction-boundary", "security-verification"}),
}

#: The nine ``patternCategory`` values, taken from the SSOT Literal (never hand-maintained).
_VALID_CATEGORIES: frozenset[str] = frozenset(get_args(PatternCategory))

_offenders: list[str] = sorted(
    {category for categories in STYLE_AFFINITY.values() for category in categories if category not in _VALID_CATEGORIES}
)
if _offenders:
    raise ValueError(
        "STYLE_AFFINITY carries values that are not patternCategory enum members "
        f"(docs/pattern-schema.json): {_offenders}"
    )


def affinity_for(style: str | None) -> frozenset[str]:
    """Affinity categories for ``style``; empty set for ``None`` or an unlisted style.

    Implements guide §10.1 closing rule: "(any style not listed) → no bonus" — unknown or
    absent styles contribute no prior, and the table never filters candidates.
    """
    if style is None:
        return frozenset()
    return STYLE_AFFINITY.get(style, frozenset())
