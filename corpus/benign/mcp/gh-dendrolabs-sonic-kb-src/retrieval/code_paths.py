"""Code path tracing retrieval for sonic-kb."""

from __future__ import annotations

from ._loader import load_code_path, load_code_path_index
from ._resolver import resolve_def_refs


def trace_config_flow(entity_type: str, action: str | None = None) -> dict | None:
    """Find the code path for a given entity type and action."""
    index = load_code_path_index()
    et = entity_type.lower().replace(" ", "-")
    act = (action or "install").lower()
    path_id = f"{et}-{act}"
    if path_id in index:
        return _load_and_resolve(path_id)
    for pid, meta in index.items():
        if et in pid:
            if action is None or act in pid:
                return _load_and_resolve(pid)
    for pid, meta in index.items():
        if et in meta.get("display_name", "").lower():
            return _load_and_resolve(pid)
    return None


def get_code_path(path_id: str) -> dict | None:
    return _load_and_resolve(path_id)


def list_code_paths() -> list[dict]:
    index = load_code_path_index()
    return [{"path_id": pid, **meta} for pid, meta in index.items()]


def _load_and_resolve(path_id: str) -> dict | None:
    data = load_code_path(path_id)
    if data is None:
        return None
    return resolve_def_refs(data)
