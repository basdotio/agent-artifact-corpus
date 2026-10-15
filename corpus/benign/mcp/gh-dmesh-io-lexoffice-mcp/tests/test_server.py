import json

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

import lexware
import main
from lexware import LexwareClient

INVOICE_ID = "e9066f04-8cc7-4616-93f8-ac9ecc8479c8"
INVOICE = {
    "id": INVOICE_ID,
    "voucherStatus": "draft",
    "voucherNumber": "RE1019",
    "voucherDate": "2023-02-22T00:00:00.000+01:00",
    "address": {"name": "Bike & Ride GmbH"},
    "totalPrice": {"currency": "EUR", "totalNetAmount": 200.0, "totalGrossAmount": 238.0, "totalTaxAmount": 38.0},
}
INVOICE_ARGS = {
    "invoice": {
        "address": {"name": "Bike & Ride GmbH", "country_code": "DE"},
        "voucher_date": "2023-02-22",
        "line_items": [
            {"name": "Beratung", "quantity": 2, "unit_name": "Stunde", "unit_price": 100, "tax_rate_percentage": 19}
        ],
    }
}


class FakeLexware:
    """Records requests and replays queued responses per (method, path)."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.responses: dict[tuple[str, str], list[httpx.Response]] = {}

    def queue(self, method: str, path: str, *responses: httpx.Response) -> None:
        self.responses.setdefault((method, path), []).extend(responses)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        queued = self.responses.get((request.method, request.url.path))
        if not queued:
            return httpx.Response(404, json={"message": "not mocked"})
        return queued.pop(0)


@pytest.fixture
def lexware_api(monkeypatch) -> FakeLexware:
    fake = FakeLexware()
    monkeypatch.setattr(lexware, "MIN_REQUEST_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(lexware, "RATE_LIMIT_BACKOFF_SECONDS", 0)
    monkeypatch.setattr(
        main,
        "create_lexware_client",
        lambda: LexwareClient(api_key="test-key", transport=httpx.MockTransport(fake.handler)),
    )
    return fake


@pytest.fixture
async def client(lexware_api):
    async with Client(main.mcp) as mcp_client:
        yield mcp_client


async def test_lists_tools_with_annotations(client):
    tools = {tool.name: tool for tool in await client.list_tools()}

    assert set(tools) == {"create_invoice", "find_contacts", "get_invoice"}
    assert tools["create_invoice"].annotations.read_only_hint is False
    assert tools["get_invoice"].annotations.read_only_hint is True


async def test_create_invoice_creates_draft_and_returns_summary(client, lexware_api):
    lexware_api.queue("POST", "/v1/invoices", httpx.Response(201, json={"id": INVOICE_ID, "version": 1}))
    lexware_api.queue("GET", f"/v1/invoices/{INVOICE_ID}", httpx.Response(200, json=INVOICE))

    result = await client.call_tool("create_invoice", INVOICE_ARGS)

    post = lexware_api.requests[0]
    assert post.headers["Authorization"] == "Bearer test-key"
    assert "finalize" not in post.url.params
    body = json.loads(post.content)
    assert body["address"] == {"name": "Bike & Ride GmbH", "countryCode": "DE"}
    assert body["lineItems"][0]["unitPrice"] == {"currency": "EUR", "netAmount": 100.0, "taxRatePercentage": 19.0}
    assert result.structured_content == {
        "id": INVOICE_ID,
        "voucher_status": "draft",
        "voucher_number": "RE1019",
        "voucher_date": "2023-02-22T00:00:00.000+01:00",
        "recipient": "Bike & Ride GmbH",
        "total_price": INVOICE["totalPrice"],
        "view_url": f"https://app.lexware.de/permalink/invoices/view/{INVOICE_ID}",
        "edit_url": f"https://app.lexware.de/permalink/invoices/edit/{INVOICE_ID}",
    }


async def test_create_invoice_finalize_sets_query_parameter(client, lexware_api):
    lexware_api.queue("POST", "/v1/invoices", httpx.Response(201, json={"id": INVOICE_ID}))
    lexware_api.queue("GET", f"/v1/invoices/{INVOICE_ID}", httpx.Response(200, json=INVOICE | {"voucherStatus": "open"}))

    result = await client.call_tool("create_invoice", INVOICE_ARGS | {"finalize": True})

    assert lexware_api.requests[0].url.params["finalize"] == "true"
    assert result.structured_content["voucher_status"] == "open"


async def test_create_invoice_retries_on_rate_limit(client, lexware_api):
    lexware_api.queue(
        "POST",
        "/v1/invoices",
        httpx.Response(429, json={"message": "Rate limit exceeded"}),
        httpx.Response(201, json={"id": INVOICE_ID}),
    )
    lexware_api.queue("GET", f"/v1/invoices/{INVOICE_ID}", httpx.Response(200, json=INVOICE))

    result = await client.call_tool("create_invoice", INVOICE_ARGS)

    assert [request.method for request in lexware_api.requests] == ["POST", "POST", "GET"]
    assert result.structured_content["voucher_number"] == "RE1019"


async def test_create_invoice_does_not_retry_server_errors(client, lexware_api):
    lexware_api.queue("POST", "/v1/invoices", httpx.Response(500, json={"message": "Internal server error"}))

    with pytest.raises(ToolError, match="Internal server error"):
        await client.call_tool("create_invoice", INVOICE_ARGS)
    assert len(lexware_api.requests) == 1


async def test_create_invoice_surfaces_validation_details(client, lexware_api):
    lexware_api.queue(
        "POST",
        "/v1/invoices",
        httpx.Response(
            406,
            json={
                "message": "Validation failed for request.",
                "details": [{"violation": "NOTNULL", "field": "lineItems[0].unitPrice", "message": "darf nicht leer sein"}],
            },
        ),
    )

    with pytest.raises(ToolError, match=r"lineItems\[0\]\.unitPrice: darf nicht leer sein"):
        await client.call_tool("create_invoice", INVOICE_ARGS)


async def test_create_invoice_reports_success_when_details_fetch_fails(client, lexware_api):
    lexware_api.queue("POST", "/v1/invoices", httpx.Response(201, json={"id": INVOICE_ID}))
    lexware_api.queue("GET", f"/v1/invoices/{INVOICE_ID}", httpx.Response(503, text="unavailable"))

    result = await client.call_tool("create_invoice", INVOICE_ARGS)

    assert result.structured_content["id"] == INVOICE_ID
    assert "could not be loaded" in result.structured_content["warning"]


async def test_create_invoice_rejects_invalid_input_without_calling_api(client, lexware_api):
    args = {"invoice": INVOICE_ARGS["invoice"] | {"address": {"name": "No country"}}}

    with pytest.raises(ToolError):
        await client.call_tool("create_invoice", args)
    assert lexware_api.requests == []


async def test_find_contacts_returns_compact_results(client, lexware_api):
    lexware_api.queue(
        "GET",
        "/v1/contacts",
        httpx.Response(
            200,
            json={
                "content": [
                    {
                        "id": "313ef116-a432-4823-9dfe-1b1200eb458a",
                        "roles": {"customer": {"number": 10309}},
                        "person": {"firstName": "Max", "lastName": "Mustermann"},
                        "emailAddresses": {"business": ["max@example.com"]},
                        "addresses": {"billing": [{"street": "Weg 1", "zip": "10115", "city": "Berlin", "countryCode": "DE"}]},
                        "archived": False,
                    }
                ],
                "number": 0,
                "totalPages": 1,
                "totalElements": 1,
            },
        ),
    )

    result = await client.call_tool("find_contacts", {"name": "Mustermann"})

    params = lexware_api.requests[0].url.params
    assert params["name"] == "Mustermann"
    assert params["customer"] == "true"
    assert result.structured_content["contacts"] == [
        {
            "id": "313ef116-a432-4823-9dfe-1b1200eb458a",
            "name": "Max Mustermann",
            "customer_number": 10309,
            "email": "max@example.com",
            "billing_address": {"street": "Weg 1", "zip": "10115", "city": "Berlin", "countryCode": "DE"},
            "archived": False,
        }
    ]


async def test_get_invoice_not_found(client, lexware_api):
    with pytest.raises(ToolError, match="not found"):
        await client.call_tool("get_invoice", {"invoice_id": INVOICE_ID})
