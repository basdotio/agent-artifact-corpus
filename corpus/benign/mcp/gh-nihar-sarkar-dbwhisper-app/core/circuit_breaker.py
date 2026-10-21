"""Circuit breaker pattern for LLM provider resilience."""

import time
import logging
import functools
from typing import Callable, Optional, Dict

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker that trips after N failures and recovers after timeout."""

    def __init__(self, name: str, threshold: int = 5, timeout: int = 60):
        self.name = name
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure = 0.0
        self.state = "closed"  # closed, open, half-open

    def _trip(self) -> None:
        self.state = "open"
        self.last_failure = time.time()
        logger.warning("Circuit breaker OPEN for %s", self.name)

    def _reset(self) -> None:
        self.state = "closed"
        self.failures = 0
        logger.info("Circuit breaker CLOSED for %s", self.name)

    def call(self, func: Callable) -> Callable:
        """Decorator / wrapper for async functions."""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "open":
                if time.time() - self.last_failure < self.timeout:
                    raise RuntimeError(f"Circuit breaker OPEN for {self.name}: try fallback provider")
                self.state = "half-open"
                logger.info("Circuit breaker HALF-OPEN for %s", self.name)

            try:
                result = await func(*args, **kwargs)
                if self.state == "half-open":
                    self._reset()
                self.failures = 0
                return result
            except Exception as e:
                self.failures += 1
                self.last_failure = time.time()
                if self.failures >= self.threshold:
                    self._trip()
                raise

        return wrapper


class CircuitBreakerRegistry:
    """Global registry of circuit breakers per provider."""

    _breakers: Dict[str, CircuitBreaker] = {}

    @classmethod
    def get(cls, name: str, threshold: Optional[int] = None, timeout: Optional[int] = None) -> CircuitBreaker:
        if name not in cls._breakers:
            from app.util.config import settings
            cls._breakers[name] = CircuitBreaker(
                name,
                threshold=threshold or settings.CIRCUIT_BREAKER_THRESHOLD,
                timeout=timeout or settings.CIRCUIT_BREAKER_TIMEOUT,
            )
        return cls._breakers[name]
