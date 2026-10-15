"""Procedure retrieval for sonic-kb."""

from __future__ import annotations

import re

from ._loader import load_procedure, load_procedure_index
from ._resolver import resolve_def_refs


def get_procedure(procedure_id: str, step_id: str | None = None) -> dict | None:
    data = load_procedure(procedure_id)
    if data is None:
        return None
    data = resolve_def_refs(data)
    _enrich_steps(data)
    if step_id:
        for step in data.get("steps", []):
            if step.get("step_id") == step_id:
                return {"procedure_id": procedure_id, "step": step}
        return None
    return data


def _enrich_steps(proc: dict) -> None:
    """Add verification hints to each procedure step."""
    for step in proc.get("steps", []):
        cmd = step.get("command", "")
        if not cmd:
            continue
        entity = _infer_entity(cmd)
        if entity:
            step["verify_hint"] = {
                "tool": "verify_action",
                "args": {"action": cmd, "entity_type": entity},
                "note": "Call verify_action to see what this command does under the hood.",
            }


def _infer_entity(cmd: str) -> str | None:
    """Infer entity type from a command string for verify_action hints."""
    c = cmd.lower()
    for pattern, entity in [
        (r"\bvlan\b", "vlan"),
        (r"\bportchannel\b|\blag\b", "lag"),
        (r"\binterface\b|\bmtu\b|\bspeed\b", "port"),
        (r"\broute\b|\bbgp\b", "route"),
        (r"\bacl\b", "acl"),
        (r"\bvxlan\b", "tunnel"),
    ]:
        if re.search(pattern, c):
            return entity
    return None


def list_procedures() -> list[dict]:
    index = load_procedure_index()
    return [{"procedure_id": pid, **meta} for pid, meta in index.items()]
