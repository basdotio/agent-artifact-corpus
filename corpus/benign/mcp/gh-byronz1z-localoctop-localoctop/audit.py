"""Server-side call audit log (JSON lines).

Every tools/call — allowed, denied, or errored — appends one record. The
writer is append-only, thread/task-safe via an asyncio.Lock, and failures
never break request serving (they are logged instead).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger("localoctop.audit")

# Retention per task spec v1.1 §7.5: size rotation keeps bounded generations
# (path.1 newest ... path.<MAX_GENERATIONS> oldest); any rotated generation
# older than RETENTION_DAYS is deleted.
MAX_GENERATIONS = 30
RETENTION_DAYS = 30


class AuditLog:
    """Appends JSON-line audit records to a file.

    path="" disables file output (records still flow to the python logger at
    DEBUG, which is handy in tests).
    """

    def __init__(self, path: str, max_bytes: int = 16 * 1024 * 1024):
        self._path = path
        self._max_bytes = max_bytes
        self._lock = asyncio.Lock()

    async def record(
        self,
        *,
        user_id: str,
        method: str,
        path: str = "",
        decision: str,  # allow | deny | error
        code: int = 0,
        detail: str = "",
        duration_ms: float = 0.0,
        client_id: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int(time.time() * 1000) % 1000:03d}Z",
            "user": user_id,
            "method": method,
            "path": path,
            "decision": decision,
            "code": code,
            "detail": detail[:512],
            "duration_ms": round(duration_ms, 2),
            "client_id": client_id,
        }
        if extra:
            rec["extra"] = extra
        logger.debug("audit %s", rec)
        if not self._path:
            return
        line = json.dumps(rec, ensure_ascii=False) + "\n"
        async with self._lock:
            try:
                self._rotate_if_needed()
                d = os.path.dirname(self._path)
                if d:
                    os.makedirs(d, exist_ok=True)
                with open(self._path, "a", encoding="utf-8") as f:  # noqa: ASYNC230 — small, lock-guarded
                    f.write(line)
            except OSError as exc:
                logger.error("audit write failed: %s", exc)

    def _rotate_if_needed(self) -> None:
        try:
            if self._max_bytes > 0 and os.path.getsize(self._path) >= self._max_bytes:
                self._rotate_locked()
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.warning("audit rotation failed: %s", exc)

    def _rotate_locked(self) -> None:
        """Size rotation with 30-generation cap and 30-day retention
        (task spec v1.1 §7.5):         path.N shifts to path.N+1, path becomes
        path.1, stale generations are pruned by mtime."""
        oldest = f"{self._path}.{MAX_GENERATIONS + 1}"
        if os.path.exists(oldest):
            os.remove(oldest)
        for i in range(MAX_GENERATIONS - 1, 0, -1):
            src = f"{self._path}.{i}"
            if os.path.exists(src):
                os.replace(src, f"{self._path}.{i + 1}")
        os.replace(self._path, f"{self._path}.1")
        # Prune rotated generations older than the retention window;
        # generation order matches age order, so stop at the first fresh one.
        cutoff = time.time() - RETENTION_DAYS * 86400
        for i in range(MAX_GENERATIONS, 1, -1):
            p = f"{self._path}.{i}"
            try:
                if os.path.getmtime(p) < cutoff:
                    os.remove(p)
                    logger.info("audit: pruned %s (older than %d days)", p, RETENTION_DAYS)
                else:
                    break
            except FileNotFoundError:
                continue
