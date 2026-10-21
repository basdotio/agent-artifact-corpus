"""DesignPipeline — stages A–H of docs/implementation-guide.md.

Everything a model does not have to do lives here: input validation and hint resolution (§1.3),
brief/part repair (§5), the anti-scope guard (§5 rule 5, E9), scoring (§7), ranking, thresholds and
supporting rules (§8), composition (§9), the deterministic part of variant binding (§8.4), and the
bounded generate/evaluate loop with best-attempt retention and the one-shot reselection rule (§11).

The four prompted LLM call kinds arrive through :class:`src.agent.LLMClientProtocol` and the retrieval
legs through :class:`src.patterns.retriever.RetrievalIndex`; both are constructor-injected, so the
deterministic core is testable without a model or a network.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Collection, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast

from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    WorkflowTimeoutError,
    step,
)

from src.anti_scope import AntiScopeGuard
from src.patterns.loader import (
    CATALOG_DOC_FILE,
    PatternLoader,
    JoinedPattern,
    parse_locally_implementable_names,
    parse_out_of_scope_terms,
)
from src.conflicts import conflicting
from src.config import ServerConfig
from src.design_normalization import (
    as_category,
    as_language,
    as_support,
    build_brief,
    first_sentence,
    kebab,
    repair_parts,
    synthesize_construction_part,
    truncate,
)
from src.errors import (
    ERROR_CANCELLED,
    ERROR_DESCRIPTION_TOO_SHORT,
    ERROR_GENERATION_FAILED,
    ERROR_LLM_PROVIDER,
    ERROR_NO_PRIMARY_PATTERN,
    DesignPatternError,
    LLMError,
)
from src.agent import DesignHints, LLMClientProtocol
from src.patterns.retriever import PartQuery, RetrievalHit, RetrievalIndex
from src.reasoning.prompts import render_degraded_context, render_reasoning_context
from src.schemas.analysis import (
    DecisionPart,
    DesignBrief,
    RawBriefAndParts,
    RequirementWeights,
)
from src.schemas.design import (
    ApplicationInteraction,
    DesignOverview,
    DesignResult,
    Interaction,
    Participant,
    PatternApplication,
    Risk,
    SupportingPattern,
    TestStrategy,
)
from src.schemas.evaluation import DesignEvaluation, PipelineResult
from src.schemas.enums import (
    FALLBACK_PRIMARY,
    QUALITY_AXES,
)
from src.schemas.generation import (
    ApplicationSeed,
    CatalogSlice,
    GenerationSeed,
    InteractionSeed,
    ParticipantSpec,
    RawApplication,
    RawGeneration,
)
from src.schemas.selection import (
    Adjustment,
    AnalysisResult,
    AnnotatedCandidate,
    PartSelection,
    SupportingChoice,
)
from src.schemas.quality import QualityMetrics
from src.schemas.variants import LanguageBinding
from src.style_affinity import affinity_for
from src.variants import bind_entry, select_variant, variant_summaries

if TYPE_CHECKING:  # pragma: no cover - type-only import (reasoning.client pulls fastmcp)
    from src.reasoning.client import ReasoningClient

logger = logging.getLogger(__name__)

#: Payload type parameter of :meth:`PipelineDone.payload_as`.
_PayloadT = TypeVar("_PayloadT")

MIN_DESCRIPTION_LENGTH = 40
MAX_APPLICATION_NAME = 100
_SUPPORTING_ROLE_MAX = 120

#: Standard/toolchain tokens the §8.4 capability floor understands (guide §1.2 `focus`/§8.4 layer 3).
_TECHNOLOGY_PATTERN = re.compile(
    r"\b(?:"
    r"C\+\+\s?\d{2}|C#\s?\d{1,2}|ES\d{4}|ECMAScript\s?\d{4}|C\d{2}|Rust\s?20\d{2}|"
    r"Java\s?\d{1,2}|Python\s?\d\.\d{1,2}|Kotlin\s?\d\.\d{1,2}|Swift\s?\d(?:\.\d)?|"
    r"Go\s?\d\.\d{1,2}|NET\s?\d{1,2}"
    r")\b",
    re.IGNORECASE,
)


class CancellationToken:
    """Cooperative cancellation flag checked between pipeline stages (§3, §15, E11)."""

    def __init__(self) -> None:
        self._event = asyncio.Event()

    def cancel(self) -> None:
        """Request cancellation."""
        self._event.set()

    def cancelled(self) -> bool:
        """True once cancellation was requested."""
        return self._event.is_set()


# --------------------------------------------------------------------------------------
# Workflow event vocabulary (llama-index Workflow realization of stages A-H)
# --------------------------------------------------------------------------------------


class DesignStart(StartEvent):
    """The single start event; ``mode`` discriminates the five public entry points.

    ``cancellation`` rides by reference (E11: events stay in-process) and is
    moved into the run-scoped store by the ``route`` step. Mid-graph entry
    payloads (``analysis``/``result``/``parts``) are set only by the
    ``generate``/``evaluate``/``design_loop`` modes.
    """

    mode: str
    description: str = ""
    architecture_style: str | None = None
    language: str | None = None
    paradigm: str | None = None
    focus: str | None = None
    cancellation: CancellationToken | None = None
    analysis: AnalysisResult | None = None
    result: DesignResult | None = None
    parts: list[DecisionPart] | None = None


class AnalysisReady(Event):
    """Stage A may start (full-pipeline and analyze-only modes)."""

    mode: str
    description: str = ""
    architecture_style: str | None = None
    language: str | None = None
    paradigm: str | None = None
    focus: str | None = None
    cancellation: CancellationToken | None = None


class SelectionReady(Event):
    """A GENERATE attempt may start (fresh analysis or a reselection round)."""

    analysis: AnalysisResult
    attempt: int = 1


class Generated(Event):
    """One GENERATE attempt produced a design result."""

    analysis: AnalysisResult
    result: DesignResult
    attempt: int = 1


class Evaluated(Event):
    """One attempt was scored; the refine step decides continue vs. stop."""

    analysis: AnalysisResult
    result: DesignResult
    evaluation: DesignEvaluation
    attempt: int = 1


class AttemptFailed(Event):
    """A GENERATE attempt raised ``DesignPatternError`` — the loop continues (E12)."""

    analysis: AnalysisResult
    error_detail: str
    failure_kind: str | None
    attempt: int = 1


class GenerateEntry(Event):
    """Mid-graph entry for the ``generate`` mode: exactly one GENERATE call."""

    analysis: AnalysisResult


class EvaluateEntry(Event):
    """Mid-graph entry for the ``evaluate`` mode: score a foreign result."""

    result: DesignResult
    parts: list[DecisionPart]


class PipelineDone(StopEvent):
    """Single terminal event of the pipeline graph (§15 Workflow realization).

    The llama-index Workflow runtime enforces *exactly one* StopEvent subclass
    per workflow at construction time (``workflows.representation.validate.
    _ensure_stop_event_class``); the pipeline's five modes therefore share this
    event and tag the payload with the originating mode. ``await handler``
    returns the ``PipelineDone`` instance itself (the runtime only unwraps the
    payload for the exact base ``StopEvent`` class), and the typed accessors
    below restore the per-mode payload types.
    """

    def __init__(
        self,
        result: AnalysisResult | DesignResult | DesignEvaluation | PipelineResult,
        *,
        mode: str,
    ) -> None:
        super().__init__(result=result)
        self._mode = mode

    @property
    def mode(self) -> str:
        """The pipeline mode that produced this terminal event."""
        return self._mode

    def payload_as(self, payload_type: type[_PayloadT]) -> _PayloadT:
        """Return the carried payload, asserting its type for the caller's mode."""
        payload = self._get_result()
        assert isinstance(payload, payload_type), (
            f"PipelineDone(mode={self._mode!r}) carries "
            f"{type(payload).__name__}, expected {payload_type.__name__}"
        )
        return payload


@dataclass
class _RunState:
    """Mutable per-run state shared by the steps through ``ctx.store`` (by reference)."""

    cancellation: CancellationToken | None = None
    mode: str = ""
    entry_analysis: AnalysisResult | None = None
    entry_result: DesignResult | None = None
    entry_parts: list[DecisionPart] = field(default_factory=list)
    attempt: int = 0
    best: DesignResult | None = None
    best_evaluation: DesignEvaluation | None = None
    best_score: float = -1.0
    best_attempt: int = 0
    attempts_log: list[dict[str, Any]] = field(default_factory=list)
    last_error: DesignPatternError | None = None
    reselected: bool = False
    sticky: set[str] = field(default_factory=set)
    current_analysis: AnalysisResult | None = None
    current_selections: dict[str, PartSelection] | None = None


@dataclass
class ComposedSelection:
    """Deterministic Stage F output: what GENERATE must turn into applications (§9)."""

    dominant_part_id: str
    primary: str
    category: str
    applications: list[ApplicationSeed] = field(default_factory=list)
    supporting: list[SupportingPattern] = field(default_factory=list)
    interaction_seeds: list[InteractionSeed] = field(default_factory=list)
    alternatives_by_application: dict[str, list[str]] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class PipelineRun:
    """One pipeline invocation's inputs and resolved hints."""

    description: str
    hints: DesignHints
    style: str | None
    language: str
    paradigm: str | None


# --------------------------------------------------------------------------------------
# §1.3 — input validation and hint resolution
# --------------------------------------------------------------------------------------


def validate_description(description: str) -> str:
    """Return the stripped description, or raise for the E1/E2 intake failures (§1.3 rules 1–2)."""
    text = description.strip()
    if len(text) < MIN_DESCRIPTION_LENGTH:
        raise DesignPatternError(
            ERROR_DESCRIPTION_TOO_SHORT,
            f"description is {len(text)} characters; at least {MIN_DESCRIPTION_LENGTH} are required",
            hint=(
                "include the component names and responsibilities from the architecture result "
                "(and the constraints you want the design patterns to satisfy)"
            ),
        )
    return text


def resolve_language(submitted: str | None, languages: Sequence[str]) -> str:
    """§1.3 language resolution table: recognized → itself, unrecognized/absent/empty → ``generic``."""
    if submitted is None:
        return "generic"
    value = submitted.strip()
    if not value:
        return "generic"
    if value in languages:
        return value
    logger.warning("Unrecognized language hint ignored; running in generic mode", extra={"language": submitted})
    return "generic"


def resolve_paradigm(submitted: str | None, paradigms: Sequence[str]) -> str | None:
    """§1.3 rule 5 / E10: an off-enum paradigm hint is dropped (with a warning), never an error."""
    if submitted is None:
        return None
    value = submitted.strip()
    if not value:
        return None
    if value in paradigms:
        return value
    logger.warning("Unrecognized paradigm hint ignored", extra={"paradigm": submitted})
    return None


def resolve_style(submitted: str | None) -> str | None:
    """§1.3 rule 3 / E10: an off-enum architecture style is ignored (logged), never an error."""
    if submitted is None:
        return None
    value = submitted.strip()
    if not value:
        return None
    if value in _STYLE_ENUM:
        return value
    logger.info("Unknown architecture style hint ignored", extra={"architecture_style": submitted})
    return None


#: The architecture server's published style enum (§10.1 table keys; the affinity table is the SSOT).
_STYLE_ENUM: frozenset[str] = frozenset(
    {
        "event-driven", "broker", "enterprise-service-bus", "event-sourcing",
        "command-query-responsibility-segregation", "saga", "microservices",
        "service-oriented-architecture", "hexagonal", "layered-monolith", "modular-monolith",
        "monolithic", "pipe-and-filter", "model-view-controller", "presentation-abstraction-control",
        "microkernel-plugin", "reflection-architecture", "reactive-architecture", "actor-based",
        "half-sync-half-async", "task-control-architecture", "serverless", "edge-computing",
        "space-based", "data-mesh", "lambda-architecture", "kappa-architecture", "api-gateway",
        "backend-for-frontend", "service-mesh", "rule-based-system", "aiml-centric",
        "blockchain-based", "hybrid-cloud", "multi-cloud",
    }
)


def extract_technology_tokens(*texts: str) -> list[str]:
    """Standard/toolchain tokens of the description and component technologies (§8.4 layer 3)."""
    tokens: list[str] = []
    for text in texts:
        for match in _TECHNOLOGY_PATTERN.finditer(text):
            token = re.sub(r"\s+", " ", match.group(0).strip())
            if token.lower() not in {t.lower() for t in tokens}:
                tokens.append(token)
    return tokens


def _tokenize(text: str) -> frozenset[str]:
    """Lower-cased alphanumeric word tokens (used by the negative-signal veto and constraint evidence)."""
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


# --------------------------------------------------------------------------------------
# §7 — weights
# --------------------------------------------------------------------------------------


async def extract_part_weights_batch(
    llm: LLMClientProtocol,
    parts: Sequence[DecisionPart],
    brief: DesignBrief,
    *,
    config: ServerConfig,
    reasoning_context: str = "",
) -> dict[str, tuple[dict[str, float], str]]:
    """§7.1 weight extraction for all parts: ONE call, then deterministic per-part processing.

    Order of operations: one batched proposal → all-zero retry (E4) batched over exactly the
    parts that came back all-zero → max-normalization → architectural prior blend (0.7
    extracted / 0.3 prior, only when the part carries no priority evidence) → convex smoothing
    ``w' = α·w + (1−α)/8``. The tail is strictly per part, so batching cannot couple the ratings.

    Returns:
        ``{part_id: (processed_weights, weights_source)}`` for every supplied part.
    """
    if not parts:
        return {}
    proposals = await _safe_extract_weights_batch(llm, parts, brief, reasoning_context)
    zero_ids = [
        part.id
        for part in parts
        if max(proposals.get(part.id, RequirementWeights()).as_dict().values(), default=0.0) <= 0.0
    ]
    if zero_ids:
        retried = await _safe_extract_weights_batch(
            llm, [part for part in parts if part.id in set(zero_ids)], brief, reasoning_context
        )
        for part_id in zero_ids:
            retry = retried.get(part_id, RequirementWeights())
            if max(retry.as_dict().values(), default=0.0) > 0.0:
                proposals[part_id] = retry
    processed: dict[str, tuple[dict[str, float], str]] = {}
    for part in parts:
        raw = proposals.get(part.id, RequirementWeights()).as_dict()
        source = "llm"
        if max(raw.values(), default=0.0) <= 0.0:
            logger.warning(
                "Weight extraction returned all-zero twice; using the unweighted mean (E4)",
                extra={"part_id": part.id},
            )
            raw = dict.fromkeys(QUALITY_AXES, 0.125)
            source = "e4_mean"
        peak = max(raw.values(), default=0.0)
        if peak <= 0.2 and brief.quality_attributes:
            prior = _normalized_prior(brief.quality_attributes)
            if prior:
                raw = {
                    axis: 0.7 * raw.get(axis, 0.0) + 0.3 * prior.get(axis, raw.get(axis, 0.0))
                    for axis in QUALITY_AXES
                }
                source = "llm+architecture_prior"
        normalized = _max_normalize(raw)
        alpha = config.scoring.weight_smoothing_alpha
        smoothed = {axis: alpha * normalized.get(axis, 0.0) + (1.0 - alpha) / len(QUALITY_AXES) for axis in QUALITY_AXES}
        logger.info(
            "Part weights extracted",
            extra={
                "part_id": part.id,
                "weights_source": source,
                "peak": peak,
                "smoothed": {axis: round(value, 4) for axis, value in smoothed.items()},
            },
        )
        processed[part.id] = (smoothed, source)
    return processed


async def _safe_extract_weights_batch(
    llm: LLMClientProtocol,
    parts: Sequence[DecisionPart],
    brief: DesignBrief,
    reasoning_context: str = "",
) -> dict[str, RequirementWeights]:
    """The §7.1 weights call, treating a hard client failure as an all-zero proposal for the batch."""
    try:
        return await llm.extract_weights_batch(parts, brief, reasoning_context=reasoning_context)
    except DesignPatternError as exc:
        logger.warning(
            "Weight extraction call failed",
            extra={"part_ids": [part.id for part in parts], "error": exc.detail},
        )
        return {}


def _normalized_prior(quality_attributes: dict[str, float]) -> dict[str, float]:
    """Max-normalized architecture quality attributes projected onto the eight scoring axes."""
    relevant = {axis: quality_attributes[axis] for axis in QUALITY_AXES if axis in quality_attributes}
    if not relevant:
        return {}
    peak = max(relevant.values())
    if peak <= 0.0:
        return {}
    return {axis: value / peak for axis, value in relevant.items()}


def _max_normalize(weights: dict[str, float]) -> dict[str, float]:
    """§7.1: normalize so the maximum weight is 1.0 (ties may all reach 1.0)."""
    peak = max(weights.values(), default=0.0)
    if peak <= 0.0:
        return dict.fromkeys(QUALITY_AXES, 0.0)
    return {axis: weights.get(axis, 0.0) / peak for axis in QUALITY_AXES}


# --------------------------------------------------------------------------------------
# §6 step 5 / §7.2 / §7.3 — vetoes and scoring
# --------------------------------------------------------------------------------------


def apply_vetoes(
    hits: Sequence[Any],
    *,
    record_of: dict[str, JoinedPattern],
    part: DecisionPart,
    language: str,
    negative_signals: Sequence[str],
) -> tuple[list[Any], list[str], int]:
    """§6 step 5 deterministic pre-filters. Returns (survivors, veto ledger, vetoed count)."""
    signal_tokens = _tokenize(" ".join(negative_signals))
    survivors: list[Any] = []
    ledger: list[str] = []
    vetoed = 0
    for hit in hits:
        record = record_of[hit.name]
        if part.scope in record.unsuitable_scopes:
            vetoed += 1
            logger.info("Scope veto", extra={"part_id": part.id, "pattern": record.name, "scope": part.scope})
            continue
        if signal_tokens and (record.name_tokens & signal_tokens):
            overlap = sorted(record.name_tokens & signal_tokens)
            vetoed += 1
            logger.info(
                "Negative-signal veto",
                extra={"part_id": part.id, "pattern": record.name, "signals": overlap},
            )
            continue
        entry = record.entry(language)
        if entry is not None and entry.support == "discouraged":
            alternative = entry.alternative or "a supported alternative"
            ledger.append(
                f"{record.name} considered but discouraged in {entry.language}; use {alternative}"
            )
            vetoed += 1
            logger.info(
                "Language discouragement veto",
                extra={"part_id": part.id, "pattern": record.name, "language": entry.language},
            )
            continue
        survivors.append(hit)
    return survivors, ledger, vetoed


def _fusion_scores(hits: Sequence[Any]) -> dict[str, float]:
    """§7.2 min–max normalization of the retrieval blend across the part's candidate pool."""
    if not hits:
        return {}
    scores = [hit.retrieval_score for hit in hits]
    low = min(scores)
    high = max(scores)
    if high - low <= 1e-12:
        return {hit.name: 100.0 for hit in hits}
    return {hit.name: (hit.retrieval_score - low) / (high - low) * 100.0 for hit in hits}


def score_candidates(
    hits: Sequence[Any],
    *,
    part: DecisionPart,
    brief: DesignBrief,
    weights: dict[str, float],
    record_of: dict[str, JoinedPattern],
    catalog: PatternLoader,
    config: ServerConfig,
) -> list[AnnotatedCandidate]:
    """§7.2 + §7.3: analysis score, blend, adjustment ledger, clamp; sorted by the §8.1 chain."""
    fusion = _fusion_scores(hits)
    affinity = affinity_for(brief.architecture_style)
    total_weight = sum(weights.get(axis, 0.0) for axis in QUALITY_AXES)
    annotated: list[AnnotatedCandidate] = []
    for rank, hit in enumerate(hits, start=1):
        record = record_of[hit.name]
        if total_weight > 0.0:
            weighted = sum(
                weights.get(axis, 0.0) * record.quality_attributes.get(axis, config.scoring.missing_axis_default)
                for axis in QUALITY_AXES
            )
            analysis = 10.0 * weighted / total_weight
        else:
            analysis = 10.0 * config.scoring.missing_axis_default
        fusion_normalized = fusion.get(record.name, 0.0)
        blended = (
            config.scoring.analysis_blend_weight * analysis
            + config.scoring.fusion_blend_weight * fusion_normalized
        )
        adjustments = _adjustments(
            record, part, brief, language=brief.language, affinity=affinity, config=config
        )
        fit = blended + sum(entry.delta for entry in adjustments)
        fit = max(0.0, min(100.0, fit))
        annotated.append(
            AnnotatedCandidate(
                name=record.name,
                category=record.category,  # type: ignore[arg-type]
                retrieval_score=hit.retrieval_score,
                analysis_score=analysis,
                fusion_score_normalized=fusion_normalized,
                blended=blended,
                fit_score=fit,
                adjustments=adjustments,
                fused_rank=getattr(hit, "fused_rank", rank),
                rerank_rank=getattr(hit, "rerank_rank", rank),
                catalog_order=catalog.order_index(record.name),
            )
        )
    annotated.sort(key=_ranking_key)
    for candidate in annotated:
        logger.info(
            "Candidate scored",
            extra={
                "part_id": part.id,
                "pattern": candidate.name,
                "retrieval_blend": round(candidate.retrieval_score, 6),
                "analysis_score": round(candidate.analysis_score, 4),
                "fusion_score_normalized": round(candidate.fusion_score_normalized, 4),
                "blended": round(candidate.blended, 4),
                "fit_score": round(candidate.fit_score, 4),
                "adjustments": [f"{a.label}{a.delta:+g}" for a in candidate.adjustments],
            },
        )
    return annotated


def _ranking_key(candidate: AnnotatedCandidate) -> tuple[float, float, float, int, str]:
    """§8.1 deterministic total order: fit → analysis → fusion_norm → catalog order → name."""
    return (
        -candidate.fit_score,
        -candidate.analysis_score,
        -candidate.fusion_score_normalized,
        candidate.catalog_order,
        candidate.name,
    )


def _adjustments(
    record: JoinedPattern,
    part: DecisionPart,
    brief: DesignBrief,
    *,
    language: str,
    affinity: frozenset[str],
    config: ServerConfig,
) -> list[Adjustment]:
    """§7.3 alignment adjustments (stacking allowed; the caller clamps the result)."""
    scoring = config.scoring
    ledger: list[Adjustment] = []
    if part.scope in record.suitable_scopes:
        ledger.append(Adjustment(label="scope_bonus", delta=scoring.scope_bonus))
    if part.category_hypothesis is not None:
        if record.category == part.category_hypothesis:
            ledger.append(Adjustment(label="category_match", delta=scoring.category_match))
        else:
            ledger.append(Adjustment(label="category_mismatch", delta=scoring.category_mismatch))
    if record.category in affinity:
        ledger.append(Adjustment(label="style_affinity", delta=scoring.style_affinity))
    if language != "generic":
        entry = record.entry(language)
        if entry is not None:
            if entry.support in ("native", "idiomatic", "library"):
                ledger.append(
                    Adjustment(label=f"language_support_{entry.support}", delta=scoring.language_support_bonus)
                )
            elif entry.support == "manual":
                ledger.append(Adjustment(label="language_support_manual", delta=scoring.language_manual_penalty))
    return ledger


# --------------------------------------------------------------------------------------
# §8 — selection thresholds, near-ties, supporting rules
# --------------------------------------------------------------------------------------


def select_for_part(
    *,
    part: DecisionPart,
    candidates: list[AnnotatedCandidate],
    record_of: dict[str, JoinedPattern],
    catalog: PatternLoader,
    brief: DesignBrief,
    config: ServerConfig,
    veto_ledger: Sequence[str],
    fallback_reason: str | None = None,
    weights: dict[str, float] | None = None,
    weights_source: str = "llm",
) -> PartSelection:
    """§8.1/§8.2/§8.3: dual gate, E7, near-tie flag, supporting set, alternatives seeds."""
    # Defensive: the §8.1 total order is a property of the selection boundary, so the pool is
    # re-sorted here even when the caller already sorted it (``score_candidates`` does).
    ordered_candidates = sorted(candidates, key=_ranking_key)
    selection = PartSelection(
        part=part,
        weights=weights or {},
        candidates=ordered_candidates,
        veto_ledger=list(veto_ledger),
        weights_source=weights_source,
    )
    if not ordered_candidates:
        return _fallback_selection(
            selection, "no candidate survived retrieval and the veto pre-filters (E5)", catalog
        )
    leader = ordered_candidates[0]
    gate = (
        leader.fit_score >= config.selection.primary_score_threshold
        and leader.analysis_score >= config.selection.primary_score_threshold
    )
    if not gate:
        reason = (
            f"top candidate {leader.name} failed the dual gate "
            f"(fit {leader.fit_score:.1f} < {config.selection.primary_score_threshold:g} or "
            f"analysis {leader.analysis_score:.1f} < {config.selection.primary_score_threshold:g}) (E6)"
        )
        return _fallback_selection(selection, reason, catalog)
    selection.primary = leader.name
    selection.primary_category = leader.category
    contenders = [
        candidate
        for candidate in ordered_candidates[1:]
        if leader.fit_score - candidate.fit_score <= config.selection.near_tie_margin
    ]
    if contenders:
        selection.ambiguous = True
        selection.near_tie = [leader.name, *(candidate.name for candidate in contenders)]
        logger.info(
            "Near-tie flagged (E8)",
            extra={
                "part_id": part.id,
                "leader": leader.name,
                "leader_fit": round(leader.fit_score, 4),
                "contenders": [
                    {"pattern": c.name, "fit_score": round(c.fit_score, 4), "delta": round(leader.fit_score - c.fit_score, 4)}
                    for c in contenders
                ],
            },
        )
    selection.supporting = _choose_supporting(
        leader=leader,
        candidates=ordered_candidates[1:],
        part=part,
        record_of=record_of,
        config=config,
    )
    selection.alternatives = _alternatives_seed(selection, leader, record_of)
    return selection


def _alternatives_seed(
    selection: PartSelection, leader: AnnotatedCandidate, record_of: dict[str, JoinedPattern]
) -> list[str]:
    """The runner-up/next-ranked seeds plus every veto-ledger entry (§11 item 1)."""
    seeds: list[str] = []
    for candidate in selection.candidates:
        if candidate.name == leader.name:
            continue
        if selection.ambiguous and candidate.name in selection.near_tie:
            delta = leader.fit_score - candidate.fit_score
            seeds.append(f"{candidate.name} (near-tie: fit {candidate.fit_score:.1f}, Δ{delta:.1f})")
        elif candidate.fit_score >= 0.0 and len(seeds) < 2:
            seeds.append(f"{candidate.name} (fit {candidate.fit_score:.1f})")
        if len(seeds) >= 2:
            break
    seeds.extend(selection.veto_ledger)
    return seeds


def _choose_supporting(
    *,
    leader: AnnotatedCandidate,
    candidates: Sequence[AnnotatedCandidate],
    part: DecisionPart,
    record_of: dict[str, JoinedPattern],
    config: ServerConfig,
) -> list[SupportingChoice]:
    """§8.3 supporting rules 1–5, applied in fit order and capped at ``max_supporting``."""
    primary = record_of[leader.name]
    constraint_tokens = [(constraint, _tokenize(constraint)) for constraint in part.constraints]
    chosen: list[SupportingChoice] = []
    same_subgroup: list[str] = []
    for candidate in sorted(candidates, key=_ranking_key):
        if candidate.fit_score < config.selection.supporting_score_threshold:
            continue
        record = record_of[candidate.name]
        if conflicting(primary.name, record.name):
            logger.info(
                "Supporting rejected: conflict table",
                extra={"part_id": part.id, "primary": primary.name, "candidate": record.name},
            )
            continue
        evidence_b: str | None = None
        for constraint, tokens in constraint_tokens:
            if _tokenize(record.name) & tokens or _tokenize(" ".join(record.aliases)) & tokens:
                evidence_b = constraint
                break
        evidence_a = (
            record.name in primary.related_patterns or primary.name in record.related_patterns
        ) and record.subgroup != primary.subgroup
        share_subgroup_with_primary = record.subgroup == primary.subgroup
        share_subgroup_with_chosen = record.subgroup in same_subgroup
        if evidence_b is not None:
            role = f"{truncate(evidence_b, _SUPPORTING_ROLE_MAX - len(part.id) - 4)} ({part.id})"
        elif evidence_a and not share_subgroup_with_primary and not share_subgroup_with_chosen:
            role = f"{first_sentence(record.problem, _SUPPORTING_ROLE_MAX - len(part.id) - 4)} ({part.id})"
        else:
            logger.info(
                "Supporting rejected: distinct-constraint rule",
                extra={
                    "part_id": part.id,
                    "primary": primary.name,
                    "candidate": record.name,
                    "related_edge": evidence_a,
                    "same_subgroup": share_subgroup_with_primary or share_subgroup_with_chosen,
                },
            )
            continue
        chosen.append(SupportingChoice(pattern=record.name, role=role, fit_score=candidate.fit_score))
        same_subgroup.append(record.subgroup)
        if len(chosen) >= config.selection.max_supporting:
            break
    return chosen


def _fallback_selection(
    selection: PartSelection, reason: str, catalog: PatternLoader
) -> PartSelection:
    """§10.3/E5/E6 fallback primary, or the E7 structured failure for ``specialized-components``."""
    category = selection.part.category_hypothesis
    top_three = [
        {
            "pattern": candidate.name,
            "fit_score": round(candidate.fit_score, 2),
            "analysis_score": round(candidate.analysis_score, 2),
        }
        for candidate in selection.candidates[:3]
    ]
    if category == "specialized-components":
        raise DesignPatternError(
            ERROR_NO_PRIMARY_PATTERN,
            f"part {selection.part.id!r} (specialized-components) has no universal fallback: {reason}",
            hint=(
                "name the concrete component type in the description (UI, loop, parser, protocol, "
                "resource) so a specialized pattern can be retrieved"
            ),
            extra={"part_id": selection.part.id, "candidates": top_three, "reason": reason},
        )
    fallback_name = FALLBACK_PRIMARY.get(category or "", "dependency-injection")
    fallback_record = catalog.get_by_name(fallback_name)
    selection.primary = fallback_name
    fallback_category = (
        fallback_record.category
        if fallback_record is not None
        else category or "construction-composition"
    )
    selection.primary_category = as_category(fallback_category)
    selection.is_fallback = True
    selection.fallback_reason = reason
    selection.fallback_candidates = top_three
    selection.supporting = []
    selection.ambiguous = False
    selection.near_tie = []
    logger.info(
        "Category fallback primary selected",
        extra={"part_id": selection.part.id, "fallback": fallback_name, "reason": reason},
    )
    return selection


def fallback_category(selection: PartSelection) -> str:
    """Category of the fallback primary, resolved from the catalog record or the part hypothesis."""
    category = selection.part.category_hypothesis or "construction-composition"
    return category


# --------------------------------------------------------------------------------------
# §8.4 — variant binding (deterministic half of GENERATE)
# --------------------------------------------------------------------------------------


def bind_language_entry(
    record: JoinedPattern,
    *,
    language: str,
    focus: str | None,
    paradigm: str | None,
    technology_tokens: Sequence[str],
) -> LanguageBinding:
    """§8.4: bind the effective language entry (else generic) and exactly one variant."""
    entry = bind_entry(record, language)
    variant = select_variant(
        entry, focus=focus, paradigm=paradigm, technology_tokens=list(technology_tokens)
    )
    if variant is None:
        return LanguageBinding(
            language=as_language(entry.language),
            support=as_support(entry.support),
            idiom_name=entry.idiom_name,
            implementation_notes=entry.implementation_notes,
            code_sketch=entry.code_sketch,
            alternative=None,
        )
    return LanguageBinding(
        language=as_language(entry.language),
        support=as_support(entry.support),
        idiom_name=variant.idiom_name or entry.idiom_name,
        implementation_notes=variant.implementation_notes,
        code_sketch=variant.code_sketch if variant.code_sketch is not None else entry.code_sketch,
        alternative=None,
        bound_variant=variant.variant_id,
        variants=variant_summaries(entry, variant.variant_id),
    )


def catalog_slice(
    record: JoinedPattern, binding: LanguageBinding, *, limit: int = 3
) -> CatalogSlice:
    """The per-application catalog context handed to GENERATE (§11 item 1)."""
    return CatalogSlice(
        pattern=record.name,
        category=as_category(record.category),
        intent=record.intent,
        problem=record.problem,
        context=record.context,
        benefits=list(record.benefits[:limit]),
        tradeoffs=list(record.tradeoffs[:limit]),
        participants=[ParticipantSpec(role=role, responsibility=responsibility) for role, responsibility in record.participants],
        avoid_when=list(record.avoid_when[:limit]),
        best_practices=list(record.best_practices[:limit]),
        test_notes=first_sentence(" ".join(record.benefits), 200),
        language_binding=binding,
    )


# --------------------------------------------------------------------------------------
# §9 — composition
# --------------------------------------------------------------------------------------


def compose_selection(
    *,
    selections: dict[str, PartSelection],
    brief: DesignBrief,
    catalog: PatternLoader,
    config: ServerConfig,
) -> ComposedSelection:
    """§9: dominant-part election, supporting union, application seeds, interaction seeds, trace."""
    ordered = list(selections.values())
    scored = [s for s in ordered if s.primary is not None]
    if not scored:
        raise DesignPatternError(
            ERROR_NO_PRIMARY_PATTERN,
            "no part produced a primary pattern",
            hint="every part failed selection without a fallback; check the description's components",
        )
    dominant = _elect_dominant(scored)
    dominant_record = catalog.get_by_name(dominant.primary or "")
    if dominant_record is None:
        raise DesignPatternError(
            ERROR_NO_PRIMARY_PATTERN,
            f"dominant primary {dominant.primary!r} does not resolve to a catalog record",
        )
    applications: list[ApplicationSeed] = []
    alternatives: dict[str, list[str]] = {}
    component_to_application: dict[str, str] = {}
    primary_application_of: dict[str, str] = {}
    for selection in ordered:
        if selection.primary is None:
            continue
        application = _application_seed(selection, selection.primary, role=None, is_primary=True)
        applications.append(application)
        primary_application_of.setdefault(selection.primary, application.id)
        alternatives[application.id] = list(selection.alternatives)
        _map_components(application, selection, component_to_application)
    for selection in ordered:
        for choice in selection.supporting:
            if choice.pattern in primary_application_of:
                continue
            application = _application_seed(selection, choice.pattern, role=choice.role, is_primary=False)
            if any(existing.id == application.id for existing in applications):
                continue
            applications.append(application)
            alternatives[application.id] = list(selection.alternatives)
            _map_components(application, selection, component_to_application)
    supporting = _supporting_union(scored, config)
    interactions = _interaction_seeds(brief, applications, component_to_application)
    composed = ComposedSelection(
        dominant_part_id=dominant.part.id,
        primary=dominant_record.name,
        category=dominant_record.category,
        applications=applications,
        supporting=supporting,
        interaction_seeds=interactions,
        alternatives_by_application=alternatives,
    )
    composed.reasoning = _reasoning(composed, ordered, catalog, config)
    logger.info(
        "Selection composed",
        extra={
            "dominant_part": composed.dominant_part_id,
            "primary_pattern": composed.primary,
            "applications": [application.id for application in applications],
            "supporting": [pattern.pattern for pattern in supporting],
            "interaction_seeds": len(interactions),
        },
    )
    return composed


def _elect_dominant(scored: Sequence[PartSelection]) -> PartSelection:
    """§9 rule 1: dominance = priority × fit/100; ties by fit, analysis, part order."""

    def key(selection: PartSelection) -> tuple[float, float, float]:
        fit = next(
            (c.fit_score for c in selection.candidates if c.name == selection.primary),
            0.0,
        )
        analysis = next(
            (c.analysis_score for c in selection.candidates if c.name == selection.primary),
            0.0,
        )
        dominance = selection.part.priority * (fit / 100.0)
        return (-dominance, -fit, -analysis)

    return sorted(scored, key=key)[0]


def _application_seed(
    selection: PartSelection, pattern: str, *, role: str | None, is_primary: bool
) -> ApplicationSeed:
    """§9 rule 3: one seed per selected (part, pattern) pair."""
    return ApplicationSeed(
        id=f"{selection.part.id}--{pattern}" if not is_primary else f"{selection.part.id}-{pattern}",
        pattern=pattern,
        category=as_category(str((selection.primary_category if is_primary else None) or _category_of(selection, pattern))),
        part_id=selection.part.id,
        part_statement=selection.part.statement,
        constraints=list(selection.part.constraints),
        component_refs=list(selection.part.component_refs),
        is_primary=is_primary,
        role=role,
    )


def _category_of(selection: PartSelection, pattern: str) -> str:
    """Category of ``pattern`` as seen from ``selection`` (candidate list, else part hypothesis)."""
    for candidate in selection.candidates:
        if candidate.name == pattern:
            return str(candidate.category)
    return str(selection.part.category_hypothesis or "construction-composition")


def _map_components(
    application: ApplicationSeed, selection: PartSelection, index: dict[str, str]
) -> None:
    """Map brief components named by the part onto the application (interaction seeding, §9 rule 5)."""
    for ref in selection.part.component_refs:
        index.setdefault(kebab(ref), application.id)
    for component in selection.part.component_refs:
        index.setdefault(kebab(component), application.id)


def _supporting_union(
    scored: Sequence[PartSelection], config: ServerConfig
) -> list[SupportingPattern]:
    """§9 rule 2: union of all parts' supporting sets, deduped by name, capped by fit desc."""
    flattened: list[SupportingChoice] = [choice for selection in scored for choice in selection.supporting]
    flattened.sort(key=lambda choice: (-choice.fit_score, choice.pattern))
    union: list[SupportingPattern] = []
    seen: set[str] = set()
    for choice in flattened:
        if choice.pattern in seen:
            continue
        seen.add(choice.pattern)
        union.append(SupportingPattern(pattern=choice.pattern, role=choice.role))
        if len(union) >= config.selection.max_supporting:
            break
    return union


def _interaction_seeds(
    brief: DesignBrief,
    applications: Sequence[ApplicationSeed],
    component_to_application: dict[str, str],
) -> list[InteractionSeed]:
    """§9 rule 5: brief flows between components of different applications pre-seed interactions."""
    seeds: list[InteractionSeed] = []
    known_ids = {application.id for application in applications}
    for flow in brief.flows:
        source = component_to_application.get(kebab(flow.source))
        target = component_to_application.get(kebab(flow.target))
        if source is None or target is None or source == target:
            continue
        if source not in known_ids or target not in known_ids:
            continue
        seeds.append(
            InteractionSeed(
                source=source,
                target=target,
                type=flow.kind or "sync",
                description=f"{flow.source} {flow.kind or 'sync'} to {flow.target}",
            )
        )
    return seeds


def _reasoning(
    composed: ComposedSelection,
    selections: Sequence[PartSelection],
    catalog: PatternLoader,
    config: ServerConfig,
) -> str:
    """§9 rule 6: assemble the reasoning trace from the ledgers — no LLM narration."""
    lines: list[str] = [
        f"{len(selections)} decision part(s) decomposed; dominant part: {composed.dominant_part_id}.",
    ]
    for selection in selections:
        primary = ", ".join(
            f"{candidate.name} (blend {candidate.retrieval_score:.4f}, fit {candidate.fit_score:.1f})"
            for candidate in selection.candidates[:3]
        ) or "none"
        flags: list[str] = []
        if selection.is_fallback:
            flags.append(f"fallback primary ({selection.fallback_reason})")
        if selection.ambiguous:
            flags.append("ambiguous: near-tie " + ", ".join(selection.near_tie))
        if selection.veto_ledger:
            flags.append("vetoed: " + "; ".join(selection.veto_ledger))
        peak_axes = sorted(selection.weights.items(), key=lambda item: -item[1])[:3]
        weight_text = ", ".join(f"{axis} {value:.3f}" for axis, value in peak_axes) or "unweighted"
        lines.append(
            f"- {selection.part.id} [{selection.part.scope}] primary={selection.primary} "
            f"category={selection.primary_category or selection.part.category_hypothesis}; "
            f"retrieval top-3: {primary}; weights source={selection.weights_source} "
            f"(top axes: {weight_text}); thresholds: fit ≥ {config.selection.primary_score_threshold:g} "
            f"and analysis ≥ {config.selection.primary_score_threshold:g}; "
            f"supporting={[choice.pattern for choice in selection.supporting] or 'none'}"
            + (f"; {'; '.join(flags)}" if flags else "")
        )
        lines.append(f"  statement: {selection.part.statement}")
        vector_text = (
            " ".join(f"{axis}={selection.weights.get(axis, 0.0):.3f}" for axis in QUALITY_AXES)
            if selection.weights
            else "none"
        )
        lines.append(f"  weights vector: {vector_text}")
        applied = [
            f"{candidate.name}: " + ", ".join(f"{entry.label}{entry.delta:+g}" for entry in candidate.adjustments)
            for candidate in selection.candidates
            if candidate.name in ({selection.primary} | {choice.pattern for choice in selection.supporting})
            and candidate.adjustments
        ]
        if applied:
            lines.append("  adjustments: " + " | ".join(applied))
    lines.append(
        "supporting set (union, capped at "
        f"{config.selection.max_supporting}): "
        + (", ".join(f"{entry.pattern} — {entry.role}" for entry in composed.supporting) or "none")
    )
    catalog_categories = {
        record.category
        for application in composed.applications
        if (record := catalog.get_by_name(application.pattern)) is not None
    }
    lines.append(f"categories in play: {sorted(catalog_categories)}")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------
# GENERATE seed assembly
# --------------------------------------------------------------------------------------


def build_generation_seed(
    *,
    composed: ComposedSelection,
    selections: dict[str, PartSelection],
    brief: DesignBrief,
    catalog: PatternLoader,
    focus: str | None,
    technology_tokens: Sequence[str],
) -> GenerationSeed:
    """Assemble the deterministic GENERATE input, including the §8.4 language bindings."""
    slices: dict[str, CatalogSlice] = {}
    bindings: dict[str, LanguageBinding] = {}
    for application in composed.applications:
        if application.pattern in slices:
            continue
        record = catalog.get_by_name(application.pattern)
        if record is None:
            raise DesignPatternError(
                ERROR_GENERATION_FAILED,
                f"selected pattern {application.pattern!r} does not resolve to a catalog record",
            )
        binding = bind_language_entry(
            record,
            language=brief.language,
            focus=focus,
            paradigm=brief.paradigm,
            technology_tokens=technology_tokens,
        )
        bindings[application.pattern] = binding
        slices[application.pattern] = catalog_slice(record, binding)
    return GenerationSeed(
        restated_goal=brief.restated_goal,
        constraints=list(brief.constraints),
        negative_signals=list(brief.negative_signals),
        language=brief.language,
        applications=list(composed.applications),
        catalog_slices=slices,
        interaction_seeds=list(composed.interaction_seeds),
        part_weights={pid: selection.weights for pid, selection in selections.items()},
    )


# --------------------------------------------------------------------------------------
# §11 item 1 — assembling the DesignResult from the GENERATE payload
# --------------------------------------------------------------------------------------


def assemble_result(
    *,
    seed: GenerationSeed,
    raw: RawGeneration,
    composed: ComposedSelection,
    brief: DesignBrief,
    catalog: PatternLoader,
    config: ServerConfig,
    score: float | None = None,
) -> DesignResult:
    """Validate the GENERATE payload against the seed and attach every deterministic field."""
    by_id = {application.id: application for application in raw.applications if application.id}
    by_pattern: dict[str, list[RawApplication]] = {}
    for application in raw.applications:
        by_pattern.setdefault(application.pattern, []).append(application)
    problems: list[str] = []
    applications: list[PatternApplication] = []
    for application_seed in seed.applications:
        record = catalog.get_by_name(application_seed.pattern)
        if record is None:
            problems.append(f"{application_seed.pattern}: not a catalog record")
            continue
        generated = by_id.get(application_seed.id)
        if generated is None:
            candidates = by_pattern.get(application_seed.pattern, [])
            if len(candidates) == 1:
                generated = candidates[0]
        if generated is None:
            problems.append(f"{application_seed.id}: no generated application for this seed")
            continue
        if generated.pattern and generated.pattern != application_seed.pattern:
            problems.append(
                f"{application_seed.id}: generated pattern {generated.pattern!r} != seed pattern "
                f"{application_seed.pattern!r}"
            )
            continue
        if not generated.solution.strip():
            problems.append(f"{application_seed.id}: 'solution' is empty (schema requires minLength 1)")
            continue
        binding = seed.catalog_slices[application_seed.pattern].language_binding
        alternatives = list(
            dict.fromkeys(
                [
                    *composed.alternatives_by_application.get(application_seed.id, []),
                    *(a.strip() for a in generated.alternatives_considered if a.strip()),
                ]
            )
        )
        applications.append(
            PatternApplication(
                id=application_seed.id,
                pattern=application_seed.pattern,
                category=application_seed.category,
                name=truncate(generated.name.strip() or _default_application_name(application_seed), MAX_APPLICATION_NAME),
                problem=generated.problem.strip() or _default_problem(application_seed),
                solution=generated.solution.strip(),
                participants=[
                    Participant(
                        role=participant.role.strip() or "participant",
                        maps_to=participant.maps_to.strip() or _default_maps_to(application_seed),
                        responsibility=participant.responsibility.strip() or "implements the pattern role",
                    )
                    for participant in generated.participants
                ],
                interactions=[
                    ApplicationInteraction(
                        **{
                            "from": interaction.from_.strip() or "client",
                            "to": interaction.to.strip() or "participant",
                            "description": interaction.description.strip()
                            or interaction.to.strip()
                            or "collaboration",
                        }
                    )
                    for interaction in generated.interactions
                ],
                implementation_steps=[step.strip() for step in generated.implementation_steps if step.strip()],
                code_sketch=generated.code_sketch or (binding.code_sketch if binding is not None else None),
                language_binding=binding,
                test_notes=generated.test_notes,
                alternatives_considered=alternatives,
            )
        )
    extra_ids = sorted(set(by_id) - {application_seed.id for application_seed in seed.applications})
    if extra_ids:
        problems.append(f"generated applications for unknown seeds: {extra_ids}")
    if problems:
        raise DesignPatternError(
            ERROR_GENERATION_FAILED,
            "GENERATE output failed validation: " + "; ".join(problems[:5]),
            hint="the payload must answer every seed exactly once with the seed id and pattern echoed",
            extra={"problems": problems},
        )
    dominant_record = catalog.get_by_name(composed.primary)
    return DesignResult(
        overview=DesignOverview(
            reasoning=composed.reasoning,
            primary_pattern=composed.primary,
            category=as_category(composed.category),
            supporting_patterns=list(composed.supporting),
            principles=list(dominant_record.design_principles[:5]) if dominant_record else [],
            constraints=list(brief.constraints),
            languages=[as_language(brief.language)],
            score=score,
        ),
        applications=applications,
        interactions=[
            Interaction(
                source=interaction.source,
                target=interaction.target,
                type=interaction.type,
                description=interaction.description,
            )
            for interaction in seed.interaction_seeds
        ],
        quality_attributes=_aggregate_quality_attributes(applications, catalog),
        test_strategy=_test_strategy(applications, brief),
        risks=_risks(applications, catalog, config),
    )


def _default_application_name(application: ApplicationSeed) -> str:
    """Deterministic fallback name when GENERATE leaves it empty (§9 rule 3)."""
    target = application.component_refs[0] if application.component_refs else application.part_id
    return f"{application.pattern.replace('-', ' ').title()} for {target}"


def _default_problem(application: ApplicationSeed) -> str:
    """Deterministic fallback problem statement (part statement + constraints)."""
    problem = application.part_statement
    if application.constraints:
        problem = f"{problem} Constraints: {'; '.join(application.constraints)}"
    return truncate(problem, 400)


def _default_maps_to(application: ApplicationSeed) -> str:
    """Deterministic fallback entity name for a participant map."""
    return application.component_refs[0] if application.component_refs else application.part_id


def _aggregate_quality_attributes(
    applications: Sequence[PatternApplication], catalog: PatternLoader
) -> dict[str, float]:
    """Mean of the applied patterns' eight axes — traceable to catalog data, never invented."""
    totals = dict.fromkeys(QUALITY_AXES, 0.0)
    counted = 0
    for application in applications:
        record = catalog.get_by_name(application.pattern)
        if record is None:
            continue
        counted += 1
        for axis in QUALITY_AXES:
            totals[axis] += record.quality_attributes.get(axis, 0.0)
    if not counted:
        return {}
    return {axis: round(value / counted, 2) for axis, value in totals.items()}


def _test_strategy(
    applications: Sequence[PatternApplication], brief: DesignBrief
) -> TestStrategy:
    """§11 item 1 test_notes/seams: participants give the injection points, weights the emphasis."""
    seams: list[str] = []
    for application in applications:
        for participant in application.participants:
            if participant.maps_to and participant.maps_to not in seams:
                seams.append(participant.maps_to)
    approach = (
        f"Unit-test each application at its seams ({len(applications)} application(s), "
        f"{len(seams)} named seam(s)); substitute every collaborator role a participant maps to, "
        f"and assert the decision each application owns rather than its internal call order."
    )
    if brief.constraints:
        approach += f" Cover the stated constraints: {'; '.join(brief.constraints[:3])}."
    return TestStrategy(approach=approach, test_seams=seams[:10])


def _risks(
    applications: Sequence[PatternApplication], catalog: PatternLoader, config: ServerConfig
) -> list[Risk]:
    """Risks from the applied patterns' own tradeoffs/avoid_when text (catalog-grounded, capped)."""
    risks: list[Risk] = []
    for application in applications:
        record = catalog.get_by_name(application.pattern)
        if record is None or not record.tradeoffs:
            continue
        tradeoff = first_sentence(record.tradeoffs[0], 240)
        avoid = first_sentence(record.avoid_when[0], 200) if record.avoid_when else ""
        mitigation = "Re-check against the part's constraint"
        if avoid:
            mitigation += f"; drop this application when {avoid}"
        if application.alternatives_considered:
            mitigation += f"; alternatives: {application.alternatives_considered[0]}"
        risks.append(Risk(risk=f"{application.id}: {tradeoff}", mitigation=mitigation))
        if len(risks) >= len(applications) or len(risks) >= 5:
            break
    return risks


# --------------------------------------------------------------------------------------
# The pipeline
# --------------------------------------------------------------------------------------


class DesignPipeline(Workflow):
    """Coordinate stages A–H of docs/implementation-guide.md. Dependencies are injected.

    Realized as a llama-index Workflow: the five public phase methods start one run of the
    event graph (``route`` → ``analyze_step`` → ``generate_step`` ⇄ ``evaluate_step`` →
    ``refine_step``) and translate the graph's timeout; the deterministic stage helpers are
    unchanged. The MCP tools and the job runner call :meth:`run_design` and serialize the
    result through ``pipeline_result_to_output`` (the ``DesignResult`` wire contract).
    """

    def __init__(
        self,
        *,
        config: ServerConfig,
        catalog: PatternLoader,
        index: RetrievalIndex,
        llm: LLMClientProtocol,
        guard: AntiScopeGuard | None = None,
        reasoning: ReasoningClient | None = None,
    ) -> None:
        # Internal whole-run budget (§14): fires strictly inside the outer
        # ``run_with_deadline`` backstop and cancels the in-flight step cleanly
        # (WorkflowTimeoutError → translated to TimeoutError → ERR_014).
        super().__init__(timeout=config.tasks.deadline_seconds * 0.9)
        self._config = config
        self._catalog = catalog
        self._index = index
        self._llm = llm
        self._reasoning = reasoning
        self._guard = (
            guard
            if guard is not None
            else AntiScopeGuard(
                parse_out_of_scope_terms(Path(config.paths.docs_directory) / CATALOG_DOC_FILE),
                catalog,
                parse_locally_implementable_names(Path(config.paths.docs_directory) / CATALOG_DOC_FILE),
            )
        )

    def validate(
        self,
        *,
        validate_resource_configs: bool = True,
        validate_resources: bool = False,
    ) -> bool:
        """Fail fast on inconsistent state (called after warmup at startup).

        The two DesignPatternError guards are the pinned contract; the llama-index
        graph checks are re-run as well so callers keep one entry point. Returns
        whatever the base validation reports (human-in-the-loop usage flag).
        """
        if not self._catalog.records:
            raise DesignPatternError(ERROR_NO_PRIMARY_PATTERN, "catalog is empty")
        if self._config.retrieval.min_fusion_score > 2.0 / self._config.retrieval.rrf_k + 1e-3:
            raise DesignPatternError(
                ERROR_GENERATION_FAILED,
                "min_fusion_score exceeds the reciprocal-rank blend maximum 2/rrf_k",
            )
        return super().validate(
            validate_resource_configs=validate_resource_configs,
            validate_resources=validate_resources,
        )

    async def warmup(self) -> None:
        """No-op: the retrieval index is built by the server before the pipeline exists."""

    async def _reasoning_block(self, phase: str, payload: dict[str, Any]) -> str:
        """The pre-emit reasoning block for one phase call; empty when disabled or degraded.

        Never raises: a reasoning outage degrades to the in-prompt scaffold, it must never
        fail a tool call.
        """
        if self._reasoning is None or not self._reasoning.enabled:
            return ""
        try:
            trace = await self._reasoning.run_pre_llm(phase, payload)
        except Exception as exc:  # noqa: BLE001 - the degradation contract
            logger.warning(
                "Reasoning client failed unexpectedly; continuing without a trace",
                extra={"phase": phase, "error": str(exc)},
            )
            return ""
        if not trace.steps:
            return render_degraded_context(trace) if trace.degraded else ""
        logger.info(
            "Reasoning trace ready",
            extra={"phase": phase, "steps": len(trace.steps), "duration_ms": trace.total_duration_ms},
        )
        return render_reasoning_context(trace, max_chars=self._config.reasoning.max_injected_chars)


    # -- Workflow steps and public phase API ---------------------------------------

    @step
    async def route(
        self, ctx: Context, ev: DesignStart
    ) -> AnalysisReady | SelectionReady | GenerateEntry | EvaluateEntry:
        """Seed the run-scoped state, then route by mode (mid-graph entry per E11)."""
        state = _RunState()
        state.cancellation = ev.cancellation
        state.mode = ev.mode
        if isinstance(ev.analysis, AnalysisResult):
            state.entry_analysis = ev.analysis
            state.current_analysis = ev.analysis
            state.current_selections = ev.analysis.selections
        if isinstance(ev.result, DesignResult):
            state.entry_result = ev.result
        if ev.parts is not None:
            state.entry_parts = list(ev.parts)
        await ctx.store.set("run", state)
        if ev.mode in ("analyze", "run_design"):
            return AnalysisReady(
                mode=ev.mode,
                description=ev.description,
                architecture_style=ev.architecture_style,
                language=ev.language,
                paradigm=ev.paradigm,
                focus=ev.focus,
                cancellation=ev.cancellation,
            )
        # generate / evaluate / design_loop: mid-graph entry into the loop.
        if ev.mode == "generate":
            assert state.current_analysis is not None, "generate mode requires an analysis"
            return GenerateEntry(analysis=state.current_analysis)
        if ev.mode == "evaluate":
            assert state.entry_result is not None
            return EvaluateEntry(result=state.entry_result, parts=state.entry_parts)
        assert state.current_analysis is not None, "design_loop mode requires an analysis"
        return SelectionReady(analysis=state.current_analysis, attempt=1)

    @step
    async def analyze_step(
        self, ctx: Context, ev: AnalysisReady
    ) -> PipelineDone | SelectionReady:
        """ANALYZE phase (§1–§8): intake, decomposition repair, per-part retrieval and selection."""
        text = validate_description(ev.description)
        effective_language = resolve_language(ev.language, self._catalog.enums.languages)
        effective_paradigm = resolve_paradigm(ev.paradigm, self._catalog.enums.paradigms)
        style = resolve_style(ev.architecture_style or None)
        hints = DesignHints(
            architecture_style=style,
            language=effective_language,
            paradigm=effective_paradigm,
            focus=ev.focus,
        )
        logger.info(
            "Analyze phase started",
            extra={
                "description_chars": len(text),
                "architecture_style": style,
                "language": effective_language,
                "paradigm": effective_paradigm,
                "focus": ev.focus,
                "parameters": self._config.effective_parameters(),
            },
        )
        analyze_reasoning = await self._reasoning_block("analyze", {"description": text})
        brief, parts = await self._stage_a_b(text, hints, analyze_reasoning)
        if not parts:
            parts = [synthesize_construction_part(brief, text)]
        _check_cancelled(ev.cancellation, "stage B")
        weights_reasoning = await self._reasoning_block(
            "weights",
            {
                "description": text,
                "restated_goal": brief.restated_goal,
                "decision_parts": "; ".join(f"{part.id}: {part.statement}" for part in parts),
            },
        )
        selections = await self._select_all(parts, brief, ev.cancellation, weights_reasoning)
        _check_cancelled(ev.cancellation, "stage E")
        technology_tokens = extract_technology_tokens(
            text, *[tech for component in brief.components for tech in component.technologies]
        )
        analysis = AnalysisResult(
            design_brief=brief,
            decision_parts=parts,
            selections=selections,
            effective_language=as_language(effective_language),
            focus=ev.focus,
            technology_tokens=technology_tokens,
            is_fallback=any(selection.is_fallback for selection in selections.values()),
        )
        if ev.mode == "analyze":
            return PipelineDone(result=analysis, mode="analyze")
        # run_design: publish the fresh analysis into the run state so the loop
        # steps (generate/refine) read it from the store.
        state = cast(_RunState, (await ctx.store.get("run", _RunState())))
        state.entry_analysis = analysis
        state.current_analysis = analysis
        state.current_selections = analysis.selections
        return SelectionReady(analysis=analysis, attempt=1)

    @step
    async def generate_step(
        self, ctx: Context, ev: SelectionReady | GenerateEntry
    ) -> Generated | AttemptFailed | PipelineDone:
        """GENERATE for one attempt (§11 items 1–2); a failure continues the loop (E12).

        The ``generate`` mode enters via ``GenerateEntry`` and terminates with
        ``PipelineDone(result=..., mode="generate")`` instead of continuing the loop.
        """
        state = cast(_RunState, (await ctx.store.get("run", _RunState())))
        single_shot = isinstance(ev, GenerateEntry)
        state.attempt = 1 if single_shot else ev.attempt
        analysis = ev.analysis if single_shot else state.current_analysis
        assert analysis is not None
        cancellation = state.cancellation
        _check_cancelled(cancellation, "stage G")
        try:
            composed = self._compose(analysis)
            seed = build_generation_seed(
                composed=composed,
                selections=analysis.selections,
                brief=analysis.design_brief,
                catalog=self._catalog,
                focus=analysis.focus,
                technology_tokens=analysis.technology_tokens,
            )
            reasoning_context = await self._reasoning_block(
                "generate",
                {
                    "restated_goal": analysis.design_brief.restated_goal,
                    "applications": "; ".join(
                        f"{seed_item.id}: {seed_item.pattern} for {seed_item.part_id}"
                        for seed_item in seed.applications
                    ),
                },
            )
            raw_generation = await self._generate_in_batches(seed, reasoning_context=reasoning_context)
            result = assemble_result(
                seed=seed,
                raw=raw_generation,
                composed=composed,
                brief=analysis.design_brief,
                catalog=self._catalog,
                config=self._config,
            )
        except DesignPatternError as exc:
            if single_shot:
                raise
            return AttemptFailed(
                analysis=analysis,
                error_detail=exc.detail,
                failure_kind=exc.failure_kind if isinstance(exc, LLMError) else None,
                attempt=ev.attempt,
            )
        if single_shot:
            return PipelineDone(result=result, mode="generate")
        return Generated(analysis=analysis, result=result, attempt=ev.attempt)

    @step
    async def evaluate_step(
        self, ev: Generated | EvaluateEntry
    ) -> Evaluated | PipelineDone:
        """EVALUATE phase (§11 item 2): score the attempt against the decision parts.

        The ``evaluate`` mode enters via ``EvaluateEntry`` (a foreign result plus its
        decision parts) and terminates with ``PipelineDone(result=..., mode="evaluate")``.
        """
        if isinstance(ev, EvaluateEntry):
            reasoning_context = await self._reasoning_block(
                "evaluate",
                {
                    "primary_pattern": ev.result.overview.primary_pattern,
                    "applications": "; ".join(
                        f"{application.id}: {application.pattern}" for application in ev.result.applications
                    ),
                    "parts": "; ".join(f"{part.id}: {part.statement}" for part in ev.parts),
                },
            )
            evaluation = await self._llm.evaluate(ev.result, ev.parts, reasoning_context=reasoning_context)
            return PipelineDone(result=evaluation, mode="evaluate")
        reasoning_context = await self._reasoning_block(
            "evaluate",
            {
                "primary_pattern": ev.result.overview.primary_pattern,
                "applications": "; ".join(
                    f"{application.id}: {application.pattern}" for application in ev.result.applications
                ),
                "parts": "; ".join(f"{part.id}: {part.statement}" for part in ev.analysis.decision_parts),
            },
        )
        evaluation = await self._llm.evaluate(
            ev.result, ev.analysis.decision_parts, reasoning_context=reasoning_context
        )
        return Evaluated(
            analysis=ev.analysis, result=ev.result, evaluation=evaluation, attempt=ev.attempt
        )

    @step
    async def refine_step(
        self, ctx: Context, ev: Evaluated | AttemptFailed
    ) -> PipelineDone | SelectionReady:
        """§11 loop tail: best retention, early stop, one-shot reselection, E12 terminal raise."""
        state = cast(_RunState, (await ctx.store.get("run", _RunState())))
        max_tries = self._config.loop.max_tries
        if isinstance(ev, AttemptFailed):
            error = DesignPatternError(
                ERROR_GENERATION_FAILED if ev.failure_kind is None else ERROR_LLM_PROVIDER,
                ev.error_detail,
            )
            state.last_error = error
            state.attempts_log.append(
                {
                    "attempt": ev.attempt,
                    "status": "failed",
                    "error": ev.error_detail,
                    "failure_kind": ev.failure_kind,
                }
            )
            logger.warning(
                "Attempt failed (E12 path)",
                extra={"attempt": ev.attempt, "error": ev.error_detail, "failure_kind": ev.failure_kind},
            )
            if ev.attempt >= max_tries:
                # An earlier attempt may already have produced a valid result: the
                # old design_loop finished with the best attempt instead of raising.
                if state.best is not None and state.best_evaluation is not None:
                    return PipelineDone(result=self._finish(state), mode=state.mode)
                raise error
            _check_cancelled(state.cancellation, f"attempt {ev.attempt + 1}")
            assert state.current_analysis is not None, "failed attempt without a current analysis"
            return SelectionReady(analysis=state.current_analysis, attempt=ev.attempt + 1)
        evaluation = ev.evaluation
        result = ev.result
        result.overview.score = evaluation.score
        state.attempts_log.append(
            {
                "attempt": ev.attempt,
                "status": "valid",
                "score": evaluation.score,
                "findings": [finding.detail for finding in evaluation.findings],
            }
        )
        logger.info(
            "Attempt evaluated",
            extra={
                "attempt": ev.attempt,
                "score": evaluation.score,
                "min_quality_score": self._config.loop.min_quality_score,
                "findings": [
                    {"kind": f.kind, "pattern": f.pattern, "detail": truncate(f.detail, 200)}
                    for f in evaluation.findings
                ],
            },
        )
        if evaluation.score > state.best_score:
            state.best, state.best_evaluation = result, evaluation
            state.best_score = evaluation.score
            state.best_attempt = ev.attempt
        if evaluation.score >= self._config.loop.min_quality_score:
            logger.info(
                "Early stop: min_quality_score reached",
                extra={"attempt": ev.attempt, "score": evaluation.score},
            )
            return PipelineDone(result=self._finish(state), mode=state.mode)
        if evaluation.selection_defect and not state.reselected and state.entry_analysis is not None:
            state.reselected = True
            state.sticky.update(evaluation.offending_patterns)
            assert state.current_selections is not None
            state.current_selections = self._reselect(
                state.current_selections, state.sticky, brief=state.entry_analysis.design_brief
            )
            assert state.current_analysis is not None
            state.current_analysis = state.entry_analysis.model_copy(
                update={"selections": state.current_selections}
            )
            logger.info("Reselection ledger", extra={"excluded": sorted(state.sticky)})
        if ev.attempt >= max_tries:
            return PipelineDone(result=self._finish(state), mode=state.mode)
        _check_cancelled(state.cancellation, f"attempt {ev.attempt + 1}")
        assert state.current_analysis is not None, "loop re-entry without a current analysis"
        return SelectionReady(analysis=state.current_analysis, attempt=ev.attempt + 1)

    def _finish(self, state: _RunState) -> PipelineResult:
        """Best-attempt header rewrite and result assembly (the loop tail)."""
        best = state.best
        best_evaluation = state.best_evaluation
        assert best is not None and best_evaluation is not None
        max_tries = self._config.loop.max_tries
        header = (
            f"attempts={len(state.attempts_log)} (max_tries={max_tries}), best attempt={state.best_attempt} "
            f"(score {state.best_score:.1f}, min_quality_score {self._config.loop.min_quality_score:g}), "
            f"reselection={'yes' if state.reselected else 'no'}"
            + (f", sticky exclusions={sorted(state.sticky)}" if state.sticky else "")
        )
        findings = [
            f"{entry.get('attempt')}: {entry.get('status')} "
            + (f"score {entry.get('score')}" if entry.get("status") == "valid" else f"error {entry.get('error')}")
            for entry in state.attempts_log
        ]
        best.overview.reasoning = (
            f"{header}\n" + "\n".join(findings) + "\n" + best.overview.reasoning
        )
        logger.info(
            "Selection run completed",
            extra={
                "attempts": state.attempts_log,
                "best_score": state.best_score,
                "reselected": state.reselected,
            },
        )
        entry_analysis = state.entry_analysis
        assert entry_analysis is not None
        selections = state.current_selections
        assert selections is not None
        return self._pipeline_result(
            best=best,
            evaluation=best_evaluation,
            attempts=len(state.attempts_log),
            score=state.best_score,
            analysis=entry_analysis,
            selections=selections,
        )

    # -- Public phase API ---------------------------------------------------------

    async def run_design(
        self,
        *,
        description: str,
        architecture_style: str | None = None,
        language: str | None = None,
        paradigm: str | None = None,
        focus: str | None = None,
        cancellation: CancellationToken | None = None,
    ) -> PipelineResult:
        """Run the full pipeline (§3: analyze → generate → evaluate) and return its result."""
        try:
            handler = self.run(
                start_event=DesignStart(
                    mode="run_design",
                    description=description,
                    architecture_style=architecture_style,
                    language=language,
                    paradigm=paradigm,
                    focus=focus,
                    cancellation=cancellation,
                )
            )
            done = cast(PipelineDone, await handler)
            return done.payload_as(PipelineResult)
        except WorkflowTimeoutError as exc:
            raise TimeoutError(str(exc)) from exc

    async def analyze(
        self,
        *,
        description: str,
        architecture_style: str | None = None,
        language: str | None = None,
        paradigm: str | None = None,
        focus: str | None = None,
        cancellation: CancellationToken | None = None,
    ) -> AnalysisResult:
        """ANALYZE phase (§1–§8): intake, decomposition repair, per-part retrieval and selection."""
        try:
            handler = self.run(
                start_event=DesignStart(
                    mode="analyze",
                    description=description,
                    architecture_style=architecture_style,
                    language=language,
                    paradigm=paradigm,
                    focus=focus,
                    cancellation=cancellation,
                )
            )
            done = cast(PipelineDone, await handler)
            return done.payload_as(AnalysisResult)
        except WorkflowTimeoutError as exc:
            raise TimeoutError(str(exc)) from exc

    async def generate(
        self, analysis: AnalysisResult, *, cancellation: CancellationToken | None = None
    ) -> DesignResult:
        """GENERATE phase (§9–§11 item 1): compose the selection and materialize its applications."""
        try:
            handler = self.run(
                start_event=DesignStart(mode="generate", analysis=analysis, cancellation=cancellation)
            )
            done = cast(PipelineDone, await handler)
            return done.payload_as(DesignResult)
        except WorkflowTimeoutError as exc:
            raise TimeoutError(str(exc)) from exc

    async def evaluate(
        self, result: DesignResult, parts: Sequence[DecisionPart]
    ) -> DesignEvaluation:
        """EVALUATE phase (§11 item 2): score ``result`` against the decision parts."""
        try:
            handler = self.run(
                start_event=DesignStart(mode="evaluate", result=result, parts=list(parts))
            )
            done = cast(PipelineDone, await handler)
            return done.payload_as(DesignEvaluation)
        except WorkflowTimeoutError as exc:
            raise TimeoutError(str(exc)) from exc

    async def design_loop(
        self, analysis: AnalysisResult, *, cancellation: CancellationToken | None = None
    ) -> PipelineResult:
        """§11: GENERATE → validate → EVALUATE ≤ ``max_tries``, best attempt retained."""
        try:
            handler = self.run(
                start_event=DesignStart(
                    mode="design_loop", analysis=analysis, cancellation=cancellation
                )
            )
            done = cast(PipelineDone, await handler)
            return done.payload_as(PipelineResult)
        except WorkflowTimeoutError as exc:
            raise TimeoutError(str(exc)) from exc

    # -- Phase internals ----------------------------------------------------------

    def _compose(self, analysis: AnalysisResult) -> ComposedSelection:
        """Deterministic Stage F composition of one analysis payload."""
        return compose_selection(
            selections=analysis.selections,
            brief=analysis.design_brief,
            catalog=self._catalog,
            config=self._config,
        )

    async def _generate_in_batches(
        self, seed: GenerationSeed, *, reasoning_context: str
    ) -> RawGeneration:
        """GENERATE in bounded-concurrent batches (§11 item 1, ``generation_batch_size``).

        One provider call carries at most ``generation_batch_size`` applications and only the
        catalog slices / interaction seeds those applications reference; at most
        ``generation_max_concurrency`` batches are in flight at once. Results are concatenated
        in batch order, so the :class:`RawGeneration` assembled against the FULL seed by the
        caller is identical to the sequential loop — the deterministic Stage F-G contract and
        its pattern-only fallback are unchanged.
        A failing batch propagates its :class:`~src.errors.LLMError` /
        :class:`~src.errors.DesignPatternError` unchanged into the design-loop/E12 path;
        in-flight sibling batches are cancelled before the exception leaves this method.
        """
        applications = seed.applications
        if not applications:
            return await self._llm.generate(seed, reasoning_context=reasoning_context)
        batch_size = self._config.generator.config.generation_batch_size
        max_concurrency = self._config.generator.config.generation_max_concurrency
        chunks = [
            applications[start : start + batch_size]
            for start in range(0, len(applications), batch_size)
        ]
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _run_batch(index: int, chunk: list[ApplicationSeed]) -> list[RawApplication]:
            chunk_ids = {application.id for application in chunk}
            batch_seed = seed.model_copy(
                update={
                    "applications": list(chunk),
                    "catalog_slices": {
                        application.pattern: seed.catalog_slices[application.pattern]
                        for application in chunk
                        if application.pattern in seed.catalog_slices
                    },
                    "interaction_seeds": [
                        interaction
                        for interaction in seed.interaction_seeds
                        if interaction.source in chunk_ids and interaction.target in chunk_ids
                    ],
                }
            )
            logger.info(
                "GENERATE batch dispatched",
                extra={
                    "batch": index + 1,
                    "batches": len(chunks),
                    "applications": len(chunk),
                    "batch_size": batch_size,
                    "max_concurrency": max_concurrency,
                    "application_ids": [application.id for application in chunk],
                },
            )
            async with semaphore:
                raw = await self._llm.generate(batch_seed, reasoning_context=reasoning_context)
            return raw.applications

        tasks = [
            asyncio.create_task(_run_batch(index, chunk))
            for index, chunk in enumerate(chunks)
        ]
        collected: list[RawApplication] = []
        try:
            for part in await asyncio.gather(*tasks):
                collected.extend(part)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        logger.info(
            "GENERATE batches complete",
            extra={
                "batches": len(chunks),
                "applications": len(applications),
                "returned_applications": len(collected),
            },
        )
        return RawGeneration(applications=collected)

    def _pipeline_result(
        self,
        *,
        best: DesignResult,
        evaluation: DesignEvaluation,
        attempts: int,
        score: float,
        analysis: AnalysisResult,
        selections: dict[str, PartSelection],
    ) -> PipelineResult:
        """Assemble the loop's outcome: design, evaluation and the loop metadata."""
        fallback = any(selection.is_fallback for selection in selections.values())
        categories: list[str] = []
        alternatives: list[str] = []
        for part in analysis.decision_parts:
            selection = selections.get(part.id)
            if selection is None:
                continue
            if selection.primary_category and selection.primary_category not in categories:
                categories.append(selection.primary_category)
            if fallback:
                continue
            for candidate in sorted(selection.candidates, key=lambda item: -item.fit_score):
                if candidate.name != selection.primary and candidate.name not in alternatives:
                    alternatives.append(candidate.name)
        return PipelineResult(
            design=best,
            evaluation=evaluation,
            attempts=max(attempts, 1),
            final_pattern=self._compose(
                analysis.model_copy(update={"selections": selections})
            ).primary,
            quality_metrics=QualityMetrics(**_aggregate_quality_attributes(best.applications, self._catalog)),
            final_quality_score=max(score, 0.0),
            matched_categories=categories,
            is_fallback=fallback,
            alternative_patterns=[] if fallback else alternatives,
        )

    # -- Stage A/B ----------------------------------------------------------------

    async def _stage_a_b(
        self, text: str, hints: DesignHints, reasoning_context: str = ""
    ) -> tuple[DesignBrief, list[DecisionPart]]:
        """§4/§5: the combined brief+parts call, its deterministic repair and the anti-scope guard."""
        raw: RawBriefAndParts | None
        try:
            raw = await self._llm.extract_brief_and_parts(
                text, hints, reasoning_context=reasoning_context
            )
        except DesignPatternError as exc:
            logger.warning(
                "Brief/parts extraction failed; falling back to a minimal single-part brief (E3)",
                extra={"error": exc.detail},
            )
            raw = None
        brief = build_brief(
            raw,
            language=hints.language,
            paradigm=hints.paradigm,
            style=hints.architecture_style,
            description=text,
        )
        if raw is None:
            return brief, [
                DecisionPart(
                    id="whole-description",
                    statement=truncate(text, 400),
                    component_refs=[],
                    scope="module",
                    category_hypothesis=None,
                    constraints=list(brief.constraints),
                    priority=1.0,
                    negative_signals=list(brief.negative_signals),
                    is_fallback=True,
                )
            ]
        parts = repair_parts(
            raw.decision_parts,
            max_parts=self._config.selection.max_parts,
            scopes=self._catalog.enums.scopes,
            categories=self._catalog.enums.categories,
            inherited_negative_signals=brief.negative_signals,
        )
        component_names = [component.name for component in brief.components]
        kept: list[DecisionPart] = []
        for part in parts:
            hypothesis = self._guard.hypothesis_for(part)
            if hypothesis is not None:
                kept.append(part.model_copy(update={"category_hypothesis": as_category(hypothesis)}))
                continue
            if self._guard.is_architecture_only(part, component_names):
                logger.info(
                    "Dropped architecture-level part (§5 rule 5)",
                    extra={"part_id": part.id, "statement": truncate(part.statement, 160)},
                )
                continue
            kept.append(part)
        if not kept and parts:
            logger.info("All parts were architecture-level; synthesizing a construction part (E9)")
        logger.info(
            "Decomposition repaired",
            extra={
                "parts": [{"id": p.id, "scope": p.scope, "category": p.category_hypothesis, "priority": p.priority} for p in kept],
                "components": component_names,
                "constraints": brief.constraints,
            },
        )
        return brief, kept

    # -- Stage C/D/E --------------------------------------------------------------

    async def _select_all(
        self,
        parts: Sequence[DecisionPart],
        brief: DesignBrief,
        cancellation: CancellationToken | None,
        weights_reasoning: str = "",
    ) -> dict[str, PartSelection]:
        """Stage C/D/E per part, in pipeline order (weights → retrieval → vetoes → scoring → selection)."""
        selections: dict[str, PartSelection] = {}
        _check_cancelled(cancellation, "weight extraction")
        # Stage D (weights) and Stage C (retrieval) depend only on parts+brief, so
        # they overlap; the deterministic Stage E loop below joins both (§14 note:
        # bounded-concurrent stage overlap). extract_part_weights_batch never
        # raises (safe per-part wrappers); retrieval errors propagate (RET-1).
        batch_weights, hits_by_part = await asyncio.gather(
            extract_part_weights_batch(
                self._llm, parts, brief, config=self._config, reasoning_context=weights_reasoning
            ),
            self._retrieve_for_parts(parts, brief, cancellation),
        )
        for part, hits in zip(parts, hits_by_part, strict=True):
            weights, weights_source = batch_weights[part.id]
            survivors, ledger, vetoed = apply_vetoes(
                hits,
                record_of=self._catalog.records,
                part=part,
                language=brief.language,
                negative_signals=[*part.negative_signals, *brief.negative_signals],
            )
            best_blend = max((hit.retrieval_score for hit in survivors), default=0.0)
            if not survivors or best_blend < self._config.retrieval.min_fusion_score:
                selection = select_for_part(
                    part=part,
                    candidates=[],
                    record_of=self._catalog.records,
                    catalog=self._catalog,
                    brief=brief,
                    config=self._config,
                    veto_ledger=ledger,
                    fallback_reason=(
                        "retrieval pool empty after the veto pre-filters"
                        if not survivors
                        else (
                            f"best retrieval blend {best_blend:.4f} < min_fusion_score "
                            f"{self._config.retrieval.min_fusion_score:.4f}"
                        )
                    ),
                    weights=weights,
                    weights_source=weights_source,
                )
            else:
                annotated = score_candidates(
                    survivors,
                    part=part,
                    brief=brief,
                    weights=weights,
                    record_of=self._catalog.records,
                    catalog=self._catalog,
                    config=self._config,
                )[: self._config.retrieval.top_k_candidates]
                selection = select_for_part(
                    part=part,
                    candidates=annotated,
                    record_of=self._catalog.records,
                    catalog=self._catalog,
                    brief=brief,
                    config=self._config,
                    veto_ledger=ledger,
                    weights=weights,
                    weights_source=weights_source,
                )
            selections[part.id] = selection
            logger.info(
                "Part selected",
                extra={
                    "part_id": part.id,
                    "primary": selection.primary,
                    "is_fallback": selection.is_fallback,
                    "ambiguous": selection.ambiguous,
                    "supporting": [choice.pattern for choice in selection.supporting],
                    "vetoed": vetoed,
                },
            )
        return selections

    def _retrieve_for_parts(
        self,
        parts: Sequence[DecisionPart],
        brief: DesignBrief,
        cancellation: CancellationToken | None,
    ) -> Awaitable[list[list[RetrievalHit]]]:
        """One batched §6 retrieval for all parts (embed round trip shared, L1)."""

        async def _run() -> list[list[RetrievalHit]]:
            _check_cancelled(cancellation, "retrieval")
            queries = [
                PartQuery(
                    statement=part.statement,
                    constraints=[*part.constraints, *brief.constraints],
                    scope=part.scope,
                )
                for part in parts
            ]
            return await self._index.retrieve_many(queries)

        return _run()

    def _reselect(
        self,
        selections: dict[str, PartSelection],
        excluded: Collection[str],
        *,
        brief: DesignBrief,
    ) -> dict[str, PartSelection]:
        """§11 item 4: one bounded reselection — exclusions are sticky for the whole loop."""
        sticky = bool(excluded)
        updated: dict[str, PartSelection] = {}
        for part_id, selection in selections.items():
            touched = selection.primary in excluded or any(
                choice.pattern in excluded for choice in selection.supporting
            )
            if not touched:
                updated[part_id] = selection
                continue
            remaining = [candidate for candidate in selection.candidates if candidate.name not in excluded]
            logger.info(
                "Reselection",
                extra={
                    "part_id": part_id,
                    "excluded": sorted(excluded),
                    "remaining": [candidate.name for candidate in remaining],
                },
            )
            updated[part_id] = select_for_part(
                part=selection.part,
                candidates=remaining,
                record_of=self._catalog.records,
                catalog=self._catalog,
                brief=brief,
                config=self._config,
                veto_ledger=selection.veto_ledger,
                fallback_reason=(
                    "reselection exclusions left no eligible candidate (sticky exclusions)"
                    if not remaining
                    else None
                ),
                weights=selection.weights,
                weights_source=selection.weights_source,
            )
        if not sticky:
            return selections
        return updated

def _check_cancelled(cancellation: CancellationToken | None, boundary: str) -> None:
    """E11: stop at the next stage boundary once cancellation was requested."""
    if cancellation is not None and cancellation.cancelled():
        raise DesignPatternError(ERROR_CANCELLED, f"cancelled at stage boundary: {boundary}")
