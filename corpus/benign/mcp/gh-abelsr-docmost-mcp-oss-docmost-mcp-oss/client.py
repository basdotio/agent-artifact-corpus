"""Asynchronous client for the Docmost REST API.

All Docmost endpoints are `POST /api/<resource>` with a JSON body and
return a wrapper `{"data": ..., "success": true, "status": 200}`.
This module handles:

* authentication (API Key `Bearer`, `authToken` cookie, or `data.tokens.accessToken`),
* unwrapping `data`,
* converting Nest errors (`{statusCode, message, error}`) into exceptions.

Details verified against real instances (see `docs/DOCMOST-API.md`):

* **Page content is not included in `/pages/info`**: it must be requested from
  `POST /pages/export` with `format` ∈ {`markdown`, `html`}, which returns the
  file as raw content (no `data` wrapper).
* Lists return `{items, meta}` with pagination by `page` (not cursor).
* `/search` requires `query` **and** `spaceId`; without `spaceId`, a fan-out
  per space is performed from here.
* `sidebar-pages` always requires `spaceId` (and optionally `pageId`).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from .position import MAX_LENGTH, PositionError, key_between

API_PREFIX = "/api"

#: Formats accepted by `/pages/export` (validated by the server).
EXPORT_FORMATS = ("markdown", "html")

#: Formats accepted by `/pages/create` and `/pages/update`.
CONTENT_FORMATS = ("markdown", "html", "json")


class DocmostError(RuntimeError):
    """Error returned by Docmost (4xx/5xx) or a transport error."""

    def __init__(self, status: int | None, message: str, payload: Any = None):
        super().__init__(f"[{status}] {message}" if status else message)
        self.status = status
        self.message = message
        self.payload = payload


class DocmostMFARequired(DocmostError):
    """Login requires MFA / MFA setup; could not obtain a session."""


class DocmostClient:
    """Minimal client for the Docmost API.

    Example::

        async with DocmostClient.from_env() as dm:
            spaces = await dm.list_spaces()
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        email: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not base_url:
            raise ValueError("DOCMOST_URL is required")
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key or None
        self._email = email or None
        self._password = password or None
        # Token to send as `Authorization: Bearer` (API key or the
        # `accessToken` returned by login in some builds).
        self._bearer: str | None = self._api_key
        self._refresh_token: str | None = None
        self._authenticated = bool(self._api_key)
        # The cookie jar persists the `authToken` cookie in builds that use it.
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            follow_redirects=True,
            headers={"Accept": "application/json"},
        )

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def from_env(cls) -> DocmostClient:
        """Creates the client from environment variables."""
        return cls(
            os.environ["DOCMOST_URL"],
            api_key=os.getenv("DOCMOST_API_KEY"),
            email=os.getenv("DOCMOST_EMAIL"),
            password=os.getenv("DOCMOST_PASSWORD"),
            timeout=float(os.getenv("DOCMOST_TIMEOUT", "30")),
        )

    async def __aenter__(self) -> DocmostClient:
        await self.authenticate()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------ #
    # Authentication
    # ------------------------------------------------------------------ #
    async def authenticate(self) -> None:
        """Idempotent: authenticates only if needed."""
        if self._authenticated:
            return
        if not (self._email and self._password):
            raise DocmostError(
                None,
                "Missing authentication: set DOCMOST_API_KEY or DOCMOST_EMAIL + DOCMOST_PASSWORD.",
            )

        resp = await self._client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": self._email, "password": self._password},
        )
        payload = _safe_json(resp)
        if resp.status_code >= 400:
            raise DocmostError(resp.status_code, _error_message(payload), payload)

        data = payload.get("data") if isinstance(payload, dict) else None

        # MFA case: Docmost responds 200 with flags and no session.
        if isinstance(data, dict) and data.get("userHasMfa") is not None:
            raise DocmostMFARequired(
                resp.status_code,
                "The account requires MFA; use an API key instead.",
                payload,
            )

        # Form 1 — `authToken` cookie (builds that issue it).
        if self._client.cookies.get("authToken"):
            self._authenticated = True
            return

        # Form 2 — tokens in the body: data.tokens.accessToken.
        tokens = data.get("tokens") if isinstance(data, dict) else None
        if isinstance(tokens, dict) and tokens.get("accessToken"):
            self._bearer = tokens["accessToken"]
            self._refresh_token = tokens.get("refreshToken")
            self._authenticated = True
            return

        raise DocmostError(
            resp.status_code,
            "Login returned neither the 'authToken' cookie nor "
            "'data.tokens.accessToken'. Unexpected response shape.",
            payload,
        )

    # ------------------------------------------------------------------ #
    # HTTP core
    # ------------------------------------------------------------------ #
    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._bearer:
            headers["Authorization"] = f"Bearer {self._bearer}"
        return headers

    async def request(self, path: str, body: dict[str, Any] | None = None) -> Any:
        """`POST /api<path>` and returns the unwrapped `data` field."""
        await self.authenticate()
        resp = await self._client.post(
            f"{API_PREFIX}{path}", json=body if body is not None else {}, headers=self._headers()
        )
        payload = _safe_json(resp)
        if resp.status_code >= 400:
            raise DocmostError(resp.status_code, _error_message(payload), payload)
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload

    # ------------------------------------------------------------------ #
    # User / workspace
    # ------------------------------------------------------------------ #
    async def get_current_user(self) -> Any:
        return await self.request("/users/me")

    async def list_workspace_members(self, *, limit: int = 50) -> list[dict]:
        raw = await self.request("/workspace/members", {"limit": _clamp_limit(limit)})
        return _items(raw)

    # ------------------------------------------------------------------ #
    # Spaces
    # ------------------------------------------------------------------ #
    async def list_spaces(self, *, limit: int = 50) -> list[dict]:
        return _items(await self.request("/spaces", {"limit": _clamp_limit(limit)}))

    async def get_space(self, space_id: str) -> Any:
        return await self.request("/spaces/info", {"spaceId": space_id})

    async def create_space(
        self, name: str, *, slug: str | None = None, description: str | None = None
    ) -> Any:
        """Creates a space. Note: the server requires `slug` to be **alphanumeric only**."""
        body: dict[str, Any] = {"name": name}
        if slug is not None:
            body["slug"] = slug
        if description is not None:
            body["description"] = description
        return await self.request("/spaces/create", body)

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #
    async def search_pages(
        self,
        query: str,
        *,
        space_id: str | None = None,
        title_only: bool | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Searches pages. Without `space_id`, searches all spaces.

        `/search` **requires `spaceId`** in most builds (returns 400 without
        it), so when not specified, each accessible space is queried and results
        are merged by `rank`.
        """
        if not query or not query.strip():
            raise ValueError("`query` is required to search")

        if space_id:
            return {
                "query": query,
                "items": await self._search_in_space(
                    query, space_id, title_only=title_only, limit=limit
                ),
                "spaces_searched": 1,
            }

        spaces = await self.list_spaces(limit=100)
        merged: list[dict] = []
        searched: list[dict] = []
        for space in spaces:
            try:
                merged.extend(
                    await self._search_in_space(
                        query, space["id"], title_only=title_only, limit=limit
                    )
                )
                searched.append({"id": space["id"], "name": space.get("name")})
            except DocmostError:
                continue  # no read permission in that space

        merged.sort(key=lambda r: r.get("rank") or 0, reverse=True)
        seen: set[str] = set()
        unique: list[dict] = []
        for row in merged:
            key = row.get("id") or row.get("slugId")
            if key and key not in seen:
                seen.add(key)
                unique.append(row)

        return {
            "query": query,
            "items": unique[:limit],
            "spaces_searched": len(searched),
            "spaces": searched,
        }

    async def _search_in_space(
        self,
        query: str,
        space_id: str,
        *,
        title_only: bool | None = None,
        limit: int = 20,
    ) -> list[dict]:
        body: dict[str, Any] = {"query": query, "spaceId": space_id, "limit": _clamp_limit(limit)}
        if title_only is not None:
            body["titleOnly"] = title_only
        return _items(await self.request("/search", body))

    # ------------------------------------------------------------------ #
    # Pages
    # ------------------------------------------------------------------ #
    async def get_page(
        self,
        page_id: str,
        *,
        format: str = "markdown",
        include_content: bool = True,
    ) -> dict[str, Any]:
        """Page metadata + its content in Markdown/HTML.

        `/pages/info` **does not return the content**: it is fetched separately
        via `/pages/export`. If the export fails, the metadata is still returned
        with `content_error` explaining the reason.
        """
        page = await self.request("/pages/info", {"pageId": page_id})
        if not include_content:
            return page
        if not isinstance(page, dict):
            return {"page": page}

        try:
            export = await self.export_page(page_id, format=format)
        except DocmostError as exc:
            return {**page, "content": None, "content_error": str(exc)}
        return {**page, "content": export["content"], "content_format": format}

    async def export_page(self, page_id: str, *, format: str = "markdown") -> dict:
        """Downloads the page content as text (`markdown` or `html`).

        `/pages/export` responds with the raw file, no `data` wrapper.
        """
        if format not in EXPORT_FORMATS:
            raise ValueError(f"format must be one of {EXPORT_FORMATS}")
        await self.authenticate()
        resp = await self._client.post(
            f"{API_PREFIX}/pages/export",
            json={"pageId": page_id, "format": format},
            headers=self._headers(),
        )
        if resp.status_code >= 400:
            payload = _safe_json(resp)
            raise DocmostError(resp.status_code, _error_message(payload), payload)
        return {
            "content": resp.text,
            "format": format,
            "filename": _filename_from_headers(resp),
        }

    async def create_page(
        self,
        space_id: str,
        *,
        title: str | None = None,
        parent_page_id: str | None = None,
        content: str | None = None,
        format: str = "markdown",
        icon: str | None = None,
    ) -> Any:
        """Creates a page.

        **Important:** `/pages/create` ignores the `content` field (verified
        against real instances: the body is owned by the Yjs collaboration
        server). Therefore, when `content` is passed, the page is created
        via `/pages/import` (multipart), which **does** persist the body.

        The title is derived from the first heading in the content; if `title`
        is specified, a `# <title>` is prepended to fix it.
        """
        if content is None:
            body: dict[str, Any] = {"spaceId": space_id}
            if title is not None:
                body["title"] = title
            if parent_page_id is not None:
                body["parentPageId"] = parent_page_id
            if icon is not None:
                body["icon"] = icon
            return await self.request("/pages/create", body)

        page = await self.import_page(
            space_id, content, title=title, format=format, parent_page_id=parent_page_id
        )
        if icon is not None and page.get("slugId"):
            await self.request("/pages/update", {"pageId": page["slugId"], "icon": icon})
        return page

    async def import_page(
        self,
        space_id: str,
        content: str,
        *,
        title: str | None = None,
        format: str = "markdown",
        filename: str | None = None,
        parent_page_id: str | None = None,
    ) -> dict:
        """Creates a page **with content** by uploading it to `/pages/import`.

        This is the only REST path that persists a page body. The title
        comes from the first heading in the document; if `title` is passed,
        `# <title>` is prepended (Markdown only).
        """
        if format not in ("markdown", "html"):
            raise ValueError("format must be 'markdown' or 'html'")
        mime = "text/markdown" if format == "markdown" else "text/html"
        ext = "md" if format == "markdown" else "html"

        body_text = content
        if title:
            body_text = _ensure_heading(content, title, format)

        await self.authenticate()
        resp = await self._client.post(
            f"{API_PREFIX}/pages/import",
            data={"spaceId": space_id},
            files={"file": (filename or f"page.{ext}", body_text.encode(), mime)},
            headers=self._headers(),
        )
        payload = _safe_json(resp)
        if resp.status_code >= 400:
            raise DocmostError(resp.status_code, _error_message(payload), payload)
        page = (payload or {}).get("data") or {}

        # `/pages/import` accepts but ignores a `parentPageId` field (verified
        # against a real instance), so the page always lands at the root.
        # Nesting is applied afterwards with `/pages/move`, which is the
        # endpoint that actually sets the parent. The page keeps the position it
        # was given at creation so it does not jump around.
        if parent_page_id and page:
            page_id = page.get("slugId") or page.get("id")
            if page_id:
                await self.move_page(
                    page_id,
                    page.get("position") or "a0000",
                    parent_page_id=parent_page_id,
                )
                page["parentPageId"] = parent_page_id
        return page

    async def update_page(
        self,
        page_id: str,
        *,
        title: str | None = None,
        content: str | None = None,
        format: str = "markdown",
        operation: str = "replace",
    ) -> Any:
        """Updates a page.

        ⚠️ **Metadata only.** Verified against real instances: although
        `/pages/update` accepts `content` and responds 200, it **does not
        modify the body** (the content is managed by the Yjs server). Therefore,
        if `content` is passed, an explicit error is raised instead of failing
        silently.
        """
        if content is not None:
            raise DocmostError(
                None,
                "This Docmost instance does not allow updating page content "
                "over REST (`/pages/update` ignores `content`). Options: "
                "create a new page with the content (`create_page`, which "
                "uses `/pages/import`), or edit the body in the web UI.",
            )
        body: dict[str, Any] = {"pageId": page_id}
        if title is not None:
            body["title"] = title
        return await self.request("/pages/update", body)

    async def delete_page(self, page_id: str) -> Any:
        """Moves the page to the trash (this build does not expose permanent deletion)."""
        return await self.request("/pages/delete", {"pageId": page_id})

    async def restore_page(self, page_id: str) -> Any:
        return await self.request("/pages/restore", {"pageId": page_id})

    async def move_page(
        self,
        page_id: str,
        position: str | None = None,
        *,
        parent_page_id: str | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> Any:
        """Moves or reorders a page.

        The position is a base62 string Docmost compares lexicographically, and
        it must be 5-12 characters. Rather than making the caller invent one,
        give it a destination:

        * ``parent_page_id`` nests the page under that parent (or pass ``None``
          explicitly to send it back to the root).
        * ``after``/``before`` place it relative to a sibling page id.
        * Neither of those appends it at the end of the target's children.

        ``position`` is the manual escape hatch: passing it skips all of the
        above and sends the value as-is.
        """
        if position is None:
            position = await self._position_for(
                page_id, parent_page_id=parent_page_id, after=after, before=before
            )

        body: dict[str, Any] = {"pageId": page_id, "position": position}
        if parent_page_id is not None:
            body["parentPageId"] = parent_page_id
        return await self.request("/pages/move", body)

    async def _position_for(
        self,
        page_id: str,
        *,
        parent_page_id: str | None,
        after: str | None,
        before: str | None,
    ) -> str:
        """Computes a position that lands the page where the caller asked."""
        if after and before:
            raise ValueError("Pass either `after` or `before`, not both")

        page = await self.request("/pages/info", {"pageId": page_id})
        if not isinstance(page, dict):
            raise DocmostError(None, f"Page {page_id} not found")

        space_id = page.get("spaceId")
        # `parent_page_id=None` means "the root", which is also the default when
        # the caller did not ask for a specific parent.
        target_parent = parent_page_id if parent_page_id is not None else page.get("parentPageId")

        siblings = await self.list_child_pages(space_id=space_id, page_id=target_parent, limit=100)

        def is_self(sibling: dict) -> bool:
            # Callers identify pages by UUID or slugId; the list always returns
            # the UUID, so comparing only the caller's value silently matches
            # nothing and the page ends up as its own neighbour.
            return page_id in (sibling.get("id"), sibling.get("slugId"))

        ordered = sorted(
            (sibling for sibling in siblings if not is_self(sibling) and sibling.get("position")),
            key=lambda sibling: sibling["position"],
        )
        positions = [sibling["position"] for sibling in ordered]

        def index_of(page_ref: str) -> int:
            for index, sibling in enumerate(ordered):
                if sibling.get("id") == page_ref or sibling.get("slugId") == page_ref:
                    return index
            raise DocmostError(
                None,
                f"{page_ref} is not a sibling of {page_id} in the target parent; "
                "cannot place the page relative to it",
            )

        if before:
            index = index_of(before)
            lower = positions[index - 1] if index > 0 else None
            upper = positions[index]
        elif after:
            index = index_of(after)
            lower = positions[index]
            upper = positions[index + 1] if index + 1 < len(positions) else None
        else:
            lower = positions[-1] if positions else None
            upper = None

        try:
            return key_between(lower, upper)
        except PositionError as exc:
            raise DocmostError(
                None,
                f"Cannot place the page there: {exc}. Docmost positions cap at "
                f"{MAX_LENGTH} characters, so a slot can only be subdivided so "
                "many times. Spread the surrounding pages out, or use the web UI.",
            ) from exc

    async def list_recent_pages(
        self, *, space_id: str | None = None, limit: int = 20
    ) -> list[dict]:
        body: dict[str, Any] = {"limit": _clamp_limit(limit)}
        if space_id:
            body["spaceId"] = space_id
        return _items(await self.request("/pages/recent", body))

    async def list_child_pages(
        self,
        *,
        space_id: str | None = None,
        page_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Children of a page or roots of a space.

        `/pages/sidebar-pages` **requires `spaceId`**. If only `page_id` is given,
        its `spaceId` is resolved with a prior call to `/pages/info`.
        """
        if not space_id and page_id:
            page = await self.request("/pages/info", {"pageId": page_id})
            space_id = (page or {}).get("spaceId") if isinstance(page, dict) else None
        if not space_id:
            raise ValueError("Provide space_id (or page_id)")

        body: dict[str, Any] = {"spaceId": space_id, "limit": _clamp_limit(limit)}
        if page_id:
            body["pageId"] = page_id
        return _items(await self.request("/pages/sidebar-pages", body))

    async def list_all_pages(
        self,
        *,
        space_id: str | None = None,
        max_pages: int = 500,
    ) -> list[dict[str, Any]]:
        """Every page in a space (or in the whole workspace), flattened.

        `/pages/sidebar-pages` only returns the children of a given node — a
        `{spaceId}` call gives the roots, not the whole tree — so enumerating a
        space means walking it. That is what this does, returning one flat list
        where each entry carries `parent_page_id` and `depth` so the tree can be
        reconstructed.
        """
        if space_id:
            space_ids = [space_id]
        else:
            space_ids = [s["id"] for s in await self.list_spaces(limit=100)]

        pages: list[dict[str, Any]] = []
        for sid in space_ids:
            pages.extend(await self._walk_space(sid, max_pages=max_pages - len(pages)))
            if len(pages) >= max_pages:
                break
        return pages

    async def _walk_space(self, space_id: str, *, max_pages: int = 500) -> list[dict[str, Any]]:
        """Depth-first walk of a space's page tree. Cycles are guarded against."""
        found: list[dict[str, Any]] = []
        seen: set[str] = set()

        async def walk(page_id: str | None, depth: int) -> None:
            if len(found) >= max_pages:
                return
            body: dict[str, Any] = {"spaceId": space_id}
            if page_id:
                body["pageId"] = page_id
            for item in _items(await self.request("/pages/sidebar-pages", body)):
                page_key = item.get("id")
                if not page_key or page_key in seen:
                    continue
                seen.add(page_key)
                found.append(
                    {
                        "id": page_key,
                        "slug_id": item.get("slugId"),
                        "title": item.get("title"),
                        "icon": item.get("icon"),
                        "parent_page_id": item.get("parentPageId"),
                        "position": item.get("position"),
                        "has_children": bool(item.get("hasChildren")),
                        "depth": depth,
                    }
                )
                if len(found) >= max_pages:
                    return
                if item.get("hasChildren"):
                    await walk(page_key, depth + 1)

        await walk(None, 0)
        return found

    async def get_page_breadcrumbs(self, page_id: str) -> list[dict]:
        return _items(await self.request("/pages/breadcrumbs", {"pageId": page_id}))

    async def get_page_history(self, page_id: str) -> list[dict]:
        return _items(await self.request("/pages/history", {"pageId": page_id}))

    # ------------------------------------------------------------------ #
    # Comments
    # ------------------------------------------------------------------ #
    async def get_comments(self, page_id: str, *, limit: int = 50) -> list[dict]:
        return _items(
            await self.request("/comments", {"pageId": page_id, "limit": _clamp_limit(limit)})
        )

    async def create_comment(
        self,
        page_id: str,
        content: str,
        *,
        comment_type: str = "page",
        parent_comment_id: str | None = None,
    ) -> Any:
        """`content` must be a **valid JSON string** (Tiptap/ProseMirror document)."""
        body: dict[str, Any] = {
            "pageId": page_id,
            "content": content,
            "type": comment_type,
        }
        if parent_comment_id:
            body["parentCommentId"] = parent_comment_id
        return await self.request("/comments/create", body)

    async def update_comment(self, comment_id: str, content: str) -> Any:
        return await self.request("/comments/update", {"commentId": comment_id, "content": content})

    async def delete_comment(self, comment_id: str) -> Any:
        return await self.request("/comments/delete", {"commentId": comment_id})


# ---------------------------------------------------------------------- #
# Utilities
# ---------------------------------------------------------------------- #
#: Docmost rejects `limit > 100` on its list endpoints.
MAX_LIMIT = 100


def _clamp_limit(limit: int, *, maximum: int = MAX_LIMIT) -> int:
    """Keeps a page size inside the range Docmost accepts."""
    return max(1, min(int(limit), maximum))


def _items(raw: Any) -> list[dict]:
    """Lists return `{items: [...]}` in some builds and `[...]` in others."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("items") or []
    return []


def _ensure_heading(content: str, title: str, fmt: str) -> str:
    """Prepends a heading with the title if the document does not start with one.

    Docmost derives the page title from the first heading of the imported
    document, so this is what allows setting it explicitly.
    """
    stripped = content.lstrip()
    if fmt == "html":
        return content if stripped.lower().startswith("<h1") else f"<h1>{title}</h1>\n{content}"
    return content if stripped.startswith("# ") else f"# {title}\n\n{content}"


def _safe_json(resp: httpx.Response) -> Any:
    """Docmost returns 200 with an empty body on some endpoints."""
    try:
        return resp.json()
    except Exception:
        return None


def _error_message(payload: Any) -> str:
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, list):
            return "; ".join(str(m) for m in message)
        if message:
            return str(message)
        if payload.get("error"):
            return str(payload["error"])
    return "Unknown Docmost error"


def _filename_from_headers(resp: httpx.Response) -> str | None:
    disposition = resp.headers.get("content-disposition") or ""
    if "filename=" not in disposition:
        return None
    from urllib.parse import unquote

    return unquote(disposition.split("filename=", 1)[1].strip().strip('"'))
