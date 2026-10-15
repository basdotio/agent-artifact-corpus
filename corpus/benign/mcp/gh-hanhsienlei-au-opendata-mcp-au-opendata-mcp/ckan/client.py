import asyncio
import json
import logging
from typing import Any

import httpx

from au_opendata_mcp.cache import MetadataCache
from au_opendata_mcp.config import Settings
from au_opendata_mcp.errors import ResourceNotFound, UpstreamUnavailable
from au_opendata_mcp.portals import Portal

log = logging.getLogger(__name__)

INTERNAL_COLUMNS = {"_full_text"}


def strip_internal_columns(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop CKAN's tsvector column. Left in, it dominates every response for zero information."""
    return [{k: v for k, v in r.items() if k not in INTERNAL_COLUMNS} for r in records]


class CkanClient:
    def __init__(
        self,
        portal: Portal,
        http: httpx.AsyncClient,
        settings: Settings,
        cache: MetadataCache | None = None,
    ) -> None:
        self.portal = portal
        self.http = http
        self.settings = settings
        self.cache = cache

    def _cache_key(self, name: str, params: dict[str, Any]) -> str:
        return f"{self.portal.id}:{name}:{json.dumps(params, sort_keys=True, default=str)}"

    async def action(self, name: str, params: dict[str, Any]) -> Any:
        """Call a CKAN action and return its `result` payload.

        On a cache hit, the returned object is the **live cached object**, not a copy —
        it may be shared with other callers (including concurrent ones) and must not be
        mutated. A caller that needs to mutate the result should copy at its own call
        site (e.g. `dict(result)`), and only if it actually needs to. We deliberately do
        not deep-copy on every hit: some actions (e.g. `datastore_search`) can return
        thousands of rows, and copying on the fast path would defeat much of the point
        of caching them.

        Only successful CKAN responses are cached. A 4xx/5xx HTTP status, a transport
        error, and a CKAN `{"success": false}` body are never cached — each of those
        raises before the single `cache.set` call below is reached, so a failed call
        never poisons the cache for a subsequent successful one.
        """
        cache_key = self._cache_key(name, params) if self.cache is not None else None
        if self.cache is not None and cache_key is not None:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        url = f"{self.portal.api_base}/{name}"
        # A short, fixed classification of why the last attempt failed -- deliberately not
        # the exception object. httpx errors can stringify with the failing URL attached,
        # and that URL carries the caller's own `q` in its query string.
        last_reason = "no attempt completed"

        for attempt in range(self.settings.upstream_retries + 1):
            try:
                resp = await self.http.get(
                    url, params=params, timeout=self.settings.upstream_timeout_seconds
                )
            except httpx.HTTPError as exc:
                last_reason = f"transport error ({type(exc).__name__})"
                if attempt < self.settings.upstream_retries:
                    await asyncio.sleep(0.2 * (2**attempt))
                    continue
                break

            log.info(
                "upstream call",
                extra={
                    "event": "upstream",
                    "portal": self.portal.id,
                    "action": name,
                    "status": resp.status_code,
                },
            )

            if resp.status_code == 404:
                # Param *keys* only. The values are caller content -- package_search's `q`
                # is a user's question -- and this message is logged by the fan-out in
                # services/catalog.py and returned to the caller by the REST layer.
                raise ResourceNotFound(
                    f"{name}(params: {', '.join(sorted(params)) or 'none'}) "
                    f"not found on {self.portal.id}",
                    remedy_url=self.portal.site_url,
                )
            if resp.status_code >= 500:
                last_reason = f"HTTP {resp.status_code}"
                if attempt < self.settings.upstream_retries:
                    await asyncio.sleep(0.2 * (2**attempt))
                    continue
                break
            if resp.status_code >= 400:
                raise UpstreamUnavailable(
                    f"{self.portal.id} rejected {name}: HTTP {resp.status_code}",
                    remedy_url=self.portal.site_url,
                )
            if 300 <= resp.status_code < 400:
                # The shared client is built with follow_redirects=False, so a redirect
                # arriving here is an upstream anomaly (a moved API endpoint, a captive
                # portal), not something to parse as JSON.
                raise UpstreamUnavailable(
                    f"{self.portal.id} redirected the {name} API call "
                    f"(HTTP {resp.status_code}); the portal's API may have moved",
                    remedy_url=self.portal.site_url,
                )

            # A 204, or a 200 carrying a WAF block page or a CDN error page, are realistic
            # government-portal outage modes. Left to a bare resp.json() they raise
            # ValueError, which the REST layer turns into HTTP 400 -- telling the caller
            # (often a model, which will then retry with different arguments forever) that
            # a portal outage was their mistake. Spec 4.2: this is UpstreamUnavailable/502.
            try:
                body = resp.json()
            except ValueError as exc:
                raise UpstreamUnavailable(
                    f"{self.portal.id} returned a non-JSON body for {name} "
                    f"(HTTP {resp.status_code}); the portal is likely down or "
                    "serving an error page",
                    remedy_url=self.portal.site_url,
                ) from exc
            if not isinstance(body, dict):
                raise UpstreamUnavailable(
                    f"{self.portal.id} returned JSON that is not a CKAN response envelope "
                    f"for {name} (HTTP {resp.status_code})",
                    remedy_url=self.portal.site_url,
                )
            if not body.get("success"):
                # CKAN's own error text is not interpolated: Solr routinely echoes the
                # submitted query back inside it, which would put the caller's search
                # text straight into this message (and from there into the logs).
                raise UpstreamUnavailable(
                    f"{self.portal.id} reported failure for {name} "
                    "(upstream error text suppressed: it can echo caller input)",
                    remedy_url=self.portal.site_url,
                )
            result = body["result"]
            if self.cache is not None and cache_key is not None:
                self.cache.set(cache_key, result)
            return result

        raise UpstreamUnavailable(
            f"{self.portal.id} unreachable for {name}: {last_reason}",
            remedy_url=self.portal.site_url,
        )
