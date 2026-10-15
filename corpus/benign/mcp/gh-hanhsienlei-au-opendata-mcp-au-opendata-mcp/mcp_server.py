from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from au_opendata_mcp.deps import get_services
from au_opendata_mcp.errors import AuOpenDataError
from au_opendata_mcp.observability import ToolTimingMiddleware
from au_opendata_mcp.services import au_tools

mcp: FastMCP = FastMCP(
    name="au-opendata-mcp",
    instructions=(
        "Australian government open data. Typical workflow: search_datasets to find a "
        "dataset (or list_organizations to browse by publisher first), get_dataset to list "
        "its resources and see which are queryable, preview_resource to learn a resource's "
        "columns, then query_resource to ask the real question with SQL. list_portals shows "
        "which portals are available to search. Every result carries its source URL, "
        "publisher and licence — cite them."
    ),
)

mcp.add_middleware(ToolTimingMiddleware())


def _fail(exc: AuOpenDataError) -> ToolError:
    suffix = f" You can download the source directly: {exc.remedy_url}" if exc.remedy_url else ""
    return ToolError(f"{exc.message}.{suffix}")


@mcp.tool
async def list_portals() -> list[dict[str, Any]]:
    """List the Australian open data portals this server can query, with dataset counts.

    Call this when the user asks what data sources are available."""
    try:
        return [p.model_dump() for p in await get_services().catalog.list_portals()]
    except AuOpenDataError as exc:
        raise _fail(exc) from exc


@mcp.tool
async def search_datasets(
    q: str,
    portal: str = "data.gov.au",
    organisation: str | None = None,
    format: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search Australian government datasets by keyword.

    Args:
        q: Keywords, e.g. "bus stops", "rainfall", "hospital waiting times".
        portal: "data.gov.au" (federal, default), "data.sa.gov.au" (South Australia),
            or "all" to search both.
        organisation: Optional publisher name to filter by, as returned by list_organizations.
        format: Optional resource format filter, e.g. "CSV".
        limit: Maximum datasets to return, capped at 50.

    Returns total_matches, each portal's count of every matching dataset (use this for "how
    many" questions; results is only the first page), and results: each dataset's id, title,
    publisher, licence, available formats and URL. Follow up with get_dataset to see a
    dataset's individual resources."""
    try:
        search = await get_services().catalog.search_datasets(
            q=q, portal=portal, organisation=organisation, format=format, limit=limit
        )
        return search.model_dump()
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except AuOpenDataError as exc:
        raise _fail(exc) from exc


@mcp.tool
async def get_dataset(dataset_id: str, portal: str = "data.gov.au") -> dict[str, Any]:
    """Get one dataset's full metadata and its list of resources (files).

    Each resource reports `queryable`: "yes" means query_resource will work on it,
    "no" gives the reason (wrong format, or too large), "unknown" means the size could
    not be determined in advance. Use the resource_id of a queryable resource with
    preview_resource and query_resource.

    Args:
        dataset_id: The dataset name/id from search_datasets.
        portal: The portal the dataset came from."""
    try:
        return (await get_services().catalog.get_dataset(dataset_id, portal)).model_dump()
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except AuOpenDataError as exc:
        raise _fail(exc) from exc


@mcp.tool
async def list_organizations(
    portal: str = "data.gov.au", q: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    """List a portal's publishers with how many datasets each has, largest first.

    Only publishers with at least one public dataset are counted. The first result is the
    portal's largest publisher; use q to find a specific one beyond the limit.

    Args:
        portal: The portal to list publishers for.
        q: Optional case-insensitive substring filter, e.g. "bureau".
        limit: Maximum publishers to return, capped at 100."""
    try:
        orgs = await get_services().catalog.list_organizations(portal=portal, q=q, limit=limit)
        return [o.model_dump() for o in orgs]
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except AuOpenDataError as exc:
        raise _fail(exc) from exc


@mcp.tool
async def preview_resource(
    resource_id: str, portal: str = "data.gov.au", limit: int = 20
) -> dict[str, Any]:
    """Show a resource's columns, their types, a sample of rows, and the total row count.

    ALWAYS call this before query_resource: you cannot write correct SQL without first
    seeing the column names. Costs nothing for resources held in the portal's DataStore;
    for others it downloads and caches the file, which then makes the follow-up query free.

    Args:
        resource_id: From get_dataset's resources list.
        portal: The portal the resource belongs to.
        limit: Sample rows to return, capped at 20."""
    try:
        result = await get_services().query.preview_resource(resource_id, portal, limit)
        return result.model_dump()
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except AuOpenDataError as exc:
        raise _fail(exc) from exc


@mcp.tool
async def query_resource(
    resource_id: str, sql: str, portal: str = "data.gov.au", limit: int = 100
) -> dict[str, Any]:
    """Run a read-only SQL query over one tabular resource and get the rows back.

    The SQL dialect is DuckDB. The resource is always exposed as the table `t`,
    whatever the file was called. Only a single SELECT statement is permitted:
    no DDL, no DML, no reading other tables or files.

    Example:
        sql = "SELECT suburb, AVG(price) AS mean FROM t GROUP BY suburb ORDER BY mean DESC"

    Call preview_resource first to learn the column names. At most 100 rows are returned;
    `truncated` tells you whether there were more.

    Args:
        resource_id: From get_dataset's resources list. Must have queryable == "yes".
        sql: A single DuckDB SELECT over the table `t`.
        portal: The portal the resource belongs to.
        limit: Maximum rows to return, capped at 100."""
    try:
        result = await get_services().query.query_resource(resource_id, sql, portal, limit)
        return result.model_dump()
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except AuOpenDataError as exc:
        raise _fail(exc) from exc


@mcp.tool
def validate_abn(abn: str) -> dict[str, Any]:
    """Validate an Australian Business Number against the ATO's official checksum.

    Use this instead of judging an ABN yourself — the check is a deterministic
    modulus-89 calculation and guessing gets it wrong.

    Args:
        abn: 11 digits, with or without spaces or hyphens.

    Returns whether it is valid, the conventional "NN NNN NNN NNN" formatting if so,
    and the specific reason if not."""
    return au_tools.validate_abn(abn).model_dump()


@mcp.tool
def au_financial_year(date: str) -> dict[str, Any]:
    """Map a date to the Australian financial year, which runs 1 July to 30 June.

    Use this whenever a question involves an Australian financial year, rather than
    assuming a calendar year.

    Args:
        date: A date as YYYY-MM-DD.

    Returns e.g. label "FY2026–27" with its start and end dates."""
    try:
        return au_tools.au_financial_year(date).model_dump()
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
