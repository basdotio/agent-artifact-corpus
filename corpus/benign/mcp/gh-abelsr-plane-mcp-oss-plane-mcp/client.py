"""Thin async wrapper around the Plane REST API.

The client is intentionally small: it owns authentication, URL building, error
translation and pagination, and exposes one method per operation we surface as
an MCP tool. Nothing here depends on FastMCP, which keeps it easy to test and
reuse.

API reference: https://developers.plane.so/api-reference/introduction
"""

from __future__ import annotations

import html
from typing import Any, Iterable

import httpx

from .config import Settings


class PlaneAPIError(RuntimeError):
    """A non-2xx response from the Plane API."""

    def __init__(self, status_code: int, detail: Any, method: str, url: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.method = method
        self.url = url
        super().__init__(self._message())

    def _message(self) -> str:
        detail = self.detail
        if isinstance(detail, dict):
            # Plane returns errors under a few common keys.
            for key in ("error", "detail", "message", "errors"):
                if key in detail:
                    detail = detail[key]
                    break
        if not isinstance(detail, str):
            detail = str(detail)
        detail = detail.strip() or "no response body"
        return f"Plane API {self.status_code} for {self.method} {self.url}: {detail}"


def _text_to_html(text: str | None) -> str | None:
    """Wrap plain text in a paragraph, escaping HTML-sensitive characters."""
    if not text:
        return None
    return "<p>" + html.escape(text).replace("\n", "<br>") + "</p>"


def _clean(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop keys whose value is ``None`` so PATCH/POST bodies stay minimal."""
    return {key: value for key, value in payload.items() if value is not None}


class PlaneClient:
    """Async client for a single Plane workspace."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings.validate()
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------ infra

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            headers = {"Accept": "application/json"}
            if self.settings.api_key:
                headers["X-API-Key"] = self.settings.api_key
            elif self.settings.oauth_token:
                headers["Authorization"] = f"Bearer {self.settings.oauth_token}"
            self._http = httpx.AsyncClient(
                base_url=self.settings.base_url,
                headers=headers,
                timeout=self.settings.timeout,
            )
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = path if path.startswith("http") else "/" + path.lstrip("/")
        response = await self.http.request(method, url, params=_clean(params or {}), json=json)
        if response.status_code == 204 or not response.content:
            if response.status_code >= 400:
                raise PlaneAPIError(response.status_code, None, method, url)
            return None
        try:
            body = response.json()
        except ValueError:
            body = response.text
        if response.status_code >= 400:
            raise PlaneAPIError(response.status_code, body, method, url)
        return body

    def _workspace(self, *parts: str) -> str:
        joined = "/".join(part.strip("/") for part in parts if part)
        return f"/workspaces/{self.settings.workspace_slug}/{joined}/"

    @staticmethod
    def _pagination(per_page: int | None, cursor: str | None, **extra: Any) -> dict[str, Any]:
        params: dict[str, Any] = {"per_page": per_page, "cursor": cursor}
        params.update(extra)
        return params

    # --------------------------------------------------------------- workspace

    async def me(self) -> dict[str, Any]:
        """Return the authenticated user's profile."""
        return await self.request("GET", "/users/me/")

    async def list_members(self) -> list[dict[str, Any]]:
        """Return every member of the workspace."""
        return await self.request("GET", self._workspace("members"))

    # ---------------------------------------------------------------- projects

    async def list_projects(
        self,
        *,
        per_page: int | None = None,
        cursor: str | None = None,
        order_by: str | None = None,
        expand: str | None = None,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            self._workspace("projects"),
            params=self._pagination(per_page, cursor, order_by=order_by, expand=expand),
        )

    async def get_project(self, project_id: str) -> dict[str, Any]:
        return await self.request("GET", self._workspace("projects", project_id))

    async def create_project(
        self,
        *,
        name: str,
        identifier: str,
        description: str | None = None,
        project_lead: str | None = None,
        default_assignee: str | None = None,
        emoji: str | None = None,
    ) -> dict[str, Any]:
        payload = _clean(
            {
                "name": name,
                "identifier": identifier,
                "description": description,
                "project_lead": project_lead,
                "default_assignee": default_assignee,
                "emoji": emoji,
            }
        )
        return await self.request("POST", self._workspace("projects"), json=payload)

    async def update_project(
        self,
        project_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        project_lead: str | None = None,
        default_assignee: str | None = None,
        emoji: str | None = None,
    ) -> dict[str, Any]:
        payload = _clean(
            {
                "name": name,
                "description": description,
                "project_lead": project_lead,
                "default_assignee": default_assignee,
                "emoji": emoji,
            }
        )
        return await self.request("PATCH", self._workspace("projects", project_id), json=payload)

    async def delete_project(self, project_id: str) -> None:
        await self.request("DELETE", self._workspace("projects", project_id))

    # ------------------------------------------------------------- work items

    async def list_work_items(
        self,
        project_id: str,
        *,
        per_page: int | None = None,
        cursor: str | None = None,
        order_by: str | None = None,
        expand: str | None = None,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            self._workspace("projects", project_id, "work-items"),
            params=self._pagination(per_page, cursor, order_by=order_by, expand=expand),
        )

    async def get_work_item(self, project_id: str, work_item_id: str) -> dict[str, Any]:
        return await self.request(
            "GET", self._workspace("projects", project_id, "work-items", work_item_id)
        )

    async def get_work_item_by_identifier(self, identifier: str) -> dict[str, Any]:
        """Look a work item up by its human identifier, e.g. ``PROJ-123``."""
        return await self.request("GET", self._workspace("work-items", identifier))

    async def create_work_item(
        self,
        project_id: str,
        *,
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
        payload = _clean(
            {
                "name": name,
                "description_html": description_html or _text_to_html(description),
                "priority": priority,
                "state": state,
                "assignees": assignees,
                "labels": labels,
                "parent": parent,
                "start_date": start_date,
                "target_date": target_date,
                "estimate_point": estimate_point,
            }
        )
        return await self.request(
            "POST", self._workspace("projects", project_id, "work-items"), json=payload
        )

    async def update_work_item(
        self,
        project_id: str,
        work_item_id: str,
        *,
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
        payload = _clean(
            {
                "name": name,
                "description_html": description_html or _text_to_html(description),
                "priority": priority,
                "state": state,
                "assignees": assignees,
                "labels": labels,
                "start_date": start_date,
                "target_date": target_date,
                "estimate_point": estimate_point,
            }
        )
        return await self.request(
            "PATCH",
            self._workspace("projects", project_id, "work-items", work_item_id),
            json=payload,
        )

    async def delete_work_item(self, project_id: str, work_item_id: str) -> None:
        await self.request(
            "DELETE", self._workspace("projects", project_id, "work-items", work_item_id)
        )

    async def search_work_items(
        self,
        *,
        search: str,
        project_id: str | None = None,
        limit: int | None = None,
        workspace_search: bool | None = None,
    ) -> dict[str, Any]:
        """Semantic search across work item name, sequence id and project identifier.

        Uses ``GET /work-items/search/`` and returns ``{"issues": [...]}``.
        """
        return await self.request(
            "GET",
            self._workspace("work-items", "search"),
            params={
                "search": search,
                "project_id": project_id,
                "limit": limit,
                "workspace_search": None if workspace_search is None else str(workspace_search).lower(),
            },
        )

    async def advanced_search_work_items(
        self,
        *,
        query: str | None = None,
        project_id: str | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        workspace_search: bool | None = None,
    ) -> Any:
        """Filtered search over ``POST /work-items/advanced-search/``.

        This endpoint is permission-gated on some workspaces/editions and may
        return 403.
        """
        payload = _clean(
            {
                "query": query,
                "project_id": project_id,
                "filters": filters,
                "limit": limit,
                "workspace_search": workspace_search,
            }
        )
        return await self.request(
            "POST", self._workspace("work-items", "advanced-search"), json=payload
        )

    # ------------------------------------------------------- project metadata

    async def list_states(self, project_id: str, *, per_page: int | None = None) -> dict[str, Any]:
        return await self.request(
            "GET",
            self._workspace("projects", project_id, "states"),
            params=self._pagination(per_page, None),
        )

    async def list_labels(self, project_id: str, *, per_page: int | None = None) -> dict[str, Any]:
        return await self.request(
            "GET",
            self._workspace("projects", project_id, "labels"),
            params=self._pagination(per_page, None),
        )

    async def create_label(
        self, project_id: str, *, name: str, color: str | None = None, description: str | None = None
    ) -> dict[str, Any]:
        payload = _clean({"name": name, "color": color, "description": description})
        return await self.request(
            "POST", self._workspace("projects", project_id, "labels"), json=payload
        )

    async def list_cycles(
        self,
        project_id: str,
        *,
        per_page: int | None = None,
        cursor: str | None = None,
        cycle_view: str | None = None,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            self._workspace("projects", project_id, "cycles"),
            params=self._pagination(per_page, cursor, cycle_view=cycle_view),
        )

    async def list_modules(
        self,
        project_id: str,
        *,
        per_page: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            self._workspace("projects", project_id, "modules"),
            params=self._pagination(per_page, cursor),
        )

    # --------------------------------------------------------------- comments

    async def list_comments(
        self, project_id: str, work_item_id: str, *, per_page: int | None = None
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            self._workspace("projects", project_id, "work-items", work_item_id, "comments"),
            params=self._pagination(per_page, None),
        )

    async def add_comment(
        self, project_id: str, work_item_id: str, *, comment: str
    ) -> dict[str, Any]:
        """Add a comment; ``comment`` may be plain text or HTML."""
        looks_like_html = "<" in comment and ">" in comment
        payload = {"comment_html": comment if looks_like_html else _text_to_html(comment)}
        return await self.request(
            "POST",
            self._workspace("projects", project_id, "work-items", work_item_id, "comments"),
            json=payload,
        )

    async def update_comment(
        self, project_id: str, work_item_id: str, comment_id: str, *, comment: str
    ) -> dict[str, Any]:
        """Replace a comment's body; ``comment`` may be plain text or HTML."""
        looks_like_html = "<" in comment and ">" in comment
        payload = {"comment_html": comment if looks_like_html else _text_to_html(comment)}
        return await self.request(
            "PATCH",
            self._workspace(
                "projects", project_id, "work-items", work_item_id, "comments", comment_id
            ),
            json=payload,
        )

    async def delete_comment(
        self, project_id: str, work_item_id: str, comment_id: str
    ) -> None:
        await self.request(
            "DELETE",
            self._workspace(
                "projects", project_id, "work-items", work_item_id, "comments", comment_id
            ),
        )

    # --------------------------------------------------------------------- pages
    #
    # Pass ``project_id`` for a project page, or ``None`` for a workspace wiki
    # page. Both families share the same shape; only the root path differs.

    def _pages_root(self, project_id: str | None) -> str:
        if project_id:
            return self._workspace("projects", project_id, "pages")
        return self._workspace("pages")

    async def list_pages(
        self,
        *,
        project_id: str | None = None,
        page_type: str | None = None,
        search: str | None = None,
        per_page: int | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            self._pages_root(project_id),
            params=self._pagination(per_page, cursor, type=page_type, search=search),
        )

    async def get_page(self, page_id: str, *, project_id: str | None = None) -> dict[str, Any]:
        return await self.request("GET", f"{self._pages_root(project_id)}{page_id}/")

    async def create_page(
        self,
        *,
        name: str,
        description: str | None = None,
        description_html: str | None = None,
        project_id: str | None = None,
        access: int = 0,
        color: str | None = None,
        is_locked: bool | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        payload = _clean(
            {
                "name": name,
                "description_html": description_html or _text_to_html(description),
                "access": access,
                "color": color,
                "is_locked": is_locked,
                "parent_id": parent_id,
            }
        )
        return await self.request("POST", self._pages_root(project_id), json=payload)

    async def update_page(
        self,
        page_id: str,
        *,
        project_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        description_html: str | None = None,
    ) -> dict[str, Any]:
        # Plane uses PUT here (not PATCH) and requires at least one field.
        payload = _clean(
            {
                "name": name,
                "description_html": description_html or _text_to_html(description),
            }
        )
        return await self.request("PUT", f"{self._pages_root(project_id)}{page_id}/", json=payload)

    async def archive_page(self, page_id: str, *, project_id: str | None = None) -> None:
        await self.request("POST", f"{self._pages_root(project_id)}{page_id}/archive/")

    async def restore_page(self, page_id: str, *, project_id: str | None = None) -> None:
        # Restore is DELETE on the same /archive/ sub-resource.
        await self.request("DELETE", f"{self._pages_root(project_id)}{page_id}/archive/")

    async def delete_page(self, page_id: str, *, project_id: str | None = None) -> None:
        # The page must be archived first, otherwise Plane returns 400.
        await self.request("DELETE", f"{self._pages_root(project_id)}{page_id}/")


def summarize_paginated(data: Any, *, keys: Iterable[str] = ("results",)) -> dict[str, Any]:
    """Normalize a paginated Plane response into a compact dict.

    Plane list endpoints return ``{results: [...], next_cursor, ...}`` but some
    newer endpoints return a bare list. This keeps tool output predictable.
    """
    if isinstance(data, list):
        return {"results": data, "count": len(data), "next_cursor": None}
    if isinstance(data, dict):
        result: dict[str, Any] = {}
        for key in keys:
            if key in data:
                result[key] = data[key]
        for meta in ("count", "total_results", "next_cursor", "next_page_results"):
            if meta in data:
                result[meta] = data[meta]
        if "results" not in result:
            result["results"] = data
        return result
    return {"results": data, "count": 1, "next_cursor": None}
