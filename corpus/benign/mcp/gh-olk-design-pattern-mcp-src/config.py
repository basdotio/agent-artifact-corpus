"""Server configuration models and JSON loader (with {env:VAR:-default} expansion).

Every numeric parameter of docs/implementation-guide.md §14 lives here and is validated at load
time: weight pairs must sum to 1.0 ± 1e-3, ``min_fusion_score`` may not exceed the reciprocal-rank
blend maximum ``2/rrf_k``, thresholds stay in [0, 100], and ``weight_smoothing_alpha`` stays in
[0, 1]. ``ServerConfig.effective_parameters()`` is the snapshot the server logs at startup so any
selection is reproducible from the logs (§14 closing rule).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, ClassVar, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

from src.config_expansion import expand_env_in_obj
from src.reasoning.config import ReasoningConfig

ERROR_CONFIG_NOT_FOUND = "ERR_010"
ERROR_INVALID_CONFIG = "INVALID_CONFIG"

WEIGHT_SUM_TOLERANCE = 1e-3

logger = logging.getLogger(__name__)


class GeneratorInnerConfig(BaseModel):
    """LiteLLM generator settings."""

    model: str = Field(default="gpt-4o-mini")
    base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str = Field(default="")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    top_k: int = Field(default=20, ge=1)
    timeout_seconds: float = Field(default=120.0, gt=0.0)
    #: Applications per GENERATE provider call (§11 item 1); larger requests exceed the
    #: per-provider-call timeout more often than smaller ones.
    generation_batch_size: int = Field(default=5, ge=1)
    #: Ceiling on GENERATE batches in flight at once (§14 latency notes); batches are
    #: dispatched bounded-concurrently and concatenated in batch order, so the assembled
    #: RawGeneration is byte-identical to the sequential loop.
    generation_max_concurrency: int = Field(default=2, ge=1)
    #: Consecutive qualifying provider failures (timeout, connection, 408/429/5xx, empty
    #: response) that open this agent's circuit. Auth/configuration 4xx never count.
    circuit_breaker_failure_threshold: int = Field(default=3, ge=1)
    #: Seconds an open circuit rejects calls before one half-open probe is admitted.
    circuit_breaker_cooldown_seconds: float = Field(default=60.0, gt=0.0)

    model_config = {"extra": "forbid"}


class GeneratorConfig(BaseModel):
    """Provider selector plus the generator inner config."""

    provider: str = Field(default="openai")
    config: GeneratorInnerConfig = Field(default_factory=GeneratorInnerConfig)

    model_config = {"extra": "forbid"}


class EmbedderInnerConfig(BaseModel):
    """TEI/LiteLLM embedder settings for the dense retrieval leg."""

    base_url: str = Field(default="http://design-pattern-tei-embed:8080")
    api_key: str = Field(default="")
    model: str = Field(default="openai//data/embedding-model")
    embed_batch_size: int = Field(default=16, ge=1)
    query_instruction: str = Field(default="")
    text_instruction: str = Field(default="")
    model_repo: str = Field(default="")
    onnx_variant: str = Field(default="")
    document_embed_attempts: int = Field(default=10, ge=1)
    document_embed_backoff_seconds: float = Field(default=2.0, gt=0.0)

    model_config = {"extra": "forbid"}


class EmbedderConfig(BaseModel):
    """Provider selector plus the embedder inner config."""

    provider: str = Field(default="tei")
    config: EmbedderInnerConfig = Field(default_factory=EmbedderInnerConfig)

    model_config = {"extra": "forbid"}


class DenseCacheConfig(BaseModel):
    """Precomputed dense-embedding cache (§2.2): vectors, fingerprint and probe guard."""

    path: str = Field(default="/app/data/dense-cache")
    mode: Literal["auto", "require", "off"] = Field(default="auto")
    write: bool = Field(default=True)
    #: Must exceed the sidecar's single-request latency: measured 13-29 s per
    #: ``/v1/embeddings`` call on the CPU TEI image (one input, queue + ORT
    #: inference), so a tighter bound would miss on every cold start.
    probe_timeout_seconds: float = Field(default=120.0, gt=0.0)
    probe_min_cosine: float = Field(default=0.999, ge=-1.0, le=1.0)

    model_config = {"extra": "forbid"}


class RerankerInnerConfig(BaseModel):
    """TEI cross-encoder settings for the mandatory rerank stage."""

    base_url: str = Field(default="http://design-pattern-tei-rerank:8080")
    model_name: str = Field(default="Alibaba-NLP/gte-reranker-modernbert-base")
    api_key: str = Field(default="")
    #: Per-batch HTTP timeout. Must exceed one full ``max_batch_size`` request:
    #: measured 51.3 s for 48 catalog documents on the CPU sidecar (vs 9.9 s for 8),
    #: so a 30 s bound times out every full batch and fails the whole retrieval.
    timeout: float = Field(default=300.0, gt=0.0)
    max_batch_size: int = Field(default=48, ge=1)

    model_config = {"extra": "forbid"}


class RerankerConfig(BaseModel):
    """Cross-encoder config plus the survivor cap (§14 ``rerank_top_n``)."""

    rerank_top_n: int = Field(default=10, ge=1)
    #: Document text fed to the cross-encoder (§6 step 4): ``full`` = the §2.2
    #: document text (shipped default), ``capsule`` = name + intent + problem +
    #: first two use cases (~3x fewer characters, measured 3.6-4.3x faster on
    #: the CPU sidecar). Rankings are NOT equivalent — capsule is opt-in.
    rerank_text: Literal["full", "capsule"] = Field(default="full")
    config: RerankerInnerConfig = Field(default_factory=RerankerInnerConfig)

    model_config = {"extra": "forbid"}


class RetrievalConfig(BaseModel):
    """§6 retrieval parameters (§14 defaults); per-leg top-k caps stage-1 recall."""

    dense_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    bm25_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    rrf_k: int = Field(default=60, ge=1)
    min_fusion_score: float = Field(default=0.0, ge=0.0)
    top_k_candidates: int = Field(default=5, ge=1)
    dense_top_k: int = Field(default=20, ge=0)
    bm25_top_k: int = Field(default=20, ge=0)
    max_concurrent_parts: int = Field(default=1, ge=1)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _check_weights(self) -> RetrievalConfig:
        total = self.dense_weight + self.bm25_weight
        if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise ValueError(
                f"retrieval weights must sum to 1.0 ± {WEIGHT_SUM_TOLERANCE} "
                f"(dense_weight={self.dense_weight}, bm25_weight={self.bm25_weight}, sum={total})"
            )
        for name, value in (("dense_weight", self.dense_weight), ("bm25_weight", self.bm25_weight)):
            if value < 0.05:
                logger.warning("Retrieval leg weight below 0.05", extra={"leg": name, "value": value})
        blend_max = 2.0 / self.rrf_k
        if self.min_fusion_score > blend_max + WEIGHT_SUM_TOLERANCE:
            raise ValueError(
                f"min_fusion_score must be ≤ 2/rrf_k = {blend_max:.6f} "
                f"(got {self.min_fusion_score}); the reciprocal-rank blend cannot reach higher"
            )
        return self


class ScoringConfig(BaseModel):
    """§7 scoring parameters (§14 defaults)."""

    weight_smoothing_alpha: float = Field(default=0.7, ge=0.0, le=1.0)
    analysis_blend_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    fusion_blend_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    scope_bonus: float = Field(default=3.0)
    category_match: float = Field(default=5.0)
    category_mismatch: float = Field(default=-10.0)
    style_affinity: float = Field(default=5.0)
    language_support_bonus: float = Field(default=2.0)
    language_manual_penalty: float = Field(default=-2.0)
    missing_axis_default: float = Field(default=5.0, ge=0.0, le=10.0)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _check_blend(self) -> ScoringConfig:
        total = self.analysis_blend_weight + self.fusion_blend_weight
        if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise ValueError(
                f"analysis/fusion blend weights must sum to 1.0 ± {WEIGHT_SUM_TOLERANCE} "
                f"(analysis_blend_weight={self.analysis_blend_weight}, "
                f"fusion_blend_weight={self.fusion_blend_weight}, sum={total})"
            )
        return self


class SelectionConfig(BaseModel):
    """§8 thresholds and caps (§14 defaults)."""

    primary_score_threshold: float = Field(default=50.0, ge=0.0, le=100.0)
    supporting_score_threshold: float = Field(default=40.0, ge=0.0, le=100.0)
    near_tie_margin: float = Field(default=5.0, ge=0.0, le=100.0)
    max_supporting: int = Field(default=3, ge=0)
    max_parts: int = Field(default=8, ge=1)

    model_config = {"extra": "forbid"}


class LoopConfig(BaseModel):
    """§11 generate/evaluate loop parameters (§14 defaults)."""

    max_tries: int = Field(default=2, ge=1)
    min_quality_score: float = Field(default=50.0, ge=0.0, le=100.0)

    model_config = {"extra": "forbid"}


class PathsConfig(BaseModel):
    """Catalog and docs locations (repo-relative by default)."""

    pattern_directory: str = Field(default="pattern")
    docs_directory: str = Field(default="docs")

    model_config = {"extra": "forbid"}


class JobsConfig(BaseModel):
    """Job-store location; ``DESIGN_PATTERN_JOBS_DB`` overrides it at runtime."""

    db_path: str = Field(default="~/.config/design-pattern-mcp/jobs.db")

    model_config = {"extra": "forbid"}


class ValidationConfig(BaseModel):
    """Self-healing structured-output retry policy (§4 rule 1)."""

    max_retries: int = Field(
        default=1, ge=0, le=10,
        description="Repair attempts after a failed structured call (initial call excluded).",
    )
    retry_on_fail: bool = Field(
        default=True,
        description="Master switch for the repair retry; False makes every call single-shot.",
    )
    truncation_rerun: Literal["repair", "boost"] = Field(
        default="repair",
        description=(
            "What happens when a response is cut by the provider token ceiling "
            "(finish_reason=length) and does not parse (§4 rule 1a). 'repair' (shipped "
            "default) = the failed payload enters the normal repair retry. 'boost' = "
            "truncation-first: no repair re-call into the same ceiling; exactly one rerun with "
            "truncation_boost_max_completion_tokens, a second truncation raises "
            "LLMError(failure_kind='truncated')."
        ),
    )
    truncation_boost_max_completion_tokens: int = Field(
        default=65536, ge=1024,
        description="Completion budget of the boost rerun (MiniMax M2.x recommended cap).",
    )

    model_config = {"extra": "forbid"}


class TasksConfig(BaseModel):
    """Heartbeat configuration for long-running tools."""

    heartbeat_enabled: bool = Field(
        default=True,
        description="Emit progress notifications from a parallel coroutine during long tool calls.",
    )
    heartbeat_interval_seconds: int = Field(
        default=30, ge=5, le=600,
        description="Heartbeat interval in seconds; must be shorter than the client's idle timeout.",
    )
    deadline_seconds: float = Field(
        default=1800.0, gt=0.0,
        description="Complete execution budget for one tool call / job run (ERR_014 on expiry).",
    )


class PromptConfig(BaseModel):
    """Prompt assembly toggles (§1.3 rule 6 order; latency lever L7)."""

    stable_prefix_first: bool = Field(
        default=False,
        description=(
            "Reorder each operation's user prompt so the schema JSON + static instruction "
            "block (identical across all calls of that operation) leads and every per-run "
            "payload (description, parts, traces) trails — maximizing MiniMax passive "
            "prompt-cache hits (≥512-token stable prefix). False (shipped default) = the "
            "legacy order. Behavior-neutral for the wire contract: prompt CONTENT is identical, "
            "only its ordering changes."
        ),
    )

    model_config = {"extra": "forbid"}


class ServerConfig(BaseModel):
    """Validated server configuration. Unknown keys are rejected (extra=forbid)."""

    logging_level: str = Field(default="INFO")
    logging_format: str = Field(default="json")
    transport: str = Field(default="stdio")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8050, ge=1, le=65535)
    generator: GeneratorConfig = Field(default_factory=GeneratorConfig)
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    dense_cache: DenseCacheConfig = Field(default_factory=DenseCacheConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    selection: SelectionConfig = Field(default_factory=SelectionConfig)
    loop: LoopConfig = Field(default_factory=LoopConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    jobs: JobsConfig = Field(default_factory=JobsConfig)
    tasks: TasksConfig = Field(default_factory=TasksConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    prompts: PromptConfig = Field(default_factory=PromptConfig)
    reasoning: ReasoningConfig = Field(default_factory=ReasoningConfig)
    litellm_log_level: str = Field(
        default="WARNING",
        description="Log level applied to the LiteLLM/httpx/openai loggers (they are noisy at INFO).",
    )

    model_config = {"extra": "forbid"}

    def effective_parameters(self) -> dict[str, Any]:
        """The §14 parameter snapshot logged at startup (inputs of every gated decision)."""
        return {
            "dense_weight": self.retrieval.dense_weight,
            "bm25_weight": self.retrieval.bm25_weight,
            "rrf_k": self.retrieval.rrf_k,
            "dense_cache_mode": self.dense_cache.mode,
            "dense_cache_path": self.dense_cache.path,
            "rerank_top_n": self.reranker.rerank_top_n,
            "rerank_text": self.reranker.rerank_text,
            "min_fusion_score": self.retrieval.min_fusion_score,
            "top_k_candidates": self.retrieval.top_k_candidates,
            "dense_top_k": self.retrieval.dense_top_k,
            "bm25_top_k": self.retrieval.bm25_top_k,
            "max_concurrent_parts": self.retrieval.max_concurrent_parts,
            "weight_smoothing_alpha": self.scoring.weight_smoothing_alpha,
            "analysis_blend_weight": self.scoring.analysis_blend_weight,
            "fusion_blend_weight": self.scoring.fusion_blend_weight,
            "scope_bonus": self.scoring.scope_bonus,
            "category_match": self.scoring.category_match,
            "category_mismatch": self.scoring.category_mismatch,
            "style_affinity": self.scoring.style_affinity,
            "language_support_bonus": self.scoring.language_support_bonus,
            "language_manual_penalty": self.scoring.language_manual_penalty,
            "primary_score_threshold": self.selection.primary_score_threshold,
            "supporting_score_threshold": self.selection.supporting_score_threshold,
            "near_tie_margin": self.selection.near_tie_margin,
            "max_supporting": self.selection.max_supporting,
            "max_parts": self.selection.max_parts,
            "max_tries": self.loop.max_tries,
            "min_quality_score": self.loop.min_quality_score,
            "reasoning_enabled": self.reasoning.enabled,
            "reasoning_max_total_steps": self.reasoning.max_total_steps,
            "prompt_stable_prefix_first": self.prompts.stable_prefix_first,
            "reasoning_phases": {
                phase: {
                    "enabled": strategy.enabled,
                    "pre_llm_thoughts": strategy.pre_llm_thoughts,
                    "tools": list(strategy.tools),
                }
                for phase, strategy in self.reasoning.per_phase.items()
            },
            "generator_timeout_seconds": self.generator.config.timeout_seconds,
            "generator_generation_batch_size": self.generator.config.generation_batch_size,
            "generator_circuit_breaker_failure_threshold": (
                self.generator.config.circuit_breaker_failure_threshold
            ),
            "generator_circuit_breaker_cooldown_seconds": (
                self.generator.config.circuit_breaker_cooldown_seconds
            ),
            "tasks_deadline_seconds": self.tasks.deadline_seconds,
        }


class ConfigManager:
    """Load the JSON config once, expanding {env:VAR}/{env:VAR:-default} placeholders."""

    DEFAULT_CONFIG_PATH: str = "config/config.json"

    _config: ClassVar[dict[str, Any] | None] = None

    @classmethod
    def load_config(cls, config_path: str | None = None) -> dict[str, Any]:
        """Resolve DESIGN_PATTERN_CONFIG_PATH env > argument > DEFAULT_CONFIG_PATH, expand, return."""
        load_dotenv()
        resolved = os.path.expanduser(
            os.environ.get("DESIGN_PATTERN_CONFIG_PATH") or config_path or cls.DEFAULT_CONFIG_PATH
        )
        try:
            with open(resolved, encoding="utf-8") as fh:
                raw: dict[str, Any] = json.load(fh)
        except FileNotFoundError:
            logger.error(
                "Configuration file not found",
                extra={"error": ERROR_CONFIG_NOT_FOUND, "config_path": resolved},
            )
            raise
        except json.JSONDecodeError as exc:
            logger.error(
                "Configuration file is not valid JSON",
                extra={"error": ERROR_INVALID_CONFIG, "config_path": resolved, "details": str(exc)},
            )
            raise ValueError(f"{ERROR_INVALID_CONFIG}: {exc}") from exc
        expanded: dict[str, Any] = expand_env_in_obj(raw)
        cls._config = expanded
        return expanded
