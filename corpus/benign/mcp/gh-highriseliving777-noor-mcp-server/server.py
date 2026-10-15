#!/usr/bin/env python3
"""Noor Governance MCP Server - Streamable HTTP transport."""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from noor_governance_mcp import mcp

ALLOWED_HOSTS = os.environ.get(
    "NOOR_ALLOWED_HOSTS",
    "noor-mcp-server.onrender.com,localhost,127.0.0.1,0.0.0.0",
).split(",")

try:
    from mcp.server.transport_security import TransportSecuritySettings
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=ALLOWED_HOSTS,
    )
    print("✅ DNS rebinding protection disabled; allowed hosts set")
except Exception as e:
    print(f"⚠️ Could not configure transport security: {e}")


async def health(request):
    return JSONResponse({
        "status": "ok",
        "server": "noor-governance",
        "version": "1.0.0",
        "transport": "streamable-http",
        "endpoint": "/mcp",
        "allowed_hosts": ALLOWED_HOSTS,
    })


async def glama_well_known(request):
    """Serve the Glama ownership verification file."""
    from starlette.responses import Response
    return Response(
        content='{"$schema": "https://glama.ai/mcp/schemas/connector.json", "claim": "glama_claim_NNji3nr9QzNoEX3rXAuhOieFj31GPJk6"}',
        media_type="application/json",
    )


child = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/health", health),
        Route("/.well-known/glama.json", glama_well_known),
        Mount("/", app=child),
    ],
    lifespan=lifespan,
)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8090))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
