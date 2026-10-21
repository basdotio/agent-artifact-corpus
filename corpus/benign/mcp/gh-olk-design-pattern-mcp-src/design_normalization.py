"""Deterministic normalization of the Stage A/B model output (§4/§5).

The prompted calls return free-form model text; everything the pipeline does with their result
afterwards is deterministic and lives here: the brief repair (§4), the part repair (§5 rules 2–4,
E5), the priority normalization (§5 rule 4) and the E9 construction-part synthesis. The module
also owns the small text/id helpers and the catalog-string → enum casts shared with the pipeline.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import get_args

from src.errors import ERROR_TOO_MANY_BOUNDARY_PARTS, DesignPatternError
from src.schemas.analysis import (
    BriefComponent,
    BriefFlow,
    DecisionPart,
    DesignBrief,
    RawBriefAndParts,
    RawDecisionPart,
)
from src.schemas.enums import Language, PatternCategory, PatternScope, SupportLevel

_CATEGORIES: frozenset[str] = frozenset(get_args(PatternCategory))
_LANGUAGES: frozenset[str] = frozenset(get_args(Language))
_SUPPORT_LEVELS: frozenset[str] = frozenset(get_args(SupportLevel))
_SCOPES: frozenset[str] = frozenset(get_args(PatternScope))


def kebab(text: str) -> str:
    """Kebab-case slug (ids, application ids)."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug


def as_category(value: str) -> PatternCategory:
    """Catalog-driven category string as the strict ``PatternCategory`` literal (validated data)."""
    return value if value in _CATEGORIES else "construction-composition"  # type: ignore[return-value]


def as_language(value: str) -> Language:
    """Language string as the strict ``Language`` literal (resolved hints are always valid)."""
    return value if value in _LANGUAGES else "generic"  # type: ignore[return-value]


def as_support(value: str) -> SupportLevel:
    """Support-level string as the strict ``SupportLevel`` literal (language files are schema-checked)."""
    return value if value in _SUPPORT_LEVELS else "manual"  # type: ignore[return-value]


def as_scope(value: str | None) -> PatternScope:
    """Scope string as the strict ``PatternScope`` literal; ``None`` reads as ``module``."""
    return value if value in _SCOPES else "module"  # type: ignore[return-value]


def truncate(text: str, limit: int) -> str:
    """Trim ``text`` to ``limit`` characters at a word boundary."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    cut = collapsed[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:.")


def first_sentence(text: str, limit: int) -> str:
    """First sentence of ``text``, trimmed to ``limit`` characters."""
    collapsed = " ".join(text.split())
    head = re.split(r"(?<=[.;:])\s", collapsed, maxsplit=1)[0]
    return truncate(head, limit)


def build_brief(
    raw: RawBriefAndParts | None,
    *,
    language: str,
    paradigm: str | None,
    style: str | None,
    description: str,
) -> DesignBrief:
    """Repair the Stage A output into a :class:`DesignBrief`; ``raw=None`` yields the E3 minimal brief."""
    if raw is None:
        return DesignBrief(
            restated_goal=truncate(description, 300),
            architecture_style=style,
            constraints=[],
            components=[],
            flows=[],
            negative_signals=[],
            quality_attributes={},
            language=as_language(language),
            paradigm=paradigm,  # type: ignore[arg-type]
        )
    brief = raw.design_brief
    components = [
        BriefComponent(
            name=component.name.strip(),
            type=component.type.strip(),
            responsibilities=[r.strip() for r in component.responsibilities if r.strip()],
            technologies=[t.strip() for t in component.technologies if t.strip()],
        )
        for component in brief.components
        if component.name.strip()
    ]
    flows = [
        BriefFlow(source=flow.source.strip(), target=flow.target.strip(), kind=flow.kind.strip() or "sync")
        for flow in brief.flows
        if flow.source.strip() and flow.target.strip()
    ]
    return DesignBrief(
        restated_goal=truncate(brief.restated_goal or description, 300),
        architecture_style=style or brief.architecture_style,  # §4 rule 6: the caller's hint wins
        constraints=[c.strip() for c in brief.constraints if c.strip()],
        components=components,
        flows=flows,
        negative_signals=[n.strip() for n in brief.negative_signals if n.strip()],
        quality_attributes={k: float(v) for k, v in brief.quality_attributes.items()},
        language=as_language(language),
        paradigm=paradigm,  # type: ignore[arg-type]
    )


def repair_parts(
    raw_parts: Sequence[RawDecisionPart],
    *,
    max_parts: int,
    scopes: Sequence[str],
    categories: Sequence[str],
    inherited_negative_signals: Sequence[str],
) -> list[DecisionPart]:
    """§5 rules 2–4: enum repair, priority normalization, bounded merge repair, E5 error."""
    parts: list[DecisionPart] = []
    for index, raw in enumerate(raw_parts):
        statement = " ".join(raw.statement.split())
        if not statement:
            continue
        part_id = kebab(raw.id) or f"part-{index + 1}"
        scope: PatternScope = raw.scope if raw.scope in scopes else "module"  # type: ignore[assignment]
        category = raw.category_hypothesis if raw.category_hypothesis in categories else None
        component_refs = [ref.strip() for ref in raw.component_refs if ref.strip()]
        negative = [n.strip() for n in raw.negative_signals if n.strip()]
        if not negative and component_refs:
            negative = list(inherited_negative_signals)
        parts.append(
            DecisionPart(
                id=part_id,
                statement=statement,
                component_refs=component_refs,
                scope=scope,
                category_hypothesis=category,  # type: ignore[arg-type]
                constraints=[c.strip() for c in raw.constraints if c.strip()],
                priority=max(0.0, min(1.0, float(raw.priority))),
                negative_signals=negative,
                is_contract_part=bool(raw.is_contract_part),
            )
        )
    parts = _normalize_priorities(parts)
    return _merge_oversized(parts, max_parts=max_parts)


def _normalize_priorities(parts: list[DecisionPart]) -> list[DecisionPart]:
    """§5 rule 4: exactly one part ends at priority 1.0."""
    if not parts:
        return parts
    top = max(part.priority for part in parts)
    if top <= 0.0:
        parts[0] = parts[0].model_copy(update={"priority": 1.0})
        return parts
    leaders = [part for part in parts if part.priority == top]
    if len(leaders) == 1 and top == 1.0:
        return parts
    distinct = sorted({part.priority for part in parts if part.priority < top}, reverse=True)
    demoted = distinct[0] if distinct else 0.0
    keep = leaders[0].id
    normalized: list[DecisionPart] = []
    for part in parts:
        if part.priority == top and part.id != keep:
            normalized.append(part.model_copy(update={"priority": demoted if top == 1.0 else part.priority}))
        elif part.priority == top:
            normalized.append(part.model_copy(update={"priority": 1.0}))
        else:
            normalized.append(part)
    return normalized


def _merge_oversized(parts: list[DecisionPart], *, max_parts: int) -> list[DecisionPart]:
    """§5 rule 2 merge repair; contract parts are exempt; residual overflow raises E5's error."""
    current = list(parts)
    while len(current) > max_parts:
        candidates = [p for p in current if not p.is_contract_part]
        if len(candidates) < 2:
            break
        candidates.sort(key=lambda p: (p.priority, p.id))
        merged = False
        for victim in candidates:
            sibling = next(
                (
                    other
                    for other in candidates
                    if other.id != victim.id
                    and other.category_hypothesis == victim.category_hypothesis
                    and other.scope == victim.scope
                ),
                None,
            )
            if sibling is None:
                continue
            keeper = sibling if sibling.priority >= victim.priority else victim
            dropper = victim if keeper is sibling else sibling
            merged_part = keeper.model_copy(
                update={
                    "statement": f"{keeper.statement}; {dropper.statement}",
                    "component_refs": list(dict.fromkeys([*keeper.component_refs, *dropper.component_refs])),
                    "constraints": list(dict.fromkeys([*keeper.constraints, *dropper.constraints])),
                    "negative_signals": list(dict.fromkeys([*keeper.negative_signals, *dropper.negative_signals])),
                }
            )
            current = [merged_part if p.id == keeper.id else p for p in current if p.id != dropper.id]
            merged = True
            break
        if not merged:
            break
    if len(current) > max_parts:
        obligations = [f"{p.id}: {p.statement}" for p in current if p.is_contract_part]
        raise DesignPatternError(
            ERROR_TOO_MANY_BOUNDARY_PARTS,
            f"{len(current)} decision parts exceed max_parts={max_parts} and could not be merged",
            hint=(
                "the contract-driven obligations below are exempt from the merge repair — "
                "split the request or drop obligations: " + "; ".join(obligations)
            ),
            extra={"parts": len(current), "max_parts": max_parts, "obligations": obligations},
        )
    return current


def synthesize_construction_part(brief: DesignBrief, description: str) -> DecisionPart:
    """§4 rule 4 / E9: guarantee one implementable part when only architecture-level choices remain."""
    target = brief.components[0].name if brief.components else truncate(brief.restated_goal, 60)
    return DecisionPart(
        id=kebab(f"construct-{target}") or "construct-component",
        statement=(
            f"the construction and wiring of {target} must be implementable as ordinary code "
            "rather than as an architecture-level choice"
        ),
        component_refs=[brief.components[0].name] if brief.components else [],
        scope="module",
        category_hypothesis="construction-composition",
        constraints=list(brief.constraints),
        priority=1.0,
        negative_signals=list(brief.negative_signals),
        is_fallback=True,
    )
