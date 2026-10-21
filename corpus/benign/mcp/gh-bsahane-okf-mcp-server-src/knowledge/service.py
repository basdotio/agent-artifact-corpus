"""Request-scoped access to the published snapshot, shared by the MCP tools.

Every tool call resolves the snapshot once, so a publish during the call
cannot mix a bundle with another snapshot's index.
"""

import json
import threading
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional

from fastmcp.exceptions import ToolError

from okf_mcp_server.src.knowledge.access import LOCAL_OPERATOR, Identity, allowed
from okf_mcp_server.src.knowledge.embed import (
    Embedder,
    EmbeddingUnavailable,
    get_embedder,
)
from okf_mcp_server.src.knowledge.snapshot import (
    Snapshot,
    SnapshotError,
    current_snapshot,
)
from okf_mcp_server.src.settings import settings
from okf_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()
_audit_lock = threading.Lock()


IDENTITY_STATE_KEY = "okf_identity"


def caller() -> Identity:
    """The identity for this tool call; fails closed.

    With authentication disabled the local operator is trusted (single-user
    pilot). With it enabled, the identity must have been set on the HTTP
    request by the token-validating middleware; tool arguments never carry it.

    Raises:
        ToolError: When authentication is on and no validated identity exists.
    """
    if not settings.ENABLE_AUTH:
        return LOCAL_OPERATOR
    try:
        from fastmcp.server.dependencies import get_http_request

        request = get_http_request()
    except (RuntimeError, ImportError):
        request = None
    state = getattr(request, "scope", {}).get("state", {}) if request else {}
    identity = state.get(IDENTITY_STATE_KEY) if isinstance(state, dict) else None
    if not isinstance(identity, Identity):
        raise ToolError(
            "Knowledge access requires a validated identity; this request has none, "
            "so it fails closed."
        )
    return identity


def require_access() -> Identity:
    """Backwards-compatible name for `caller()`."""
    return caller()


def principals_for(identity: Identity) -> Optional[FrozenSet[str]]:
    """Principals to filter by, or None for a trusted caller (no filtering)."""
    return None if identity.trusted else identity.principals


def can_see(identity: Identity, frontmatter: Dict[str, Any]) -> bool:
    """Whether the caller may see a concept, from its `access` frontmatter."""
    return allowed(identity, frontmatter.get("access"), settings.OKF_DEFAULT_ACCESS)


def audit(tool: str, identity: Identity, **fields: Any) -> None:
    """Record one tool call: who, what and which documents were returned."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "event": f"tool.{tool}",
        "tool": tool,
        "caller": identity.audit(),
        **fields,
    }
    line = json.dumps(record, ensure_ascii=False, default=str)
    logger.info(f"okf.audit {line}")
    if settings.OKF_AUDIT_LOG:
        with _audit_lock, open(settings.OKF_AUDIT_LOG, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def open_snapshot() -> Snapshot:
    """Resolve the published snapshot for this request.

    Raises:
        ToolError: If no snapshot is published.
    """
    try:
        return current_snapshot(Path(settings.OKF_DATA_DIR))
    except SnapshotError as e:
        raise ToolError(str(e)) from e


def search_embedder() -> Optional[Embedder]:
    """The embedder for hybrid search, or None for keyword-only search.

    None when disabled with OKF_SEMANTIC_SEARCH=false, or when the model or
    its libraries are not installed (logged once, not an error).
    """
    if not settings.OKF_SEMANTIC_SEARCH:
        return None
    return _load_embedder()


@lru_cache(maxsize=1)
def _load_embedder() -> Optional[Embedder]:
    try:
        return get_embedder()
    except EmbeddingUnavailable as e:
        logger.warning(f"Semantic search unavailable, using keyword search: {e}")
        return None


def warm_up_search() -> None:
    """Load the embedding model before serving, so no request pays for it.

    A no-op when semantic search is disabled or unavailable.
    """
    embedder = search_embedder()
    if embedder is not None:
        embedder.encode(["warm-up"], "query")
        logger.info("Semantic search ready")
