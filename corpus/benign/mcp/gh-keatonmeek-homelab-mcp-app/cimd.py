"""Opt-in, exact-URL CIMD with separately trusted JWKS destinations.

This adapter targets the pinned FastMCP 4.0.10 CIMD manager extension points.
Network requests retain upstream HTTPS, public-IP/DNS-pinning, timeout, size,
and no-redirect protections. Remote keys are fetched here and converted to
inline JWKS before the assertion verifier sees them, so it cannot fetch a new
URL based on metadata. No client-supplied URL can expand either allowlist.
"""
from __future__ import annotations

import json
import time
from urllib.parse import urlsplit

from fastmcp import settings as fastmcp_settings
from fastmcp.server.auth.cimd import CIMDClientManager, CIMDDocument, CIMDFetcher, CIMDValidationError
from fastmcp.server.auth.ssrf import SSRFError, SSRFFetchError, ssrf_safe_fetch_response


class TrustedCIMDFetcher(CIMDFetcher):
    MAX_METADATA_BYTES = 5120
    MAX_JWKS_BYTES = 65536
    MAX_CACHE_SECONDS = 300

    def __init__(self, metadata_uris: tuple[str, ...], jwks_uris: tuple[str, ...], redirects: tuple[str, ...]):
        super().__init__()
        self.metadata_uris = frozenset(metadata_uris)
        self.jwks_uris = frozenset(jwks_uris)
        self.redirects = frozenset(redirects)
        self._trusted_cache: dict[str, tuple[float, CIMDDocument]] = {}

    @staticmethod
    def _cache_seconds(headers: dict[str, str]) -> int:
        directives = {item.strip().lower() for item in headers.get("cache-control", headers.get("Cache-Control", "")).split(",")}
        if {"no-store", "no-cache"} & directives:
            return 0
        result = TrustedCIMDFetcher.MAX_CACHE_SECONDS
        for directive in directives:
            if directive.startswith("max-age="):
                try:
                    result = min(result, max(0, int(directive.split("=", 1)[1].strip('"'))))
                except ValueError:
                    return 0
        try:
            result = max(0, result - int(headers.get("age", headers.get("Age", "0"))))
        except ValueError:
            return 0
        return result

    async def _fetch_json(self, uri: str, allowed: frozenset[str], limit: int):
        if uri not in allowed:
            raise CIMDValidationError("CIMD/JWKS URL is not explicitly trusted")
        # Opting into an outbound proxy must not silently bypass pinned DNS/IP
        # protection for this authentication surface.
        if fastmcp_settings.ssrf_trust_proxy:
            raise CIMDValidationError("CIMD requires DNS-pinned SSRF protection; trusted proxy mode is unsupported")
        try:
            response = await ssrf_safe_fetch_response(
                uri, require_path=True, max_size=limit, timeout=10.0,
                overall_timeout=30.0, allowed_status_codes={200},
            )
            if response.status_code != 200 or len(response.content) > limit:
                raise CIMDValidationError("Invalid or oversized CIMD/JWKS response")
            data = json.loads(response.content)
        except (SSRFError, SSRFFetchError, ValueError, UnicodeError) as exc:
            raise CIMDValidationError("Trusted CIMD/JWKS document could not be safely fetched") from exc
        if not isinstance(data, dict):
            raise CIMDValidationError("CIMD/JWKS must be a JSON object")
        return data, self._cache_seconds(dict(response.headers))

    async def fetch(self, client_id_url: str) -> CIMDDocument:
        if client_id_url not in self.metadata_uris:
            raise CIMDValidationError("Client metadata URL is not explicitly trusted")
        cached = self._trusted_cache.get(client_id_url)
        if cached and cached[0] > time.monotonic():
            return cached[1].model_copy(deep=True)
        # Remove expired records so failures never return stale key material.
        self._trusted_cache.pop(client_id_url, None)
        data, ttl = await self._fetch_json(client_id_url, self.metadata_uris, self.MAX_METADATA_BYTES)
        try:
            doc = CIMDDocument.model_validate(data)
        except ValueError as exc:
            raise CIMDValidationError("Invalid trusted client metadata") from exc
        if str(doc.client_id) != client_id_url:
            raise CIMDValidationError("Client metadata identity does not exactly match its URL")
        redirects = [uri for uri in doc.redirect_uris if uri in self.redirects]
        if not redirects:
            raise CIMDValidationError("Client metadata has no exact configured callback")
        # Metadata cannot broaden configured callbacks, even via wildcard or query.
        doc = doc.model_copy(update={"redirect_uris": redirects}, deep=True)
        if doc.jwks_uri is not None:
            uri = str(doc.jwks_uri)
            # Check exact trust before any DNS resolution or network access.
            keys, keys_ttl = await self._fetch_json(uri, self.jwks_uris, self.MAX_JWKS_BYTES)
            ttl = min(ttl, keys_ttl)
            doc = doc.model_copy(update={"jwks_uri": None, "jwks": keys}, deep=True)
        if doc.token_endpoint_auth_method == "private_key_jwt":
            if not isinstance(doc.jwks, dict) or not isinstance(doc.jwks.get("keys"), list) or not doc.jwks["keys"]:
                raise CIMDValidationError("private_key_jwt requires a nonempty trusted JWKS")
        if ttl > 0:
            self._trusted_cache[client_id_url] = (time.monotonic() + ttl, doc.model_copy(deep=True))
        return doc

    def validate_redirect_uri(self, doc: CIMDDocument, redirect_uri: str) -> bool:
        return redirect_uri in self.redirects and redirect_uri in doc.redirect_uris


class TrustedCIMDClientManager(CIMDClientManager):
    def __init__(self, *, metadata_uris: tuple[str, ...], jwks_uris: tuple[str, ...], redirects: tuple[str, ...], default_scope: str):
        super().__init__(enable_cimd=True, default_scope=default_scope, allowed_redirect_uri_patterns=list(redirects))
        self.metadata_uris = frozenset(metadata_uris)
        self._fetcher = TrustedCIMDFetcher(metadata_uris, jwks_uris, redirects)

    def is_cimd_client_id(self, client_id: str) -> bool:
        return client_id in self.metadata_uris

    async def get_client(self, client_id_url: str):
        if client_id_url not in self.metadata_uris:
            return None
        return await super().get_client(client_id_url)


def is_url_client_id(client_id: str) -> bool:
    try:
        return bool(urlsplit(client_id).scheme)
    except ValueError:
        return True
