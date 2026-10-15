import asyncio
import contextlib
import datetime
import decimal
import logging
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import duckdb
from pydantic import BaseModel

from au_opendata_mcp.ckan.client import CkanClient, strip_internal_columns
from au_opendata_mcp.ckan.models import CkanResource
from au_opendata_mcp.config import Settings
from au_opendata_mcp.errors import AuOpenDataError, QueryTimeout, ResourceNotFound, SqlRejected
from au_opendata_mcp.models import Sourced
from au_opendata_mcp.portals import get_portal
from au_opendata_mcp.safety import validate_sql, wrap_with_limit
from au_opendata_mcp.services.catalog import (
    CatalogService,
    DatasetDetail,
    ResourceInfo,
    assess_queryable,
)
from au_opendata_mcp.services.materialise import Materialiser

log = logging.getLogger(__name__)


class ColumnInfo(BaseModel):
    name: str
    type: str


class QueryResult(Sourced):
    resource_id: str
    portal: str
    sql: str
    columns: list[ColumnInfo]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool


class PreviewResult(Sourced):
    resource_id: str
    portal: str
    source: Literal["datastore", "materialised"]
    columns: list[ColumnInfo]
    rows: list[dict[str, Any]]
    total_rows: int | None


@dataclass(slots=True)
class ResolvedResource:
    resource: ResourceInfo
    dataset: DatasetDetail
    catalog_urls: set[str]
    last_modified: str | None


def jsonable(value: Any) -> Any:
    """Coerce DuckDB values into something both MCP and JSON can carry."""
    if isinstance(value, datetime.datetime | datetime.date | datetime.time):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, bytes | bytearray | memoryview):
        return bytes(value).hex()
    return value


def execute_in_sandbox(
    parquet: Path,
    sql: str,
    limit: int,
    memory_limit: str,
    timeout_seconds: float | None = None,
) -> tuple[list[ColumnInfo], list[dict[str, Any]], bool]:
    """Run caller SQL against a locked-down in-memory DuckDB.

    THE ORDER OF THE FIRST THREE STATEMENTS IS THE SECURITY CONTROL (docs/design.md §6.2).
    The table must be materialised BEFORE external access is revoked, because revoking it
    also disables read_parquet. Locking first and loading second fails outright; loading
    first and never locking leaves the filesystem open to caller SQL.
    Verified on DuckDB 1.5.5. Do not reorder. See tests/test_query_execute.py.

    This call blocks the calling thread for as long as the query runs -- callers on the
    event loop must go through `run_sandboxed_query` instead of calling this directly, or a
    slow or runaway query stalls every other concurrent request, not just its own.

    `timeout_seconds`, when given, bounds only the caller's query, not the CREATE TABLE load
    above it: a watchdog timer calls `con.interrupt()` if the query is still running once the
    budget elapses, and that abort is reported as `QueryTimeout` rather than `SqlRejected` --
    a timeout is a runtime abort, not a rejected query. `memory_limit` bounds memory; this
    bounds wall-clock time; they are complementary, and neither substitutes for the other.
    """
    con = duckdb.connect()
    timer: threading.Timer | None = None
    try:
        con.execute(f"SET memory_limit = '{memory_limit}'")
        con.execute("CREATE TABLE t AS SELECT * FROM read_parquet(?)", [str(parquet)])
        con.execute("SET enable_external_access = false")
        con.execute("SET lock_configuration = true")

        if timeout_seconds is not None:

            def _interrupt_ignoring_races() -> None:
                # Timer.cancel() cannot stop a callback that has already left its wait
                # state, so this can in principle still fire after `con.close()` below has
                # run (a narrow race between the finally block and the daemon timer
                # thread). Swallow duckdb.Error rather than let it surface as unhandled
                # exception noise on the timer thread -- there is nothing left to abort.
                with contextlib.suppress(duckdb.Error):
                    con.interrupt()

            timer = threading.Timer(timeout_seconds, _interrupt_ignoring_races)
            timer.daemon = True
            timer.start()

        try:
            cursor = con.execute(wrap_with_limit(sql, limit))
            description = cursor.description or []
            columns = [ColumnInfo(name=str(d[0]), type=str(d[1])) for d in description]
            names = [c.name for c in columns]
            fetched = cursor.fetchall()
        finally:
            if timer is not None:
                timer.cancel()
    except duckdb.InterruptException as exc:
        # Only ever armed when timeout_seconds is not None (see above).
        assert timeout_seconds is not None
        raise QueryTimeout(
            f"the query exceeded the {timeout_seconds:g}s time budget and was aborted; "
            "narrow it and try again -- add a WHERE clause, reduce the number of joins, or "
            "use an aggregate instead of a full scan"
        ) from exc
    except duckdb.Error as exc:
        raise SqlRejected(f"the query could not be run: {exc}") from exc
    finally:
        con.close()

    truncated = len(fetched) > limit
    rows = [
        {name: jsonable(value) for name, value in zip(names, row, strict=True)}
        for row in fetched[:limit]
    ]
    return columns, rows, truncated


async def run_sandboxed_query(
    parquet: Path,
    sql: str,
    limit: int,
    memory_limit: str,
    timeout_seconds: float,
) -> tuple[list[ColumnInfo], list[dict[str, Any]], bool]:
    """Run `execute_in_sandbox` off the event loop, bounded by `timeout_seconds`.

    DuckDB's `execute()` is a blocking call. Running it directly inside `async def` code
    would stall the event loop -- and therefore every other concurrent MCP/REST caller, not
    just this one -- for as long as a caller-supplied query takes to run, or hang: a single
    runaway query needs no external access at all to do this, since `enable_external_access`
    has nothing to do with CPU time. `asyncio.to_thread` hops the blocking call onto a worker
    thread so the loop keeps ticking while it runs; `timeout_seconds` is passed straight
    through to `execute_in_sandbox`'s own watchdog, which aborts the query via
    `con.interrupt()` if it overruns.

    Every caller that runs SQL against the sandbox -- `query_resource` here, and
    `preview_resource` -- must call this, not `execute_in_sandbox` directly, so
    both get the same event-loop protection and time budget.
    """
    return await asyncio.to_thread(
        execute_in_sandbox, parquet, sql, limit, memory_limit, timeout_seconds
    )


def _read_parquet_row_count(parquet: Path) -> int:
    """Read the exact row count straight from the Parquet file's own footer metadata.

    Deliberately NOT run through the sandbox in `execute_in_sandbox`: `parquet_file_metadata`
    requires external file access, which the sandbox revokes (`enable_external_access =
    false`) as its core security control (see `execute_in_sandbox`'s docstring), and calling
    it inside the sandbox raises `duckdb.PermissionException`. That lockdown exists to
    contain caller-supplied SQL; it has nothing to protect here, because `parquet` is our own
    trusted artifact written by `materialise.py`, not caller SQL. A plain, unlocked
    connection reads only the footer -- no `SET`, no `CREATE TABLE`, no scan of the data --
    so it is also far cheaper than the `COUNT(*)` full scan this replaces, and (unlike that
    scan) it does not consume any part of the caller's query time budget.

    Confirmed empirically on DuckDB 1.5.5: `parquet_file_metadata` returns one row per file
    with `num_rows` already the file's total row count, not one row per row group.
    """
    con = duckdb.connect()
    try:
        row = con.execute(
            "SELECT num_rows FROM parquet_file_metadata(?)", [str(parquet)]
        ).fetchone()
        return int(row[0]) if row is not None else 0
    finally:
        con.close()


async def read_parquet_row_count(parquet: Path) -> int:
    """Run `_read_parquet_row_count` off the event loop -- it is still a blocking DuckDB call.

    Cheap as this metadata read is, it is not free, and it still holds the GIL while DuckDB's
    C++ layer does the footer read -- so it goes through `asyncio.to_thread` for the same
    reason `run_sandboxed_query` does: no blocking DuckDB call may run directly on the event
    loop, no matter how fast it usually is.
    """
    return await asyncio.to_thread(_read_parquet_row_count, parquet)


class QueryService:
    def __init__(
        self,
        clients: Mapping[str, CkanClient],
        catalog: CatalogService,
        materialiser: Materialiser,
        settings: Settings,
    ) -> None:
        self.clients = clients
        self.catalog = catalog
        self.materialiser = materialiser
        self.settings = settings

    def _client(self, portal_id: str) -> CkanClient:
        # Mirrors CatalogService._client(): validate before indexing, so an unknown
        # portal fails loudly with a ValueError naming the valid options rather than
        # a bare KeyError -- portal is free-text from a model, so this is a likely
        # mistake, not an exotic one, and the clean error lets the model self-correct.
        get_portal(portal_id)
        return self.clients[portal_id]

    async def resolve(self, resource_id: str, portal: str = "data.gov.au") -> ResolvedResource:
        raw = await self._client(portal).action("resource_show", {"id": resource_id})
        package_id = raw.get("package_id")
        if not package_id:
            raise ResourceNotFound(
                f"resource {resource_id!r} has no parent dataset on {portal}",
                remedy_url=raw.get("url"),
            )
        dataset = await self.catalog.get_dataset(package_id, portal)
        listed = next((r for r in dataset.resources if r.resource_id == resource_id), None)
        if listed is None:
            raise ResourceNotFound(
                f"resource {resource_id!r} is not listed on dataset {dataset.dataset_id!r}",
                remedy_url=dataset.dataset_url,
            )
        # resource_show is the authoritative, freshly fetched source for THIS resource_id.
        # The matching entry inside the parent dataset's resources list (from package_show)
        # is only used above to confirm the resource is genuinely part of this dataset --
        # trusting its (potentially stale) format/url instead of resource_show's own answer
        # would let a resource whose format has since changed be classified from cached data.
        ckan_resource = CkanResource.model_validate(raw)
        verdict, reason = assess_queryable(ckan_resource, self.settings)
        resource = ResourceInfo(
            resource_id=ckan_resource.id,
            name=ckan_resource.name,
            format=ckan_resource.format,
            size_bytes=ckan_resource.size,
            url=ckan_resource.url,
            datastore_active=ckan_resource.datastore_active,
            queryable=verdict,
            queryable_reason=reason,
        )
        catalog_urls = {r.url for r in dataset.resources if r.url}
        if resource.url:
            # Portal-declared for this exact resource_id via resource_show -- same trust
            # boundary as the dataset's own resources list, so this only widens coverage
            # for the case above, never the set of hosts that could be trusted.
            catalog_urls.add(resource.url)
        return ResolvedResource(
            resource=resource,
            dataset=dataset,
            catalog_urls=catalog_urls,
            last_modified=raw.get("last_modified") or dataset.modified,
        )

    async def query_resource(
        self,
        resource_id: str,
        sql: str,
        portal: str = "data.gov.au",
        limit: int = 100,
    ) -> QueryResult:
        # Validate before resolving or downloading: a bad query must cost nothing.
        normalised = validate_sql(sql)
        capped = max(1, min(limit, self.settings.max_query_limit))

        resolved = await self.resolve(resource_id, portal)
        parquet = await self.materialiser.parquet_for(
            resolved.resource, resolved.catalog_urls, portal, resolved.last_modified
        )
        columns, rows, truncated = await run_sandboxed_query(
            parquet,
            normalised,
            capped,
            self.settings.duckdb_memory_limit,
            self.settings.query_timeout_seconds,
        )
        log.info(
            "query_resource resource_id=%s rows=%d truncated=%s", resource_id, len(rows), truncated
        )
        return QueryResult(
            resource_id=resource_id,
            portal=portal,
            sql=normalised,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            dataset_url=resolved.dataset.dataset_url,
            organisation=resolved.dataset.organisation,
            licence=resolved.dataset.licence,
        )

    async def preview_resource(
        self, resource_id: str, portal: str = "data.gov.au", limit: int = 20
    ) -> PreviewResult:
        capped = max(1, min(limit, self.settings.max_preview_limit))
        resolved = await self.resolve(resource_id, portal)

        if resolved.resource.datastore_active:
            try:
                return await self._preview_from_datastore(resolved, portal, capped)
            except AuOpenDataError as exc:
                # DataStore is a fast path, not a hard dependency: fall back to
                # materialising on a genuine upstream failure (UpstreamUnavailable,
                # ResourceNotFound). Deliberately NOT `except Exception` -- that would
                # also swallow a real bug (a KeyError on a malformed field, a
                # pydantic.ValidationError building PreviewResult) and silently mask it
                # as "DataStore didn't work" instead of surfacing it.
                log.info("datastore preview failed for %s, materialising: %s", resource_id, exc)

        return await self._preview_from_parquet(resolved, portal, capped)

    async def _preview_from_datastore(
        self, resolved: ResolvedResource, portal: str, limit: int
    ) -> PreviewResult:
        result = await self._client(portal).action(
            "datastore_search", {"resource_id": resolved.resource.resource_id, "limit": limit}
        )
        fields = result.get("fields", [])
        rows = strip_internal_columns(result.get("records", []))
        return PreviewResult(
            resource_id=resolved.resource.resource_id,
            portal=portal,
            source="datastore",
            columns=[
                ColumnInfo(name=str(f["id"]), type=str(f.get("type", "unknown"))) for f in fields
            ],
            rows=[{k: jsonable(v) for k, v in row.items()} for row in rows],
            total_rows=result.get("total"),
            dataset_url=resolved.dataset.dataset_url,
            organisation=resolved.dataset.organisation,
            licence=resolved.dataset.licence,
        )

    async def _preview_from_parquet(
        self, resolved: ResolvedResource, portal: str, limit: int
    ) -> PreviewResult:
        parquet = await self.materialiser.parquet_for(
            resolved.resource, resolved.catalog_urls, portal, resolved.last_modified
        )
        columns, rows, _ = await run_sandboxed_query(
            parquet,
            "SELECT * FROM t",
            limit,
            self.settings.duckdb_memory_limit,
            self.settings.query_timeout_seconds,
        )
        # Row count comes from the Parquet footer, not a second sandboxed COUNT(*): that
        # would double the memory/IO of loading the whole file and -- because each sandbox
        # call gets its own full timeout budget -- would let a preview legitimately take up
        # to 2x query_timeout_seconds. See read_parquet_row_count's docstring.
        total_rows = await read_parquet_row_count(parquet)
        return PreviewResult(
            resource_id=resolved.resource.resource_id,
            portal=portal,
            source="materialised",
            columns=columns,
            rows=rows,
            total_rows=total_rows,
            dataset_url=resolved.dataset.dataset_url,
            organisation=resolved.dataset.organisation,
            licence=resolved.dataset.licence,
        )
