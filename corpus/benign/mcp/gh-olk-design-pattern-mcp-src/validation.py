"""Self-healing structured-output validation (§4 rule 1, §7.1, §12).

When a model response cannot be parsed as JSON or fails schema validation, this module
formats the failure into a correction instruction and re-issues the call — at most
``max_retries`` times, each repair carrying the previous validation error. The retry is
bounded on purpose: the deterministic E3/E4/E12 fallbacks own the failure afterwards.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from pydantic import BaseModel, ValidationError

from src.errors import DesignPatternError, LLMError

logger = logging.getLogger(__name__)

#: Appended to the user prompt of every repair attempt (§4 rule 1).
RETRY_INSTRUCTION = (
    "Your previous response could not be parsed as JSON or failed schema validation. "
    "Return ONLY the corrected JSON payload matching the requested schema — "
    "no prose, no markdown, no explanations."
)


def format_validation_errors(exc: ValidationError) -> str:
    """Format a Pydantic ``ValidationError`` into a human-readable correction note."""
    lines = ["The following fields failed validation:"]
    for err in exc.errors():
        loc = ".".join(str(item) for item in err["loc"])
        lines.append(f"  - {loc}: {err['msg']} (got: {repr(err['input'])[:80]})")
    return "\n".join(lines)


def _format_failure(exc: Exception) -> str:
    """Human-readable description of one failed attempt."""
    if isinstance(exc, ValidationError):
        return format_validation_errors(exc)
    if isinstance(exc, DesignPatternError):
        return exc.detail
    return str(exc)


async def validate_with_retries[ModelT: BaseModel](
    initial_caller: Callable[[], Awaitable[ModelT]],
    repair_caller: Callable[[str, str], Awaitable[ModelT]],
    response_schema: type[ModelT],
    *,
    operation: str,
    max_retries: int = 3,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
) -> ModelT:
    """Generate a structured response with a self-healing repair retry on output failures only.

    Calls ``initial_caller`` for the first attempt. On a model-output failure
    (:class:`ValueError`, Pydantic ``ValidationError`` or a non-LLM
    :class:`DesignPatternError`), calls ``repair_caller`` with the original system prompt and
    a user prompt extended by the previous failure — up to ``max_retries`` times.
    :class:`LLMError` is re-raised immediately: a provider timeout, provider exception, empty
    response or open circuit is a transport failure, and an identical second call only burns
    another provider-call budget.

    Args:
        initial_caller: Zero-arg async callable performing the first attempt.
        repair_caller: Async callable(system_prompt, user_prompt) performing exactly one
            further attempt per call.
        response_schema: Pydantic model class used for validation (error reporting).
        operation: Logical operation label (``"generate"``, ``"brief_and_parts"``, …) recorded
            in the aggregate failure metadata.
        max_retries: Maximum repair attempts (default 3).
        system_prompt: Original system prompt (forwarded unchanged to ``repair_caller``).
        user_prompt: Original user prompt (base of every repaired prompt).

    Returns:
        The validated model instance of the first successful attempt.

    Raises:
        LLMError: When the provider failed (``failure_kind`` set by the transport seam, re-raised
            unchanged) or every attempt failed validation (``failure_kind="validation"``);
            code ``ERR_009`` in both cases.
    """
    base_user_prompt = user_prompt if user_prompt is not None else ""
    base_system_prompt = system_prompt if system_prompt is not None else ""
    started = time.monotonic()
    last_error: Exception | None = None
    try:
        return await initial_caller()
    except LLMError:
        raise
    except (ValueError, DesignPatternError) as exc:
        last_error = exc

    for attempt in range(max_retries):
        if last_error is None:
            raise RuntimeError("validate_with_retries: entered the repair loop without a failure")
        repaired_user = (
            f"{base_user_prompt}\n\n{RETRY_INSTRUCTION}\n"
            f"Previous validation error:\n{_format_failure(last_error)}"
        )
        logger.warning(
            "LLM %s output failed validation (attempt %d/%d): %s",
            response_schema.__name__,
            attempt + 1,
            max_retries,
            _format_failure(last_error),
        )
        try:
            return await repair_caller(base_system_prompt, repaired_user)
        except LLMError:
            raise
        except (ValueError, DesignPatternError) as exc:
            last_error = exc

    raise LLMError(
        failure_kind="validation",
        provider_message=(
            f"LLM {response_schema.__name__} output did not validate after the initial call and "
            f"{max_retries} repair attempt(s); last error: "
            f"{_format_failure(last_error) if last_error else 'unknown'}"
        ),
        hint="the pipeline's E3/E4/E12 fallback semantics own this failure from here",
        extra={
            "operation": operation,
            "attempts": max_retries + 1,
            "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
            "last_validation_error": _format_failure(last_error) if last_error else "unknown",
        },
    )
