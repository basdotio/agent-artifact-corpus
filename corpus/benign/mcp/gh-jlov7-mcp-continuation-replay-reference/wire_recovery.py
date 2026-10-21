"""Parse an identity-bound guarded status result for the recovery consumer."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from reference.backend import OperationIdentity
from reference.readback import EffectObservation, result_matches_effect


def observation_from_wire(
    value: Mapping[str, Any], *, expected_identity: OperationIdentity
) -> EffectObservation:
    """Validate a guarded status result before it can settle a consumer."""
    operation_id = value.get("operationId")
    principal = value.get("principal")
    backend = value.get("backend")
    if any(not isinstance(item, str) or not item for item in (operation_id, principal, backend)):
        raise ValueError("wire reconciliation identity fields must be nonempty strings")
    assert isinstance(operation_id, str) and isinstance(principal, str) and isinstance(backend, str)
    identity = OperationIdentity(operation_id, principal, backend)
    if identity != expected_identity:
        raise ValueError("wire reconciliation identity does not match the attempt")
    binding = value.get("scopeBinding")
    if binding != {
        "operationId": identity.operation_id,
        "principal": identity.principal,
        "backend": identity.backend,
    }:
        raise ValueError("wire reconciliation structured scope does not match the attempt")
    if value.get("authoritative") is not True:
        raise ValueError("wire reconciliation result is not authoritative")
    if value.get("freshWriteAuthorized") is not False:
        raise ValueError("wire reconciliation must never authorize a fresh write")
    state = value.get("state")
    if state not in {"not_applied", "applied", "partial", "unknown"}:
        raise ValueError("wire reconciliation state is invalid")
    matching = value.get("matchingIds")
    if not isinstance(matching, list) or any(
        isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in matching
    ):
        raise ValueError("wire reconciliation effect ids are invalid")
    if len(matching) != len(set(matching)):
        raise ValueError("wire reconciliation effect ids are duplicated")
    if len(matching) != (1 if state in {"applied", "partial"} else 0):
        raise ValueError("wire reconciliation state and effect count disagree")
    stored_result = value.get("storedResult")
    if state == "applied" and (not isinstance(stored_result, str) or not stored_result):
        raise ValueError("applied operation lacks a stored result")
    if state in {"unknown", "not_applied"} and stored_result is not None:
        raise ValueError("unsettled operation cannot carry a stored result")
    if state == "partial" and stored_result is not None and not isinstance(stored_result, str):
        raise ValueError("partial operation stored result is invalid")
    if not result_matches_effect(state, tuple(matching), stored_result):
        raise ValueError("wire reconciliation stored result disagrees with state or effect")
    observed_at = value.get("observedAt")
    scope = value.get("scope")
    detail = value.get("detail", "")
    if (
        not isinstance(observed_at, str)
        or not isinstance(scope, str)
        or not scope
        or not isinstance(detail, str)
    ):
        raise ValueError("wire reconciliation metadata is invalid")
    try:
        timestamp = datetime.fromisoformat(observed_at)
    except ValueError as exc:
        raise ValueError("wire reconciliation observation time is invalid") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("wire reconciliation observation time lacks timezone")
    return EffectObservation(
        identity=identity,
        observed_at=observed_at,
        authoritative=True,
        scope=scope,
        state=state,
        matching_ids=tuple(matching),
        detail=detail,
        stored_result=stored_result,
        scope_binding=identity,
    )
