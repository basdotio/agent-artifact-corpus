"""Lexware (lexoffice) MCP server.

Run locally over stdio:  uv run main.py
Requires the LEXWARE_API_KEY environment variable (https://app.lexware.de/addons/public-api).
"""

import logging
import os
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.lifespan import lifespan
from mcp.types import ToolAnnotations
from pydantic import Field

from lexware import DEFAULT_APP_URL, DEFAULT_BASE_URL, LexwareClient, LexwareError
from models import InvoiceDraft, build_invoice_payload

logger = logging.getLogger(__name__)

INSTRUCTIONS = """\
Tools for creating and inspecting invoices in Lexware Office (formerly lexoffice).

Workflow for creating an invoice:
1. If the recipient is an existing customer, call find_contacts and pass the contact id as
   address.contact_id. Otherwise provide a one-time address with at least name and country_code.
2. Call create_invoice. Invoices are created as editable drafts by default.
3. Only set finalize=true when the user explicitly asks for a finalized invoice. Finalizing assigns
   a legally binding invoice number and the invoice can no longer be edited or deleted.
All amounts are in EUR. Unit prices are net unless tax_type is 'gross'.
"""


def create_lexware_client() -> LexwareClient:
    api_key = os.environ.get("LEXWARE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "LEXWARE_API_KEY is not set. Create a key at https://app.lexware.de/addons/public-api."
        )
    return LexwareClient(api_key=api_key, base_url=os.environ.get("LEXWARE_BASE_URL", DEFAULT_BASE_URL))


@lifespan
async def lexware_lifespan(server: FastMCP) -> Any:
    async with create_lexware_client() as client:
        yield {"lexware": client}


mcp = FastMCP("Lexware", instructions=INSTRUCTIONS, lifespan=lexware_lifespan)


def get_client(ctx: Context) -> LexwareClient:
    return ctx.lifespan_context["lexware"]


def app_url() -> str:
    return os.environ.get("LEXWARE_APP_URL", DEFAULT_APP_URL)


def summarize_contact(contact: dict[str, Any]) -> dict[str, Any]:
    person = contact.get("person") or {}
    company = contact.get("company") or {}
    name = company.get("name") or " ".join(
        part for part in (person.get("firstName"), person.get("lastName")) if part
    )
    billing = ((contact.get("addresses") or {}).get("billing") or [None])[0]
    emails = contact.get("emailAddresses") or {}
    return {
        "id": contact.get("id"),
        "name": name,
        "customer_number": ((contact.get("roles") or {}).get("customer") or {}).get("number"),
        "email": next((addresses[0] for addresses in emails.values() if addresses), None),
        "billing_address": billing,
        "archived": contact.get("archived"),
    }


@mcp.tool(
    annotations=ToolAnnotations(
        title="Find Lexware contacts",
        read_only_hint=True,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def find_contacts(
    ctx: Context,
    name: Annotated[
        str | None, Field(min_length=3, description="Part of the contact name (min. 3 characters).")
    ] = None,
    email: Annotated[
        str | None, Field(min_length=3, description="Part of the email address (min. 3 characters).")
    ] = None,
    number: Annotated[int | None, Field(description="Exact customer number.")] = None,
    customers_only: Annotated[
        bool, Field(description="Only return contacts with the customer role (required for invoices).")
    ] = True,
    page: Annotated[int, Field(ge=0, description="Zero based result page.")] = 0,
) -> dict[str, Any]:
    """Search Lexware contacts to obtain the contact_id for an invoice recipient."""
    filters: dict[str, str] = {}
    if name:
        filters["name"] = name
    if email:
        filters["email"] = email
    if number is not None:
        filters["number"] = str(number)
    if customers_only:
        filters["customer"] = "true"

    try:
        result = await get_client(ctx).find_contacts(filters, page=page, size=25)
    except (LexwareError, httpx.HTTPError) as exc:
        raise ToolError(f"Contact search failed: {exc}") from exc

    return {
        "contacts": [summarize_contact(contact) for contact in result.get("content", [])],
        "page": result.get("number", page),
        "total_pages": result.get("totalPages"),
        "total_contacts": result.get("totalElements"),
    }


@mcp.tool(
    annotations=ToolAnnotations(
        title="Create Lexware invoice",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    )
)
async def create_invoice(
    ctx: Context,
    invoice: InvoiceDraft,
    finalize: Annotated[
        bool,
        Field(
            description=(
                "False (default) creates an editable draft. True creates a finalized invoice with "
                "status 'open' and a binding invoice number that cannot be edited or deleted. "
                "Only use true when the user explicitly confirmed it."
            )
        ),
    ] = False,
) -> dict[str, Any]:
    """Create an invoice in Lexware Office and return its id, number, status, totals and links.

    Each call creates a new invoice, so do not retry after a timeout without first checking
    Lexware for the invoice.
    """
    client = get_client(ctx)
    payload = build_invoice_payload(invoice)

    try:
        created = await client.create_invoice(payload, finalize=finalize)
    except LexwareError as exc:
        raise ToolError(f"Lexware rejected the invoice: {exc.message} (HTTP {exc.status_code})") from exc
    except httpx.TimeoutException as exc:
        raise ToolError(
            "The request to Lexware timed out. The invoice may still have been created; "
            "check https://app.lexware.de/vouchers before retrying."
        ) from exc
    except httpx.HTTPError as exc:
        raise ToolError(f"Could not reach Lexware: {exc}") from exc

    invoice_id = created["id"]
    summary: dict[str, Any] = {
        "id": invoice_id,
        "voucher_status": "open" if finalize else "draft",
        "view_url": f"{app_url()}/permalink/invoices/view/{invoice_id}",
        "edit_url": f"{app_url()}/permalink/invoices/edit/{invoice_id}",
    }

    # The create response only carries the id; fetch the invoice for number and totals.
    # The invoice already exists at this point, so a failure here must not surface as a
    # tool error, otherwise the caller might retry and create a duplicate.
    try:
        details = await client.get_invoice(invoice_id)
    except (LexwareError, httpx.HTTPError) as exc:
        logger.warning("Invoice %s created but could not be fetched: %s", invoice_id, exc)
        summary["warning"] = f"Invoice was created, but its details could not be loaded: {exc}"
        return summary

    summary.update(
        voucher_number=details.get("voucherNumber"),
        voucher_status=details.get("voucherStatus", summary["voucher_status"]),
        voucher_date=details.get("voucherDate"),
        recipient=(details.get("address") or {}).get("name"),
        total_price=details.get("totalPrice"),
    )
    return summary


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Lexware invoice",
        read_only_hint=True,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def get_invoice(
    ctx: Context,
    invoice_id: Annotated[UUID, Field(description="Lexware invoice id.")],
) -> dict[str, Any]:
    """Retrieve the full Lexware invoice, including line items, totals and status."""
    try:
        return await get_client(ctx).get_invoice(str(invoice_id))
    except LexwareError as exc:
        if exc.status_code == 404:
            raise ToolError(f"Invoice {invoice_id} not found.") from exc
        raise ToolError(f"Could not load invoice: {exc}") from exc
    except httpx.HTTPError as exc:
        raise ToolError(f"Could not reach Lexware: {exc}") from exc


if __name__ == "__main__":
    mcp.run()
