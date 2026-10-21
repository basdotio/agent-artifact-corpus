"""Official MCP SDK adapter; no business logic or writes."""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from backend.domain import ApplianceCatalog

mcp = FastMCP("HomeResolve", host="127.0.0.1", port=8000, json_response=True)
catalog = ApplianceCatalog()
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)


@mcp.tool(annotations=READ_ONLY)
def find_appliance(query: str) -> dict:
    """Search fictional appliances by identifying details; blank queries are errors."""
    return catalog.find(query)


@mcp.tool(annotations=READ_ONLY)
def get_purchase_evidence(appliance_id: str) -> dict:
    """Return verified fictional purchase evidence or explicitly missing information."""
    return catalog.evidence(appliance_id)


@mcp.tool(annotations=READ_ONLY)
def evaluate_warranty(appliance_id: str, evaluation_date: str | None = None) -> dict:
    """Evaluate recorded coverage dates, never claim approval. Date defaults to server local today."""
    return catalog.warranty(appliance_id, evaluation_date)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
