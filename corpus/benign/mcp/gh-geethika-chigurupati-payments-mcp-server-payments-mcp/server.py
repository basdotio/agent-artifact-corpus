"""FastMCP server exposing a mock payments ledger as tools for AI agents.

Run over stdio (local dev):    REQUIRE_AUTH=false python -m payments_mcp.server
Run over HTTP (with JWT auth): PAYMENTS_JWT_SECRET=... python -m payments_mcp.server --http
"""
import argparse
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from pydantic import Field

from . import config
from .auth import READ_SCOPE, WRITE_SCOPE, AuthError, claims_from_headers, require_scope
from .ledger import Ledger, PaymentError

mcp = FastMCP(
    "payments-mcp-server",
    instructions=(
        "Mock payments API. Amounts are decimal strings such as '19.99'. "
        "Always send a unique idempotency_key when creating a payment so retries are safe."
    ),
)
ledger = Ledger()


def _authorize(scope: str) -> None:
    """Check the bearer token on the current HTTP request. No-op when auth is disabled."""
    if not config.auth_required():
        return
    try:
        headers = get_http_headers(include={"authorization"})
        claims = claims_from_headers(headers, config.jwt_secret())
        require_scope(claims, scope)
    except AuthError as exc:
        raise ToolError(f"unauthorized: {exc}") from exc


@mcp.tool
def create_payment(
    amount: Annotated[str, Field(description="Decimal string, e.g. '19.99' (max 2 decimals)")],
    currency: Annotated[str, Field(description="One of USD, EUR, GBP")],
    idempotency_key: Annotated[str, Field(description="Unique key; repeating it is safe")],
    description: Annotated[str, Field(description="Short note, up to 200 characters")] = "",
) -> dict:
    """Create a payment. Repeating the same request with the same key returns the original."""
    _authorize(WRITE_SCOPE)
    try:
        payment, created = ledger.create_payment(amount, currency, description, idempotency_key)
    except PaymentError as exc:
        raise ToolError(str(exc)) from exc
    return {"created": created, "payment": payment.model_dump(mode="json")}


@mcp.tool
def get_payment(payment_id: str) -> dict:
    """Look up a payment and its refund status."""
    _authorize(READ_SCOPE)
    try:
        return ledger.get_payment(payment_id).model_dump(mode="json")
    except PaymentError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool
def refund_payment(
    payment_id: str,
    amount: Annotated[
        str | None, Field(description="Decimal string; omit to refund the remaining balance")
    ] = None,
) -> dict:
    """Refund part or all of a payment's remaining balance."""
    _authorize(WRITE_SCOPE)
    try:
        return ledger.refund_payment(payment_id, amount).model_dump(mode="json")
    except PaymentError as exc:
        raise ToolError(str(exc)) from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="serve over HTTP instead of stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.http:
        if config.auth_required():
            config.jwt_secret()  # fail fast if the secret is missing or too short
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
