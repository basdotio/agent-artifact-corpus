"""LedgerFlow MCP tools. Run with `python -m mcp_server.server` for stdio.

For Streamable HTTP, run `mcp dev mcp_server/server.py` or mount the MCP ASGI app
at /mcp in the host application using the MCP SDK's streamable HTTP transport.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.schemas import PaymentAction
from services.document_extractor import extract_document
from services.payments_agent import execute_payment
from services.tabpfn_forecaster import run_forecast
from services.storage import storage

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise SystemExit("Install backend dependencies with: pip install -e .") from exc

mcp = FastMCP("LedgerFlow MCP", stateless_http=True, json_response=True)
allowed_hosts=os.getenv("MCP_ALLOWED_HOSTS","").strip()
if allowed_hosts and getattr(mcp.settings,"transport_security",None):
    mcp.settings.transport_security.allowed_hosts=[host.strip() for host in allowed_hosts.split(",") if host.strip()]


@mcp.tool()
async def extract_invoice(text: str = "", load_sample: bool = False) -> dict:
    """Extract a structured invoice from text, or import the five sample invoices."""
    invoices, provider, trace_id = await extract_document(text=text, load_sample=load_sample)
    saved = [storage.save_invoice(item.model_dump(mode="json")) for item in invoices]
    return {"invoices":saved,"provider":provider,"trace_id":trace_id}


@mcp.tool()
def forecast_runway_tabpfn(rows: list[dict] | None = None) -> dict:
    """Forecast net cash flow at 30, 60 and 90 days with uncertainty bands."""
    return run_forecast(rows).model_dump(mode="json")


@mcp.tool()
def audit_vendor_anomalies(rows: list[dict] | None = None) -> list[dict]:
    """Return duplicate, amount-spike and overdue payment risk findings."""
    return run_forecast(rows).anomalies


@mcp.tool()
async def create_agentic_payment_link(provider: str, amount: float, currency: str = "USD", description: str = "LedgerFlow payment", recipient_email: str = "") -> dict:
    """Create a sandbox payment link/order. Requires configured sandbox credentials."""
    action=PaymentAction(provider=provider,amount=amount,currency=currency,description=description,recipient_email=recipient_email)
    return await execute_payment(action)


def main():
    transport=os.getenv("MCP_TRANSPORT","stdio")
    if transport=="streamable-http":
        mcp.settings.host=os.getenv("MCP_HOST","0.0.0.0")
        mcp.settings.port=int(os.getenv("MCP_PORT","8001"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__=="__main__": main()
