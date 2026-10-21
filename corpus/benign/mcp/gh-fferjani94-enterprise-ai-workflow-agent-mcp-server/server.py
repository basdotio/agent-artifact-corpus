import logging
from collections.abc import Callable
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from enterprise_ai_workflow_agent.db.session import SessionLocal
from enterprise_ai_workflow_agent.mcp_server import services

logger = logging.getLogger(__name__)

mcp = FastMCP("OpsPilot Enterprise Data")

# Published in the tool schema (minimum/maximum) so models can see the allowed range.
# services._limit still enforces it as defense in depth.
Limit = Annotated[
    int,
    Field(ge=1, le=services.MAX_RESULTS,
          description=f"Maximum number of results, 1-{services.MAX_RESULTS}."),
]


def _run(operation: Callable[..., Any], *args: Any) -> Any:
    """Run a read-only lookup; expose validation messages, never internal exceptions."""
    try:
        with SessionLocal() as db:
            return operation(db, *args)
    except ValueError as exc:
        # Raised by services for invalid arguments; the messages are written for callers.
        raise ToolError(str(exc)) from None
    except Exception:
        logger.exception("Tool %s failed", operation.__name__)
        raise ToolError(
            "Internal error while reading data; the lookup was not completed."
        ) from None


@mcp.tool()
def search_accounts(query: str, limit: Limit = 10) -> list[dict]:
    """Search fictional SaaS customer accounts by name (read-only)."""
    return _run(services.search_accounts, query, limit)


@mcp.tool()
def get_account_tickets(account_id: int, limit: Limit = 10) -> list[dict]:
    """List support tickets for a customer account (read-only)."""
    return _run(services.get_account_tickets, account_id, limit)


@mcp.tool()
def get_ticket_details(ticket_id: int) -> dict:
    """Get the description, status and priority of a support ticket."""
    return _run(services.get_ticket_details, ticket_id)


@mcp.tool()
def get_product_information(product_id: int) -> dict:
    """Get the version and description of a SaaS product."""
    return _run(services.get_product_information, product_id)


@mcp.tool()
def search_knowledge(
    query: str, product_id: int | None = None, limit: Limit = 5
) -> list[dict]:
    """Search internal product documents using deterministic lexical ranking."""
    return _run(services.search_knowledge, query, product_id, limit)


def main() -> None:
    # stdio MCP transport: stdout is reserved for protocol messages.
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
