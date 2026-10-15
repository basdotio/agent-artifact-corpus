import asyncio
import hashlib
import logging
import tempfile
from collections.abc import Callable
from pathlib import Path

import duckdb
import httpx

from au_opendata_mcp.cache import BlobCache
from au_opendata_mcp.config import Settings
from au_opendata_mcp.errors import DownloadFailed, ResourceNotQueryable, ResourceTooLarge
from au_opendata_mcp.safety import (
    MAX_REDIRECTS,
    _resolve_host,
    assert_safe_url,
    assert_url_in_catalog,
)
from au_opendata_mcp.services.catalog import ResourceInfo

log = logging.getLogger(__name__)

TABULAR_READERS: dict[str, str] = {
    "CSV": "csv",
    "TSV": "csv",
    "XLSX": "excel",
    "XLS": "excel",
}


class Materialiser:
    def __init__(self, http: httpx.AsyncClient, settings: Settings, blobs: BlobCache) -> None:
        if http.follow_redirects:
            # _download's SSRF guard only works because it sees every redirect hop and
            # re-validates it itself. If httpx follows redirects internally, that loop
            # never runs and the final -- possibly private -- address is never checked.
            # Fail loudly (not an assert, which vanishes under python -O) rather than
            # let this invariant rot silently across files.
            raise ValueError(
                "Materialiser requires an httpx.AsyncClient constructed with "
                "follow_redirects=False: _download re-validates SSRF safety on every "
                "redirect hop itself, and a client that follows redirects internally "
                "would silently bypass that guard."
            )
        self.http = http
        self.settings = settings
        self.blobs = blobs
        self._resolve: Callable[[str], list[str]] = _resolve_host

    def cache_key(self, resource: ResourceInfo, portal: str, last_modified: str | None) -> str:
        raw = f"{portal}|{resource.resource_id}|{last_modified or ''}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def parquet_for(
        self,
        resource: ResourceInfo,
        catalog_urls: set[str],
        portal: str = "data.gov.au",
        last_modified: str | None = None,
    ) -> Path:
        fmt = (resource.format or "").strip().upper()
        reader = TABULAR_READERS.get(fmt)
        if reader is None:
            raise ResourceNotQueryable(
                f"format {resource.format or 'unknown'!r} is not tabular",
                remedy_url=resource.url,
            )
        if not resource.url:
            raise ResourceNotQueryable(
                "resource has no download URL in the catalog", remedy_url=None
            )

        key = self.cache_key(resource, portal, last_modified)
        cached = self.blobs.path_for(key)
        if cached is not None:
            # A cache hit must return before the resource budget applies -- a cached
            # resource is not downloaded at all, so it must not be subject to a
            # download timeout.
            log.info(
                "materialisation served from cache",
                extra={"event": "cache", "outcome": "hit", "resource_id": resource.resource_id},
            )
            return cached

        log.info(
            "materialising resource",
            extra={"event": "cache", "outcome": "miss", "resource_id": resource.resource_id},
        )
        assert_url_in_catalog(resource.url, catalog_urls)
        try:
            parquet = await asyncio.wait_for(
                self._fetch_and_convert(resource.url, reader),
                timeout=self.settings.resource_budget_seconds,
            )
        except TimeoutError as exc:
            raise DownloadFailed(
                f"materialising {resource.url} exceeded the "
                f"{self.settings.resource_budget_seconds:.0f}s total resource budget",
                remedy_url=resource.url,
            ) from exc
        return self.blobs.store(key, parquet)

    async def _fetch_and_convert(self, url: str, reader: str) -> Path:
        """Download and convert one resource. Wrapped by parquet_for in the overall
        per-resource time budget -- httpx's download_timeout_seconds is only a
        per-phase timeout, not a wall-clock cap, so a slow-trickle upstream (or a long
        redirect chain) could otherwise hold this open well past the budget without
        ever tripping a phase timeout or the byte ceiling.
        """
        downloaded = await self._download(url)
        try:
            # Off the event loop, for the same reason run_sandboxed_query hops DuckDB off
            # it: _convert is a blocking DuckDB COPY, and _pick_csv_encoding reads and
            # decodes the whole file in memory before that even starts. Measured on a
            # 90 MB CSV, running it inline blocked the loop for ~1.1s -- every other
            # concurrent MCP/REST caller stalled behind one conversion. It also gives
            # parquet_for's asyncio.wait_for an await point, without which the 60s
            # resource budget cannot fire while a conversion is in progress.
            return await asyncio.to_thread(self._convert, downloaded, reader, url)
        finally:
            downloaded.unlink(missing_ok=True)

    async def _download(self, url: str) -> Path:
        """Stream to a temp file under a hard byte ceiling, re-validating every redirect hop.

        SSRF re-validation is per-hop, not per-connection, and that gap does not fully
        close: assert_safe_url resolves the hostname with socket.getaddrinfo, then httpx
        independently resolves it again when it actually opens the connection. A hostile
        authoritative DNS server can answer differently between those two resolutions
        (classic DNS rebinding / TOCTOU), and because every redirect hop re-validates, a
        long redirect chain gives such a server N chances rather than one. Re-validating
        on each hop narrows the race window; it does not eliminate it. Closing this
        properly needs a custom transport that connects to the already-validated IP while
        still presenting the original hostname for TLS SNI, which is disproportionate for
        a self-hosted tool fetching from known government domains. That trade-off is a
        deliberate, accepted decision, not an oversight -- do not read this loop as a
        complete guarantee.
        """
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            assert_safe_url(current, resolve=self._resolve)
            try:
                async with self.http.stream(
                    "GET", current, timeout=self.settings.download_timeout_seconds
                ) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise DownloadFailed(f"redirect from {current} had no location header")
                        current = str(httpx.URL(current).join(location))
                        continue
                    if response.status_code >= 400:
                        raise DownloadFailed(
                            f"download of {current} failed with HTTP {response.status_code}",
                            remedy_url=url,
                        )

                    return await self._stream_to_tempfile(response, url)
            except httpx.HTTPError as exc:
                raise DownloadFailed(
                    f"download of {current} failed: {exc}", remedy_url=url
                ) from exc

        raise DownloadFailed(f"too many redirects fetching {url}", remedy_url=url)

    async def _stream_to_tempfile(self, response: httpx.Response, remedy_url: str) -> Path:
        """Write the response body to a temp file under the byte ceiling.

        The partial file is deleted on any failure -- ceiling exceeded, connection
        dropped mid-stream, anything -- so a rejected or interrupted download never
        leaves an orphaned file on disk. Without this, an attacker (or just a flaky
        upstream) could fill the cache disk over many rejected oversized requests even
        though every individual request is correctly refused.
        """
        written = 0
        with tempfile.NamedTemporaryFile(delete=False, suffix=".download") as handle:
            dest = Path(handle.name)
            try:
                async for chunk in response.aiter_bytes():
                    written += len(chunk)
                    # content-length is a hint. This is the limit.
                    if written > self.settings.max_resource_bytes:
                        limit_mb = self.settings.max_resource_bytes // (1024 * 1024)
                        raise ResourceTooLarge(
                            f"resource exceeds the {limit_mb} MB limit", remedy_url=remedy_url
                        )
                    handle.write(chunk)
            except BaseException:
                dest.unlink(missing_ok=True)
                raise
        return dest

    def _convert(self, source: Path, reader: str, remedy_url: str) -> Path:
        """Convert the downloaded file to Parquet at a fresh temp path.

        Reserves the destination path with NamedTemporaryFile (not mkdtemp): a
        directory created just to hold one file, with only the file moved out on
        success, leaves an empty directory behind forever -- on every successful
        conversion, not just failed ones. A single temp file, deleted in the except
        clause on any failure, has no such residue.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet") as handle:
            dest = Path(handle.name)

        con = duckdb.connect()
        try:
            con.execute(f"SET memory_limit = '{self.settings.duckdb_memory_limit}'")

            if reader == "excel":
                try:
                    con.execute("INSTALL excel")
                    con.execute("LOAD excel")
                except duckdb.Error as exc:
                    raise ResourceNotQueryable(
                        "XLSX support needs DuckDB's excel extension, which could not be "
                        f"loaded: {exc}",
                        remedy_url=remedy_url,
                    ) from exc
                expression = f"SELECT * FROM read_xlsx('{source}')"
            else:
                # The encoding must be picked before calling DuckDB, not discovered by
                # retrying on failure: with ignore_errors=true DuckDB does not raise
                # when a row fails to decode under the wrong encoding, it silently
                # drops that row. A retry-on-exception fallback would therefore never
                # fire and a Café row would just vanish instead of being read
                # correctly under latin-1.
                encoding = _pick_csv_encoding(source)
                expression = (
                    f"SELECT * FROM read_csv_auto('{source}', ignore_errors=true, "
                    f"sample_size=-1, encoding='{encoding}')"
                )

            try:
                con.execute(f"COPY ({expression}) TO '{dest}' (FORMAT PARQUET)")
            except duckdb.Error as exc:
                raise ResourceNotQueryable(
                    f"resource could not be parsed as a table: {exc}", remedy_url=remedy_url
                ) from exc
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
        finally:
            con.close()

        return dest


def _pick_csv_encoding(path: Path) -> str:
    """UTF-8 when the raw bytes are valid UTF-8, otherwise latin-1.

    latin-1 maps every byte 0-255 to a character, so it never fails to decode -- but
    declaring it for a genuinely UTF-8 file would turn legitimate multi-byte sequences
    (e.g. accented characters) into mojibake. So UTF-8 is preferred whenever the bytes
    are actually valid UTF-8, and latin-1 is used only as the fallback for files that
    are not.
    """
    try:
        path.read_bytes().decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"
