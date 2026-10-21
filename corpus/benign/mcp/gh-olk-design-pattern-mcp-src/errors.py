"""Error codes and domain-specific exceptions.

Error-code scheme (docs/implementation-guide.md §12):
    ERR_0xx — input / pre-condition failures
    ERR_2xx — pipeline decision failures
    ERR_9xx — infrastructure failures
"""

from __future__ import annotations

from typing import Any, Literal

# Input validation (§1.3, E1/E2).
ERROR_DESCRIPTION_TOO_SHORT = "ERR_001"
ERROR_DESCRIPTION_INVALID = "ERR_002"

# Tool-boundary lookup failures.
ERROR_PATTERNS_NOT_FOUND = "ERR_003"
ERROR_MIN_REQUIREMENTS = "ERR_004"
ERROR_PATTERN_CATALOG = "ERR_013"

# Decomposition (§5 rule 2).
ERROR_TOO_MANY_BOUNDARY_PARTS = "ERR_005"

# Selection (§12 E7).
ERROR_NO_PRIMARY_PATTERN = "ERR_006"

# Generation / evaluation (§12 E12).
ERROR_GENERATION_FAILED = "ERR_007"

# Jobs trio.
ERROR_JOB_NOT_FOUND = "ERR_404"
ERROR_CANCELLED = "ERR_012"

# Infrastructure.
ERROR_CATALOG_INVALID = "ERR_011"
ERROR_CONFIG_INVALID = "ERR_010"
ERROR_LLM_PROVIDER = "ERR_009"
ERROR_RETRIEVAL_UNAVAILABLE = "ERR_008"
ERROR_DEADLINE_EXCEEDED = "ERR_014"


#: Why a structured LLM call failed. ``timeout``/``provider``/``empty_response``/``circuit_open``
#: are transport-side failures and are never repair-prompted; ``validation`` is the only
#: model-output failure eligible for the bounded structured-output repair retry (§4 rule 1).
LLMFailureKind = Literal[
    "timeout", "provider", "empty_response", "circuit_open", "validation", "truncated"
]


class DesignPatternError(Exception):
    """Structured pipeline failure carrying a machine-readable error code.

    Attributes:
        code: one of the ``ERROR_*`` constants; surfaces as the ``ERR_x`` prefix
            of the ToolError message.
        detail: human-readable explanation of what failed.
        hint: optional actionable next step for the calling agent.
        extra: structured payload (e.g. E7's top-3 candidates with scores).
    """

    def __init__(
        self,
        code: str,
        detail: str,
        *,
        hint: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.detail = detail
        self.hint = hint
        self.extra = extra or {}
        message = f"{code}: {detail}"
        if hint:
            message = f"{message} — {hint}"
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Serializable form of the failure (code, detail, hint, extra)."""
        payload: dict[str, Any] = {"code": self.code, "detail": self.detail}
        if self.hint:
            payload["hint"] = self.hint
        if self.extra:
            payload["extra"] = self.extra
        return payload


class JobStateError(RuntimeError):
    """Internal transition-guard signal: a guarded JobsStore transition was rejected
    because the job's current status is outside the setter's guard set."""

    def __init__(self, job_id: str, current_status: str | None = None) -> None:
        self.job_id = job_id
        self.current_status = current_status
        super().__init__(
            f"job {job_id!r} transition rejected (current status: {current_status or 'unknown'})"
        )


class MalformedDesignOverviewError(ValueError):
    """A caller-supplied design payload carries no valid ``overview`` (tool-boundary input).

    Raised by the tool adapters (:mod:`src.tools._adapters`) and mapped onto the input
    validation code ``ERR_002`` by the tool handlers; never raised by the pipeline itself.
    """


class LLMError(DesignPatternError):
    """LLM failure (E-9, code ``ERR_009``) with transport/validation classification.

    Carries the provider identity, the model, the provider's own message and a
    machine-readable :data:`LLMFailureKind`; ``code`` is always
    :data:`ERROR_LLM_PROVIDER`. A subclass of :class:`DesignPatternError` so the pipeline's
    documented fallbacks (E3/E4/E12) catch it.

    Attributes:
        provider: provider name from the generator config (e.g. ``"openai"``); empty when the
            failure happened after the transport call (exhausted repair attempts).
        model: model name from the generator config; empty when unknown.
        failure_kind: transport-side (``timeout``/``provider``/``empty_response``/``circuit_open``)
            or model-output (``validation``) classification.
        error: the error code, always ``ERR_009``.
        provider_message: the provider's own error message.
        extra: structured operation metadata (``operation``, ``elapsed_ms``, ``prompt_chars``,
            ``attempts``, batch/circuit fields). Never carries credentials, prompts or responses.
    """

    def __init__(
        self,
        provider: str = "",
        model: str = "",
        failure_kind: LLMFailureKind = "provider",
        error: str = ERROR_LLM_PROVIDER,
        provider_message: str = "",
        *,
        hint: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.failure_kind = failure_kind
        self.error = error
        self.provider_message = provider_message
        prefix = f"LLM provider {provider} error: " if provider else "LLM error: "
        super().__init__(error, f"{prefix}{provider_message}", hint=hint, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        """Serializable form: the base payload plus provider/model/failure_kind."""
        payload = super().to_dict()
        payload["provider"] = self.provider
        payload["model"] = self.model
        payload["failure_kind"] = self.failure_kind
        return payload
