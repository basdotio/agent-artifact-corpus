"""Process-local provider circuit breaker and failure classification.

The breaker is per :class:`~src.agent.DesignAgent` (one instance per configured
provider/model pair) and keeps no shared state: no Redis, no gateway, no cross-process
coordination. Its only job is to stop burning the full provider-call budget on a provider that
is already failing — after ``failure_threshold`` qualifying failures in a row the next call is
rejected locally for ``cooldown_seconds``; then exactly one half-open probe decides whether the
provider recovered.

Only transport-side failures count: timeouts, connection errors, HTTP 408/429, HTTP >= 500 and
empty responses. Authentication/configuration 4xx responses are the operator's problem, not a
provider outage, so they leave the breaker closed.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

#: Circuit states. ``half_open`` admits exactly one probe call.
CircuitState = Literal["closed", "open", "half_open"]


def extract_status_code(exc: BaseException) -> int | None:
    """Best-effort HTTP status of a provider exception, or ``None`` when it carries none.

    LiteLLM/provider SDK exceptions expose the status on ``status_code`` (or ``code``) and,
    for some wrappers, on ``response.status_code``.
    """
    for attribute in ("status_code", "code"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    if response is not None:
        value = getattr(response, "status_code", None)
        if isinstance(value, int):
            return value
    return None


def is_circuit_qualifying_status(status_code: int | None) -> bool:
    """Whether an HTTP status counts toward opening the circuit.

    Qualifying: no status at all (connection/transport failure), 408, 429 and every >= 500.
    Non-qualifying: the remaining 4xx (authentication, permission, malformed request) — those
    repeat identically until the configuration changes.
    """
    if status_code is None:
        return True
    return status_code in (408, 429) or status_code >= 500


@dataclass(frozen=True)
class CircuitDecision:
    """Outcome of :meth:`ProviderCircuitBreaker.before_call`."""

    state: CircuitState
    allowed: bool
    retry_after_seconds: float
    previous_state: CircuitState

    @property
    def transitioned(self) -> bool:
        """True when this call changed the circuit state (open -> half-open, …)."""
        return self.state != self.previous_state


class ProviderCircuitBreaker:
    """Closed/open/half-open breaker over one provider/model pair.

    Args:
        failure_threshold: Consecutive qualifying failures that open the circuit (>= 1).
        cooldown_seconds: Time an open circuit rejects calls before one half-open probe
            is admitted (> 0).
        clock: Injectable monotonic clock (tests drive it explicitly).
    """

    def __init__(
        self,
        failure_threshold: int,
        cooldown_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if cooldown_seconds <= 0.0:
            raise ValueError("cooldown_seconds must be > 0")
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._state: CircuitState = "closed"
        self._consecutive_failures = 0
        self._opened_at = 0.0
        self._probe_in_flight = False

    @property
    def state(self) -> CircuitState:
        """Current state (without advancing the clock)."""
        return self._state

    @property
    def consecutive_failures(self) -> int:
        """Consecutive qualifying failures since the last success."""
        return self._consecutive_failures

    @property
    def cooldown_seconds(self) -> float:
        """Configured open-state cooldown."""
        return self._cooldown_seconds

    def before_call(self) -> CircuitDecision:
        """Decide whether the next provider call may run.

        Returns:
            A :class:`CircuitDecision`; ``allowed`` is False while the circuit is open or while
            the single half-open probe is still in flight.
        """
        previous = self._state
        if self._state == "open":
            remaining = self._cooldown_seconds - (self._clock() - self._opened_at)
            if remaining > 0.0:
                return CircuitDecision("open", False, remaining, previous)
            self._state = "half_open"
            self._probe_in_flight = True
            return CircuitDecision("half_open", True, 0.0, previous)
        if self._state == "half_open":
            if self._probe_in_flight:
                return CircuitDecision("half_open", False, self._cooldown_seconds, previous)
            self._probe_in_flight = True
            return CircuitDecision("half_open", True, 0.0, previous)
        return CircuitDecision("closed", True, 0.0, previous)

    def record_success(self) -> None:
        """Close the circuit and reset the failure counter."""
        self._state = "closed"
        self._consecutive_failures = 0
        self._probe_in_flight = False

    def record_failure(self) -> None:
        """Count one qualifying failure; reopen immediately from half-open."""
        self._consecutive_failures += 1
        self._probe_in_flight = False
        if self._state == "half_open" or self._consecutive_failures >= self._failure_threshold:
            self._state = "open"
            self._opened_at = self._clock()

    def state_after_call(self) -> CircuitState:
        """Current state (log field for the per-call provider log line)."""
        return self._state
