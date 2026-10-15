"""Guards against runaway use: per-hub rate limits and per-call caps.

A model in a loop ("volume up... still quiet... volume up...") can send a lot
of IR in a few seconds, and an activity start/stop loop can wear out a TV's
power relay. The schema caps one call (repeat <= 10, hold <= 3 s); these
token buckets cap the *rate* across calls, per hub.

A token bucket holds up to ``capacity`` tokens and refills at ``rate`` per
second. Each press (or activity change) takes one. A call that needs more
tokens than are there is refused whole, with how long to wait, rather than
half-sent: half a "volume up x5" is worse than none.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

# Presses per hub: a burst of 20, then 4 per second sustained.
PRESS_CAPACITY, PRESS_RATE = 20.0, 4.0
# Activity changes (start or power off) per hub: 4 in a burst, then one per 15 s.
ACTIVITY_CAPACITY, ACTIVITY_RATE = 4.0, 1 / 15
# Per call.
MAX_REPEAT = 10
MAX_HOLD_MS = 3000
MIN_DELAY_MS, MAX_DELAY_MS = 100, 2000
MAX_CALL_SECONDS = 15.0  # repeat * (hold + delay) for one send_command


@dataclass
class TokenBucket:
    capacity: float
    rate: float  # tokens per second
    clock: Callable[[], float] = time.monotonic
    tokens: float = field(init=False)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = self.capacity
        self._last = self.clock()

    def _refill(self) -> None:
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self._last) * self.rate)
        self._last = now

    def take(self, n: float = 1.0) -> float:
        """Take n tokens and return 0.0, or take nothing and return the seconds until n are available."""
        self._refill()
        if n > self.capacity:
            return float("inf")
        if self.tokens >= n:
            self.tokens -= n
            return 0.0
        return (n - self.tokens) / self.rate
