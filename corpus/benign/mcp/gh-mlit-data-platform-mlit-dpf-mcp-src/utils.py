import asyncio
import logging
import time
import uuid
import random
from pythonjsonlogger import jsonlogger

# ---------- logger JSON ----------
logger = logging.getLogger("mlit_mcp")
_handler = logging.StreamHandler()
_formatter = jsonlogger.JsonFormatter("%(levelname)s %(message)s %(asctime)s %(name)s")
_handler.setFormatter(_formatter)
logger.setLevel(logging.INFO)
logger.addHandler(_handler)


def new_request_id() -> str:
    return uuid.uuid4().hex


class Timer:
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.elapsed_ms = (time.perf_counter() - self.t0) * 1000.0


# ---------- token-bucket rate limiter ----------
class RateLimiter:
    """
    Simple per-instance token-bucket.
    - capacity = rps (min 1)
    - refill_rate = rps tokens/second
    """
    def __init__(self, rps: float):
        self.capacity = max(1.0, float(rps))
        self.tokens = self.capacity
        self.refill_rate = float(rps)
        self.last = time.perf_counter()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """
        Wait until at least 1 token is available, then consume 1 token.
        Implementation ensures token is ALWAYS decremented by 1 even if it sleeps.
        """
        async with self._lock:
            while True:
                now = time.perf_counter()
                elapsed = now - self.last
                self.last = now

                # refill
                self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)

                if self.tokens >= 1.0:
                    self.tokens -= 1.0  # konsumsi
                    return
                # butuh tunggu
                missing = 1.0 - self.tokens
                sleep_s = missing / self.refill_rate if self.refill_rate > 0 else 0.01
                # cap supaya tidak terlalu lama sleep dalam satu loop
                await asyncio.sleep(max(0.0, min(sleep_s, 1.0)))


# ---------- backoff helper ----------
async def backoff_sleep(attempt: int, *, base: float = 1.0, cap: float = 8.0, jitter: float = 0.3):
    """
    Exponential backoff with jitter.
    attempt: 0,1,2,... → delay = min(cap, base * 2**attempt) ± jitter%
    """
    delay = min(cap, base * (2 ** attempt))
    if jitter:
        # jitter ± (jitter * delay)
        delta = delay * jitter
        delay = max(0.0, delay + random.uniform(-delta, delta))
    await asyncio.sleep(delay)


# ---------- string/bytes helpers ----------
def safe_truncate_bytes(s: str, limit_bytes: int) -> str:
    """
    Truncate string based on byte limit (UTF-8) to avoid cutting in the middle of multi-byte char.
    """
    raw = s.encode("utf-8")
    if len(raw) <= limit_bytes:
        return s
    trimmed = raw[:limit_bytes]
    # coba decode; jika gagal, buang byte terakhir hingga valid
    while True:
        try:
            return trimmed.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            trimmed = trimmed[:-1]
            if not trimmed:
                return ""
