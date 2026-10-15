"""Synthetic, local MCP server for the discovery demo. No credentials or external data."""

import sys
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

server = FastMCP("mcp-witness-invoice-example")
annotations = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

if "--breaking" in sys.argv:

    @server.tool(annotations=annotations)
    def lookup_invoice(invoice_id: str, workspace: str) -> dict:
        """Read one invoice from the current workspace."""
        return {"invoice_id": invoice_id, "total": 42, "workspace": workspace}

    @server.tool(annotations=annotations)
    def list_invoices(status: Literal["paid"]) -> list[dict]:
        """List invoices by their payment status."""
        return [{"invoice_id": "demo-001", "status": status}]

else:

    @server.tool(annotations=annotations)
    def lookup_invoice(invoice_id: str) -> dict:
        """Read one invoice from the current workspace."""
        return {"invoice_id": invoice_id, "amount": 42}

    @server.tool(annotations=annotations)
    def list_invoices(status: Literal["pending", "paid"]) -> list[dict]:
        """List invoices by their payment status."""
        return [{"invoice_id": "demo-001", "status": status}]


if __name__ == "__main__":
    server.run(transport="stdio")
