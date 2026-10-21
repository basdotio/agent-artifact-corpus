"""Fixed-schema SQLite bridge for the additive TypeScript v2 stdio experiment."""

from __future__ import annotations

import json
import math
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from continuation_replay.fingerprint import LogicalRequest, fingerprint
from reference.backend import (
    IssueStore,
    OperationAuthorityExpired,
    OperationConflict,
    OperationIdentity,
    OperationInProgress,
    OperationRetentionExpired,
)
from reference.readback import ReadBack


class SyntheticWatcherFailure(RuntimeError):
    pass


class SyntheticCompensationFailure(RuntimeError):
    pass


def _fail_watcher(_db: sqlite3.Connection, _issue_id: int, _watcher: str) -> None:
    raise SyntheticWatcherFailure("injected watcher failure")


def _fail_compensation(_db: sqlite3.Connection, _issue_id: int) -> None:
    raise SyntheticCompensationFailure("injected rollback failure")


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a nonempty string")
    return value


def _state(
    value: Any, operation_id: str, title: str, mode: str, now_epoch: float
) -> dict[str, Any]:
    fields = {
        "v",
        "operation_id",
        "title",
        "mode",
        "nonce",
        "issued_at",
        "authority_expires_at",
        "replay_expires_at",
    }
    if (
        not isinstance(value, dict)
        or set(value) != fields
        or type(value["v"]) is not int
        or value["v"] != 1
    ):
        raise ValueError("invalid application requestState")
    if value["operation_id"] != operation_id:
        raise ValueError("requestState operation binding mismatch")
    if value["title"] != title or value["mode"] != mode:
        raise ValueError("requestState arguments mismatch")
    _required_string(value["nonce"], "nonce")
    for name in ("issued_at", "authority_expires_at", "replay_expires_at"):
        field = value[name]
        if (
            isinstance(field, bool)
            or not isinstance(field, int | float)
            or not math.isfinite(field)
        ):
            raise ValueError(f"{name} must be finite")
    if value["issued_at"] > now_epoch:
        raise ValueError("issued_at is in the future")
    if value["authority_expires_at"] <= value["issued_at"]:
        raise ValueError("invalid authority deadline")
    if value["replay_expires_at"] <= value["issued_at"]:
        raise ValueError("invalid retention deadline")
    return value


def _apply(store: IssueStore, value: dict[str, Any], now_epoch: float) -> dict[str, Any]:
    if set(value) != {"op", "operation_id", "title", "mode", "body", "state", "responses"}:
        raise ValueError("unsupported bridge apply fields")
    operation_id = _required_string(value["operation_id"], "operation_id")
    title = _required_string(value["title"], "title")
    body = value["body"]
    if not isinstance(body, str):
        raise TypeError("body must be text")
    mode = value["mode"]
    if mode not in {"atomic", "partial"}:
        raise ValueError("unsupported mode")
    state = _state(value["state"], operation_id, title, mode, now_epoch)
    responses = value["responses"]
    expected = {"body": {"_meta": None, "action": "accept", "content": {"body": body}}}
    if responses != expected:
        raise ValueError("unsupported accepted input response")
    principal = _required_string(os.environ.get("WIRE_PRINCIPAL"), "WIRE_PRINCIPAL")
    backend = _required_string(os.environ.get("WIRE_BACKEND_ID"), "WIRE_BACKEND_ID")
    key = bytes.fromhex(
        _required_string(os.environ.get("WIRE_FINGERPRINT_KEY_HEX"), "WIRE_FINGERPRINT_KEY_HEX")
    )
    request_fingerprint = fingerprint(
        LogicalRequest(
            principal=principal,
            tool_id="create_guarded_issue",
            tool_version="1",
            arguments={"operation_id": operation_id, "title": title, "mode": mode},
            continuation_state=json.dumps(state, sort_keys=True, separators=(",", ":")),
            input_responses=responses,
        ),
        key=key,
    )
    common = {
        "identity": OperationIdentity(operation_id, principal, backend),
        "request_fingerprint": request_fingerprint,
        "title": title,
        "body": body,
        "issued_at": float(state["issued_at"]),
        "authority_expires_at": float(state["authority_expires_at"]),
        "replay_expires_at": float(state["replay_expires_at"]),
        "now_epoch": now_epoch,
    }
    if mode == "partial":
        applied = store.apply_partial_issue_once(
            watcher="audit@example.test",
            watcher_operation=_fail_watcher,
            compensation_operation=_fail_compensation,
            **common,
        )
    else:

        def precommit_fault(point: str) -> None:
            if os.environ.get("WIRE_FAULT") == f"exit-{point}":
                os._exit(71 if point == "after-ledger-insert" else 72)

        applied = store.apply_issue_once(**common, fault_hook=precommit_fault)
    return {
        "operationId": operation_id,
        "effectId": applied.effect_id,
        "result": applied.result,
        "replayed": applied.replayed,
        "state": applied.state,
    }


def _status(store: IssueStore, value: dict[str, Any], now_epoch: float) -> dict[str, Any]:
    if set(value) != {"op", "operation_id"}:
        raise ValueError("unsupported bridge status fields")
    operation_id = _required_string(value["operation_id"], "operation_id")
    principal = _required_string(os.environ.get("WIRE_PRINCIPAL"), "WIRE_PRINCIPAL")
    backend = _required_string(os.environ.get("WIRE_BACKEND_ID"), "WIRE_BACKEND_ID")
    identity = OperationIdentity(operation_id, principal, backend)
    readback = ReadBack(
        store,
        principal=principal,
        now=lambda: datetime.fromtimestamp(now_epoch, UTC),
    )
    observation = readback.reconcile_operation(identity)
    return {
        "operationId": operation_id,
        "principal": principal,
        "backend": backend,
        "observedAt": observation.observed_at,
        "authoritative": observation.authoritative,
        "freshWriteAuthorized": False,
        "scope": observation.scope,
        "scopeBinding": {
            "operationId": identity.operation_id,
            "principal": identity.principal,
            "backend": identity.backend,
        },
        "state": observation.state,
        "matchingIds": list(observation.matching_ids),
        "detail": observation.detail,
        "storedResult": observation.stored_result,
    }


def main() -> int:
    try:
        value = json.loads(sys.stdin.read(65537))
        if not isinstance(value, dict):
            raise TypeError("bridge input must be an object")
        now_epoch = float(_required_string(os.environ.get("WIRE_CLOCK_EPOCH"), "WIRE_CLOCK_EPOCH"))
        if not math.isfinite(now_epoch):
            raise ValueError("clock must be finite")
        db_path = Path(_required_string(os.environ.get("WIRE_SERVER_DB"), "WIRE_SERVER_DB"))
        backend = _required_string(os.environ.get("WIRE_BACKEND_ID"), "WIRE_BACKEND_ID")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        store = IssueStore(str(db_path), backend_id=backend)
        try:
            if value.get("op") == "apply":
                result = _apply(store, value, now_epoch)
            elif value.get("op") == "status":
                result = _status(store, value, now_epoch)
            else:
                raise ValueError("unsupported bridge operation")
        finally:
            store.close()
        print(json.dumps({"ok": True, "result": result}, separators=(",", ":")))
        return 0
    except (
        ValueError,
        TypeError,
        OperationConflict,
        OperationAuthorityExpired,
        OperationRetentionExpired,
        OperationInProgress,
    ) as exc:
        print(
            json.dumps(
                {"ok": False, "error": type(exc).__name__, "detail": str(exc)},
                separators=(",", ":"),
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
