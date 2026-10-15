"""Definition resolver -- inlines def_refs into retrieval results.

The deduplication contract: write once in definitions/, reference by def_id
everywhere else, resolve at query time.
"""

from __future__ import annotations

from ._loader import load_all_definitions


def resolve_def_refs(obj: dict) -> dict:
    """Inline def_refs into an object, adding a 'resolved_defs' key.

    If obj has no def_refs, returns it unchanged.
    Missing def_ids produce an error marker in the output.
    """
    refs = obj.get("def_refs", [])
    if not refs:
        return obj
    all_defs = load_all_definitions()
    resolved = {}
    for ref in refs:
        resolved[ref] = all_defs.get(ref, {"error": f"def_id '{ref}' not found in definitions/"})
    return {**obj, "resolved_defs": resolved}


def resolve_single_def(def_id: str) -> dict | None:
    """Look up a single definition by def_id."""
    return load_all_definitions().get(def_id)


def list_definitions_by_type(def_type: str) -> list[dict]:
    """Return all definitions whose def_id starts with a given type prefix.

    e.g., list_definitions_by_type("timer") returns all timer:* definitions.
    """
    prefix = f"{def_type}:"
    return [d for did, d in load_all_definitions().items() if did.startswith(prefix)]
