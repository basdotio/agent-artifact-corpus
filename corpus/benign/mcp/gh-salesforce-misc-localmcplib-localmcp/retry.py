"""Bounded retries for transient model and gateway errors."""

from __future__ import annotations

import asyncio
import random
import re
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import anthropic
import openai
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

from localmcp.observability.logging import get_logger

log = get_logger(__name__)

RetryCallback = Callable[[int, float, BaseException], None]

_RATE_LIMIT_STATUS = 429

# LiteLLM-style gateways report request-per-minute caps as a 429 whose message
# embeds the window reset instant, e.g. "... Limit resets at: 2026-09-03
# 01:11:46 UTC", without a Retry-After header. A few seconds of exponential
# backoff never outlasts such a window, so the delay waits for the reset instead.
# The gateway controls the message's capitalization, so match it case-insensitively.
_RESET_AT_PATTERN = re.compile(r"limit resets at:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*UTC", re.IGNORECASE)

# The reset instant comes from an untrusted error message, so a garbled or
# hostile far-future value is capped at a ceiling no legitimate per-minute
# window exceeds, independently of the caller's max_delay.
_MAX_RESET_DELAY_SECONDS = 120.0


def is_rate_limit_error(exc: BaseException) -> bool:
    """Return True when ``exc`` is a provider or gateway 429 rejection."""
    if isinstance(exc, (anthropic.RateLimitError, openai.RateLimitError)):
        return True
    return getattr(exc, "status_code", None) == _RATE_LIMIT_STATUS


def is_retryable_error(exc: BaseException) -> bool:
    """Return True for transient model errors worth retrying with backoff.

    Covers rate limits, 5xx responses, and connection or timeout faults.
    Deterministic failures such as validation errors or unknown models are
    excluded so a retry never hides them behind repeated attempts.
    """
    if is_rate_limit_error(exc):
        return True
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and status >= 500:
        return True
    # Each SDK's timeout error subclasses its connection error.
    return isinstance(exc, (anthropic.APIConnectionError, openai.APIConnectionError))


def _retry_after_seconds(exc: BaseException) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    raw = headers.get("retry-after")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


def _reset_after_seconds(exc: BaseException, *, now: datetime | None = None) -> float | None:
    """Seconds until a gateway rate-limit window reopens, parsed from ``exc``.

    Returns ``None`` when the error carries no recognizable reset instant. A
    window already in the past yields ``0.0``.
    """
    match = _RESET_AT_PATTERN.search(str(exc))
    if match is None:
        return None
    try:
        reset_at = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None
    reference = now or datetime.now(UTC)
    return min(_MAX_RESET_DELAY_SECONDS, max(0.0, (reset_at - reference).total_seconds()))


def rate_limit_delay(exc: BaseException, attempt: int, *, base_delay: float, max_delay: float) -> float:
    """Seconds to wait before retrying after attempt ``attempt`` (1-based) raised ``exc``.

    A rate limit with a ``Retry-After`` header waits exactly that long. One
    whose message embeds a ``Limit resets at: ... UTC`` instant waits until the
    window reopens plus a jittered buffer, so concurrent callers do not stampede
    it. Both are bounded by ``max_delay``. Every other error uses capped
    exponential backoff with jitter.
    """
    if is_rate_limit_error(exc):
        retry_after = _retry_after_seconds(exc)
        if retry_after is not None:
            return min(retry_after, max_delay)
        reset_after = _reset_after_seconds(exc)
        if reset_after is not None:
            return min(reset_after + 1.0 + random.random(), max_delay)
    backoff = base_delay * float(2 ** (attempt - 1))
    jitter = backoff * 0.25 * random.random()
    return min(backoff + jitter, max_delay)


def _validate_policy(max_attempts: int, base_delay: float, max_delay: float) -> None:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if base_delay < 0 or max_delay < 0:
        raise ValueError("retry delays must not be negative")
    if base_delay > max_delay:
        raise ValueError("base_delay must not exceed max_delay")


async def call_with_rate_limit_retry[T](
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int,
    base_delay: float,
    max_delay: float,
    on_retry: RetryCallback | None = None,
) -> T:
    """Await ``operation`` with bounded retries for transient errors.

    Non-retryable errors propagate immediately, and the last attempt's error
    propagates unchanged. ``on_retry`` receives the failed attempt number, the
    delay about to elapse, and the error.
    """
    _validate_policy(max_attempts, base_delay, max_delay)
    attempt = 1
    while True:
        try:
            return await operation()
        except Exception as exc:
            if attempt >= max_attempts or not is_retryable_error(exc):
                raise
            delay = rate_limit_delay(exc, attempt, base_delay=base_delay, max_delay=max_delay)
            if on_retry is not None:
                on_retry(attempt, delay, exc)
            await asyncio.sleep(delay)
            attempt += 1


def _log_retry(attempt: int, delay: float, exc: BaseException) -> None:
    log.warning(
        "model_call.retry",
        attempt=attempt,
        delay_seconds=round(delay, 2),
        rate_limited=is_rate_limit_error(exc),
        error_type=type(exc).__name__,
        status_code=getattr(exc, "status_code", None),
    )


class ModelCallRetryMiddleware(AgentMiddleware[Any, Any, Any]):
    """Retry one failed model call on transient errors without restarting the agent run.

    Only the rejected request is repeated, so completed tool calls are neither
    replayed nor charged again. Delays follow :func:`rate_limit_delay`, and
    deterministic errors propagate immediately. It recognizes OpenAI and
    Anthropic SDK errors and gateway-specific rate-limit messages, so one policy
    applies across models and routes. It is separate from
    :class:`~localmcp.structured_output.SubmitResultMiddleware`'s correction
    rounds: it never re-prompts the model, only repeats an identical request. ``on_retry`` replaces the
    default warning log, for example to add application context. An
    enclosing deadline still bounds the total wait.
    """

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 90.0,
        on_retry: RetryCallback | None = None,
    ) -> None:
        super().__init__()
        _validate_policy(max_attempts, base_delay, max_delay)
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._on_retry = on_retry or _log_retry

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        attempt = 1
        while True:
            try:
                return handler(request)
            except Exception as exc:
                if attempt >= self._max_attempts or not is_retryable_error(exc):
                    raise
                delay = rate_limit_delay(exc, attempt, base_delay=self._base_delay, max_delay=self._max_delay)
                self._on_retry(attempt, delay, exc)
                time.sleep(delay)
                attempt += 1

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        return await call_with_rate_limit_retry(
            lambda: handler(request),
            max_attempts=self._max_attempts,
            base_delay=self._base_delay,
            max_delay=self._max_delay,
            on_retry=self._on_retry,
        )
