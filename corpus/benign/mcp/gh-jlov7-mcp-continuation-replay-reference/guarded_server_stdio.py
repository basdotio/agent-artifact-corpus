"""Guarded MCP stdio server for the frozen completion experiment.

This server is separate from ``server_stdio.py`` so the historical unguarded
controls stay unchanged. It combines the SDK's request-state integrity boundary
with a durable application operation ledger before dispatching local effects.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import secrets
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import mcp.server.request_state as request_state_module
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.request_state import RequestStateSecurity
from mcp.shared.exceptions import MCPError
from mcp_types import INVALID_PARAMS, ElicitRequest, ElicitRequestFormParams, InputRequiredResult

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

TOOL_ID = "create_guarded_issue"
TOOL_VERSION = "1"


@dataclass(frozen=True, slots=True)
class Settings:
    db_path: Path
    backend_id: str
    principal: str
    now_epoch: float
    authority_ttl: float
    replay_retention_ttl: float
    request_state_ttl: float
    state_key: bytes
    fingerprint_key: bytes
    fault: str


class _FrozenTime:
    value = 0.0

    @classmethod
    def time(cls) -> float:
        return cls.value


class SyntheticWatcherFailure(RuntimeError):
    """Injected second-step failure for the bounded partial-effect case."""


class SyntheticCompensationFailure(RuntimeError):
    """Injected rollback failure for the bounded partial-effect case."""


def _fail_watcher(_conn: sqlite3.Connection, _issue_id: int, _watcher: str) -> None:
    raise SyntheticWatcherFailure("injected watcher failure")


def _fail_compensation(_conn: sqlite3.Connection, _issue_id: int) -> None:
    raise SyntheticCompensationFailure("injected issue rollback failure")


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def _positive_float(name: str) -> float:
    try:
        value = float(_required(name))
    except ValueError as exc:
        raise SystemExit(f"{name} must be numeric") from exc
    if not math.isfinite(value) or value <= 0:
        raise SystemExit(f"{name} must be positive")
    return value


def _key(name: str) -> bytes:
    try:
        value = bytes.fromhex(_required(name))
    except ValueError as exc:
        raise SystemExit(f"{name} must be hexadecimal") from exc
    if len(value) < 32:
        raise SystemExit(f"{name} must contain at least 32 bytes")
    return value


def load_settings() -> Settings:
    try:
        now_epoch = float(_required("WIRE_CLOCK_EPOCH"))
    except ValueError as exc:
        raise SystemExit("WIRE_CLOCK_EPOCH must be numeric") from exc
    if not math.isfinite(now_epoch):
        raise SystemExit("WIRE_CLOCK_EPOCH must be finite")
    return Settings(
        db_path=Path(_required("WIRE_SERVER_DB")),
        backend_id=_required("WIRE_BACKEND_ID"),
        principal=_required("WIRE_PRINCIPAL"),
        now_epoch=now_epoch,
        authority_ttl=_positive_float("WIRE_AUTHORITY_TTL"),
        replay_retention_ttl=_positive_float("WIRE_REPLAY_RETENTION_TTL"),
        request_state_ttl=_positive_float("WIRE_REQUEST_STATE_TTL"),
        state_key=_key("WIRE_STATE_KEY_HEX"),
        fingerprint_key=_key("WIRE_FINGERPRINT_KEY_HEX"),
        fault=os.environ.get("WIRE_FAULT", ""),
    )


def _ask(title: str) -> ElicitRequest:
    return ElicitRequest(
        params=ElicitRequestFormParams(
            message=f"Body for {title}?",
            requested_schema={
                "type": "object",
                "properties": {"body": {"type": "string"}},
                "required": ["body"],
            },
        )
    )


def _accepted_body(responses: object) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(responses, dict):
        raise MCPError(code=INVALID_PARAMS, message="invalid input responses")
    resp = responses.get("body")
    if resp is None:
        return None
    if hasattr(resp, "model_dump"):
        resp = resp.model_dump(by_alias=True, exclude_none=False)
    if not isinstance(resp, dict):
        raise MCPError(code=INVALID_PARAMS, message="invalid body response")
    action = resp.get("action")
    action = getattr(action, "value", action)
    content = resp.get("content")
    if (
        action != "accept"
        or not isinstance(content, dict)
        or not isinstance(content.get("body"), str)
    ):
        raise MCPError(code=INVALID_PARAMS, message="body response must be accepted text")
    body = str(content["body"])
    return body, {"body": {"_meta": None, "action": "accept", "content": {"body": body}}}


def _parse_state(raw: str, operation_id: str) -> dict[str, Any]:
    try:
        state = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise MCPError(code=INVALID_PARAMS, message="invalid application requestState") from exc
    expected_keys = {
        "v",
        "operation_id",
        "nonce",
        "issued_at",
        "authority_expires_at",
        "replay_expires_at",
    }
    if (
        not isinstance(state, dict)
        or set(state) != expected_keys
        or state.get("v") != 1
        or state.get("operation_id") != operation_id
    ):
        raise MCPError(code=INVALID_PARAMS, message="requestState operation binding mismatch")
    if not isinstance(state.get("nonce"), str) or not state["nonce"]:
        raise MCPError(code=INVALID_PARAMS, message="requestState nonce missing")
    for key in ("issued_at", "authority_expires_at", "replay_expires_at"):
        value = state.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(float(value))
        ):
            raise MCPError(code=INVALID_PARAMS, message=f"requestState {key} is invalid")
    issued_at = float(state["issued_at"])
    if issued_at > _FrozenTime.value:
        raise MCPError(code=INVALID_PARAMS, message="requestState issued_at is in the future")
    if float(state["authority_expires_at"]) <= issued_at:
        raise MCPError(code=INVALID_PARAMS, message="requestState authority deadline is invalid")
    if float(state["replay_expires_at"]) <= issued_at:
        raise MCPError(code=INVALID_PARAMS, message="requestState replay deadline is invalid")
    return state


def build_server(
    store: IssueStore, settings: Settings, *, principal_for_request: Callable[[], str] | None = None
) -> MCPServer:
    principal = principal_for_request or (lambda: settings.principal)
    security = RequestStateSecurity(
        keys=[settings.state_key],
        ttl=settings.request_state_ttl,
        bind_principal=lambda _ctx: principal(),
        audience="guarded-wire-reference",
    )
    mcp = MCPServer("guarded-wire-reference", request_state_security=security)

    def precommit_fault(point: str) -> None:
        # Lab-only hard exits at named transaction cut points. SQLite rolls back
        # the uncommitted ledger and issue rows on process termination.
        if settings.fault == f"exit-{point}":
            os._exit(
                {
                    "after-ledger-insert": 71,
                    "after-issue-insert": 72,
                    "after-partial-first-commit": 73,
                }[point]
            )

    @mcp.tool(name="get_operation_status")
    async def get_operation_status(operation_id: str, ctx: Context | None = None) -> dict[str, Any]:
        if ctx is None or not operation_id:
            raise MCPError(code=INVALID_PARAMS, message="operation_id and context are required")
        identity = OperationIdentity(operation_id, principal(), settings.backend_id)
        readback = ReadBack(
            store,
            principal=identity.principal,
            now=lambda: datetime.fromtimestamp(settings.now_epoch, UTC),
        )
        observation = readback.reconcile_operation(identity)
        return {
            "operationId": identity.operation_id,
            "principal": identity.principal,
            "backend": identity.backend,
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

    @mcp.tool(name=TOOL_ID)
    async def create_guarded_issue(
        operation_id: str,
        title: str,
        mode: Literal["atomic", "partial"] = "atomic",
        ctx: Context | None = None,
    ) -> dict[str, str | int | bool] | InputRequiredResult:
        if ctx is None:
            raise MCPError(code=INVALID_PARAMS, message="request context is required")
        if not operation_id or not title:
            raise MCPError(code=INVALID_PARAMS, message="operation_id and title are required")
        if ctx.input_responses is None:
            if ctx.request_state is not None:
                raise MCPError(code=INVALID_PARAMS, message="requestState without input responses")
            state = {
                "v": 1,
                "operation_id": operation_id,
                "nonce": secrets.token_hex(16),
                "issued_at": settings.now_epoch,
                "authority_expires_at": settings.now_epoch + settings.authority_ttl,
                "replay_expires_at": settings.now_epoch + settings.replay_retention_ttl,
            }
            return InputRequiredResult(
                input_requests={"body": _ask(title)},
                request_state=json.dumps(state, sort_keys=True, separators=(",", ":")),
            )
        if ctx.request_state is None:
            raise MCPError(
                code=INVALID_PARAMS,
                message="unsupported continuation: input responses require requestState",
            )
        state = _parse_state(ctx.request_state, operation_id)
        accepted = _accepted_body(ctx.input_responses)
        if accepted is None:
            if settings.now_epoch >= float(state["authority_expires_at"]):
                raise MCPError(code=INVALID_PARAMS, message="operation_authority_expired")
            return InputRequiredResult(
                input_requests={"body": _ask(title)}, request_state=ctx.request_state
            )
        body, normalized_responses = accepted
        request_fingerprint = fingerprint(
            LogicalRequest(
                principal=principal(),
                tool_id=TOOL_ID,
                tool_version=TOOL_VERSION,
                arguments={"operation_id": operation_id, "title": title, "mode": mode},
                continuation_state=ctx.request_state,
                input_responses=normalized_responses,
            ),
            key=settings.fingerprint_key,
        )
        identity = OperationIdentity(operation_id, principal(), settings.backend_id)
        common = {
            "identity": identity,
            "request_fingerprint": request_fingerprint,
            "title": title,
            "body": body,
            "issued_at": float(state["issued_at"]),
            "authority_expires_at": float(state["authority_expires_at"]),
            "replay_expires_at": float(state["replay_expires_at"]),
            "now_epoch": settings.now_epoch,
        }
        try:
            if mode == "partial":
                result = store.apply_partial_issue_once(
                    watcher="audit@example.test",
                    watcher_operation=_fail_watcher,
                    compensation_operation=_fail_compensation,
                    fault_hook=precommit_fault,
                    **common,
                )
            else:
                result = store.apply_issue_once(**common, fault_hook=precommit_fault)
        except OperationConflict as exc:
            raise MCPError(code=INVALID_PARAMS, message="operation_conflict") from exc
        except OperationAuthorityExpired as exc:
            raise MCPError(code=INVALID_PARAMS, message="operation_authority_expired") from exc
        except OperationRetentionExpired as exc:
            raise MCPError(code=INVALID_PARAMS, message="operation_retention_expired") from exc
        except OperationInProgress as exc:
            raise MCPError(code=INVALID_PARAMS, message="operation_in_progress") from exc
        if settings.fault == "drop-after-commit" and not result.replayed:
            os._exit(70)
        return {
            "operationId": operation_id,
            "effectId": result.effect_id,
            "result": result.result,
            "replayed": result.replayed,
            "state": result.state,
        }

    return mcp


def main() -> None:
    settings = load_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    _FrozenTime.value = settings.now_epoch
    request_state_module.time = _FrozenTime  # type: ignore[assignment]
    store = IssueStore(str(settings.db_path), backend_id=settings.backend_id)
    asyncio.run(build_server(store, settings).run_stdio_async())


if __name__ == "__main__":
    main()
