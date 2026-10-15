from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from au_opendata_mcp.config import get_settings
from au_opendata_mcp.deps import get_services
from au_opendata_mcp.errors import (
    AuOpenDataError,
    DownloadFailed,
    QueryTimeout,
    ResourceNotFound,
    ResourceNotQueryable,
    ResourceTooLarge,
    SqlRejected,
    UpstreamUnavailable,
)
from au_opendata_mcp.services import au_tools as au_tools_service

STATUS_FOR: dict[type[AuOpenDataError], int] = {
    ResourceNotFound: 404,
    ResourceNotQueryable: 422,
    ResourceTooLarge: 413,
    SqlRejected: 400,
    UpstreamUnavailable: 502,
    DownloadFailed: 502,
    QueryTimeout: 504,
}

# The service layer already clamps every limit against Settings. REST used to hardcode
# its own ceilings next to it (and leave QueryRequest.limit unbounded), so the two adapters
# disagreed about who owns the limit -- harmless while the numbers happened to match, and a
# silent divergence the moment a Settings default moved. FastAPI/pydantic evaluate these
# constraints at import time, so they are read once here rather than per request; Settings
# is itself lru_cached and read from the environment.
_LIMITS = get_settings()


def _default(preferred: int, ceiling: int) -> int:
    """A default can never exceed its own ceiling, however low the ceiling is configured."""
    return min(preferred, ceiling)


router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/portals")
async def portals() -> list[dict[str, Any]]:
    return [p.model_dump() for p in await get_services().catalog.list_portals()]


@router.get("/datasets")
async def datasets(
    q: str,
    portal: str = "data.gov.au",
    organisation: str | None = None,
    format: str | None = None,
    limit: int = Query(_default(20, _LIMITS.max_search_limit), ge=1, le=_LIMITS.max_search_limit),
) -> dict[str, Any]:
    search = await get_services().catalog.search_datasets(
        q=q, portal=portal, organisation=organisation, format=format, limit=limit
    )
    return search.model_dump()


@router.get("/datasets/{dataset_id}")
async def dataset(dataset_id: str, portal: str = "data.gov.au") -> dict[str, Any]:
    return (await get_services().catalog.get_dataset(dataset_id, portal)).model_dump()


@router.get("/organizations")
async def organizations(
    portal: str = "data.gov.au",
    q: str | None = None,
    limit: int = Query(_default(20, _LIMITS.max_org_limit), ge=1, le=_LIMITS.max_org_limit),
) -> list[dict[str, Any]]:
    orgs = await get_services().catalog.list_organizations(portal=portal, q=q, limit=limit)
    return [o.model_dump() for o in orgs]


class QueryRequest(BaseModel):
    sql: str
    portal: str = "data.gov.au"
    limit: int = Field(
        default=_default(100, _LIMITS.max_query_limit), ge=1, le=_LIMITS.max_query_limit
    )


@router.get("/resources/{resource_id}/preview")
async def preview(
    resource_id: str,
    portal: str = "data.gov.au",
    limit: int = Query(_default(20, _LIMITS.max_preview_limit), ge=1, le=_LIMITS.max_preview_limit),
) -> dict[str, Any]:
    result = await get_services().query.preview_resource(resource_id, portal, limit)
    return result.model_dump()


@router.post("/resources/{resource_id}/query")
async def query(resource_id: str, body: QueryRequest) -> dict[str, Any]:
    result = await get_services().query.query_resource(
        resource_id, body.sql, body.portal, body.limit
    )
    return result.model_dump()


tools_router = APIRouter(prefix="/api/tools", tags=["australian tools"])


@tools_router.get("/abn/{abn}")
async def abn(abn: str) -> dict[str, Any]:
    return au_tools_service.validate_abn(abn).model_dump()


@tools_router.get("/financial-year")
async def financial_year(date: str) -> dict[str, Any]:
    return au_tools_service.au_financial_year(date).model_dump()
