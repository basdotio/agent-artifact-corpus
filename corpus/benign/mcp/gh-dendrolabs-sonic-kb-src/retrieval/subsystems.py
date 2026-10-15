"""Subsystem and daemon retrieval for sonic-kb."""

from __future__ import annotations

from ._loader import (
    load_all_definitions,
    load_daemon_index,
    load_subsystem,
    load_subsystem_index,
)
from ._resolver import resolve_def_refs


def get_daemon_info(daemon_name: str) -> dict | None:
    """Look up a daemon by process name or def_id."""
    all_defs = load_all_definitions()
    daemon_key = daemon_name if daemon_name.startswith("daemon:") else f"daemon:{daemon_name}"
    if daemon_key in all_defs:
        return all_defs[daemon_key]
    for did, d in all_defs.items():
        if did.startswith("daemon:") and d.get("process_name", "") == daemon_name:
            return d
    idx = load_daemon_index()
    return idx.get(daemon_name) or idx.get(daemon_key)


def get_subsystem_info(subsystem_id: str) -> dict | None:
    data = load_subsystem(subsystem_id)
    if data is None:
        return None
    return resolve_def_refs(data)


def list_containers() -> list[dict]:
    """Return all SONiC containers sorted by startup order."""
    index = load_subsystem_index()
    containers = []
    for sub_id, meta in index.items():
        containers.append({"subsystem_id": sub_id, **meta})
    containers.sort(key=lambda c: c.get("startup_order", 99))
    return containers
