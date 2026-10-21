"""Small shared helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


class QlsError(Exception):
    """User-facing error: printed or returned without a traceback."""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))


def dumps(obj: Any) -> str:
    """Canonical JSON (sorted keys) so hashes of payloads are stable."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
