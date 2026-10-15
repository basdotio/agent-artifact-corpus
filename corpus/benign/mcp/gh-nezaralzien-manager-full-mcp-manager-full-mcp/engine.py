"""Business sessions: client + catalog + permission policy, with hot reload."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from manager_full_mcp.catalog import Catalog, Resource, build_catalog
from manager_full_mcp.client import ManagerClient
from manager_full_mcp.config import (
    Business,
    load_cached_catalog,
    load_registry,
    save_catalog,
)
from manager_full_mcp.approval import (
    DENY as ANSWER_DENY,
    GRANTS,
    ONCE,
    REMEMBER,
    UNAVAILABLE,
    ApprovalRequest,
    ask,
)
from manager_full_mcp.permissions import (
    ALLOW,
    ASK,
    Policy,
    load_policy,
    policy_is_stale,
)

HIGH_RISK_CAUTION = (
    "HIGH-RISK RESOURCE: this changes the structure of the books, not a single "
    "transaction, and Manager has no undo. Tell the user exactly what changed."
)


def _caution(res: Resource, result: dict[str, Any]) -> dict[str, Any]:
    if res.risk == "high":
        result["caution"] = f"{HIGH_RISK_CAUTION} {res.risk_note}".strip()
    return result


class PermissionDenied(Exception):
    """Refused: the box is off, or the user said no to the confirmation."""

    def __init__(
        self,
        message: str,
        *,
        resource: str,
        op: str,
        business: str,
        error: str = "permission_denied",
    ) -> None:
        super().__init__(message)
        self.resource = resource
        self.op = op
        self.business = business
        self.error = error

    def payload(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": self.error,
            "business": self.business,
            "resource": self.resource,
            "operation": self.op,
            "message": str(self),
        }


def summarize_fields(fields: dict[str, Any], limit: int = 10) -> str:
    """A short, human-readable preview of a body for the approval dialog."""
    lines: list[str] = []
    for key, value in list(fields.items())[:limit]:
        if isinstance(value, dict):
            text = f"<{len(value)} field(s)>"
        elif isinstance(value, list):
            text = f"<{len(value)} line(s)>"
        else:
            text = str(value)
        lines.append(f"  {key}: {text[:60]}{'…' if len(text) > 60 else ''}")
    if len(fields) > limit:
        lines.append(f"  … and {len(fields) - limit} more field(s)")
    return "\n".join(lines) or "  (empty)"


@dataclass
class Session:
    business: Business
    client: ManagerClient
    catalog: Catalog
    policy: Policy

    def refresh_policy(self) -> None:
        """Pick up panel edits without restarting the MCP host."""
        if policy_is_stale(self.policy):
            self.policy = load_policy(self.business.id, self.catalog)

    def resource(self, name: str) -> Resource:
        key = name.strip().replace("-", "_").casefold()
        found = self.catalog.get(key)
        if found:
            return found
        matches = self.catalog.search(name)
        hint = ", ".join(sorted(m.name for m in matches)[:10])
        raise ValueError(
            f"Unknown resource '{name}' for business '{self.business.name}'. "
            + (f"Did you mean: {hint}? " if hint else "")
            + "Use manager_catalog to browse resource names."
        )

    async def require(self, res: Resource, op: str, details: str = "") -> None:
        """Enforce the tick box: allow, deny, or stop and ask the user."""
        self.refresh_policy()
        mode = self.policy.decide(res, op)
        if mode == ALLOW:
            return
        if mode != ASK:
            raise PermissionDenied(
                self.policy.denial_reason(res, op),
                resource=res.name,
                op=op,
                business=self.business.id,
            )
        if GRANTS.is_granted(self.business.id, res.name, op):
            return
        answer = await ask(
            ApprovalRequest(
                business=self.business.name,
                resource_label=res.label,
                resource=res.name,
                operation=op,
                details=details,
                risk_note=res.risk_note,
            )
        )
        if answer == REMEMBER:
            GRANTS.remember(self.business.id, res.name, op)
            return
        if answer == ONCE:
            return
        if answer == UNAVAILABLE:
            raise PermissionDenied(
                f"'{op}' on '{res.name}' is set to Ask first, but no confirmation "
                "dialog could be shown on this machine. Change the box to Allow in "
                "the permissions panel if you want this without a prompt.",
                resource=res.name,
                op=op,
                business=self.business.id,
                error="approval_unavailable",
            )
        raise PermissionDenied(
            f"The user declined the confirmation for '{op}' on '{res.name}'. "
            "Nothing was written. Do not retry unless they ask you to.",
            resource=res.name,
            op=op,
            business=self.business.id,
            error="approval_declined",
        )


_SESSIONS: dict[str, Session] = {}


def clear_sessions() -> None:
    _SESSIONS.clear()


def _no_business_message(ref: str | None) -> str:
    registry = load_registry()
    names = [b.name for b in registry.businesses if b.enabled]
    if not names:
        return (
            "No Manager business is configured yet. Ask me to open the permissions "
            "panel (open_permissions_panel), then add a business with its API URL "
            "and access token."
        )
    listed = ", ".join(names)
    if ref:
        return f"No business matches '{ref}'. Configured businesses: {listed}."
    return (
        "Several businesses are configured, so name one with the 'business' "
        f"argument. Configured: {listed}."
    )


async def get_session(ref: str | None = None, *, refresh_catalog: bool = False) -> Session:
    registry = load_registry()
    business = registry.resolve(ref)
    if business is None or not business.enabled:
        raise ValueError(_no_business_message(ref))

    cached = _SESSIONS.get(business.id)
    if cached and not refresh_catalog:
        if (
            cached.business.api_url == business.api_url
            and cached.business.api_key == business.api_key
        ):
            cached.refresh_policy()
            return cached
        await cached.client.aclose()

    client = ManagerClient(business)
    catalog = None if refresh_catalog else load_cached_catalog(business.id)
    if catalog is None:
        doc = await client.openapi()
        catalog = build_catalog(doc, built_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
        save_catalog(business.id, catalog)
    session = Session(
        business=business,
        client=client,
        catalog=catalog,
        policy=load_policy(business.id, catalog),
    )
    _SESSIONS[business.id] = session
    return session


def extract_items(body: Any) -> tuple[list[Any], int | None]:
    """Manager list responses are envelopes: {"customers": [...], "totalRecords": n}."""
    if isinstance(body, list):
        return body, len(body)
    if not isinstance(body, dict):
        return [], None
    total = body.get("totalRecords")
    for key, value in body.items():
        if isinstance(value, list):
            return value, total if isinstance(total, int) else None
    return [], total if isinstance(total, int) else None


async def list_records(
    session: Session,
    resource: str,
    *,
    term: str | None = None,
    skip: int = 0,
    page_size: int = 50,
    sort_by: str | None = None,
    sort_by_desc: bool | None = None,
    fields: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    res = session.resource(resource)
    await session.require(res, "read", details=f"  list {resource}"
                          + (f" matching '{term}'" if term else ""))
    if not res.list_path:
        raise ValueError(
            f"'{res.name}' has no list endpoint; fetch it by key with manager_get."
        )
    wanted = {
        "term": term,
        "skip": skip,
        "pageSize": page_size,
        "sortBy": sort_by,
        "sortByDesc": sort_by_desc,
        "fields": fields,
        "fromDate": from_date,
        "toDate": to_date,
        **(extra_params or {}),
    }
    allowed = set(res.list_params)
    params = {k: v for k, v in wanted.items() if v is not None and k in allowed}
    ignored = sorted(
        k for k, v in wanted.items() if v is not None and k not in allowed
    )
    body = await session.client.get(res.list_path, params=params)
    items, total = extract_items(body)
    out: dict[str, Any] = {
        "ok": True,
        "business": session.business.name,
        "resource": res.name,
        "items": items,
        "count": len(items),
        "total_records": total,
        "skip": skip,
        "page_size": page_size,
        "has_more": (skip + len(items) < total) if isinstance(total, int) else None,
    }
    if ignored:
        out["ignored_params"] = ignored
        out["supported_params"] = res.list_params
    return out


async def get_record(session: Session, resource: str, key: str) -> dict[str, Any]:
    res = session.resource(resource)
    await session.require(res, "read", details=f"  record {key}")
    if not res.form_path:
        raise ValueError(
            f"'{res.name}' is a list-only feed with no per-record form; use manager_list."
        )
    body = await session.client.get(f"{res.form_path}/{key}")
    return {
        "ok": True,
        "business": session.business.name,
        "resource": res.name,
        "key": key,
        "body": body,
    }


async def create_record(
    session: Session, resource: str, fields: dict[str, Any]
) -> dict[str, Any]:
    res = session.resource(resource)
    if not isinstance(fields, dict) or not fields:
        raise ValueError(
            f"create on '{res.name}' needs a non-empty JSON body. "
            "Fetch an existing record with manager_get to see the shape."
        )
    await session.require(res, "create", details=summarize_fields(fields))
    body = await session.client.post(res.form_path or "", json=fields)
    key = body.get("Key") if isinstance(body, dict) else None
    return _caution(res, {
        "ok": True,
        "business": session.business.name,
        "resource": res.name,
        "created_key": key,
        "body": body,
    })


async def update_record(
    session: Session,
    resource: str,
    key: str,
    fields: dict[str, Any],
    *,
    mode: str = "merge",
) -> dict[str, Any]:
    res = session.resource(resource)
    if mode not in {"merge", "replace"}:
        raise ValueError("mode must be 'merge' or 'replace'.")
    await session.require(
        res,
        "update",
        details=f"  record: {key}\n  mode: {mode}\n" + summarize_fields(fields),
    )
    path = f"{res.form_path}/{key}"
    payload = dict(fields)
    before: Any = None
    if mode == "merge":
        # Manager PUT replaces the whole document, so merge onto the live one.
        before = await session.client.get(path)
        if isinstance(before, dict):
            payload = {**before, **fields}
    body = await session.client.put(path, json=payload)
    return _caution(res, {
        "ok": True,
        "business": session.business.name,
        "resource": res.name,
        "key": key,
        "mode": mode,
        "changed_fields": sorted(fields.keys()),
        "body": body if body is not None else {"Key": key},
    })


async def delete_record(session: Session, resource: str, key: str) -> dict[str, Any]:
    res = session.resource(resource)
    snapshot: Any = None
    try:
        snapshot = await session.client.get(f"{res.form_path}/{key}")
    except Exception:  # deletion should not fail because the preview failed
        snapshot = None
    await session.require(
        res,
        "delete",
        details=f"  record: {key}\n"
        + (summarize_fields(snapshot, 6) if isinstance(snapshot, dict) else "  (record not readable)"),
    )
    body = await session.client.delete(f"{res.form_path}/{key}")
    return _caution(res, {
        "ok": True,
        "business": session.business.name,
        "resource": res.name,
        "key": key,
        "deleted": True,
        "deleted_record": snapshot,
        "body": body,
    })
