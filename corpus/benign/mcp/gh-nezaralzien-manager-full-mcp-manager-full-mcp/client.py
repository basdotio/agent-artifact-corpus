"""Thin async HTTP client for one Manager.io business."""

from __future__ import annotations

from typing import Any

import httpx

from manager_full_mcp.config import Business


class ConfigError(ValueError):
    """Business is missing a URL or token."""


class ManagerUnavailableError(RuntimeError):
    """Manager is unreachable (closed, wrong URL, offline)."""


class ManagerApiError(RuntimeError):
    """Manager answered with an HTTP error."""


class ManagerClient:
    def __init__(self, business: Business, *, client: httpx.AsyncClient | None = None) -> None:
        if not business.api_url:
            raise ConfigError(f"Business '{business.name}' has no API URL.")
        if not business.api_key:
            raise ConfigError(
                f"Business '{business.name}' has no access token. "
                "Add it in the permissions panel."
            )
        self.business = business
        self.base_url = business.api_url.rstrip("/")
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-KEY": business.api_key, "Accept": "application/json"},
            timeout=90.0,
            follow_redirects=True,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        url_path = path if path.startswith(("/", "http")) else f"/{path}"
        try:
            response = await self._client.request(
                method.upper(),
                url_path,
                params={k: v for k, v in (params or {}).items() if v is not None} or None,
                json=json,
            )
        except httpx.RequestError as exc:
            raise ManagerUnavailableError(
                f"Manager is not reachable at {self.base_url} ({exc.__class__.__name__}). "
                "Check that the business is online and the API URL is right."
            ) from exc
        if response.status_code >= 400:
            snippet = (response.text or "")[:400]
            raise ManagerApiError(
                f"Manager returned HTTP {response.status_code} for "
                f"{method.upper()} {url_path}. {snippet}"
            )
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return {"raw_text": response.text[:4000]}

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, *, json: Any = None) -> Any:
        return await self.request("POST", path, json=json)

    async def put(self, path: str, *, json: Any = None) -> Any:
        return await self.request("PUT", path, json=json)

    async def delete(self, path: str) -> Any:
        return await self.request("DELETE", path)

    async def openapi(self) -> dict[str, Any]:
        """The instance's own OpenAPI document (served at the API base URL).

        Manager serves it at the base URL with no trailing slash; `/api2/` is a
        different route and answers 401, so this asks for the absolute URL.
        """
        doc = await self.request("GET", self.base_url)
        if not isinstance(doc, dict) or "paths" not in doc:
            raise ManagerApiError(
                f"{self.base_url} did not return an OpenAPI document. "
                "The URL usually ends with /api2."
            )
        return doc

    async def aclose(self) -> None:
        await self._client.aclose()
