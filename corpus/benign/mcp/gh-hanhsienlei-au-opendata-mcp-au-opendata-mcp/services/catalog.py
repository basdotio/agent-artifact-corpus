import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Literal, TypeVar

import httpx
from pydantic import BaseModel

from au_opendata_mcp.ckan.client import CkanClient
from au_opendata_mcp.ckan.models import CkanDataset, CkanResource
from au_opendata_mcp.config import Settings
from au_opendata_mcp.errors import AuOpenDataError, UpstreamUnavailable
from au_opendata_mcp.models import Sourced
from au_opendata_mcp.portals import Portal, all_portals, get_portal
from au_opendata_mcp.safety import _resolve_host, assert_safe_url

log = logging.getLogger(__name__)

TABULAR_FORMATS = frozenset({"CSV", "TSV", "XLSX", "XLS"})
Queryable = Literal["yes", "no", "unknown"]
T = TypeVar("T")


class PortalInfo(BaseModel):
    id: str
    label: str
    site_url: str
    dataset_count: int | None


class ResourceInfo(BaseModel):
    resource_id: str
    name: str | None
    format: str | None
    size_bytes: int | None
    url: str | None
    datastore_active: bool
    queryable: Queryable
    queryable_reason: str | None


class DatasetSummary(Sourced):
    dataset_id: str
    title: str
    portal: str
    formats: list[str]
    modified: str | None


class DatasetSearch(BaseModel):
    """Search hits plus each portal's count of every match, of which `results` is a page.

    A portal that could not be reached has no entry in `total_matches`, rather than 0:
    zero would claim nothing matched there.
    """

    total_matches: dict[str, int]
    results: list[DatasetSummary]


class DatasetDetail(Sourced):
    dataset_id: str
    title: str
    description: str | None
    portal: str
    modified: str | None
    resources: list[ResourceInfo]


class OrganizationSummary(BaseModel):
    name: str
    title: str | None
    dataset_count: int | None
    portal: str


def _mb(n: int) -> str:
    return f"{n / (1024 * 1024):.0f} MB"


def assess_queryable(resource: CkanResource, settings: Settings) -> tuple[Queryable, str | None]:
    """Decide up front whether query_resource can work, so the caller need not discover it
    by consuming an error (docs/design.md §5.1).

    data.gov.au uses ``size: -1`` as its "unknown size" sentinel, and CKAN's absent-size
    case is ``None``. Both, along with a reported ``0``, mean the same thing: the portal
    has not told us how big the resource is. Any non-positive size is normalised to
    "unknown" so the HEAD size probe (which only fires on "unknown") gets a chance to
    resolve the real size instead of the resource being wrongly advertised as queryable.
    """
    fmt = (resource.format or "").strip().upper()
    if fmt not in TABULAR_FORMATS:
        shown = resource.format or "unknown"
        return "no", f"format {shown!r} is not tabular"
    size = resource.size
    if size is not None and size > 0:
        if size > settings.max_resource_bytes:
            return "no", (
                f"resource is {_mb(size)}, over the {_mb(settings.max_resource_bytes)} limit"
            )
        return "yes", None
    return "unknown", "size not declared by the portal; enforced during download instead"


def _licence(ds: CkanDataset) -> str:
    return ds.license_title or ds.license_id or "not specified"


def _organisation(ds: CkanDataset) -> str:
    if ds.organization is None:
        return "unknown"
    return ds.organization.title or ds.organization.name


def _dataset_url(portal: Portal, ds: CkanDataset) -> str:
    return f"{portal.site_url}/dataset/{ds.name}"


class CatalogService:
    def __init__(
        self,
        clients: Mapping[str, CkanClient],
        settings: Settings,
        http: httpx.AsyncClient,
    ) -> None:
        self.clients = clients
        self.settings = settings
        # The HEAD probe is an outbound fetch of a *portal-supplied* URL, not a CKAN API
        # call, so it gets the shared client directly rather than reaching into an
        # arbitrary CkanClient's `.http` and borrowing its transport.
        self.http = http
        # Injectable for the same reason Materialiser's is: so tests exercise the guard
        # without a real DNS lookup. See tests/test_safety_urls.py for the resolver itself.
        self._resolve: Callable[[str], list[str]] = _resolve_host

    def _client(self, portal_id: str) -> CkanClient:
        get_portal(portal_id)
        return self.clients[portal_id]

    async def _probe_size(self, resource: ResourceInfo) -> None:
        """Resolve one undeclared size via HEAD, under a dedicated short budget.

        The URL comes from portal metadata, but "the portal named it" is not the same as
        "it is safe to fetch": a resource whose url is ``http://169.254.169.254/...``
        would otherwise be HEADed by the server, from inside the server's own network.
        So this goes through the same `assert_safe_url` guard as an actual download, and
        a refusal is recorded as the resource's `queryable_reason` rather than failing the
        whole `get_dataset` call over one bad resource among many.

        Redirects are deliberately not followed. The shared client is built with
        ``follow_redirects=False`` -- an invariant `Materialiser.__init__` raises to
        protect, because following redirects internally means the post-redirect address is
        never re-validated. Passing ``follow_redirects=True`` here would have violated that
        invariant on the very same client object. An unchecked redirect target is exactly
        the address this guard exists to refuse, so an unresolved size is the right answer.

        `assert_safe_url` resolves DNS with a blocking `socket.getaddrinfo`, so it is
        offloaded: `_probe_sizes` runs these concurrently, and a blocking resolve would
        serialise them and stall the loop besides.
        """
        if resource.queryable != "unknown" or not resource.url:
            return
        try:
            await asyncio.to_thread(assert_safe_url, resource.url, resolve=self._resolve)
        except AuOpenDataError as exc:
            resource.queryable = "no"
            resource.queryable_reason = f"refused to probe this URL: {exc.message}"
            return
        try:
            resp = await self.http.head(
                resource.url,
                timeout=self.settings.head_timeout_seconds,
            )
        except httpx.HTTPError:
            resource.queryable_reason = "size could not be probed; enforced during download instead"
            return

        # Redirects (3xx) and errors (>=400) carry their own Content-Length for the
        # redirect/error body, not the actual resource. Treat as unresolvable and do
        # not follow the redirect (an invariant Materialiser.__init__ protects).
        if resp.is_redirect or resp.status_code >= 400:
            resource.queryable_reason = "size could not be probed; enforced during download instead"
            return

        length = resp.headers.get("content-length")
        if not length or not length.isdigit():
            resource.queryable_reason = (
                "size not declared and not reported by the server; enforced during download instead"
            )
            return

        resource.size_bytes = int(length)
        if resource.size_bytes > self.settings.max_resource_bytes:
            resource.queryable = "no"
            resource.queryable_reason = (
                f"resource is {_mb(resource.size_bytes)}, over the "
                f"{_mb(self.settings.max_resource_bytes)} limit"
            )
        else:
            resource.queryable = "yes"
            resource.queryable_reason = None

    async def _probe_sizes(self, resources: list[ResourceInfo]) -> None:
        pending = [r for r in resources if r.queryable == "unknown" and r.url]
        if pending:
            await asyncio.gather(*(self._probe_size(r) for r in pending))

    async def _fan_out_all_portals(
        self, op: str, make_call: Callable[[Portal], Awaitable[list[T]]]
    ) -> list[T]:
        """Run `make_call` concurrently against every portal and merge the successes.

        A per-portal failure is logged at WARNING (naming the portal and the
        exception type) and otherwise silently excluded from the merge — that is the
        intended "partial degradation" behaviour. But if *every* portal failed,
        returning an empty list would be indistinguishable from "no results",
        and the consumer here is a language model that reports the answer to a
        user in prose: it must not be able to confuse "nothing matched" with
        "we could not reach anything". So a total outage raises instead.
        """
        portals = all_portals()
        results = await asyncio.gather(*(make_call(p) for p in portals), return_exceptions=True)
        merged: list[T] = []
        failed: list[str] = []
        for p, item in zip(portals, results, strict=True):
            if isinstance(item, BaseException):
                # The *type*, never the exception: a portal's error text (and anything
                # this codebase interpolates into an exception message) can carry the
                # caller's own search string, and this line is the last thing between
                # that and the log file.
                log.warning("%s failed for portal %s: %s", op, p.id, type(item).__name__)
                failed.append(p.id)
            else:
                merged.extend(item)
        if portals and len(failed) == len(portals):
            raise UpstreamUnavailable(f"all portals unreachable for {op}: {', '.join(failed)}")
        return merged

    async def list_portals(self) -> list[PortalInfo]:
        async def count(portal: Portal) -> int | None:
            try:
                result = await self._client(portal.id).action("package_search", {"rows": 0})
                return int(result["count"])
            except Exception:
                return None  # a portal being down must not fail the whole listing

        portals = all_portals()
        counts = await asyncio.gather(*(count(p) for p in portals))
        return [
            PortalInfo(id=p.id, label=p.label, site_url=p.site_url, dataset_count=c)
            for p, c in zip(portals, counts, strict=True)
        ]

    async def search_datasets(
        self,
        q: str,
        portal: str = "data.gov.au",
        organisation: str | None = None,
        format: str | None = None,
        limit: int = 20,
    ) -> DatasetSearch:
        if portal == "all":

            async def one(p: Portal) -> list[DatasetSearch]:
                return [await self.search_datasets(q, p.id, organisation, format, limit)]

            parts = await self._fan_out_all_portals("search_datasets", one)
            return DatasetSearch(
                total_matches={k: v for part in parts for k, v in part.total_matches.items()},
                results=[hit for part in parts for hit in part.results],
            )

        rows = max(1, min(limit, self.settings.max_search_limit))
        params: dict[str, object] = {"q": q, "rows": rows}
        filters = []
        if organisation:
            filters.append(f'organization:"{organisation}"')
        if format:
            filters.append(f'res_format:"{format.upper()}"')
        if filters:
            params["fq"] = " ".join(filters)

        result = await self._client(portal).action("package_search", params)
        p = get_portal(portal)
        summaries = []
        for raw in result.get("results", []):
            ds = CkanDataset.model_validate(raw)
            formats = sorted({r.format.upper() for r in ds.resources if r.format})
            summaries.append(
                DatasetSummary(
                    dataset_id=ds.name,
                    title=ds.title or ds.name,
                    portal=portal,
                    formats=formats,
                    modified=ds.metadata_modified,
                    dataset_url=_dataset_url(p, ds),
                    organisation=_organisation(ds),
                    licence=_licence(ds),
                )
            )
        total = result.get("count")
        return DatasetSearch(
            total_matches={portal: int(total)} if total is not None else {},
            results=summaries,
        )

    async def get_dataset(self, dataset_id: str, portal: str = "data.gov.au") -> DatasetDetail:
        result = await self._client(portal).action("package_show", {"id": dataset_id})
        ds = CkanDataset.model_validate(result)
        p = get_portal(portal)
        resources = []
        for r in ds.resources:
            verdict, reason = assess_queryable(r, self.settings)
            resources.append(
                ResourceInfo(
                    resource_id=r.id,
                    name=r.name,
                    format=r.format,
                    size_bytes=r.size,
                    url=r.url,
                    datastore_active=r.datastore_active,
                    queryable=verdict,
                    queryable_reason=reason,
                )
            )
        await self._probe_sizes(resources)
        return DatasetDetail(
            dataset_id=ds.name,
            title=ds.title or ds.name,
            description=ds.notes,
            portal=portal,
            modified=ds.metadata_modified,
            resources=resources,
            dataset_url=_dataset_url(p, ds),
            organisation=_organisation(ds),
            licence=_licence(ds),
        )

    async def list_organizations(
        self, portal: str = "data.gov.au", q: str | None = None, limit: int = 20
    ) -> list[OrganizationSummary]:
        if portal == "all":
            return await self._fan_out_all_portals(
                "list_organizations",
                lambda p: self.list_organizations(p.id, q, limit),
            )

        # Not organization_list: CKAN caps it at 25 rows whenever all_fields is set, which
        # on data.gov.au is 25 of over a thousand publishers. The organization facet of a
        # zero-row search returns every publisher with a public dataset, and its count.
        result = await self._client(portal).action(
            "package_search",
            {"rows": 0, "facet.field": '["organization"]', "facet.limit": -1},
        )
        items = result.get("search_facets", {}).get("organization", {}).get("items", [])
        orgs = []
        for raw in items:
            name = raw.get("name", "")
            title = raw.get("display_name")
            if q and q.lower() not in f"{name} {title or ''}".lower():
                continue
            orgs.append(
                OrganizationSummary(
                    name=name,
                    title=title,
                    dataset_count=raw.get("count"),
                    portal=portal,
                )
            )
        orgs.sort(key=lambda o: o.dataset_count or 0, reverse=True)
        return orgs[: max(1, min(limit, self.settings.max_org_limit))]
