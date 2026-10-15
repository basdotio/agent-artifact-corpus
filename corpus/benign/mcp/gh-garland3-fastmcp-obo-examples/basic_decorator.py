"""FastMCP tool that reads a downstream token inside the function body.

Run with the variables in ``.env.example`` set:

    uv run python examples/basic_decorator.py
"""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.auth.providers.azure import AzureJWTVerifier

from fastmcp_obo import EntraOBO, get_obo_token, with_obo_token


def create_server(obo: EntraOBO) -> FastMCP:
    """Build a server that validates Entra tokens and exchanges them per call."""

    mcp = FastMCP(
        "My MCP",
        auth=AzureJWTVerifier(
            client_id=obo.client_id,
            tenant_id=obo.tenant_id,
            required_scopes=["access_as_user"],
        ),
    )

    @mcp.tool
    @with_obo_token(obo)
    async def get_data(city: str) -> str:
        """Look up a city for the signed-in user."""

        token = get_obo_token()
        return await call_api(city, token)

    return mcp


async def call_api(city: str, token: str) -> str:
    """Stand-in for the downstream call. Replace this with the real API."""

    return f"{city}:{len(token)}"


def main() -> None:
    create_server(EntraOBO.from_env()).run(transport="http")


if __name__ == "__main__":
    main()
