"""FastMCP server exposing the whole Manager.io surface under tick-box control.

Twelve generic tools cover every resource the connected Manager instance has
(~310 of them), instead of hundreds of per-resource tools. What each tool may
touch is decided by the permission matrix, which the user edits in the local
control panel and this server re-reads on every call.
"""

from __future__ import annotations

import functools
from typing import Any

from fastmcp import FastMCP

from manager_full_mcp import __version__, engine
from manager_full_mcp.attachments import ConversionError, prepare
from manager_full_mcp.catalog import GROUP_LABELS, OPS
from manager_full_mcp.config import load_registry, permissions_file
from manager_full_mcp.engine import PermissionDenied
from manager_full_mcp.permissions import ALLOW, ASK
from manager_full_mcp.panel import start_panel

mcp = FastMCP(
    "manager-full-mcp",
    version=__version__,
    website_url="https://www.manager.io/",
    instructions=(
        "Manager.io bookkeeping across any number of businesses. Every resource "
        "the instance exposes is reachable, but each read/create/update/delete is "
        "gated by tick boxes the user controls in a local panel. When something is "
        "refused, say which box to tick and offer open_permissions_panel; never "
        "work around it. Before creating or updating, fetch a similar record with "
        "manager_get and copy its field names — Manager's schema is not guessable. "
        "Confirm with the user before deleting anything. Resources marked "
        "risk='high' (chart of accounts, tax codes, exchange rates, opening "
        "balances, lock date, business settings) reshape the whole ledger rather "
        "than record one transaction: state exactly what will change and get an "
        "explicit yes before writing to them, even when the box is ticked."
    ),
)

_READ = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True}
_WRITE = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False,
          "openWorldHint": True}
_DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False,
                "openWorldHint": True}


def _guard(fn):
    """Turn permission denials into a readable answer instead of a crash.

    functools.wraps keeps the real signature visible, which is what FastMCP
    reads to build each tool's input schema.
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return await fn(*args, **kwargs)
        except PermissionDenied as denied:
            return denied.payload()

    return wrapper


@mcp.tool(
    description=(
        "List the Manager businesses this connection can reach, with their ids. "
        "Every other tool takes an optional 'business' argument; it can be left "
        "out when only one business is configured."
    ),
    annotations=_READ,
)
async def list_businesses() -> dict[str, Any]:
    registry = load_registry()
    return {
        "ok": True,
        "businesses": [b.public() for b in registry.businesses],
        "count": len(registry.businesses),
        "hint": (
            "Add or edit businesses with open_permissions_panel — access tokens "
            "are typed into the local panel, never into chat."
        ),
    }


@mcp.tool(
    description=(
        "Open the local permissions control panel in the browser and return its "
        "URL. That panel is where the user ticks which resources this connection "
        "may read, create, update or delete, and where businesses and their "
        "access tokens are added. Changes apply immediately, no restart."
    ),
    annotations=_READ,
)
async def open_permissions_panel(open_browser: bool = True) -> dict[str, Any]:
    url = start_panel(open_browser=open_browser)
    return {
        "ok": True,
        "url": url,
        "note": (
            "The link only works on this machine and carries a one-time token for "
            "this session. Tick what should be allowed, press Save, and retry."
        ),
    }


@mcp.tool(
    description=(
        "Browse the resource catalog of a business: every document, list, report "
        "and setting the Manager instance exposes, with the operations allowed by "
        "the current tick boxes. Start here when you do not know a resource name. "
        "Filter with 'search' (e.g. 'invoice', 'tax') or 'group'."
    ),
    annotations=_READ,
)
async def manager_catalog(
    business: str | None = None,
    search: str | None = None,
    group: str | None = None,
    allowed_only: bool = False,
    limit: int = 80,
) -> dict[str, Any]:
    session = await engine.get_session(business)
    session.refresh_policy()
    items = session.catalog.search(search or "")
    if group:
        wanted = group.strip().casefold().replace(" ", "_")
        items = [r for r in items if r.group == wanted]
    rows = []
    for res in sorted(items, key=lambda r: (r.group, r.label.lower())):
        grants = session.policy.grants_for(res)
        if allowed_only and all(mode == "deny" for mode in grants.values()):
            continue
        rows.append(
            {
                "resource": res.name,
                "label": res.label,
                "group": res.group,
                "supports": [op for op in OPS if res.supports(op)],
                "allowed": [op for op in OPS if grants[op] == ALLOW],
                "ask_first": [op for op in OPS if grants[op] == ASK],
                "locked": res.locked,
                "risk": res.risk,
                "risk_note": res.risk_note,
                "description": res.description,
            }
        )
    return {
        "ok": True,
        "business": session.business.name,
        "total_matching": len(rows),
        "returned": rows[:limit],
        "truncated": len(rows) > limit,
        "groups": GROUP_LABELS,
    }


@mcp.tool(
    description=(
        "Show what this connection is currently allowed to do for a business: "
        "the totals per operation, where the rules come from, and the full list "
        "of resources with write access. Use it before telling the user something "
        "is not possible."
    ),
    annotations=_READ,
)
async def manager_permissions(business: str | None = None) -> dict[str, Any]:
    session = await engine.get_session(business)
    session.refresh_policy()
    by_group: dict[str, dict[str, int]] = {}
    high_risk: list[str] = []
    ask_count = 0
    for res in session.catalog.resources.values():
        modes = session.policy.grants_for(res)
        allowed = [op for op in ("create", "update", "delete") if modes[op] == ALLOW]
        asked = [op for op in ("create", "update", "delete") if modes[op] == ASK]
        if not allowed and not asked:
            continue
        row = by_group.setdefault(GROUP_LABELS.get(res.group, res.group),
                                  {"allowed": 0, "ask_first": 0})
        row["allowed"] += len(allowed)
        row["ask_first"] += len(asked)
        if asked:
            ask_count += 1
        if res.risk == "high" and allowed:
            high_risk.append(f"{res.name}({'/'.join(allowed)})")

    # Hundreds of resources can be writable; send counts, not a wall of names.
    # manager_catalog answers questions about a specific resource.
    sample = sorted(high_risk)[:12]
    if len(high_risk) > 12:
        sample.append(f"… and {len(high_risk) - 12} more")
    return {
        "ok": True,
        **session.policy.summary(session.catalog),
        "business_name": session.business.name,
        "write_access_by_group": by_group,
        "high_risk_writes_allowed_silently": sample,
        "high_risk_warning": (
            "These rewrite the structure of the books (accounts, tax codes, "
            "exchange rates, opening balances, lock date, settings). Confirm each "
            "change with the user before making it."
        ) if high_risk else "No high-risk write permissions are allowed silently.",
        "ask_first_resources": ask_count,
        "ask_first_note": (
            "Operations set to 'ask' go ahead only after the user approves a "
            "confirmation dialog on their screen. Tell them what you are about to "
            "do before triggering one."
        ),
        "permissions_file": str(permissions_file(session.business.id)),
        "change_with": "open_permissions_panel",
    }


@mcp.tool(
    description=(
        "Search or page any Manager collection, report feed or list "
        "(customers, sales_invoices, payments, tax_codes, general ledger feeds, …). "
        "'term' searches, 'sort_by' takes a column name, and date feeds accept "
        "from_date / to_date (YYYY-MM-DD). Unsupported parameters are reported "
        "back rather than silently dropped."
    ),
    annotations=_READ,
)
@_guard
async def manager_list(
    resource: str,
    business: str | None = None,
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
    session = await engine.get_session(business)
    return await engine.list_records(
        session,
        resource,
        term=term,
        skip=skip,
        page_size=page_size,
        sort_by=sort_by,
        sort_by_desc=sort_by_desc,
        fields=fields,
        from_date=from_date,
        to_date=to_date,
        extra_params=extra_params,
    )


@mcp.tool(
    description=(
        "Fetch one record by its Key (GUID) in the exact shape Manager stores it. "
        "Always do this before an update, and use an existing record as the "
        "template for a create — Manager's field names are not guessable."
    ),
    annotations=_READ,
)
@_guard
async def manager_get(
    resource: str, key: str, business: str | None = None
) -> dict[str, Any]:
    session = await engine.get_session(business)
    return await engine.get_record(session, resource, key)


@mcp.tool(
    description=(
        "Create a record (invoice, payment, customer, journal entry, tax code, …). "
        "'fields' is Manager-native JSON: copy the shape from manager_get on an "
        "existing record of the same resource. Returns the new Key. For resources "
        "the catalog marks risk='high', get an explicit yes from the user first."
    ),
    annotations=_WRITE,
)
@_guard
async def manager_create(
    resource: str, fields: dict[str, Any], business: str | None = None
) -> dict[str, Any]:
    session = await engine.get_session(business)
    return await engine.create_record(session, resource, fields)


@mcp.tool(
    description=(
        "Update a record. For resources the catalog marks risk='high' (accounts, "
        "tax codes, rates, opening balances, settings) confirm with the user "
        "first — those changes restate existing books. "
        "Default mode 'merge' reads the live document first and "
        "changes only the fields you pass, which is what you normally want because "
        "Manager's PUT replaces the whole document. Use mode='replace' to send the "
        "body verbatim."
    ),
    annotations=_WRITE,
)
@_guard
async def manager_update(
    resource: str,
    key: str,
    fields: dict[str, Any],
    business: str | None = None,
    mode: str = "merge",
) -> dict[str, Any]:
    session = await engine.get_session(business)
    return await engine.update_record(session, resource, key, fields, mode=mode)


@mcp.tool(
    description=(
        "Delete a record permanently. Manager has no undo, so confirm with the "
        "user first; the deleted document is returned in the response so it can be "
        "re-created if needed."
    ),
    annotations=_DESTRUCTIVE,
)
@_guard
async def manager_delete(
    resource: str, key: str, business: str | None = None
) -> dict[str, Any]:
    session = await engine.get_session(business)
    return await engine.delete_record(session, resource, key)


@mcp.tool(
    description=(
        "Escape hatch: GET any Manager API path directly (e.g. '/customers' or "
        "'/sales-invoice-form/{key}'). Only for paths the catalog does not model. "
        "Requires 'Raw read' in the control panel."
    ),
    annotations=_READ,
)
@_guard
async def manager_api_get(
    path: str, business: str | None = None, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    session = await engine.get_session(business)
    session.refresh_policy()
    if not session.policy.raw_read:
        return {
            "ok": False,
            "error": "permission_denied",
            "message": "Raw read is unticked in the control panel.",
        }
    body = await session.client.get(path, params=params)
    return {"ok": True, "business": session.business.name, "path": path, "body": body}


@mcp.tool(
    description=(
        "Escape hatch: send any method (POST/PUT/DELETE) to any Manager API path. "
        "Bypasses per-resource tick boxes, so it requires the separate 'Raw write' "
        "box in the control panel. Prefer manager_create / manager_update."
    ),
    annotations=_WRITE,
)
@_guard
async def manager_api_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    business: str | None = None,
) -> dict[str, Any]:
    session = await engine.get_session(business)
    session.refresh_policy()
    if method.upper() == "GET":
        return await manager_api_get(path, business)
    if not session.policy.raw_write:
        return {
            "ok": False,
            "error": "permission_denied",
            "message": (
                "Raw write is unticked in the control panel. Tick 'Raw write to any "
                "API path' there, or use manager_create / manager_update instead."
            ),
        }
    result = await session.client.request(method, path, json=body)
    return {
        "ok": True,
        "business": session.business.name,
        "method": method.upper(),
        "path": path,
        "body": result,
    }


@mcp.tool(
    description=(
        "Turn a file into something Manager will accept as evidence. Manager's "
        "Image field silently rejects PDFs, so ALWAYS run this on any PDF before "
        "attaching it: it rasterises every page and returns the image paths. "
        "Images pass through untouched. combine='vertical' (or 'horizontal') "
        "joins the pages of ONE document — a statement, a contract — into a "
        "single image, which is the right shape when the pages are one document. "
        "Leave combine='none' when the PDF holds several different documents, and "
        "never merge two different proofs into one image: each proof is its own "
        "attachment."
    ),
    annotations=_READ,
)
async def prepare_attachment(
    file_path: str, dpi: int = 150, combine: str = "none"
) -> dict[str, Any]:
    try:
        return prepare(file_path, dpi=dpi, combine=combine).payload()
    except ConversionError as exc:
        return {"ok": False, "error": "conversion_failed", "message": str(exc)}


@mcp.tool(
    description=(
        "Re-read the Manager instance's own API description and rebuild the "
        "resource catalog. Run this after upgrading Manager or when a resource "
        "seems missing."
    ),
    annotations=_READ,
)
async def refresh_catalog(business: str | None = None) -> dict[str, Any]:
    session = await engine.get_session(business, refresh_catalog=True)
    return {
        "ok": True,
        "business": session.business.name,
        "resources": len(session.catalog.resources),
        "api_version": session.catalog.api_version,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
