"""FastMCP tools that receive a downstream token or HTTP client by dependency.

``@mcp.tool`` must be the outer decorator. Injected parameters use a default
that FastMCP recognizes as a dependency, so they stay out of the tool schema.

    uv run python examples/dependency_injection.py
"""

from __future__ import annotations

import httpx2
from fastmcp import FastMCP
from fastmcp.dependencies import Depends
from fastmcp.server.auth.providers.azure import AzureJWTVerifier

from fastmcp_obo import EntraOBO, check_downstream_response


def create_server(obo: EntraOBO) -> FastMCP:
    """Build a server whose tools receive downstream credentials from FastMCP."""

    mcp = FastMCP(
        "My MCP",
        auth=AzureJWTVerifier(
            client_id=obo.client_id,
            tenant_id=obo.tenant_id,
            required_scopes=["access_as_user"],
        ),
    )

    @mcp.tool
    async def get_data(
        api: httpx2.AsyncClient = obo.http_client("https://api.example.com"),
    ) -> dict[str, object]:
        """Fetch the signed-in user's data from the downstream API."""

        response = await api.get("/data")
        check_downstream_response(response)
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return {"value": payload}

    @mcp.tool
    async def token_length(token: str = Depends(obo)) -> int:
        """Return the length of the downstream access token."""

        return len(token)

    return mcp


def main() -> None:
    create_server(EntraOBO.from_env()).run(transport="http")


if __name__ == "__main__":
    main()
