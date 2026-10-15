"""FastMCP server exposing the Plane REST API as MCP tools.

Run over stdio (default, for local MCP clients):

    PLANE_API_KEY=... PLANE_WORKSPACE_SLUG=... python -m plane_mcp

Run over streamable HTTP:

    PLANE_API_KEY=... PLANE_WORKSPACE_SLUG=... python -m plane_mcp --transport http --port 8000
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .client import PlaneAPIError, PlaneClient, summarize_paginated
from .config import ConfigError, Settings

logger = logging.getLogger("plane_mcp")


INSTRUCTIONS = """\
Tools for the Plane project management API. They act as the authenticated user
of the workspace configured through PLANE_WORKSPACE_SLUG.

Conventions:
- A project is referenced by its UUID; a work item by its UUID or by its
  human identifier such as PROJ-123.
- Before creating or updating work items, call list_states and list_labels to
  get the state and label UUIDs; the API expects UUIDs, not names.
- Prefer search_work_items for text queries and list_work_items for browsing a
  single project.
- List tools are paginated: pass the returned next_cursor to fetch the next page.
- Pages exist in two scopes: omit project_id for workspace wiki pages, or pass
  a project_id for that project's pages. Delete a page only after archiving it.
"""

mcp = FastMCP(name="Plane", instructions=INSTRUCTIONS)

_client: PlaneClient | None = None


def get_client() -> PlaneClient:
    """Return a lazily-created, process-wide Plane client.

    Credentials are validated on first use so the server can start (and list
    its tools) even when the environment is not fully configured yet.
    """
    global _client
    if _client is None:
        try:
            _client = PlaneClient(Settings.from_env())
        except ConfigError as exc:
            raise ToolError(str(exc)) from exc
    return _client


async def _call(coro: Any) -> Any:
    """Await a client call, translating API failures into MCP tool errors."""
    try:
        return await coro
    except PlaneAPIError as exc:
        # Give a useful diagnosis when the Pages REST API is not exposed at all.
        # It is absent from the open-source Community Edition entirely (checked
        # v1.3.1, v1.4.2 and master); it exists on Plane Cloud.
        if exc.status_code == 404 and "/pages/" in exc.url:
            raise ToolError(
                "Plane returned 404 for the Pages API. The public Pages REST API is not part "
                "of the open-source Plane Community Edition (it is absent from the API URL "
                "routing in v1.3.1, v1.4.2 and master) — it is a Plane Cloud capability. On a "
                "self-hosted instance, pages live behind an internal session API that does not "
                f"accept API keys. Underlying error: {exc}"
            ) from exc
        raise ToolError(str(exc)) from exc


# --------------------------------------------------------------------- workspace


@mcp.tool
async def get_current_user() -> dict[str, Any]:
    """Return the profile of the user the Plane API key belongs to."""
    client = get_client()
    return await _call(client.me())


@mcp.tool
async def list_workspace_members() -> list[dict[str, Any]]:
    """List every member of the configured workspace.

    Useful for resolving a person's name to the member UUID expected by the
    `assignees` field when creating or updating work items.
    """
    client = get_client()
    return await _call(client.list_members())


# ---------------------------------------------------------------------- projects


@mcp.tool
async def list_projects(
    per_page: int = 20,
    cursor: str | None = None,
    order_by: str | None = None,
    expand: str | None = None,
) -> dict[str, Any]:
    """List projects in the workspace.

    Args:
        per_page: Items per page (1-100, default 20).
        cursor: Pagination cursor from a previous response's `next_cursor`.
        order_by: Field to sort by; prefix with '-' for descending order.
        expand: Comma-separated related fields to expand.
    """
    client = get_client()
    data = await _call(
        client.list_projects(per_page=per_page, cursor=cursor, order_by=order_by, expand=expand)
    )
    return summarize_paginated(data)


@mcp.tool
async def get_project(project_id: str) -> dict[str, Any]:
    """Fetch a single project by its UUID.

    Args:
        project_id: Project UUID (from `list_projects`).
    """
    client = get_client()
    return await _call(client.get_project(project_id))


@mcp.tool
async def create_project(
    name: str,
    identifier: str,
    description: str | None = None,
    project_lead: str | None = None,
    default_assignee: str | None = None,
    emoji: str | None = None,
) -> dict[str, Any]:
    """Create a project.

    Args:
        name: Human-readable project name.
        identifier: Short uppercase key used in work item IDs, e.g. "WEB".
        description: Plain-text project description.
        project_lead: Member UUID of the project lead.
        default_assignee: Member UUID assigned by default.
        emoji: Emoji shown as the project icon.
    """
    client = get_client()
    return await _call(
        client.create_project(
            name=name,
            identifier=identifier,
            description=description,
            project_lead=project_lead,
            default_assignee=default_assignee,
            emoji=emoji,
        )
    )


@mcp.tool
async def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    project_lead: str | None = None,
    default_assignee: str | None = None,
    emoji: str | None = None,
) -> dict[str, Any]:
    """Update the provided fields of a project; omitted fields are left unchanged.

    Args:
        project_id: Project UUID.
        name: New project name.
        description: New plain-text description.
        project_lead: Member UUID to set as project lead.
        default_assignee: Member UUID assigned by default.
        emoji: Emoji shown as the project icon.
    """
    client = get_client()
    return await _call(
        client.update_project(
            project_id,
            name=name,
            description=description,
            project_lead=project_lead,
            default_assignee=default_assignee,
            emoji=emoji,
        )
    )


# -------------------------------------------------------------------- work items


@mcp.tool
async def list_work_items(
    project_id: str,
    per_page: int = 20,
    cursor: str | None = None,
    order_by: str | None = None,
    expand: str | None = None,
) -> dict[str, Any]:
    """List work items in a project (paginated).

    Args:
        project_id: Project UUID.
        per_page: Items per page (1-100, default 20).
        cursor: Pagination cursor from a previous response's `next_cursor`.
        order_by: Field to sort by; prefix with '-' for descending order.
        expand: Comma-separated related fields to expand, e.g. "assignees,state".
    """
    client = get_client()
    data = await _call(
        client.list_work_items(
            project_id, per_page=per_page, cursor=cursor, order_by=order_by, expand=expand
        )
    )
    return summarize_paginated(data)


@mcp.tool
async def get_work_item(project_id: str, work_item_id: str) -> dict[str, Any]:
    """Fetch a work item by project UUID and work item UUID.

    Args:
        project_id: Project UUID.
        work_item_id: Work item UUID. If you only have a human identifier such
            as "PROJ-123", use `get_work_item_by_identifier` instead.
    """
    client = get_client()
    return await _call(client.get_work_item(project_id, work_item_id))


@mcp.tool
async def get_work_item_by_identifier(identifier: str) -> dict[str, Any]:
    """Fetch a work item by its human identifier, e.g. "PROJ-123".

    Args:
        identifier: "<PROJECT_IDENTIFIER>-<sequence_id>", for example "PROJ-123"
            or "MOBINTEGRA-49". The project identifier is the short key shown in
            the Plane UI, not the project name.
    """
    client = get_client()
    return await _call(client.get_work_item_by_identifier(identifier))


@mcp.tool
async def search_work_items(
    search: str,
    project_id: str | None = None,
    limit: int | None = None,
    workspace_search: bool = True,
) -> dict[str, Any]:
    """Search work items by text across names, identifiers and descriptions.

    This is the lightweight, always-available search. For filter-based queries
    use `advanced_search_work_items` instead.

    Args:
        search: Text to look for, e.g. "login" or "MOBINTEGRA-49".
        project_id: Restrict results to one project UUID.
        limit: Maximum number of results.
        workspace_search: Search all projects (default true); set false to
            search only within project_id.
    """
    client = get_client()
    data = await _call(
        client.search_work_items(
            search=search,
            project_id=project_id,
            limit=limit,
            workspace_search=workspace_search,
        )
    )
    issues = data.get("issues", []) if isinstance(data, dict) else data
    return {"results": issues, "count": len(issues)}


@mcp.tool
async def advanced_search_work_items(
    query: str | None = None,
    project_id: str | None = None,
    filters: dict[str, Any] | None = None,
    limit: int | None = None,
    workspace_search: bool = True,
) -> Any:
    """Filtered work item search (Plane's advanced-search endpoint).

    Supports a structured `filters` object in addition to a text `query`. This
    endpoint is permission-gated on some workspaces and editions; if it returns
    403, fall back to `search_work_items` or `list_work_items`.

    Args:
        query: Free-text query matched against work item fields.
        project_id: Restrict results to one project UUID.
        filters: Advanced filter object validated by Plane's filter set.
        limit: Maximum number of results.
        workspace_search: Search all projects (default true).
    """
    client = get_client()
    return await _call(
        client.advanced_search_work_items(
            query=query,
            project_id=project_id,
            filters=filters,
            limit=limit,
            workspace_search=workspace_search,
        )
    )


@mcp.tool
async def create_work_item(
    project_id: str,
    name: str,
    description: str | None = None,
    description_html: str | None = None,
    priority: str | None = None,
    state: str | None = None,
    assignees: list[str] | None = None,
    labels: list[str] | None = None,
    parent: str | None = None,
    start_date: str | None = None,
    target_date: str | None = None,
    estimate_point: str | None = None,
) -> dict[str, Any]:
    """Create a work item in a project.

    Args:
        project_id: Project UUID.
        name: Work item title.
        description: Plain-text description (converted to HTML for you).
        description_html: HTML description; takes precedence over `description`.
        priority: One of "urgent", "high", "medium", "low", "none".
        state: State UUID — use list_states to find it.
        assignees: Member UUIDs — use list_workspace_members to find them.
        labels: Label UUIDs — use list_labels to find them.
        parent: Parent work item UUID, for sub-items.
        start_date: ISO date, e.g. "2026-01-31".
        target_date: ISO date, e.g. "2026-02-15".
        estimate_point: Estimate point UUID.
    """
    client = get_client()
    return await _call(
        client.create_work_item(
            project_id,
            name=name,
            description=description,
            description_html=description_html,
            priority=priority,
            state=state,
            assignees=assignees,
            labels=labels,
            parent=parent,
            start_date=start_date,
            target_date=target_date,
            estimate_point=estimate_point,
        )
    )


@mcp.tool
async def update_work_item(
    project_id: str,
    work_item_id: str,
    name: str | None = None,
    description: str | None = None,
    description_html: str | None = None,
    priority: str | None = None,
    state: str | None = None,
    assignees: list[str] | None = None,
    labels: list[str] | None = None,
    start_date: str | None = None,
    target_date: str | None = None,
    estimate_point: str | None = None,
) -> dict[str, Any]:
    """Update the provided fields of a work item; omitted fields are unchanged.

    `assignees` and `labels` replace the existing lists when provided, so pass
    the complete list you want rather than a single addition.

    Args:
        project_id: Project UUID.
        work_item_id: Work item UUID.
        name: New title.
        description: New plain-text description (converted to HTML for you).
        description_html: New HTML description; takes precedence over `description`.
        priority: One of "urgent", "high", "medium", "low", "none".
        state: State UUID — use `list_states` to find it.
        assignees: Member UUIDs, replacing the current assignees — use
            `list_workspace_members`.
        labels: Label UUIDs, replacing the current labels — use `list_labels`.
        start_date: ISO date, e.g. "2026-01-31".
        target_date: ISO date, e.g. "2026-02-15".
        estimate_point: Estimate point UUID.
    """
    client = get_client()
    return await _call(
        client.update_work_item(
            project_id,
            work_item_id,
            name=name,
            description=description,
            description_html=description_html,
            priority=priority,
            state=state,
            assignees=assignees,
            labels=labels,
            start_date=start_date,
            target_date=target_date,
            estimate_point=estimate_point,
        )
    )


@mcp.tool
async def delete_work_item(project_id: str, work_item_id: str) -> dict[str, Any]:
    """Permanently delete a work item. This cannot be undone.

    Prefer `update_work_item` with a "Cancelled" state when you only mean to
    close the item.

    Args:
        project_id: Project UUID.
        work_item_id: Work item UUID.
    """
    client = get_client()
    await _call(client.delete_work_item(project_id, work_item_id))
    return {"deleted": True, "work_item_id": work_item_id}


# ----------------------------------------------------------------- project metadata


@mcp.tool
async def list_states(project_id: str, per_page: int = 100) -> dict[str, Any]:
    """List a project's workflow states (with their UUIDs and groups).

    Call this before setting the `state` of a work item: the API expects a
    state UUID, not a name like "In Progress".

    Args:
        project_id: Project UUID.
        per_page: Items per page (1-100, default 100).
    """
    client = get_client()
    data = await _call(client.list_states(project_id, per_page=per_page))
    return summarize_paginated(data)


@mcp.tool
async def list_labels(project_id: str, per_page: int = 100) -> dict[str, Any]:
    """List a project's labels (with their UUIDs).

    Use this to resolve label names to the UUIDs expected by the `labels`
    field of work items.

    Args:
        project_id: Project UUID.
        per_page: Items per page (1-100, default 100).
    """
    client = get_client()
    data = await _call(client.list_labels(project_id, per_page=per_page))
    return summarize_paginated(data)


@mcp.tool
async def create_label(
    project_id: str,
    name: str,
    color: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Create a label in a project.

    Args:
        project_id: Project UUID.
        name: Label name.
        color: Hex color, e.g. "#ff4444".
        description: Optional label description.
    """
    client = get_client()
    return await _call(client.create_label(project_id, name=name, color=color, description=description))


@mcp.tool
async def list_cycles(
    project_id: str,
    per_page: int = 20,
    cursor: str | None = None,
    cycle_view: str | None = None,
) -> dict[str, Any]:
    """List a project's cycles (sprints).

    Args:
        project_id: Project UUID.
        per_page: Items per page (1-100).
        cursor: Pagination cursor from a previous response's `next_cursor`.
        cycle_view: Filter by status, e.g. "current", "upcoming", "completed", "draft".
    """
    client = get_client()
    data = await _call(
        client.list_cycles(project_id, per_page=per_page, cursor=cursor, cycle_view=cycle_view)
    )
    return summarize_paginated(data)


@mcp.tool
async def list_modules(
    project_id: str,
    per_page: int = 20,
    cursor: str | None = None,
) -> dict[str, Any]:
    """List a project's modules.

    Args:
        project_id: Project UUID.
        per_page: Items per page (1-100, default 20).
        cursor: Pagination cursor from a previous response's `next_cursor`.
    """
    client = get_client()
    data = await _call(client.list_modules(project_id, per_page=per_page, cursor=cursor))
    return summarize_paginated(data)


# --------------------------------------------------------------------- comments


@mcp.tool
async def list_comments(
    project_id: str, work_item_id: str, per_page: int = 100
) -> dict[str, Any]:
    """List the comments on a work item.

    Args:
        project_id: Project UUID.
        work_item_id: Work item UUID.
        per_page: Items per page (1-100, default 100).
    """
    client = get_client()
    data = await _call(client.list_comments(project_id, work_item_id, per_page=per_page))
    return summarize_paginated(data)


@mcp.tool
async def add_comment(project_id: str, work_item_id: str, comment: str) -> dict[str, Any]:
    """Add a comment to a work item.

    Args:
        project_id: Project UUID.
        work_item_id: Work item UUID.
        comment: Comment body; plain text is wrapped in HTML, or pass raw HTML.
    """
    client = get_client()
    return await _call(client.add_comment(project_id, work_item_id, comment=comment))


@mcp.tool
async def update_comment(
    project_id: str, work_item_id: str, comment_id: str, comment: str
) -> dict[str, Any]:
    """Replace the body of an existing work item comment.

    Args:
        project_id: Project UUID.
        work_item_id: Work item UUID.
        comment_id: Comment UUID (from `list_comments`).
        comment: New body; plain text is wrapped in HTML, or pass raw HTML.
    """
    client = get_client()
    return await _call(
        client.update_comment(project_id, work_item_id, comment_id, comment=comment)
    )


@mcp.tool
async def delete_comment(project_id: str, work_item_id: str, comment_id: str) -> dict[str, Any]:
    """Permanently delete a work item comment. This cannot be undone.

    Args:
        project_id: Project UUID.
        work_item_id: Work item UUID.
        comment_id: Comment UUID (from `list_comments`).
    """
    client = get_client()
    await _call(client.delete_comment(project_id, work_item_id, comment_id))
    return {"deleted": True, "comment_id": comment_id}


# ----------------------------------------------------------------------- pages
#
# Plane has two page families that share one shape:
#   * workspace wiki pages  -> omit project_id
#   * project pages         -> pass project_id

_ACCESS_CODES = {"public": 0, "private": 1}


def _access_code(access: str | int) -> int:
    """Map 'public'/'private' (or 0/1) to the integer Plane expects."""
    if isinstance(access, bool):
        raise ToolError("access must be 'public' or 'private'.")
    if isinstance(access, int):
        if access in (0, 1):
            return access
        raise ToolError("access must be 0 (public) or 1 (private).")
    key = str(access).strip().lower()
    if key in _ACCESS_CODES:
        return _ACCESS_CODES[key]
    if key in ("0", "1"):
        return int(key)
    raise ToolError(f"access must be 'public' or 'private', got {access!r}.")


@mcp.tool
async def list_pages(
    project_id: str | None = None,
    page_type: str | None = None,
    search: str | None = None,
    per_page: int = 20,
    cursor: str | None = None,
) -> dict[str, Any]:
    """List pages — workspace wiki pages, or a project's pages.

    Args:
        project_id: Project UUID to list project pages; omit for workspace wiki pages.
        page_type: Scope filter: "all" (default), "public", "private", "shared", "archived".
        search: Case-insensitive search on page title.
        per_page: Items per page (1-100, default 20).
        cursor: Pagination cursor from a previous response's `next_cursor`.
    """
    client = get_client()
    data = await _call(
        client.list_pages(
            project_id=project_id,
            page_type=page_type,
            search=search,
            per_page=per_page,
            cursor=cursor,
        )
    )
    return summarize_paginated(data)


@mcp.tool
async def get_page(page_id: str, project_id: str | None = None) -> dict[str, Any]:
    """Fetch a page by UUID (workspace wiki page, or a project page).

    Args:
        page_id: Page UUID (from `list_pages`).
        project_id: Project UUID for a project page; omit for a workspace wiki page.
    """
    client = get_client()
    return await _call(client.get_page(page_id, project_id=project_id))


@mcp.tool
async def create_page(
    name: str,
    description: str | None = None,
    description_html: str | None = None,
    project_id: str | None = None,
    access: str = "public",
    color: str | None = None,
    is_locked: bool | None = None,
    parent_id: str | None = None,
) -> dict[str, Any]:
    """Create a page — a workspace wiki page, or a page inside a project.

    Args:
        name: Page title.
        description: Plain-text body (converted to HTML for you).
        description_html: HTML body; takes precedence over `description`.
        project_id: Project UUID to create a project page; omit for a workspace wiki page.
        access: "public" (default) or "private".
        color: Optional page color, e.g. "#ff4444".
        is_locked: Lock the page so it cannot be edited.
        parent_id: Parent page UUID, to nest the page.
    """
    if not description and not description_html:
        raise ToolError("Provide either `description` or `description_html`.")
    client = get_client()
    return await _call(
        client.create_page(
            name=name,
            description=description,
            description_html=description_html,
            project_id=project_id,
            access=_access_code(access),
            color=color,
            is_locked=is_locked,
            parent_id=parent_id,
        )
    )


@mcp.tool
async def update_page(
    page_id: str,
    project_id: str | None = None,
    name: str | None = None,
    description: str | None = None,
    description_html: str | None = None,
) -> dict[str, Any]:
    """Update a page's title and/or body. At least one field is required.

    Note: updating a page replaces its body, so pass the full content you want.

    Args:
        page_id: Page UUID.
        project_id: Project UUID for a project page; omit for a workspace wiki page.
        name: New title.
        description: New plain-text body (converted to HTML for you).
        description_html: New HTML body; takes precedence over `description`.
    """
    if name is None and not description and not description_html:
        raise ToolError("Provide at least one of `name`, `description` or `description_html`.")
    client = get_client()
    return await _call(
        client.update_page(
            page_id,
            project_id=project_id,
            name=name,
            description=description,
            description_html=description_html,
        )
    )


@mcp.tool
async def archive_page(page_id: str, project_id: str | None = None) -> dict[str, Any]:
    """Archive a page. Archiving is reversible via `restore_page`.

    Args:
        page_id: Page UUID.
        project_id: Project UUID for a project page; omit for a workspace wiki page.
    """
    client = get_client()
    await _call(client.archive_page(page_id, project_id=project_id))
    return {"archived": True, "page_id": page_id}


@mcp.tool
async def restore_page(page_id: str, project_id: str | None = None) -> dict[str, Any]:
    """Restore a previously archived page.

    Args:
        page_id: Page UUID.
        project_id: Project UUID for a project page; omit for a workspace wiki page.
    """
    client = get_client()
    await _call(client.restore_page(page_id, project_id=project_id))
    return {"restored": True, "page_id": page_id}


@mcp.tool
async def delete_page(page_id: str, project_id: str | None = None) -> dict[str, Any]:
    """Permanently delete a page. The page must be archived first.

    Plane rejects deleting a page that is still active, so call `archive_page`
    before this. This cannot be undone.

    Args:
        page_id: Page UUID.
        project_id: Project UUID for a project page; omit for a workspace wiki page.
    """
    client = get_client()
    await _call(client.delete_page(page_id, project_id=project_id))
    return {"deleted": True, "page_id": page_id}


# --------------------------------------------------------------------- resources


@mcp.resource("plane://me")
async def current_user_resource() -> str:
    """The authenticated Plane user, as JSON."""
    client = get_client()
    return json.dumps(await _call(client.me()), indent=2)


@mcp.resource("plane://projects")
async def projects_resource() -> str:
    """All projects in the workspace, as JSON."""
    client = get_client()
    data = await _call(client.list_projects(per_page=100))
    return json.dumps(summarize_paginated(data), indent=2)


@mcp.resource("plane://projects/{project_id}/states")
async def states_resource(project_id: str) -> str:
    """Workflow states for a project, as JSON."""
    client = get_client()
    data = await _call(client.list_states(project_id, per_page=100))
    return json.dumps(summarize_paginated(data), indent=2)


# ----------------------------------------------------------------------- prompts


@mcp.prompt
def triage_work_items(project_id: str) -> str:
    """Ask the model to triage unstarted work items in a project."""
    return (
        f"Triage the work items in project {project_id}.\n\n"
        "1. Call list_states and list_work_items (expand assignees,state).\n"
        "2. Summarize what is in progress, unassigned, or blocked.\n"
        "3. Suggest a priority order and, for items missing an assignee or "
        "target date, propose concrete values.\n"
        "4. Do not modify anything until I confirm."
    )


# -------------------------------------------------------------------------- main


def _load_environment(env_file: str | None) -> None:
    """Load a .env file without overriding real environment variables.

    Precedence, lowest to highest: .env file, process environment, CLI flags
    (the latter are applied by :func:`main` after this runs).
    """
    if env_file is None:
        return
    path = os.path.expanduser(env_file)
    if os.path.isfile(path):
        load_dotenv(path, override=False)
        logger.info("Loaded environment from %s", path)


def _apply_cli_overrides(base_url: str | None, workspace: str | None, api_key: str | None) -> None:
    if base_url:
        os.environ["PLANE_BASE_URL"] = base_url
    if workspace:
        os.environ["PLANE_WORKSPACE_SLUG"] = workspace
    if api_key:
        os.environ["PLANE_API_KEY"] = api_key


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Plane MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http", "sse"),
        default="stdio",
        help="MCP transport to use (default: stdio).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP/SSE transports.")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE transports.")
    parser.add_argument(
        "--base-url",
        "--url",
        dest="base_url",
        default=None,
        help=(
            "Plane instance URL, e.g. https://api.plane.so or https://plane.example.com. "
            "A subpath install like https://example.com/plane is supported."
        ),
    )
    parser.add_argument(
        "--workspace",
        "--workspace-slug",
        dest="workspace",
        default=None,
        help="Workspace slug to operate on.",
    )
    parser.add_argument("--api-key", dest="api_key", default=None, help="Plane API key / personal access token.")
    parser.add_argument(
        "--env-file",
        dest="env_file",
        default=".env",
        help="Path to a .env file to load (default: ./.env). Pass '' to skip.",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Print the resolved configuration (secrets redacted) and exit.",
    )
    args = parser.parse_args()

    _load_environment(args.env_file or None)
    _apply_cli_overrides(args.base_url, args.workspace, args.api_key)

    if args.show_config:
        try:
            print(json.dumps(Settings.from_env().validate().redacted(), indent=2))
            return
        except ConfigError as exc:
            print(f"Configuration error: {exc}")
            raise SystemExit(1) from exc

    # Log the resolved instance so a misconfigured self-hosted URL is obvious in
    # the client logs. We don't hard-fail here: the server must still start and
    # advertise its tools, and each tool call returns the actionable error.
    try:
        logger.info("Plane MCP configuration: %s", Settings.from_env().validate().redacted())
    except ConfigError as exc:
        logger.warning("Plane MCP is not fully configured: %s", exc)

    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
