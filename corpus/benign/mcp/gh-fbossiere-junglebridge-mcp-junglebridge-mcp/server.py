"""Small STDIO protocol surface; WTTJ integration is not implemented yet."""

from typing import Literal

from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict


class ConnectionStatus(BaseModel):
    """Static scaffold status, never an assertion of API connectivity."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    status: Literal["not_implemented"] = "not_implemented"
    api_verified: Literal[False] = False
    detail: str = "WTTJ access is not implemented. No credentials are read or sent."


def create_server() -> FastMCP:
    """Create an isolated server for local use or tests."""
    server = FastMCP("JungleBridge MCP", mask_error_details=True)

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def get_connection_status() -> ConnectionStatus:
        """Return scaffold status only; does not verify or contact the WTTJ API."""
        return ConnectionStatus()

    return server
