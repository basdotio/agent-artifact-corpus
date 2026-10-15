"""System domain sub-server: health status, diagnostics, and capabilities."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from taxcode_mcp.db import db
from taxcode_mcp.errors import tool_error

logger = logging.getLogger(__name__)

ANNOTATION_READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

system_server = FastMCP(
    "taxcode-system",
    instructions="System diagnostics and capabilities domain.",
)


@system_server.tool(
    name="get_health_status",
    description="Check the operational health of the taxcode server and DuckDB storage.",
    annotations=ANNOTATION_READ_ONLY,
    tags={"system", "health", "read_only"},
)
async def get_health_status() -> dict[str, Any]:
    """Verify connectivity to upstream service and database status."""
    from taxcode_mcp import server

    try:
        if server.client._custom_client is not None or "example.com" not in server.client.base_url:
            data = await server.client.request("GET", "health")
        else:
            data = {"status": "healthy", "mode": "duckdb_offline"}

        statutes_count, pubs_count = db.get_stats()

        return {
            "status": "success",
            "upstream": data,
            "database": {
                "backend": "DuckDB",
                "path": db.db_path,
                "statutes_indexed": statutes_count,
                "publications_indexed": pubs_count,
            },
        }
    except Exception as exc:
        failure = tool_error(exc)
    raise failure from None


@system_server.resource(
    "taxcode://reference/capabilities",
    name="system_capabilities",
    description="Return static system capabilities reference.",
)
def get_capabilities() -> str:
    return (
        "Tax Code MCP Server capabilities: US Title 26 (IRC), 26 CFR (Treasury Regulations), "
        "Puerto Rico CRI (Ley 1-2011), Act 60-2019 Incentives Code, DuckDB full-text search, "
        "and IRC § 937 / Treas. Reg. § 1.937-2(f) compliance calculators."
    )
